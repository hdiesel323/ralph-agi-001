"""Tests for dependency graph implementation.

Tests cover:
- Build graph from PRD dependencies field
- Detect circular dependencies (error)
- Query: Is task X ready? (all deps complete)
- Query: What blocks task X?
- Visualize graph (for debugging)
"""

import pytest

from ralph_agi.tasks.graph import (
    CircularDependencyError,
    DependencyGraph,
    DependencyNode,
    DependencyPath,
    MissingDependencyError,
    NodeStatus,
)
from ralph_agi.tasks.prd import Feature, PRD, Project


# Fixtures


@pytest.fixture
def project():
    """Create a basic project for testing."""
    return Project(name="Test Project", description="A test project")


@pytest.fixture
def simple_features():
    """Features with no dependencies."""
    return (
        Feature(id="f1", description="Feature 1", passes=False, priority=0),
        Feature(id="f2", description="Feature 2", passes=False, priority=1),
        Feature(id="f3", description="Feature 3", passes=True, priority=2),
    )


@pytest.fixture
def simple_prd(project, simple_features):
    """PRD with simple features."""
    return PRD(project=project, features=simple_features)


@pytest.fixture
def chain_features():
    """Features in a chain: f1 -> f2 -> f3."""
    return (
        Feature(id="f1", description="Feature 1", passes=False, priority=0),
        Feature(
            id="f2",
            description="Feature 2",
            passes=False,
            priority=1,
            dependencies=("f1",),
        ),
        Feature(
            id="f3",
            description="Feature 3",
            passes=False,
            priority=2,
            dependencies=("f2",),
        ),
    )


@pytest.fixture
def chain_prd(project, chain_features):
    """PRD with chain dependencies."""
    return PRD(project=project, features=chain_features)


@pytest.fixture
def diamond_features():
    """Diamond dependency: f1 -> f2, f3 -> f4."""
    return (
        Feature(id="f1", description="Feature 1", passes=True, priority=0),
        Feature(
            id="f2",
            description="Feature 2",
            passes=False,
            priority=1,
            dependencies=("f1",),
        ),
        Feature(
            id="f3",
            description="Feature 3",
            passes=False,
            priority=1,
            dependencies=("f1",),
        ),
        Feature(
            id="f4",
            description="Feature 4",
            passes=False,
            priority=2,
            dependencies=("f2", "f3"),
        ),
    )


@pytest.fixture
def diamond_prd(project, diamond_features):
    """PRD with diamond dependencies."""
    return PRD(project=project, features=diamond_features)


@pytest.fixture
def cycle_features():
    """Features with a cycle: f1 -> f2 -> f3 -> f1."""
    return (
        Feature(
            id="f1",
            description="Feature 1",
            passes=False,
            priority=0,
            dependencies=("f3",),
        ),
        Feature(
            id="f2",
            description="Feature 2",
            passes=False,
            priority=1,
            dependencies=("f1",),
        ),
        Feature(
            id="f3",
            description="Feature 3",
            passes=False,
            priority=2,
            dependencies=("f2",),
        ),
    )


@pytest.fixture
def cycle_prd(project, cycle_features):
    """PRD with cycle."""
    return PRD(project=project, features=cycle_features)


# DependencyNode Tests


class TestDependencyNode:
    """Tests for DependencyNode dataclass."""

    def test_node_attributes(self):
        """Test DependencyNode stores attributes."""
        node = DependencyNode(
            feature_id="f1",
            dependencies=frozenset({"f0"}),
            dependents=frozenset({"f2", "f3"}),
            is_complete=True,
            priority=1,
        )

        assert node.feature_id == "f1"
        assert node.dependencies == frozenset({"f0"})
        assert node.dependents == frozenset({"f2", "f3"})
        assert node.is_complete is True
        assert node.priority == 1

    def test_node_defaults(self):
        """Test DependencyNode default values."""
        node = DependencyNode(feature_id="f1")

        assert node.dependencies == frozenset()
        assert node.dependents == frozenset()
        assert node.is_complete is False
        assert node.priority is None

    def test_has_dependencies(self):
        """Test has_dependencies property."""
        node_with = DependencyNode(
            feature_id="f1", dependencies=frozenset({"f0"})
        )
        node_without = DependencyNode(feature_id="f2")

        assert node_with.has_dependencies is True
        assert node_without.has_dependencies is False

    def test_has_dependents(self):
        """Test has_dependents property."""
        node_with = DependencyNode(
            feature_id="f1", dependents=frozenset({"f2"})
        )
        node_without = DependencyNode(feature_id="f2")

        assert node_with.has_dependents is True
        assert node_without.has_dependents is False

    def test_node_immutable(self):
        """Test DependencyNode is immutable."""
        node = DependencyNode(feature_id="f1")
        with pytest.raises(AttributeError):
            node.feature_id = "f2"


