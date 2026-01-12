"""Task selection algorithm for RALPH-AGI.

This module provides the TaskSelector class that implements the task
selection algorithm for autonomous task execution.

Design Principles:
- Deterministic selection (same input = same output)
- Clear dependency tracking
- Priority-based ordering
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from ralph_agi.tasks.prd import Feature, PRD

logger = logging.getLogger(__name__)


class TaskSelectionError(Exception):
    """Task selection error (e.g., circular dependencies)."""

    pass


@dataclass(frozen=True)
class BlockedReason:
    """Reason why a feature is blocked.

    Attributes:
        feature_id: ID of the blocked feature.
        blocking_ids: IDs of features blocking this one.
        missing_ids: IDs of dependencies that don't exist.
    """

    feature_id: str
    blocking_ids: tuple[str, ...]
    missing_ids: tuple[str, ...]

    @property
    def has_missing_dependencies(self) -> bool:
        """Check if blocked due to missing dependencies."""
        return len(self.missing_ids) > 0

    @property
    def reason_text(self) -> str:
        """Get human-readable reason."""
        parts = []
        if self.blocking_ids:
            parts.append(f"blocked by: {', '.join(self.blocking_ids)}")
        if self.missing_ids:
            parts.append(f"missing dependencies: {', '.join(self.missing_ids)}")
        return "; ".join(parts) if parts else "unknown"


@dataclass(frozen=True)
class SelectionResult:
    """Result of task selection.

    Attributes:
        next_task: The selected task, or None if none available.
        ready_tasks: All tasks that are ready to work on.
        blocked_tasks: Tasks that are blocked with reasons.
        all_complete: True if all tasks are complete.
    """

    next_task: Optional[Feature]
    ready_tasks: tuple[Feature, ...]
    blocked_tasks: tuple[BlockedReason, ...]
    all_complete: bool

    @property
    def has_ready_tasks(self) -> bool:
        """Check if there are any ready tasks."""
        return len(self.ready_tasks) > 0

    @property
    def has_blocked_tasks(self) -> bool:
        """Check if there are blocked tasks."""
        return len(self.blocked_tasks) > 0


class TaskSelector:
    """Task selection logic for autonomous execution.

    Implements the algorithm for selecting the next task to work on
    based on completion status, dependencies, and priority.

    Example:
        >>> selector = TaskSelector()
        >>> prd = load_prd("PRD.json")
        >>> result = selector.select(prd)
        >>> if result.next_task:
        ...     print(f"Working on: {result.next_task.id}")
        ... elif result.all_complete:
        ...     print("All tasks complete!")
    """

    def select(self, prd: PRD) -> SelectionResult:
        """Select the next task to work on.

        Args:
            prd: The PRD containing all features.

        Returns:
            SelectionResult with next task and related info.
        """
        # Check if all complete
        if prd.is_complete:
            return SelectionResult(
                next_task=None,
                ready_tasks=(),
                blocked_tasks=(),
                all_complete=True,
            )

        # Get incomplete features
        incomplete = list(prd.get_incomplete_features())

        # Categorize into ready and blocked
        ready = []
        blocked = []

        for feature in incomplete:
            reason = self.get_blocked_reason(feature, prd)
            if reason is None:
                ready.append(feature)
            else:
                blocked.append(reason)

        # Sort ready tasks by priority (lower = higher priority)
        ready.sort(key=lambda f: (f.priority if f.priority is not None else 4, f.id))

        # Select the first (highest priority)
        next_task = ready[0] if ready else None

        return SelectionResult(
            next_task=next_task,
            ready_tasks=tuple(ready),
            blocked_tasks=tuple(blocked),
            all_complete=False,
        )

    def get_next_task(self, prd: PRD) -> Optional[Feature]:
        """Get the next task to work on.

        Convenience method that returns just the next task.

        Args:
            prd: The PRD containing all features.

        Returns:
            The highest priority ready feature, or None.
        """
        return self.select(prd).next_task

    def get_ready_tasks(self, prd: PRD) -> list[Feature]:
        """Get all tasks that are ready to work on.

        A task is ready if:
        - passes == False
        - All dependencies have passes == True

        Args:
            prd: The PRD containing all features.

        Returns:
            List of ready features, sorted by priority.
        """
        return list(self.select(prd).ready_tasks)

    def get_blocked_tasks(self, prd: PRD) -> list[BlockedReason]:
        """Get all tasks that are blocked.

        Args:
            prd: The PRD containing all features.

        Returns:
            List of BlockedReason objects explaining why each task is blocked.
        """
        return list(self.select(prd).blocked_tasks)

    def is_blocked(self, feature: Feature, prd: PRD) -> bool:
        """Check if a feature is blocked by dependencies.

        Args:
            feature: The feature to check.
            prd: The PRD containing all features.

        Returns:
            True if the feature is blocked, False otherwise.
        """
        return self.get_blocked_reason(feature, prd) is not None

    def get_blocked_reason(self, feature: Feature, prd: PRD) -> Optional[BlockedReason]:
        """Get the reason a feature is blocked.

        Args:
            feature: The feature to check.
            prd: The PRD containing all features.

        Returns:
            BlockedReason if blocked, None if not blocked.
        """
        if not feature.dependencies:
            return None

        blocking = []
        missing = []

        for dep_id in feature.dependencies:
            dep = prd.get_feature(dep_id)
            if dep is None:
                missing.append(dep_id)
            elif not dep.passes:
                blocking.append(dep_id)

        if blocking or missing:
            return BlockedReason(
                feature_id=feature.id,
                blocking_ids=tuple(blocking),
                missing_ids=tuple(missing),
            )

        return None

    def get_blocking_dependencies(self, feature: Feature, prd: PRD) -> list[str]:
        """Get IDs of dependencies blocking a feature.

        Args:
            feature: The feature to check.
            prd: The PRD containing all features.

        Returns:
            List of dependency IDs that are blocking.
        """
        reason = self.get_blocked_reason(feature, prd)
        if reason is None:
            return []
        return list(reason.blocking_ids) + list(reason.missing_ids)

    def detect_circular_dependencies(self, prd: PRD) -> list[list[str]]:
        """Detect circular dependencies in the PRD.

        Uses depth-first search to find all cycles in the dependency graph.

        Args:
            prd: The PRD to check.

        Returns:
            List of cycles, where each cycle is a list of feature IDs.
            Empty list if no cycles found.
        """
        # Build adjacency list
        graph: dict[str, list[str]] = defaultdict(list)
        all_ids = set()

        for feature in prd.features:
            all_ids.add(feature.id)
            for dep_id in feature.dependencies:
                # Edge: feature depends on dep_id
                # This means dep_id must be done before feature
                # For cycle detection, we go the other direction
                graph[feature.id].append(dep_id)

        # Track visited state
        WHITE = 0  # Not visited
        GRAY = 1   # Currently in stack (being explored)
        BLACK = 2  # Finished

        color = {fid: WHITE for fid in all_ids}
        cycles = []

        def dfs(node: str, path: list[str]) -> None:
            """DFS to detect cycles."""
            if node not in all_ids:
                # Missing dependency - not a cycle
                return

            if color[node] == BLACK:
                return

            if color[node] == GRAY:
                # Found a cycle - extract it
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return

            color[node] = GRAY
            path.append(node)

            for neighbor in graph[node]:
                dfs(neighbor, path)

            path.pop()
            color[node] = BLACK

        # Run DFS from each node
        for node in all_ids:
            if color[node] == WHITE:
                dfs(node, [])

        return cycles

    def validate_dependencies(self, prd: PRD) -> None:
        """Validate that the PRD has no circular dependencies.

        Args:
            prd: The PRD to validate.

        Raises:
            TaskSelectionError: If circular dependencies are detected.
        """
        cycles = self.detect_circular_dependencies(prd)
        if cycles:
            cycle_strs = [" -> ".join(c) for c in cycles]
            raise TaskSelectionError(
                f"Circular dependencies detected: {'; '.join(cycle_strs)}"
            )
