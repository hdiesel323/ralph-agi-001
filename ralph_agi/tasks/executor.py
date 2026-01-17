"""Task executor for single-feature-per-iteration constraint.

This module provides the TaskExecutor class that enforces the
single-feature-per-iteration principle for context quality.

Design Principles:
- One task at a time (no concurrent execution)
- Clear task lifecycle (begin, complete, abort)
- Size analysis for large task warnings
- Optional worktree isolation for parallel execution
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ralph_agi.tasks.prd import Feature, PRD, PRDError, load_prd
from ralph_agi.tasks.selector import TaskSelector
from ralph_agi.tasks.writer import mark_complete

if TYPE_CHECKING:
    from ralph_agi.tools.git import GitTools

logger = logging.getLogger(__name__)

# Size thresholds for warnings
MAX_STEPS = 10
MAX_DESCRIPTION_LENGTH = 500
MAX_ACCEPTANCE_CRITERIA = 8


class TaskExecutionError(Exception):
    """Task execution error (e.g., lock conflict)."""

    pass


@dataclass(frozen=True)
class TaskAnalysis:
    """Analysis of a task's size and complexity.

    Attributes:
        is_large: Whether the task is considered large.
        warnings: List of warning messages.
        suggestions: List of suggestions for improvement.
    """

    is_large: bool
    warnings: tuple[str, ...]
    suggestions: tuple[str, ...]


@dataclass
class ExecutionContext:
    """Context for a single task execution.

    Attributes:
        feature: The feature being worked on.
        started_at: When execution started.
        prd_path: Path to the PRD.json file.
        analysis: Task size analysis.
        worktree_path: Path to isolated worktree (if enabled).
        branch_name: Git branch name for worktree (if enabled).
    """

    feature: Feature
    started_at: datetime
    prd_path: Path
    analysis: TaskAnalysis = field(default_factory=lambda: TaskAnalysis(False, (), ()))
    worktree_path: Optional[Path] = None
    branch_name: Optional[str] = None

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        delta = datetime.now(timezone.utc) - self.started_at
        return delta.total_seconds()

    @property
    def work_dir(self) -> Path:
        """Get the working directory for this task.

        Returns worktree path if isolation is enabled, otherwise
        the directory containing PRD.json.
        """
        if self.worktree_path:
            return self.worktree_path
        return self.prd_path.parent

    @property
    def is_isolated(self) -> bool:
        """Check if task is running in isolated worktree."""
        return self.worktree_path is not None


class TaskExecutor:
    """Single-feature-per-iteration task executor.

    Enforces that only one task can be worked on at a time,
    preventing context pollution from concurrent work.

    Example:
        >>> executor = TaskExecutor()
        >>> ctx = executor.begin_task(Path("PRD.json"))
        >>> if ctx:
        ...     print(f"Working on: {ctx.feature.id}")
        ...     # Do work...
        ...     executor.complete_task(ctx)

    With worktree isolation:
        >>> executor = TaskExecutor(enable_worktree_isolation=True, repo_path=Path("."))
        >>> ctx = executor.begin_task(Path("PRD.json"))
        >>> if ctx:
        ...     print(f"Isolated work_dir: {ctx.work_dir}")  # Points to worktree
        ...     print(f"Branch: {ctx.branch_name}")  # e.g., "ralph/feature-123"
    """

    def __init__(
        self,
        selector: Optional[TaskSelector] = None,
        enable_worktree_isolation: bool = False,
        repo_path: Optional[Path] = None,
        worktree_base: Optional[Path] = None,
    ):
        """Initialize the executor.

        Args:
            selector: Task selector to use. Creates default if not provided.
            enable_worktree_isolation: If True, create isolated worktrees for tasks.
            repo_path: Path to main git repository (required if isolation enabled).
            worktree_base: Base directory for worktrees. Defaults to parent of repo_path.
        """
        self.selector = selector or TaskSelector()
        self._current_task: Optional[Feature] = None
        self._current_context: Optional[ExecutionContext] = None
        self._lock = threading.Lock()

        # Worktree isolation settings
        self._enable_worktree_isolation = enable_worktree_isolation
        self._repo_path = Path(repo_path) if repo_path else None
        self._worktree_base = Path(worktree_base) if worktree_base else None
        self._git_tools: Optional[GitTools] = None

        if enable_worktree_isolation and not repo_path:
            raise ValueError("repo_path is required when worktree isolation is enabled")

    @property
    def is_executing(self) -> bool:
        """Check if currently executing a task."""
        return self._current_task is not None

    @property
    def current_task(self) -> Optional[Feature]:
        """Get the currently executing task, if any."""
        return self._current_task

    def begin_task(self, prd_path: Path | str) -> Optional[ExecutionContext]:
        """Start working on the next available task.

        Selects the highest priority ready task and locks it
        for execution. If worktree isolation is enabled, creates
        an isolated worktree for the task.

        Args:
            prd_path: Path to the PRD.json file.

        Returns:
            ExecutionContext if a task was found, None if all complete.

        Raises:
            TaskExecutionError: If already executing a task or worktree creation fails.
        """
        prd_path = Path(prd_path)

        with self._lock:
            if self._current_task is not None:
                raise TaskExecutionError(
                    f"Already executing task '{self._current_task.id}'. "
                    "Complete or abort it first."
                )

            # Load PRD and select next task
            prd = load_prd(prd_path)
            result = self.selector.select(prd)

            if result.next_task is None:
                if result.all_complete:
                    logger.info("All tasks complete")
                elif result.has_blocked_tasks:
                    blocked_ids = [r.feature_id for r in result.blocked_tasks]
                    logger.warning(f"No ready tasks. Blocked: {', '.join(blocked_ids)}")
                return None

            # Analyze task size
            analysis = analyze_task_size(result.next_task)
            if analysis.is_large:
                for warning in analysis.warnings:
                    logger.warning(f"Large task warning: {warning}")
                for suggestion in analysis.suggestions:
                    logger.info(f"Suggestion: {suggestion}")

            # Create worktree if isolation enabled
            worktree_path = None
            branch_name = None

            if self._enable_worktree_isolation:
                worktree_path, branch_name = self._create_task_worktree(result.next_task)

            # Lock the task
            self._current_task = result.next_task
            ctx = ExecutionContext(
                feature=result.next_task,
                started_at=datetime.now(timezone.utc),
                prd_path=prd_path,
                analysis=analysis,
                worktree_path=worktree_path,
                branch_name=branch_name,
            )
            self._current_context = ctx

            if worktree_path:
                logger.info(
                    f"Started task '{result.next_task.id}' ({result.next_task.priority_label}) "
                    f"in worktree: {worktree_path}"
                )
            else:
                logger.info(f"Started task '{result.next_task.id}' ({result.next_task.priority_label})")

            return ctx

    def _create_task_worktree(self, task: Feature) -> tuple[Path, str]:
        """Create an isolated worktree for a task.

        Args:
            task: The task feature to create worktree for.

        Returns:
            Tuple of (worktree_path, branch_name).

        Raises:
            TaskExecutionError: If worktree creation fails.
        """
        from ralph_agi.tools.git import GitTools, GitCommandError

        # Initialize git tools if needed
        if self._git_tools is None:
            self._git_tools = GitTools(repo_path=self._repo_path)

        # Generate branch name: ralph/<task-id>
        # Sanitize task ID for git branch name
        safe_task_id = _sanitize_branch_name(task.id)
        branch_name = f"ralph/{safe_task_id}"

        # Generate worktree path: <worktree_base>/ralph-<task-id>
        if self._worktree_base:
            base = self._worktree_base
        else:
            base = self._repo_path.parent

        worktree_path = base / f"ralph-{safe_task_id}"

        try:
            # Create worktree with new branch
            result_path = self._git_tools.worktree_add(
                path=str(worktree_path),
                branch=branch_name,
                create_branch=True,
                base_ref="HEAD",
            )
            logger.info(f"Created worktree at {result_path} on branch {branch_name}")
            return Path(result_path), branch_name

        except GitCommandError as e:
            raise TaskExecutionError(
                f"Failed to create worktree for task '{task.id}': {e}"
            ) from e

    def complete_task(self, ctx: ExecutionContext) -> PRD:
        """Mark the current task as complete.

        Updates the PRD.json file and releases the task lock.
        Does NOT remove the worktree - changes should be merged separately.

        Args:
            ctx: The execution context from begin_task.

        Returns:
            The updated PRD.

        Raises:
            TaskExecutionError: If the context doesn't match current task.
        """
        with self._lock:
            if self._current_task is None:
                raise TaskExecutionError("No task is currently being executed")

            if self._current_task.id != ctx.feature.id:
                raise TaskExecutionError(
                    f"Context mismatch: expected '{self._current_task.id}', "
                    f"got '{ctx.feature.id}'"
                )

            # Mark complete in PRD.json
            prd = mark_complete(ctx.prd_path, ctx.feature.id)

            elapsed = ctx.elapsed_seconds
            if ctx.is_isolated:
                logger.info(
                    f"Completed task '{ctx.feature.id}' in {elapsed:.1f}s "
                    f"(worktree: {ctx.worktree_path}, branch: {ctx.branch_name})"
                )
            else:
                logger.info(f"Completed task '{ctx.feature.id}' in {elapsed:.1f}s")

            # Release lock (worktree preserved for merge)
            self._current_task = None
            self._current_context = None

            return prd

    def abort_task(
        self,
        reason: str = "aborted",
        cleanup_worktree: bool = False,
    ) -> Optional[Feature]:
        """Abort the current task without marking complete.

        Releases the task lock without modifying the PRD.
        Optionally removes the worktree if isolation was enabled.

        Args:
            reason: Reason for aborting.
            cleanup_worktree: If True, remove the worktree on abort.

        Returns:
            The aborted feature, or None if no task was executing.
        """
        with self._lock:
            if self._current_task is None:
                return None

            aborted = self._current_task
            ctx = self._current_context

            # Cleanup worktree if requested
            if cleanup_worktree and ctx and ctx.is_isolated:
                try:
                    self._cleanup_worktree(ctx.worktree_path)
                    logger.info(f"Cleaned up worktree: {ctx.worktree_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup worktree: {e}")

            logger.warning(f"Aborted task '{aborted.id}': {reason}")

            self._current_task = None
            self._current_context = None

            return aborted

    def _cleanup_worktree(self, worktree_path: Path) -> None:
        """Remove a worktree and its branch.

        Args:
            worktree_path: Path to worktree to remove.
        """
        if self._git_tools is None:
            return

        try:
            self._git_tools.worktree_remove(str(worktree_path), force=True)
        except Exception as e:
            logger.warning(f"Failed to remove worktree {worktree_path}: {e}")

    def get_status(self) -> dict:
        """Get current executor status.

        Returns:
            Dictionary with execution status information.
        """
        with self._lock:
            if self._current_task is None:
                return {
                    "executing": False,
                    "task_id": None,
                    "elapsed_seconds": None,
                    "worktree_isolation": self._enable_worktree_isolation,
                }

            elapsed = None
            worktree_path = None
            branch_name = None

            if self._current_context:
                elapsed = self._current_context.elapsed_seconds
                worktree_path = str(self._current_context.worktree_path) if self._current_context.worktree_path else None
                branch_name = self._current_context.branch_name

            return {
                "executing": True,
                "task_id": self._current_task.id,
                "priority": self._current_task.priority_label,
                "elapsed_seconds": elapsed,
                "worktree_isolation": self._enable_worktree_isolation,
                "worktree_path": worktree_path,
                "branch_name": branch_name,
            }


def analyze_task_size(feature: Feature) -> TaskAnalysis:
    """Analyze a task's size and complexity.

    Provides warnings if the task appears too large for
    a single iteration.

    Args:
        feature: The feature to analyze.

    Returns:
        TaskAnalysis with warnings and suggestions.
    """
    warnings = []
    suggestions = []

    # Check number of steps
    if len(feature.steps) > MAX_STEPS:
        warnings.append(
            f"Task has {len(feature.steps)} steps (recommended max: {MAX_STEPS})"
        )
        suggestions.append("Break into smaller tasks with 3-5 steps each")

    # Check description length
    if len(feature.description) > MAX_DESCRIPTION_LENGTH:
        warnings.append(
            f"Task description is {len(feature.description)} chars "
            f"(recommended max: {MAX_DESCRIPTION_LENGTH})"
        )
        suggestions.append("Extract sub-features from detailed description")

    # Check acceptance criteria count
    if len(feature.acceptance_criteria) > MAX_ACCEPTANCE_CRITERIA:
        warnings.append(
            f"Task has {len(feature.acceptance_criteria)} acceptance criteria "
            f"(recommended max: {MAX_ACCEPTANCE_CRITERIA})"
        )
        suggestions.append("Group related criteria into separate tasks")

    return TaskAnalysis(
        is_large=len(warnings) > 0,
        warnings=tuple(warnings),
        suggestions=tuple(suggestions),
    )


def _sanitize_branch_name(task_id: str) -> str:
    """Sanitize a task ID for use in git branch names.

    Git branch names have restrictions:
    - No spaces
    - No special characters like ~, ^, :, ?, *, [
    - No consecutive dots
    - No leading/trailing dots or slashes

    Args:
        task_id: The task ID to sanitize.

    Returns:
        A git-safe branch name derived from the task ID.
    """
    # Replace spaces and special chars with hyphens
    safe_name = re.sub(r'[~^:?*\[\]\\@\s]+', '-', task_id)

    # Replace consecutive dots with single hyphen
    safe_name = re.sub(r'\.{2,}', '-', safe_name)

    # Remove leading/trailing dots, hyphens, slashes
    safe_name = safe_name.strip('.-/')

    # Ensure non-empty
    if not safe_name:
        safe_name = "task"

    return safe_name
