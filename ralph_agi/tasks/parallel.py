"""Parallel Task Executor for RALPH-AGI.

Processes multiple tasks concurrently using git worktrees for isolation.
Each task runs in its own worktree, preventing conflicts and enabling
true parallel execution.

Usage:
    from ralph_agi.tasks.parallel import ParallelExecutor

    # Initialize executor
    executor = ParallelExecutor(
        project_root=Path("."),
        max_concurrent=3,
    )

    # Process all pending tasks
    results = await executor.run()

    # Or start processing in background
    executor.start()
    # ... later ...
    executor.stop()
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from ralph_agi.tasks.queue import (
    TaskQueue,
    QueuedTask,
    TaskStatus,
    TaskNotFoundError,
)
from ralph_agi.tasks.worktree import (
    WorktreeManager,
    ActiveWorktree,
    WorktreeError,
)

logger = logging.getLogger(__name__)


class ExecutionState(Enum):
    """State of the parallel executor."""

    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class TaskResult:
    """Result of executing a single task.

    Attributes:
        task_id: ID of the executed task
        success: Whether execution succeeded
        worktree_path: Path to the worktree where task ran
        branch: Git branch name
        started_at: When execution started
        completed_at: When execution completed
        error: Error message if failed
        pr_url: URL of created PR (if any)
        confidence: Confidence score from execution (0.0-1.0)
    """

    task_id: str
    success: bool
    worktree_path: Optional[Path] = None
    branch: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    pr_url: Optional[str] = None
    confidence: float = 0.0

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class ExecutionProgress:
    """Progress tracking for parallel execution.

    Attributes:
        total_tasks: Total number of tasks to process
        completed: Number of completed tasks
        failed: Number of failed tasks
        running: Number of currently running tasks
        pending: Number of pending tasks
        results: List of completed task results
    """

    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    running: int = 0
    pending: int = 0
    results: list[TaskResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.completed + self.failed == 0:
            return 0.0
        return self.completed / (self.completed + self.failed) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_tasks": self.total_tasks,
            "completed": self.completed,
            "failed": self.failed,
            "running": self.running,
            "pending": self.pending,
            "success_rate": f"{self.success_rate:.1f}%",
        }


class ParallelExecutor:
    """Executes multiple tasks in parallel using git worktrees.

    Each task is executed in its own isolated worktree, allowing
    concurrent development without merge conflicts.

    Example:
        executor = ParallelExecutor(
            project_root=Path("."),
            max_concurrent=3,
        )

        # Process all pending tasks (blocking)
        results = executor.run_sync()

        # Or use async
        results = await executor.run()

    Attributes:
        max_concurrent: Maximum number of concurrent tasks
        state: Current executor state
    """

    DEFAULT_MAX_CONCURRENT = 3
    DEFAULT_TASK_TIMEOUT = 3600  # 1 hour

    def __init__(
        self,
        project_root: Path | str | None = None,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        task_timeout: int = DEFAULT_TASK_TIMEOUT,
        task_callback: Optional[Callable[[QueuedTask, Path], TaskResult]] = None,
        on_task_start: Optional[Callable[[QueuedTask], None]] = None,
        on_task_complete: Optional[Callable[[TaskResult], None]] = None,
        on_progress: Optional[Callable[[ExecutionProgress], None]] = None,
    ):
        """Initialize parallel executor.

        Args:
            project_root: Root directory of the project (default: cwd)
            max_concurrent: Maximum concurrent tasks (default: 3)
            task_timeout: Timeout for each task in seconds (default: 3600)
            task_callback: Function to execute for each task
            on_task_start: Callback when task starts
            on_task_complete: Callback when task completes
            on_progress: Callback for progress updates
        """
        self._project_root = Path(project_root).resolve() if project_root else Path.cwd()
        self._max_concurrent = max_concurrent
        self._task_timeout = task_timeout

        # Callbacks
        self._task_callback = task_callback
        self._on_task_start = on_task_start
        self._on_task_complete = on_task_complete
        self._on_progress = on_progress

        # Initialize queue and worktree manager
        self._queue = TaskQueue(project_root=self._project_root)
        self._worktree_manager = WorktreeManager(repo_path=self._project_root)

        # Execution state
        self._state = ExecutionState.IDLE
        self._state_lock = threading.Lock()
        self._progress = ExecutionProgress()
        self._executor: Optional[ThreadPoolExecutor] = None
        self._running_futures: dict[str, Future] = {}
        self._stop_event = threading.Event()

        logger.debug(
            f"ParallelExecutor initialized: root={self._project_root}, "
            f"max_concurrent={max_concurrent}"
        )

    @property
    def state(self) -> ExecutionState:
        """Get current execution state."""
        return self._state

    @property
    def progress(self) -> ExecutionProgress:
        """Get current progress."""
        return self._progress

    @property
    def max_concurrent(self) -> int:
        """Get maximum concurrent tasks."""
        return self._max_concurrent

    @max_concurrent.setter
    def max_concurrent(self, value: int) -> None:
        """Set maximum concurrent tasks."""
        if value < 1:
            raise ValueError("max_concurrent must be at least 1")
        self._max_concurrent = value

    def _get_ready_tasks(self) -> list[QueuedTask]:
        """Get tasks ready for execution (no blocking dependencies).

        Returns:
            List of tasks ready to execute, sorted by priority
        """
        pending = self._queue.list(status="pending")
        ready = []

        for task in pending:
            if not task.dependencies:
                ready.append(task)
                continue

            # Check if all dependencies are complete
            all_deps_complete = True
            for dep_id in task.dependencies:
                try:
                    dep = self._queue.get(dep_id)
                    if dep.status != TaskStatus.COMPLETE:
                        all_deps_complete = False
                        break
                except TaskNotFoundError:
                    # Dependency doesn't exist - treat as satisfied
                    pass

            if all_deps_complete:
                ready.append(task)

        # Sort by priority (P0 first)
        ready.sort(key=lambda t: t.priority.value)
        return ready

    def _execute_task(self, task: QueuedTask) -> TaskResult:
        """Execute a single task in a worktree.

        Args:
            task: Task to execute

        Returns:
            TaskResult with execution outcome
        """
        started_at = datetime.now(timezone.utc)
        worktree_path: Optional[Path] = None
        branch: Optional[str] = None

        try:
            # Notify task start
            if self._on_task_start:
                self._on_task_start(task)

            # Update task status to running
            self._queue.update_status(task.id, "running")

            # Create worktree for this task
            worktree_path = self._worktree_manager.create(task.id)
            worktree = self._worktree_manager.get(task.id)
            branch = worktree.branch

            logger.info(f"TASK_START: {task.id} -> {worktree_path}")

            # Execute the task callback in the worktree
            if self._task_callback:
                result = self._worktree_manager.execute_in_worktree(
                    task.id,
                    lambda path: self._task_callback(task, path),
                )

                # Use returned result if it's a TaskResult
                if isinstance(result, TaskResult):
                    return result

            # Default success result
            completed_at = datetime.now(timezone.utc)
            return TaskResult(
                task_id=task.id,
                success=True,
                worktree_path=worktree_path,
                branch=branch,
                started_at=started_at,
                completed_at=completed_at,
                confidence=0.8,  # Default confidence for successful execution
            )

        except Exception as e:
            logger.error(f"TASK_FAILED: {task.id} - {e}")
            completed_at = datetime.now(timezone.utc)
            return TaskResult(
                task_id=task.id,
                success=False,
                worktree_path=worktree_path,
                branch=branch,
                started_at=started_at,
                completed_at=completed_at,
                error=str(e),
            )

    def _on_task_done(self, future: Future, task_id: str) -> None:
        """Handle task completion.

        Args:
            future: Completed future
            task_id: ID of completed task
        """
        try:
            result = future.result()

            # Update queue status
            if result.success:
                self._queue.update_status(
                    task_id,
                    "complete",
                    confidence=result.confidence,
                    pr_url=result.pr_url,
                )
                self._progress.completed += 1
            else:
                self._queue.update_status(
                    task_id,
                    "failed",
                    error=result.error,
                )
                self._progress.failed += 1

            self._progress.running -= 1
            self._progress.results.append(result)

            # Notify completion
            if self._on_task_complete:
                self._on_task_complete(result)

            # Update progress callback
            if self._on_progress:
                self._on_progress(self._progress)

            duration = result.duration_seconds
            duration_str = f"{duration:.1f}s" if duration is not None else "N/A"
            logger.info(
                f"TASK_COMPLETE: {task_id} success={result.success} "
                f"duration={duration_str}"
            )

        except Exception as e:
            logger.error(f"Error handling task completion for {task_id}: {e}")
            self._progress.failed += 1
            self._progress.running -= 1

        finally:
            # Remove from running futures
            self._running_futures.pop(task_id, None)

    def run_sync(self, max_tasks: Optional[int] = None) -> list[TaskResult]:
        """Run task processing synchronously.

        Processes pending tasks until all complete or max_tasks reached.

        Args:
            max_tasks: Maximum number of tasks to process (None = all)

        Returns:
            List of TaskResults
        """
        return asyncio.run(self.run(max_tasks))

    async def run(self, max_tasks: Optional[int] = None) -> list[TaskResult]:
        """Run task processing asynchronously.

        Processes pending tasks until all complete or max_tasks reached.

        Args:
            max_tasks: Maximum number of tasks to process (None = all)

        Returns:
            List of TaskResults
        """
        with self._state_lock:
            if self._state == ExecutionState.RUNNING:
                raise RuntimeError("Executor is already running")
            self._state = ExecutionState.RUNNING

        self._stop_event.clear()
        self._progress = ExecutionProgress()
        self._executor = ThreadPoolExecutor(max_workers=self._max_concurrent)
        self._running_futures = {}

        try:
            # Count total pending tasks
            ready_tasks = self._get_ready_tasks()
            if max_tasks:
                ready_tasks = ready_tasks[:max_tasks]
            self._progress.total_tasks = len(ready_tasks)
            self._progress.pending = len(ready_tasks)

            logger.info(f"PARALLEL_START: {len(ready_tasks)} tasks, max_concurrent={self._max_concurrent}")

            tasks_started = 0

            while not self._stop_event.is_set():
                # Check if we've processed enough tasks
                if max_tasks and tasks_started >= max_tasks:
                    break

                # Get ready tasks
                ready = self._get_ready_tasks()
                if max_tasks:
                    remaining = max_tasks - tasks_started
                    ready = ready[:remaining]

                # No more tasks and nothing running - we're done
                if not ready and not self._running_futures:
                    break

                # Submit new tasks up to concurrency limit
                slots_available = self._max_concurrent - len(self._running_futures)
                for task in ready[:slots_available]:
                    if task.id in self._running_futures:
                        continue  # Already running

                    # Submit task
                    future = self._executor.submit(self._execute_task, task)
                    self._running_futures[task.id] = future
                    future.add_done_callback(
                        lambda f, tid=task.id: self._on_task_done(f, tid)
                    )
                    self._progress.pending -= 1
                    self._progress.running += 1
                    tasks_started += 1

                    logger.debug(f"Submitted task: {task.id}")

                # Wait a bit before checking again
                await asyncio.sleep(0.5)

            # Wait for remaining tasks to complete
            while self._running_futures:
                await asyncio.sleep(0.5)

            logger.info(
                f"PARALLEL_COMPLETE: {self._progress.completed} succeeded, "
                f"{self._progress.failed} failed"
            )

            return self._progress.results

        finally:
            self._executor.shutdown(wait=True)
            self._executor = None
            with self._state_lock:
                self._state = ExecutionState.STOPPED

    def start(self) -> None:
        """Start background task processing.

        Runs task processing in a background thread.
        Use stop() to halt processing.
        """
        if self._state == ExecutionState.RUNNING:
            raise RuntimeError("Executor is already running")

        def _run_in_thread():
            asyncio.run(self.run())

        thread = threading.Thread(target=_run_in_thread, daemon=True)
        thread.start()
        logger.info("Started background task processing")

    def stop(self, wait: bool = True) -> None:
        """Stop task processing.

        Args:
            wait: If True, wait for running tasks to complete
        """
        logger.info("Stopping parallel executor...")
        self._stop_event.set()

        with self._state_lock:
            self._state = ExecutionState.STOPPING

        if wait and self._executor:
            self._executor.shutdown(wait=True)

        with self._state_lock:
            self._state = ExecutionState.STOPPED

    def get_status(self) -> dict[str, Any]:
        """Get current executor status.

        Returns:
            Dictionary with status information
        """
        return {
            "state": self._state.value,
            "max_concurrent": self._max_concurrent,
            "progress": self._progress.to_dict(),
            "running_tasks": list(self._running_futures.keys()),
            "worktree_stats": self._worktree_manager.stats(),
            "queue_stats": self._queue.stats(),
        }

    def cleanup(self, force: bool = False) -> int:
        """Clean up all worktrees.

        Args:
            force: Force cleanup even with uncommitted changes

        Returns:
            Number of worktrees cleaned up
        """
        return self._worktree_manager.cleanup_all(force=force)


def create_executor(
    project_root: Optional[Path] = None,
    max_concurrent: int = ParallelExecutor.DEFAULT_MAX_CONCURRENT,
    **kwargs,
) -> ParallelExecutor:
    """Factory function to create a parallel executor.

    Args:
        project_root: Project root directory
        max_concurrent: Maximum concurrent tasks
        **kwargs: Additional arguments for ParallelExecutor

    Returns:
        Configured ParallelExecutor instance
    """
    return ParallelExecutor(
        project_root=project_root,
        max_concurrent=max_concurrent,
        **kwargs,
    )