# DependencyPath Tests


class TestDependencyPath:
    """Tests for DependencyPath dataclass."""

    def test_path_attributes(self):
        """Test DependencyPath stores attributes."""
        path = DependencyPath(nodes=("f1", "f2", "f3"), is_cycle=False)

        assert path.nodes == ("f1", "f2", "f3")
        assert path.is_cycle is False

    def test_path_length(self):
        """Test DependencyPath length."""
        path = DependencyPath(nodes=("f1", "f2", "f3"))
        assert len(path) == 3

    def test_path_iteration(self):
        """Test DependencyPath iteration."""
        path = DependencyPath(nodes=("f1", "f2", "f3"))
        assert list(path) == ["f1", "f2", "f3"]


# DependencyGraph Construction Tests


class TestDependencyGraphConstruction:
    """Tests for DependencyGraph construction."""

    def test_from_prd_simple(self, simple_prd):
        """Test building graph from simple PRD."""
        graph = DependencyGraph.from_prd(simple_prd)

        assert graph.node_count == 3
        assert graph.edge_count == 0

    def test_from_prd_chain(self, chain_prd):
        """Test building graph from chain PRD."""
        graph = DependencyGraph.from_prd(chain_prd)

        assert graph.node_count == 3
        assert graph.edge_count == 2

    def test_from_prd_diamond(self, diamond_prd):
        """Test building graph from diamond PRD."""
        graph = DependencyGraph.from_prd(diamond_prd)

        assert graph.node_count == 4
        assert graph.edge_count == 4

    def test_from_prd_with_validation(self, chain_prd):
        """Test from_prd validates by default."""
        # Should not raise
        graph = DependencyGraph.from_prd(chain_prd, validate=True)
        assert graph.node_count == 3

    def test_from_prd_cycle_raises(self, cycle_prd):
        """Test from_prd raises on cycles."""
        with pytest.raises(CircularDependencyError):
            DependencyGraph.from_prd(cycle_prd, validate=True)

    def test_from_prd_cycle_no_validation(self, cycle_prd):
        """Test from_prd allows cycles without validation."""
        graph = DependencyGraph.from_prd(cycle_prd, validate=False)
        assert graph.node_count == 3

    def test_from_prd_missing_dependency_raises(self, project):
        """Test from_prd raises on missing dependencies."""
        features = (
            Feature(
                id="f1",
                description="Feature 1",
                passes=False,
                dependencies=("nonexistent",),
            ),
        )
        prd = PRD(project=project, features=features)

        with pytest.raises(MissingDependencyError) as exc_info:
            DependencyGraph.from_prd(prd, validate=True)

        assert exc_info.value.feature_id == "f1"
        assert exc_info.value.missing_id == "nonexistent"

    def test_from_prd_builds_dependents(self, chain_prd):
        """Test from_prd builds dependent relationships."""
        graph = DependencyGraph.from_prd(chain_prd)

        f1_node = graph.get_node("f1")
        f2_node = graph.get_node("f2")

        assert "f2" in f1_node.dependents
        assert "f3" in f2_node.dependents


# Node Query Tests


class TestDependencyGraphNodeQueries:
    """Tests for node query methods."""

    def test_get_node_exists(self, simple_prd):
        """Test get_node for existing node."""
        graph = DependencyGraph.from_prd(simple_prd)
        node = graph.get_node("f1")

        assert node is not None
        assert node.feature_id == "f1"

    def test_get_node_not_exists(self, simple_prd):
        """Test get_node for non-existent node."""
        graph = DependencyGraph.from_prd(simple_prd)
        node = graph.get_node("nonexistent")

        assert node is None

    def test_get_all_nodes(self, simple_prd):
        """Test get_all_nodes returns all nodes."""
        graph = DependencyGraph.from_prd(simple_prd)
        nodes = graph.get_all_nodes()

        assert len(nodes) == 3
        ids = {n.feature_id for n in nodes}
        assert ids == {"f1", "f2", "f3"}


# Ready Check Tests


