"""Batch processing for parallel task execution using worktrees.

This module provides parallel task processing by spawning multiple
independent worktrees, each running its own RALPH loop.

Design Principles:
- True parallelism via multiprocessing (not threads)
- Each worker manages its own worktree
- Progress tracked via filesystem for cross-process communication
- Configurable parallelism limit to manage resources
"""

from __future__ import annotations

import json
import logging
import multiprocessing
import os
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from ralph_agi.core.config import RalphConfig
    from ralph_agi.tasks.prd import PRD

logger = logging.getLogger(__name__)

# Default parallelism
DEFAULT_PARALLEL_LIMIT = 3
PROGRESS_DIR_NAME = ".ralph-batch"
PROGRESS_FILE_SUFFIX = ".progress.json"


class WorkerStatus(Enum):
    """Status of a batch worker."""

    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchConfig:
    """Configuration for batch processing.

    Attributes:
        parallel_limit: Maximum number of parallel workers.
        worktree_base: Base directory for worktrees.
        progress_dir: Directory for progress files.
        cleanup_on_complete: If True, cleanup worktrees after successful completion.
        cleanup_on_failure: If True, cleanup worktrees after failure.
    """

    parallel_limit: int = DEFAULT_PARALLEL_LIMIT
    worktree_base: Optional[Path] = None
    progress_dir: Optional[Path] = None
    cleanup_on_complete: bool = True
    cleanup_on_failure: bool = False


@dataclass
class WorkerProgress:
    """Progress information for a single worker.

    Attributes:
        task_id: ID of the task being worked on.
        worker_id: Unique identifier for this worker.
        status: Current status of the worker.
        worktree_path: Path to the worker's worktree.
        branch_name: Git branch for this worker.
        iteration: Current iteration number.
        max_iterations: Maximum iterations configured.
        started_at: When the worker started.
        updated_at: Last update timestamp.
        completed_at: When the worker completed (if applicable).
        error: Error message if failed.
        output: Final output or result message.
    """

    task_id: str
    worker_id: str
    status: WorkerStatus = WorkerStatus.PENDING
    worktree_path: Optional[str] = None
    branch_name: Optional[str] = None
    iteration: int = 0
    max_iterations: int = 100
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    output: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "status": self.status.value,
            "worktree_path": self.worktree_path,
            "branch_name": self.branch_name,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "output": self.output,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkerProgress:
        """Create from dictionary."""
        return cls(
            task_id=data["task_id"],
            worker_id=data["worker_id"],
            status=WorkerStatus(data.get("status", "pending")),
            worktree_path=data.get("worktree_path"),
            branch_name=data.get("branch_name"),
            iteration=data.get("iteration", 0),
            max_iterations=data.get("max_iterations", 100),
            started_at=data.get("started_at"),
            updated_at=data.get("updated_at"),
            completed_at=data.get("completed_at"),
            error=data.get("error"),
            output=data.get("output"),
        )


