"""Dependency graph for task management.

This module provides a dependency graph implementation for tracking
task dependencies and determining execution order.

Design Principles:
- Immutable graph structure for safety
- Efficient cycle detection
- Clear error messages for invalid states
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator, Optional, Sequence

from ralph_agi.tasks.prd import Feature, PRD

logger = logging.getLogger(__name__)


class DependencyError(Exception):
    """Dependency graph error."""

    pass


class CircularDependencyError(DependencyError):
    """Circular dependency detected."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        cycle_str = " -> ".join(cycle)
        super().__init__(f"Circular dependency detected: {cycle_str}")


class MissingDependencyError(DependencyError):
    """Referenced dependency does not exist."""

    def __init__(self, feature_id: str, missing_id: str):
        self.feature_id = feature_id
        self.missing_id = missing_id
        super().__init__(
            f"Feature '{feature_id}' depends on non-existent feature '{missing_id}'"
        )


class NodeStatus(Enum):
    """Status for dependency graph traversal."""

    UNVISITED = 0
    IN_PROGRESS = 1
    COMPLETED = 2


@dataclass(frozen=True)
class DependencyNode:
    """A node in the dependency graph.

    Attributes:
        feature_id: The feature ID this node represents.
        dependencies: IDs of features this one depends on.
        dependents: IDs of features that depend on this one.
        is_complete: Whether the feature is marked complete.
        priority: Feature priority (0=P0 highest).
    """

    feature_id: str
    dependencies: frozenset[str] = field(default_factory=frozenset)
    dependents: frozenset[str] = field(default_factory=frozenset)
    is_complete: bool = False
    priority: Optional[int] = None

    @property
    def has_dependencies(self) -> bool:
        """Check if this node has any dependencies."""
        return len(self.dependencies) > 0

    @property
    def has_dependents(self) -> bool:
        """Check if other nodes depend on this one."""
        return len(self.dependents) > 0


@dataclass(frozen=True)
class DependencyPath:
    """A path through the dependency graph.

    Attributes:
        nodes: Sequence of feature IDs in the path.
        is_cycle: Whether this path forms a cycle.
    """

    nodes: tuple[str, ...]
    is_cycle: bool = False

    def __len__(self) -> int:
        return len(self.nodes)

    def __iter__(self) -> Iterator[str]:
        return iter(self.nodes)