class TestDependencyGraphReadyCheck:
    """Tests for is_ready and related methods."""

    def test_is_ready_no_deps(self, simple_prd):
        """Test is_ready for feature without dependencies."""
        graph = DependencyGraph.from_prd(simple_prd)

        assert graph.is_ready("f1") is True
        assert graph.is_ready("f2") is True

    def test_is_ready_complete_feature(self, simple_prd):
        """Test is_ready returns False for complete feature."""
        graph = DependencyGraph.from_prd(simple_prd)

        assert graph.is_ready("f3") is False  # Already complete

    def test_is_ready_with_incomplete_deps(self, chain_prd):
        """Test is_ready with incomplete dependencies."""
        graph = DependencyGraph.from_prd(chain_prd)

        assert graph.is_ready("f1") is True  # No deps
        assert graph.is_ready("f2") is False  # f1 not complete
        assert graph.is_ready("f3") is False  # f2 not complete

    def test_is_ready_with_complete_deps(self, diamond_prd):
        """Test is_ready with complete dependencies."""
        graph = DependencyGraph.from_prd(diamond_prd)

        assert graph.is_ready("f2") is True  # f1 is complete
        assert graph.is_ready("f3") is True  # f1 is complete
        assert graph.is_ready("f4") is False  # f2, f3 not complete

    def test_is_ready_nonexistent(self, simple_prd):
        """Test is_ready for non-existent feature."""
        graph = DependencyGraph.from_prd(simple_prd)

        assert graph.is_ready("nonexistent") is False

    def test_get_ready_features(self, diamond_prd):
        """Test get_ready_features."""
        graph = DependencyGraph.from_prd(diamond_prd)
        ready = graph.get_ready_features()

        assert "f2" in ready
        assert "f3" in ready
        assert "f1" not in ready  # Complete
        assert "f4" not in ready  # Blocked


# Blocker Query Tests


class TestDependencyGraphBlockerQueries:
    """Tests for blocker-related methods."""

    def test_get_blockers_none(self, simple_prd):
        """Test get_blockers when no blockers."""
        graph = DependencyGraph.from_prd(simple_prd)
        blockers = graph.get_blockers("f1")

        assert blockers == []

    def test_get_blockers_with_blockers(self, chain_prd):
        """Test get_blockers with incomplete dependencies."""
        graph = DependencyGraph.from_prd(chain_prd)

        assert graph.get_blockers("f2") == ["f1"]
        assert graph.get_blockers("f3") == ["f2"]

    def test_get_blockers_nonexistent(self, simple_prd):
        """Test get_blockers for non-existent feature."""
        graph = DependencyGraph.from_prd(simple_prd)

        assert graph.get_blockers("nonexistent") == []

    def test_get_blocked_by(self, chain_prd):
        """Test get_blocked_by."""
        graph = DependencyGraph.from_prd(chain_prd)

        assert "f2" in graph.get_blocked_by("f1")
        assert "f3" in graph.get_blocked_by("f2")
        assert graph.get_blocked_by("f3") == []

    def test_get_blocked_features(self, chain_prd):
        """Test get_blocked_features."""
        graph = DependencyGraph.from_prd(chain_prd)
        blocked = graph.get_blocked_features()

        assert "f2" in blocked
        assert "f3" in blocked
        assert "f1" not in blocked


# Status Query Tests


class TestDependencyGraphStatusQueries:
    """Tests for feature status queries."""

    def test_get_complete_features(self, diamond_prd):
        """Test get_complete_features."""
        graph = DependencyGraph.from_prd(diamond_prd)
        complete = graph.get_complete_features()

        assert complete == ["f1"]

    def test_get_incomplete_features(self, diamond_prd):
        """Test get_incomplete_features."""
        graph = DependencyGraph.from_prd(diamond_prd)
        incomplete = graph.get_incomplete_features()

        assert set(incomplete) == {"f2", "f3", "f4"}


# Execution Order Tests