@dataclass
class BatchProgress:
    """Aggregate progress for a batch run.

    Attributes:
        batch_id: Unique identifier for this batch.
        total_tasks: Total number of tasks to process.
        workers: Progress for each worker.
        started_at: When the batch started.
        completed_at: When the batch completed.
    """

    batch_id: str
    total_tasks: int
    workers: dict[str, WorkerProgress] = field(default_factory=dict)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @property
    def pending_count(self) -> int:
        """Count of pending workers."""
        return sum(1 for w in self.workers.values() if w.status == WorkerStatus.PENDING)

    @property
    def running_count(self) -> int:
        """Count of running workers."""
        return sum(1 for w in self.workers.values() if w.status in (
            WorkerStatus.STARTING, WorkerStatus.RUNNING
        ))

    @property
    def completed_count(self) -> int:
        """Count of completed workers."""
        return sum(1 for w in self.workers.values() if w.status == WorkerStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        """Count of failed workers."""
        return sum(1 for w in self.workers.values() if w.status == WorkerStatus.FAILED)

    @property
    def is_complete(self) -> bool:
        """Check if all workers have finished."""
        return all(
            w.status in (WorkerStatus.COMPLETED, WorkerStatus.FAILED, WorkerStatus.CANCELLED)
            for w in self.workers.values()
        )


def _run_worker(
    task_id: str,
    worker_id: str,
    prd_path: str,
    config_path: str,
    worktree_path: str,
    branch_name: str,
    progress_dir: str,
    max_iterations: int,
) -> None:
    """Worker function that runs in a subprocess.

    Creates a worktree and runs an independent RALPH loop.

    Args:
        task_id: ID of the task to work on.
        worker_id: Unique worker identifier.
        prd_path: Path to the PRD.json file (in main repo).
        config_path: Path to config.yaml file.
        worktree_path: Path where worktree should be created.
        branch_name: Git branch name for the worktree.
        progress_dir: Directory for progress files.
        max_iterations: Maximum iterations for the loop.
    """
    import shutil

    progress_file = Path(progress_dir) / f"{worker_id}{PROGRESS_FILE_SUFFIX}"

    def update_progress(
        status: WorkerStatus,
        iteration: int = 0,
        error: Optional[str] = None,
        output: Optional[str] = None,
    ) -> None:
        """Update progress file atomically."""
        progress = WorkerProgress(
            task_id=task_id,
            worker_id=worker_id,
            status=status,
            worktree_path=worktree_path,
            branch_name=branch_name,
            iteration=iteration,
            max_iterations=max_iterations,
            started_at=datetime.now(timezone.utc).isoformat() if status == WorkerStatus.STARTING else None,
            updated_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat() if status in (
                WorkerStatus.COMPLETED, WorkerStatus.FAILED
            ) else None,
            error=error,
            output=output,
        )

        # Read existing progress to preserve started_at
        if progress_file.exists():
            try:
                with open(progress_file) as f:
                    existing = json.load(f)
                    if existing.get("started_at"):
                        progress.started_at = existing["started_at"]
            except Exception:
                pass

        # Write atomically
        temp_file = progress_file.with_suffix(".tmp")
        with open(temp_file, "w") as f:
            json.dump(progress.to_dict(), f, indent=2)
        temp_file.rename(progress_file)

    try:
        update_progress(WorkerStatus.STARTING)

        # Create worktree
        from ralph_agi.tools.git import GitTools

        # Get repo path from PRD location
        prd_file = Path(prd_path)
        repo_path = prd_file.parent

        git = GitTools(repo_path=repo_path)
        git.worktree_add(
            path=worktree_path,
            branch=branch_name,
            create_branch=True,
            base_ref="HEAD",
        )

        logger.info(f"Worker {worker_id}: Created worktree at {worktree_path}")

        # Copy PRD to worktree (so loop can modify it independently)
        worktree_prd = Path(worktree_path) / prd_file.name
        shutil.copy2(prd_path, worktree_prd)

        update_progress(WorkerStatus.RUNNING, iteration=0)

        # Load config and create loop
        from ralph_agi.core.config import load_config
        from ralph_agi.core.loop import RalphLoop

        config = load_config(config_path)

        # Create loop with worktree PRD
        loop = RalphLoop.from_config(config, prd_path=str(worktree_prd))

        # Run the loop with iteration tracking
        completed = False
        try:
            # Run loop - we can't easily inject iteration callbacks
            # so we just run and check result
            completed = loop.run(handle_signals=False)
            update_progress(
                WorkerStatus.COMPLETED,
                iteration=loop.iteration,
                output=f"Completed in {loop.iteration} iterations",
            )
        except Exception as e:
            update_progress(
                WorkerStatus.FAILED,
                iteration=loop.iteration,
                error=str(e),
            )
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Worker {worker_id} failed: {e}")
        update_progress(WorkerStatus.FAILED, error=str(e))


class BatchExecutor:
    """Parallel batch processor for RALPH tasks.

    Spawns multiple worktrees and runs independent loops in each,
    tracking aggregate progress across all workers.

    Example:
        >>> from ralph_agi.tasks.batch import BatchExecutor, BatchConfig
        >>> config = BatchConfig(parallel_limit=3)
        >>> executor = BatchExecutor(
        ...     prd_path=Path("PRD.json"),
        ...     config_path=Path("config.yaml"),
        ...     batch_config=config,
        ... )
        >>> progress = executor.run()
        >>> print(f"Completed: {progress.completed_count}/{progress.total_tasks}")
    """

    def __init__(
        self,
        prd_path: Path,
        config_path: Path,
        batch_config: Optional[BatchConfig] = None,
        repo_path: Optional[Path] = None,
    ):
        """Initialize the batch executor.

        Args:
            prd_path: Path to the PRD.json file.
            config_path: Path to the config.yaml file.
            batch_config: Batch processing configuration.
            repo_path: Path to the git repository. Defaults to PRD parent.
        """
        self._prd_path = Path(prd_path).resolve()
        self._config_path = Path(config_path).resolve()
        self._batch_config = batch_config or BatchConfig()
        self._repo_path = Path(repo_path).resolve() if repo_path else self._prd_path.parent

        # Set up paths
        self._worktree_base = self._batch_config.worktree_base or self._repo_path.parent
        self._progress_dir = self._batch_config.progress_dir or (
            self._repo_path / PROGRESS_DIR_NAME
        )

        # Track workers
        self._workers: dict[str, multiprocessing.Process] = {}
        self._batch_progress: Optional[BatchProgress] = None

    def run(
        self,
        task_ids: Optional[list[str]] = None,
        max_iterations: int = 100,
        on_progress: Optional[Callable[[BatchProgress], None]] = None,
        poll_interval: float = 2.0,
    ) -> BatchProgress:
        """Run batch processing.

        Args:
            task_ids: Specific task IDs to process. If None, processes
                     all ready tasks from PRD.
            max_iterations: Maximum iterations per worker.
            on_progress: Optional callback for progress updates.
            poll_interval: Seconds between progress polls.

        Returns:
            Final BatchProgress with all worker results.
        """
        from uuid import uuid4

        from ralph_agi.tasks.prd import load_prd
        from ralph_agi.tasks.selector import TaskSelector

        # Load PRD and get tasks
        prd = load_prd(self._prd_path)

        if task_ids is None:
            # Get all ready tasks
            selector = TaskSelector()
            task_ids = []
            while True:
                result = selector.select(prd)
                if result.next_task is None:
                    break
                task_ids.append(result.next_task.id)
                # Mark as in-progress to get next one
                # (This is a bit hacky - we're not actually modifying the PRD)
                prd = load_prd(self._prd_path)  # Reload to reset

            if not task_ids:
                logger.info("No ready tasks to process")
                return BatchProgress(
                    batch_id=str(uuid4())[:8],
                    total_tasks=0,
                    started_at=datetime.now(timezone.utc).isoformat(),
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )

        # Initialize batch progress
        batch_id = str(uuid4())[:8]
        self._batch_progress = BatchProgress(
            batch_id=batch_id,
            total_tasks=len(task_ids),
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        # Create progress directory
        self._progress_dir.mkdir(parents=True, exist_ok=True)

        # Initialize worker progress
        for task_id in task_ids:
            worker_id = f"{batch_id}-{task_id}"
            self._batch_progress.workers[worker_id] = WorkerProgress(
                task_id=task_id,
                worker_id=worker_id,
                status=WorkerStatus.PENDING,
            )

        logger.info(
            f"Starting batch {batch_id} with {len(task_ids)} tasks, "
            f"parallel_limit={self._batch_config.parallel_limit}"
        )

        # Process tasks with parallelism limit
        pending = list(task_ids)

        try:
            while pending or self._workers:
                # Start new workers up to limit
                while pending and len(self._workers) < self._batch_config.parallel_limit:
                    task_id = pending.pop(0)
                    self._start_worker(task_id, batch_id, max_iterations)

                # Poll for progress
                time.sleep(poll_interval)
                self._update_progress()

                # Check for completed workers
                completed_workers = []
                for worker_id, process in self._workers.items():
                    if not process.is_alive():
                        completed_workers.append(worker_id)

                for worker_id in completed_workers:
                    process = self._workers.pop(worker_id)
                    process.join()  # Ensure cleanup

                # Notify callback
                if on_progress:
                    on_progress(self._batch_progress)

        except KeyboardInterrupt:
            logger.warning("Batch interrupted - stopping workers")
            self._cancel_workers()

        # Final progress update
        self._update_progress()
        self._batch_progress.completed_at = datetime.now(timezone.utc).isoformat()

        # Cleanup if configured
        if self._batch_config.cleanup_on_complete:
            self._cleanup_completed_worktrees()

        return self._batch_progress

    def _start_worker(
        self,
        task_id: str,
        batch_id: str,
        max_iterations: int,
    ) -> None:
        """Start a worker process for a task.

        Args:
            task_id: ID of the task to process.
            batch_id: Batch identifier.
            max_iterations: Maximum iterations for the worker.
        """
        from ralph_agi.tasks.executor import _sanitize_branch_name

        worker_id = f"{batch_id}-{task_id}"
        safe_task_id = _sanitize_branch_name(task_id)

        worktree_path = str(self._worktree_base / f"ralph-batch-{safe_task_id}")
        branch_name = f"ralph/batch-{safe_task_id}"

        # Update progress
        if worker_id in self._batch_progress.workers:
            self._batch_progress.workers[worker_id].status = WorkerStatus.STARTING
            self._batch_progress.workers[worker_id].worktree_path = worktree_path
            self._batch_progress.workers[worker_id].branch_name = branch_name

        # Start subprocess
        process = multiprocessing.Process(
            target=_run_worker,
            args=(
                task_id,
                worker_id,
                str(self._prd_path),
                str(self._config_path),
                worktree_path,
                branch_name,
                str(self._progress_dir),
                max_iterations,
            ),
            name=f"ralph-worker-{task_id}",
        )
        process.start()
        self._workers[worker_id] = process

        logger.info(f"Started worker {worker_id} for task {task_id}")

    def _update_progress(self) -> None:
        """Update batch progress from worker progress files."""
        for worker_id in self._batch_progress.workers:
            progress_file = self._progress_dir / f"{worker_id}{PROGRESS_FILE_SUFFIX}"
            if progress_file.exists():
                try:
                    with open(progress_file) as f:
                        data = json.load(f)
                    self._batch_progress.workers[worker_id] = WorkerProgress.from_dict(data)
                except Exception as e:
                    logger.debug(f"Error reading progress for {worker_id}: {e}")

    def _cancel_workers(self) -> None:
        """Cancel all running workers."""
        for worker_id, process in self._workers.items():
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()

            # Update progress
            if worker_id in self._batch_progress.workers:
                self._batch_progress.workers[worker_id].status = WorkerStatus.CANCELLED

        self._workers.clear()

    def _cleanup_completed_worktrees(self) -> None:
        """Cleanup worktrees for completed workers."""
        from ralph_agi.tasks.cleanup import create_cleanup_manager

        cleanup = create_cleanup_manager(self._repo_path)

        for worker_id, progress in self._batch_progress.workers.items():
            if progress.status != WorkerStatus.COMPLETED:
                continue

            if not progress.worktree_path:
                continue

            worktree_path = Path(progress.worktree_path)
            if worktree_path.exists():
                result = cleanup.cleanup_worktree(worktree_path)
                if result.success:
                    logger.info(f"Cleaned up worktree for {worker_id}")
                else:
                    logger.warning(f"Failed to cleanup worktree for {worker_id}: {result.error}")

    def get_progress(self) -> Optional[BatchProgress]:
        """Get current batch progress.

        Returns:
            Current BatchProgress or None if not running.
        """
        if self._batch_progress:
            self._update_progress()
        return self._batch_progress


def format_batch_progress(progress: BatchProgress) -> str:
    """Format batch progress for display.

    Args:
        progress: BatchProgress to format.

    Returns:
        Formatted string for terminal display.
    """
    lines = [
        f"Batch {progress.batch_id}: {progress.total_tasks} tasks",
        f"  Running: {progress.running_count}  "
        f"Completed: {progress.completed_count}  "
        f"Failed: {progress.failed_count}  "
        f"Pending: {progress.pending_count}",
        "",
    ]

    for worker_id, worker in progress.workers.items():
        status_symbol = {
            WorkerStatus.PENDING: "⏳",
            WorkerStatus.STARTING: "🔄",
            WorkerStatus.RUNNING: "▶️",
            WorkerStatus.COMPLETED: "✅",
            WorkerStatus.FAILED: "❌",
            WorkerStatus.CANCELLED: "🚫",
        }.get(worker.status, "?")

        line = f"  {status_symbol} {worker.task_id}"
        if worker.status == WorkerStatus.RUNNING:
            line += f" (iteration {worker.iteration}/{worker.max_iterations})"
        elif worker.status == WorkerStatus.COMPLETED:
            line += f" - {worker.output or 'done'}"
        elif worker.status == WorkerStatus.FAILED:
            line += f" - {worker.error or 'failed'}"

        lines.append(line)

    return "\n".join(lines)