class DependencyGraph:
    """Dependency graph for task management.

    Provides efficient queries for:
    - Is a feature ready to work on?
    - What blocks a feature?
    - Execution order (topological sort)
    - Cycle detection

    Example:
        >>> graph = DependencyGraph.from_prd(prd)
        >>> if graph.is_ready("feature-3"):
        ...     print("Feature 3 is ready to work on")
        >>> blockers = graph.get_blockers("feature-5")
        >>> execution_order = graph.get_execution_order()
    """

    def __init__(self, nodes: dict[str, DependencyNode]):
        """Initialize the dependency graph.

        Args:
            nodes: Dictionary mapping feature IDs to DependencyNode objects.
        """
        self._nodes = nodes
        self._cycles: Optional[list[list[str]]] = None

    @classmethod
    def from_prd(cls, prd: PRD, validate: bool = True) -> DependencyGraph:
        """Build a dependency graph from a PRD.

        Args:
            prd: The PRD to build the graph from.
            validate: Whether to validate for cycles and missing deps.

        Returns:
            DependencyGraph instance.

        Raises:
            CircularDependencyError: If validate=True and cycles exist.
            MissingDependencyError: If validate=True and deps are missing.
        """
        # Build nodes
        nodes: dict[str, DependencyNode] = {}
        dependents_map: dict[str, set[str]] = defaultdict(set)

        # First pass: collect all feature IDs
        feature_ids = {f.id for f in prd.features}

        # Second pass: build dependency relationships
        for feature in prd.features:
            deps = frozenset(feature.dependencies)

            # Track reverse dependencies
            for dep_id in deps:
                dependents_map[dep_id].add(feature.id)

            nodes[feature.id] = DependencyNode(
                feature_id=feature.id,
                dependencies=deps,
                dependents=frozenset(),  # Will be filled in third pass
                is_complete=feature.passes,
                priority=feature.priority,
            )

        # Third pass: add dependents to nodes
        for feature_id, node in nodes.items():
            nodes[feature_id] = DependencyNode(
                feature_id=node.feature_id,
                dependencies=node.dependencies,
                dependents=frozenset(dependents_map.get(feature_id, set())),
                is_complete=node.is_complete,
                priority=node.priority,
            )

        graph = cls(nodes)

        if validate:
            # Check for missing dependencies
            for feature_id, node in nodes.items():
                for dep_id in node.dependencies:
                    if dep_id not in feature_ids:
                        raise MissingDependencyError(feature_id, dep_id)

            # Check for cycles
            cycles = graph.find_cycles()
            if cycles:
                raise CircularDependencyError(cycles[0])

        return graph

    @property
    def node_count(self) -> int:
        """Get the number of nodes in the graph."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Get the number of edges (dependencies) in the graph."""
        return sum(len(node.dependencies) for node in self._nodes.values())

    def get_node(self, feature_id: str) -> Optional[DependencyNode]:
        """Get a node by feature ID.

        Args:
            feature_id: The feature ID to look up.

        Returns:
            DependencyNode if found, None otherwise.
        """
        return self._nodes.get(feature_id)

    def get_all_nodes(self) -> list[DependencyNode]:
        """Get all nodes in the graph."""
        return list(self._nodes.values())

    def is_ready(self, feature_id: str) -> bool:
        """Check if a feature is ready to work on.

        A feature is ready if:
        - It exists in the graph
        - It is not complete
        - All its dependencies are complete

        Args:
            feature_id: The feature ID to check.

        Returns:
            True if the feature is ready, False otherwise.
        """
        node = self._nodes.get(feature_id)
        if node is None:
            return False

        # Already complete
        if node.is_complete:
            return False

        # Check all dependencies are complete
        for dep_id in node.dependencies:
            dep_node = self._nodes.get(dep_id)
            if dep_node is None or not dep_node.is_complete:
                return False

        return True

    def get_blockers(self, feature_id: str) -> list[str]:
        """Get IDs of features blocking a given feature.

        Args:
            feature_id: The feature ID to check.

        Returns:
            List of feature IDs that are blocking this feature.
            Empty list if feature is ready or doesn't exist.
        """
        node = self._nodes.get(feature_id)
        if node is None:
            return []

        blockers = []
        for dep_id in node.dependencies:
            dep_node = self._nodes.get(dep_id)
            if dep_node is None:
                blockers.append(dep_id)  # Missing dependency
            elif not dep_node.is_complete:
                blockers.append(dep_id)

        return blockers

    def get_blocked_by(self, feature_id: str) -> list[str]:
        """Get IDs of features blocked by a given feature.

        Args:
            feature_id: The feature ID to check.

        Returns:
            List of feature IDs that are waiting on this feature.
        """
        node = self._nodes.get(feature_id)
        if node is None:
            return []

        return list(node.dependents)

    def get_ready_features(self) -> list[str]:
        """Get all features that are ready to work on.

        Returns:
            List of feature IDs that are ready, sorted by priority.
        """
        ready = [fid for fid in self._nodes if self.is_ready(fid)]

        # Sort by priority (lower = higher priority)
        ready.sort(key=lambda fid: (self._nodes[fid].priority if self._nodes[fid].priority is not None else 4, fid))
        return ready

    def get_complete_features(self) -> list[str]:
        """Get all completed features."""
        return [fid for fid, node in self._nodes.items() if node.is_complete]

    def get_incomplete_features(self) -> list[str]:
        """Get all incomplete features."""
        return [fid for fid, node in self._nodes.items() if not node.is_complete]

    def get_blocked_features(self) -> list[str]:
        """Get all features that are blocked by incomplete dependencies."""
        blocked = []
        for fid, node in self._nodes.items():
            if not node.is_complete and self.get_blockers(fid):
                blocked.append(fid)
        return blocked

    def get_execution_order(self) -> list[str]:
        """Get topological order for executing features.

        Returns features in an order that respects dependencies,
        with higher priority features first among those with
        equivalent dependency depth.

        Returns:
            List of feature IDs in execution order.

        Raises:
            CircularDependencyError: If the graph has cycles.
        """
        # Kahn's algorithm with priority
        in_degree = {fid: len(node.dependencies) for fid, node in self._nodes.items()}
        ready = [(self._nodes[fid].priority if self._nodes[fid].priority is not None else 4, fid) for fid, d in in_degree.items() if d == 0]
        ready.sort()  # Sort by priority, then by ID

        result = []
        while ready:
            # Pop highest priority
            _, fid = ready.pop(0)
            result.append(fid)

            # Reduce in-degree for dependents
            node = self._nodes[fid]
            for dep_id in node.dependents:
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    # Add to ready queue with priority
                    dep_priority = self._nodes[dep_id].priority or 4
                    ready.append((dep_priority, dep_id))
                    ready.sort()

        if len(result) != len(self._nodes):
            # Cycle detected (some nodes never reached in_degree 0)
            remaining = set(self._nodes.keys()) - set(result)
            raise CircularDependencyError(list(remaining)[:5] + ["..."])

        return result

    def find_cycles(self) -> list[list[str]]:
        """Find all cycles in the dependency graph.

        Returns:
            List of cycles, where each cycle is a list of feature IDs.
            Empty list if no cycles found.
        """
        if self._cycles is not None:
            return self._cycles

        cycles = []
        status = {fid: NodeStatus.UNVISITED for fid in self._nodes}

        def dfs(node_id: str, path: list[str]) -> None:
            if status[node_id] == NodeStatus.COMPLETED:
                return

            if status[node_id] == NodeStatus.IN_PROGRESS:
                # Found cycle
                cycle_start = path.index(node_id)
                cycle = path[cycle_start:] + [node_id]
                cycles.append(cycle)
                return

            status[node_id] = NodeStatus.IN_PROGRESS
            path.append(node_id)

            node = self._nodes[node_id]
            for dep_id in node.dependencies:
                if dep_id in self._nodes:  # Only traverse existing nodes
                    dfs(dep_id, path)

            path.pop()
            status[node_id] = NodeStatus.COMPLETED

        for node_id in self._nodes:
            if status[node_id] == NodeStatus.UNVISITED:
                dfs(node_id, [])

        self._cycles = cycles
        return cycles

    def has_cycles(self) -> bool:
        """Check if the graph has any cycles."""
        return len(self.find_cycles()) > 0

    def get_depth(self, feature_id: str) -> int:
        """Get the dependency depth of a feature.

        Depth is the longest path from a root (no dependencies) to this feature.

        Args:
            feature_id: The feature ID to check.

        Returns:
            Depth (0 for root nodes), or -1 if feature not found or in cycle.
        """
        if feature_id not in self._nodes:
            return -1

        # Memoization for depth calculation
        depths: dict[str, int] = {}

        def calc_depth(fid: str, visited: set[str]) -> int:
            if fid in depths:
                return depths[fid]

            if fid in visited:
                return -1  # Cycle

            visited.add(fid)
            node = self._nodes.get(fid)
            if node is None:
                return -1

            if not node.dependencies:
                depths[fid] = 0
                return 0

            max_dep_depth = -1
            for dep_id in node.dependencies:
                if dep_id in self._nodes:
                    dep_depth = calc_depth(dep_id, visited)
                    if dep_depth == -1:
                        return -1
                    max_dep_depth = max(max_dep_depth, dep_depth)

            depth = max_dep_depth + 1 if max_dep_depth >= 0 else 0
            depths[fid] = depth
            return depth

        return calc_depth(feature_id, set())

    def get_path(self, from_id: str, to_id: str) -> Optional[DependencyPath]:
        """Find a path from one feature to another through dependencies.

        Args:
            from_id: Starting feature ID.
            to_id: Target feature ID.

        Returns:
            DependencyPath if path exists, None otherwise.
        """
        if from_id not in self._nodes or to_id not in self._nodes:
            return None

        # BFS to find shortest path
        from collections import deque

        queue = deque([(from_id, [from_id])])
        visited = {from_id}

        while queue:
            current, path = queue.popleft()

            if current == to_id:
                return DependencyPath(nodes=tuple(path))

            node = self._nodes[current]
            for dep_id in node.dependencies:
                if dep_id not in visited and dep_id in self._nodes:
                    visited.add(dep_id)
                    queue.append((dep_id, path + [dep_id]))

        return None

    def get_critical_path(self) -> list[str]:
        """Get the critical path (longest path through the graph).

        Returns:
            List of feature IDs in the critical path.
        """
        if not self._nodes:
            return []

        # Find the node with maximum depth
        max_depth = -1
        deepest_node = None

        for fid in self._nodes:
            depth = self.get_depth(fid)
            if depth > max_depth:
                max_depth = depth
                deepest_node = fid

        if deepest_node is None:
            return []

        # Trace back the critical path
        path = [deepest_node]
        current = deepest_node

        while True:
            node = self._nodes[current]
            if not node.dependencies:
                break

            # Find the dependency with the highest depth
            best_dep = None
            best_depth = -1
            for dep_id in node.dependencies:
                if dep_id in self._nodes:
                    dep_depth = self.get_depth(dep_id)
                    if dep_depth > best_depth:
                        best_depth = dep_depth
                        best_dep = dep_id

            if best_dep is None:
                break

            path.append(best_dep)
            current = best_dep

        return list(reversed(path))

    def to_dot(self, highlight_ready: bool = True) -> str:
        """Generate DOT format for visualization.

        Args:
            highlight_ready: Whether to highlight ready features.

        Returns:
            DOT format string for use with Graphviz.
        """
        lines = ["digraph DependencyGraph {"]
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box];")
        lines.append("")

        ready_ids = set(self.get_ready_features()) if highlight_ready else set()

        # Add nodes
        for fid, node in self._nodes.items():
            attrs = []
            if node.is_complete:
                attrs.append("style=filled")
                attrs.append("fillcolor=lightgreen")
            elif fid in ready_ids:
                attrs.append("style=filled")
                attrs.append("fillcolor=lightyellow")

            if node.priority is not None:
                attrs.append(f'label="{fid}\\nP{node.priority}"')
            else:
                attrs.append(f'label="{fid}"')

            attr_str = ", ".join(attrs) if attrs else ""
            lines.append(f'  "{fid}" [{attr_str}];')

        lines.append("")

        # Add edges
        for fid, node in self._nodes.items():
            for dep_id in node.dependencies:
                lines.append(f'  "{fid}" -> "{dep_id}";')

        lines.append("}")
        return "\n".join(lines)

    def to_ascii(self) -> str:
        """Generate ASCII art representation of the graph.

        Returns:
            ASCII art string showing the dependency structure.
        """
        if not self._nodes:
            return "(empty graph)"

        lines = ["Dependency Graph:"]
        lines.append("=" * 40)

        # Group by depth
        depth_groups: dict[int, list[str]] = defaultdict(list)
        for fid in self._nodes:
            depth = self.get_depth(fid)
            depth_groups[depth].append(fid)

        # Sort within each depth by priority
        for depth in sorted(depth_groups.keys()):
            if depth < 0:
                lines.append(f"\n[CYCLE] {', '.join(depth_groups[depth])}")
                continue

            lines.append(f"\nDepth {depth}:")
            features = sorted(
                depth_groups[depth],
                key=lambda f: (self._nodes[f].priority or 4, f)
            )

            for fid in features:
                node = self._nodes[fid]
                status = "[x]" if node.is_complete else "[ ]"
                priority = f"P{node.priority}" if node.priority is not None else "P?"
                deps_str = ""
                if node.dependencies:
                    deps_str = f" <- {', '.join(sorted(node.dependencies))}"
                lines.append(f"  {status} {fid} ({priority}){deps_str}")

        lines.append("")
        lines.append(f"Total: {self.node_count} nodes, {self.edge_count} edges")
        ready_count = len(self.get_ready_features())
        complete_count = len(self.get_complete_features())
        lines.append(f"Ready: {ready_count}, Complete: {complete_count}")

        return "\n".join(lines)