class TestDependencyGraphExecutionOrder:
    """Tests for execution order (topological sort)."""

    def test_execution_order_simple(self, simple_prd):
        """Test execution order for simple graph."""
        graph = DependencyGraph.from_prd(simple_prd)
        order = graph.get_execution_order()

        assert len(order) == 3
        # All can be done in any order, but priority should sort
        assert order[0] == "f1"  # P0
        assert order[1] == "f2"  # P1

    def test_execution_order_chain(self, chain_prd):
        """Test execution order for chain graph."""
        graph = DependencyGraph.from_prd(chain_prd)
        order = graph.get_execution_order()

        assert order == ["f1", "f2", "f3"]

    def test_execution_order_diamond(self, diamond_prd):
        """Test execution order for diamond graph."""
        graph = DependencyGraph.from_prd(diamond_prd)
        order = graph.get_execution_order()

        # f1 first, then f2/f3 (same priority), then f4
        assert order[0] == "f1"
        assert set(order[1:3]) == {"f2", "f3"}
        assert order[3] == "f4"

    def test_execution_order_cycle_raises(self, cycle_prd):
        """Test execution order raises on cycles."""
        graph = DependencyGraph.from_prd(cycle_prd, validate=False)

        with pytest.raises(CircularDependencyError):
            graph.get_execution_order()


# Cycle Detection Tests


class TestDependencyGraphCycleDetection:
    """Tests for cycle detection."""

    def test_find_cycles_none(self, simple_prd):
        """Test find_cycles with no cycles."""
        graph = DependencyGraph.from_prd(simple_prd)
        cycles = graph.find_cycles()

        assert cycles == []

    def test_find_cycles_chain_no_cycle(self, chain_prd):
        """Test find_cycles with chain (no cycle)."""
        graph = DependencyGraph.from_prd(chain_prd)
        cycles = graph.find_cycles()

        assert cycles == []

    def test_find_cycles_with_cycle(self, cycle_prd):
        """Test find_cycles detects cycle."""
        graph = DependencyGraph.from_prd(cycle_prd, validate=False)
        cycles = graph.find_cycles()

        assert len(cycles) > 0
        cycle = cycles[0]
        assert len(cycle) >= 2

    def test_has_cycles_false(self, simple_prd):
        """Test has_cycles returns False."""
        graph = DependencyGraph.from_prd(simple_prd)
        assert graph.has_cycles() is False

    def test_has_cycles_true(self, cycle_prd):
        """Test has_cycles returns True."""
        graph = DependencyGraph.from_prd(cycle_prd, validate=False)
        assert graph.has_cycles() is True


# Depth Tests


class TestDependencyGraphDepth:
    """Tests for depth calculation."""

    def test_get_depth_root(self, chain_prd):
        """Test get_depth for root node."""
        graph = DependencyGraph.from_prd(chain_prd)
        assert graph.get_depth("f1") == 0

    def test_get_depth_chain(self, chain_prd):
        """Test get_depth for chain."""
        graph = DependencyGraph.from_prd(chain_prd)

        assert graph.get_depth("f1") == 0
        assert graph.get_depth("f2") == 1
        assert graph.get_depth("f3") == 2

    def test_get_depth_diamond(self, diamond_prd):
        """Test get_depth for diamond."""
        graph = DependencyGraph.from_prd(diamond_prd)

        assert graph.get_depth("f1") == 0
        assert graph.get_depth("f2") == 1
        assert graph.get_depth("f3") == 1
        assert graph.get_depth("f4") == 2

    def test_get_depth_nonexistent(self, simple_prd):
        """Test get_depth for non-existent node."""
        graph = DependencyGraph.from_prd(simple_prd)
        assert graph.get_depth("nonexistent") == -1


# Path Tests


class TestDependencyGraphPath:
    """Tests for path finding."""

    def test_get_path_exists(self, chain_prd):
        """Test get_path for existing path."""
        graph = DependencyGraph.from_prd(chain_prd)
        path = graph.get_path("f3", "f1")

        assert path is not None
        assert path.nodes == ("f3", "f2", "f1")
        assert path.is_cycle is False

    def test_get_path_no_path(self, chain_prd):
        """Test get_path when no path exists."""
        graph = DependencyGraph.from_prd(chain_prd)
        path = graph.get_path("f1", "f3")  # Wrong direction

        assert path is None

    def test_get_path_self(self, simple_prd):
        """Test get_path from node to itself."""
        graph = DependencyGraph.from_prd(simple_prd)
        path = graph.get_path("f1", "f1")

        assert path is not None
        assert path.nodes == ("f1",)

    def test_get_path_nonexistent(self, simple_prd):
        """Test get_path with non-existent nodes."""
        graph = DependencyGraph.from_prd(simple_prd)

        assert graph.get_path("nonexistent", "f1") is None
        assert graph.get_path("f1", "nonexistent") is None


# Critical Path Tests


