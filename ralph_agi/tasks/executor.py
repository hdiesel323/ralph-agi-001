"""Task executor for single-feature-per-iteration constraint.

This module provides the TaskExecutor class that enforces the
single-feature-per-iteration principle for context quality.

Design Principles:
- One task at a time (no concurrent execution)
- Clear task lifecycle (begin, complete, abort)
- Size analysis for large task warnings
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ralph_agi.tasks.prd import Feature, PRD, PRDError, load_prd
from ralph_agi.tasks.selector import TaskSelector
from ralph_agi.tasks.writer import mark_complete

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
    """

    feature: Feature
    started_at: datetime
    prd_path: Path
    analysis: TaskAnalysis = field(default_factory=lambda: TaskAnalysis(False, (), ()))

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        delta = datetime.now(timezone.utc) - self.started_at
        return delta.total_seconds()


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
    """

    def __init__(self, selector: Optional[TaskSelector] = None):
        """Initialize the executor.

        Args:
            selector: Task selector to use. Creates default if not provided.
        """
        self.selector = selector or TaskSelector()
        self._current_task: Optional[Feature] = None
        self._current_context: Optional[ExecutionContext] = None
        self._lock = threading.Lock()

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
        for execution.

        Args:
            prd_path: Path to the PRD.json file.

        Returns:
            ExecutionContext if a task was found, None if all complete.

        Raises:
            TaskExecutionError: If already executing a task.
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

            # Lock the task
            self._current_task = result.next_task
            ctx = ExecutionContext(
                feature=result.next_task,
                started_at=datetime.now(timezone.utc),
                prd_path=prd_path,
                analysis=analysis,
            )
            self._current_context = ctx

            logger.info(f"Started task '{result.next_task.id}' ({result.next_task.priority_label})")
            return ctx

    def complete_task(self, ctx: ExecutionContext) -> PRD:
        """Mark the current task as complete.

        Updates the PRD.json file and releases the task lock.

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
            logger.info(f"Completed task '{ctx.feature.id}' in {elapsed:.1f}s")

            # Release lock
            self._current_task = None
            self._current_context = None

            return prd

    def abort_task(self, reason: str = "aborted") -> Optional[Feature]:
        """Abort the current task without marking complete.

        Releases the task lock without modifying the PRD.

        Args:
            reason: Reason for aborting.

        Returns:
            The aborted feature, or None if no task was executing.
        """
        with self._lock:
            if self._current_task is None:
                return None

            aborted = self._current_task
            logger.warning(f"Aborted task '{aborted.id}': {reason}")

            self._current_task = None
            self._current_context = None

            return aborted

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
                }

            elapsed = None
            if self._current_context:
                elapsed = self._current_context.elapsed_seconds

            return {
                "executing": True,
                "task_id": self._current_task.id,
                "priority": self._current_task.priority_label,
                "elapsed_seconds": elapsed,
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