class TestDependencyGraphCriticalPath:
    """Tests for critical path finding."""

    def test_critical_path_chain(self, chain_prd):
        """Test get_critical_path for chain."""
        graph = DependencyGraph.from_prd(chain_prd)
        path = graph.get_critical_path()

        assert path == ["f1", "f2", "f3"]

    def test_critical_path_diamond(self, diamond_prd):
        """Test get_critical_path for diamond."""
        graph = DependencyGraph.from_prd(diamond_prd)
        path = graph.get_critical_path()

        assert len(path) == 3
        assert path[0] == "f1"
        assert path[1] in ("f2", "f3")
        assert path[2] == "f4"

    def test_critical_path_empty(self, project):
        """Test get_critical_path for empty graph."""
        prd = PRD(project=project, features=())
        graph = DependencyGraph.from_prd(prd)
        path = graph.get_critical_path()

        assert path == []


# Visualization Tests


class TestDependencyGraphVisualization:
    """Tests for graph visualization."""

    def test_to_dot(self, chain_prd):
        """Test to_dot generates valid DOT."""
        graph = DependencyGraph.from_prd(chain_prd)
        dot = graph.to_dot()

        assert "digraph DependencyGraph" in dot
        assert '"f1"' in dot
        assert '"f2"' in dot
        assert '"f3"' in dot
        assert '"f2" -> "f1"' in dot
        assert '"f3" -> "f2"' in dot

    def test_to_dot_highlights_ready(self, diamond_prd):
        """Test to_dot highlights ready features."""
        graph = DependencyGraph.from_prd(diamond_prd)
        dot = graph.to_dot(highlight_ready=True)

        # f2 and f3 are ready (f1 is complete)
        assert "lightyellow" in dot

    def test_to_ascii(self, chain_prd):
        """Test to_ascii generates output."""
        graph = DependencyGraph.from_prd(chain_prd)
        ascii_art = graph.to_ascii()

        assert "Dependency Graph:" in ascii_art
        assert "f1" in ascii_art
        assert "f2" in ascii_art
        assert "f3" in ascii_art
        assert "Depth 0:" in ascii_art
        assert "Depth 1:" in ascii_art
        assert "Depth 2:" in ascii_art

    def test_to_ascii_empty(self, project):
        """Test to_ascii for empty graph."""
        prd = PRD(project=project, features=())
        graph = DependencyGraph.from_prd(prd)
        ascii_art = graph.to_ascii()

        assert "empty graph" in ascii_art


# Edge Cases


class TestDependencyGraphEdgeCases:
    """Tests for edge cases."""

    def test_empty_graph(self, project):
        """Test empty graph."""
        prd = PRD(project=project, features=())
        graph = DependencyGraph.from_prd(prd)

        assert graph.node_count == 0
        assert graph.edge_count == 0
        assert graph.get_ready_features() == []
        assert graph.get_execution_order() == []

    def test_single_node_graph(self, project):
        """Test graph with single node."""
        features = (
            Feature(id="f1", description="Feature 1", passes=False),
        )
        prd = PRD(project=project, features=features)
        graph = DependencyGraph.from_prd(prd)

        assert graph.node_count == 1
        assert graph.edge_count == 0
        assert graph.is_ready("f1") is True
        assert graph.get_execution_order() == ["f1"]

    def test_all_complete(self, project):
        """Test graph where all features are complete."""
        features = (
            Feature(id="f1", description="Feature 1", passes=True),
            Feature(id="f2", description="Feature 2", passes=True),
        )
        prd = PRD(project=project, features=features)
        graph = DependencyGraph.from_prd(prd)

        assert graph.get_ready_features() == []
        assert graph.get_complete_features() == ["f1", "f2"]

    def test_self_dependency(self, project):
        """Test feature depending on itself."""
        features = (
            Feature(
                id="f1",
                description="Feature 1",
                passes=False,
                dependencies=("f1",),
            ),
        )
        prd = PRD(project=project, features=features)

        with pytest.raises(CircularDependencyError):
            DependencyGraph.from_prd(prd, validate=True)

    def test_multiple_roots(self, project):
        """Test graph with multiple root nodes."""
        features = (
            Feature(id="f1", description="Feature 1", passes=False, priority=0),
            Feature(id="f2", description="Feature 2", passes=False, priority=1),
            Feature(
                id="f3",
                description="Feature 3",
                passes=False,
                priority=2,
                dependencies=("f1", "f2"),
            ),
        )
        prd = PRD(project=project, features=features)
        graph = DependencyGraph.from_prd(prd)

        ready = graph.get_ready_features()
        assert set(ready) == {"f1", "f2"}
        assert ready[0] == "f1"  # Higher priority
