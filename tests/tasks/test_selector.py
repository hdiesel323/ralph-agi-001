"""Tests for task selection algorithm."""

import pytest

from ralph_agi.tasks import (
    Feature,
    PRD,
    Project,
    BlockedReason,
    SelectionResult,
    TaskSelectionError,
    TaskSelector,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def selector():
    """Create a TaskSelector instance."""
    return TaskSelector()


@pytest.fixture
def simple_project():
    """Simple project metadata."""
    return Project(name="Test Project", description="Test description")


def make_prd(features: list[Feature], project: Project = None) -> PRD:
    """Helper to create PRD from features."""
    if project is None:
        project = Project(name="Test", description="Test")
    return PRD(project=project, features=tuple(features))


# =============================================================================
# BlockedReason Tests
# =============================================================================


class TestBlockedReason:
    """Tests for the BlockedReason dataclass."""

    def test_blocked_reason_attributes(self):
        """BlockedReason stores blocking info."""
        reason = BlockedReason(
            feature_id="f1",
            blocking_ids=("f2", "f3"),
            missing_ids=(),
        )
        assert reason.feature_id == "f1"
        assert reason.blocking_ids == ("f2", "f3")
        assert reason.missing_ids == ()

    def test_has_missing_dependencies(self):
        """has_missing_dependencies detects missing deps."""
        with_missing = BlockedReason("f1", (), ("f2",))
        without_missing = BlockedReason("f1", ("f2",), ())

        assert with_missing.has_missing_dependencies is True
        assert without_missing.has_missing_dependencies is False

    def test_reason_text_blocking(self):
        """reason_text shows blocking dependencies."""
        reason = BlockedReason("f1", ("f2", "f3"), ())
        assert "blocked by" in reason.reason_text
        assert "f2" in reason.reason_text
        assert "f3" in reason.reason_text

    def test_reason_text_missing(self):
        """reason_text shows missing dependencies."""
        reason = BlockedReason("f1", (), ("f2",))
        assert "missing dependencies" in reason.reason_text

    def test_reason_text_both(self):
        """reason_text shows both blocking and missing."""
        reason = BlockedReason("f1", ("f2",), ("f3",))
        assert "blocked by" in reason.reason_text
        assert "missing dependencies" in reason.reason_text


# =============================================================================
# SelectionResult Tests
# =============================================================================


class TestSelectionResult:
    """Tests for the SelectionResult dataclass."""

    def test_result_with_task(self):
        """SelectionResult stores task and metadata."""
        task = Feature(id="f1", description="Test", passes=False)
        result = SelectionResult(
            next_task=task,
            ready_tasks=(task,),
            blocked_tasks=(),
            all_complete=False,
        )
        assert result.next_task == task
        assert result.has_ready_tasks is True
        assert result.has_blocked_tasks is False

    def test_result_all_complete(self):
        """SelectionResult for all complete."""
        result = SelectionResult(
            next_task=None,
            ready_tasks=(),
            blocked_tasks=(),
            all_complete=True,
        )
        assert result.all_complete is True
        assert result.has_ready_tasks is False


# =============================================================================
# Basic Selection Tests
# =============================================================================


class TestBasicSelection:
    """Tests for basic task selection."""

    def test_select_incomplete_task(self, selector):
        """Select returns incomplete task."""
        features = [
            Feature(id="f1", description="Test", passes=False),
        ]
        prd = make_prd(features)

        result = selector.select(prd)

        assert result.next_task is not None
        assert result.next_task.id == "f1"

    def test_skip_complete_tasks(self, selector):
        """Select skips complete tasks."""
        features = [
            Feature(id="f1", description="Complete", passes=True),
            Feature(id="f2", description="Incomplete", passes=False),
        ]
        prd = make_prd(features)

        result = selector.select(prd)

        assert result.next_task is not None
        assert result.next_task.id == "f2"

    def test_all_complete_returns_none(self, selector):
        """Select returns None when all complete."""
        features = [
            Feature(id="f1", description="Done", passes=True),
            Feature(id="f2", description="Done", passes=True),
        ]
        prd = make_prd(features)

        result = selector.select(prd)

        assert result.next_task is None
        assert result.all_complete is True

    def test_empty_features_is_complete(self, selector):
        """Empty features means all complete."""
        prd = make_prd([])

        result = selector.select(prd)

        assert result.all_complete is True
        assert result.next_task is None


# =============================================================================
# Priority Tests
# =============================================================================


class TestPrioritySelection:
    """Tests for priority-based selection."""

    def test_select_highest_priority(self, selector):
        """Select returns highest priority task (lowest number)."""
        features = [
            Feature(id="f1", description="P2", passes=False, priority=2),
            Feature(id="f2", description="P0", passes=False, priority=0),
            Feature(id="f3", description="P1", passes=False, priority=1),
        ]
        prd = make_prd(features)

        result = selector.select(prd)

        assert result.next_task.id == "f2"  # P0 is highest

    def test_none_priority_treated_as_p4(self, selector):
        """Tasks without priority treated as P4 (lowest)."""
        features = [
            Feature(id="f1", description="No priority", passes=False),
            Feature(id="f2", description="P3", passes=False, priority=3),
        ]
        prd = make_prd(features)

        result = selector.select(prd)

        assert result.next_task.id == "f2"  # P3 before P4 (None)

    def test_same_priority_stable_order(self, selector):
        """Same priority uses ID for stable ordering."""
        features = [
            Feature(id="b-feature", description="B", passes=False, priority=1),
            Feature(id="a-feature", description="A", passes=False, priority=1),
        ]
        prd = make_prd(features)

        result = selector.select(prd)

        # Should get a-feature (alphabetically first with same priority)
        assert result.next_task.id == "a-feature"

    def test_ready_tasks_sorted_by_priority(self, selector):
        """Ready tasks list is sorted by priority."""
        features = [
            Feature(id="f1", description="P2", passes=False, priority=2),
            Feature(id="f2", description="P0", passes=False, priority=0),
            Feature(id="f3", description="P1", passes=False, priority=1),
        ]
        prd = make_prd(features)

        ready = selector.get_ready_tasks(prd)

        assert [f.id for f in ready] == ["f2", "f3", "f1"]


# =============================================================================
# Dependency Tests
# =============================================================================


class TestDependencySelection:
    """Tests for dependency-aware selection."""

    def test_respect_dependencies(self, selector):
        """Blocked tasks are not selected."""
        features = [
            Feature(id="f1", description="Base", passes=False),
            Feature(id="f2", description="Depends on f1", passes=False, dependencies=("f1",)),
        ]
        prd = make_prd(features)

        result = selector.select(prd)

        assert result.next_task.id == "f1"  # f2 is blocked

    def test_unblocked_after_dependency_complete(self, selector):
        """Task becomes selectable when dependency completes."""
        features = [
            Feature(id="f1", description="Base", passes=True),  # Complete
            Feature(id="f2", description="Depends on f1", passes=False, dependencies=("f1",)),
        ]
        prd = make_prd(features)

        result = selector.select(prd)

        assert result.next_task.id == "f2"

    def test_multiple_dependencies(self, selector):
        """Task blocked until all dependencies complete."""
        features = [
            Feature(id="f1", description="Base 1", passes=True),
            Feature(id="f2", description="Base 2", passes=False),
            Feature(id="f3", description="Depends on both", passes=False, dependencies=("f1", "f2")),
        ]
        prd = make_prd(features)

        result = selector.select(prd)

        assert result.next_task.id == "f2"  # f3 blocked by f2

    def test_missing_dependency_blocks(self, selector):
        """Missing dependency blocks the task."""
        features = [
            Feature(id="f1", description="Depends on missing", passes=False, dependencies=("nonexistent",)),
            Feature(id="f2", description="No deps", passes=False),
        ]
        prd = make_prd(features)

        result = selector.select(prd)

        assert result.next_task.id == "f2"  # f1 is blocked

    def test_get_blocked_tasks(self, selector):
        """get_blocked_tasks returns blocked tasks with reasons."""
        features = [
            Feature(id="f1", description="Base", passes=False),
            Feature(id="f2", description="Blocked", passes=False, dependencies=("f1",)),
        ]
        prd = make_prd(features)

        blocked = selector.get_blocked_tasks(prd)

        assert len(blocked) == 1
        assert blocked[0].feature_id == "f2"
        assert "f1" in blocked[0].blocking_ids

    def test_is_blocked(self, selector):
        """is_blocked returns True for blocked tasks."""
        features = [
            Feature(id="f1", description="Base", passes=False),
            Feature(id="f2", description="Blocked", passes=False, dependencies=("f1",)),
        ]
        prd = make_prd(features)

        f1 = prd.get_feature("f1")
        f2 = prd.get_feature("f2")

        assert selector.is_blocked(f1, prd) is False
        assert selector.is_blocked(f2, prd) is True

    def test_get_blocking_dependencies(self, selector):
        """get_blocking_dependencies returns blocking IDs."""
        features = [
            Feature(id="f1", description="Base", passes=False),
            Feature(id="f2", description="Blocked", passes=False, dependencies=("f1", "missing")),
        ]
        prd = make_prd(features)

        f2 = prd.get_feature("f2")
        blocking = selector.get_blocking_dependencies(f2, prd)

        assert "f1" in blocking
        assert "missing" in blocking


# =============================================================================
# Circular Dependency Tests
# =============================================================================


class TestCircularDependencies:
    """Tests for circular dependency detection."""

    def test_no_circular_dependencies(self, selector):
        """No cycles in valid dependency graph."""
        features = [
            Feature(id="f1", description="Base", passes=False),
            Feature(id="f2", description="Depends on f1", passes=False, dependencies=("f1",)),
            Feature(id="f3", description="Depends on f2", passes=False, dependencies=("f2",)),
        ]
        prd = make_prd(features)

        cycles = selector.detect_circular_dependencies(prd)

        assert len(cycles) == 0

    def test_detect_simple_cycle(self, selector):
        """Detect simple A -> B -> A cycle."""
        features = [
            Feature(id="f1", description="F1", passes=False, dependencies=("f2",)),
            Feature(id="f2", description="F2", passes=False, dependencies=("f1",)),
        ]
        prd = make_prd(features)

        cycles = selector.detect_circular_dependencies(prd)

        assert len(cycles) > 0
        # Check that both f1 and f2 are in some cycle
        all_cycle_nodes = set()
        for cycle in cycles:
            all_cycle_nodes.update(cycle)
        assert "f1" in all_cycle_nodes or "f2" in all_cycle_nodes

    def test_detect_self_cycle(self, selector):
        """Detect self-referential dependency."""
        features = [
            Feature(id="f1", description="Depends on self", passes=False, dependencies=("f1",)),
        ]
        prd = make_prd(features)

        cycles = selector.detect_circular_dependencies(prd)

        assert len(cycles) > 0

    def test_detect_longer_cycle(self, selector):
        """Detect longer cycle A -> B -> C -> A."""
        features = [
            Feature(id="f1", description="F1", passes=False, dependencies=("f2",)),
            Feature(id="f2", description="F2", passes=False, dependencies=("f3",)),
            Feature(id="f3", description="F3", passes=False, dependencies=("f1",)),
        ]
        prd = make_prd(features)

        cycles = selector.detect_circular_dependencies(prd)

        assert len(cycles) > 0

    def test_validate_dependencies_raises_on_cycle(self, selector):
        """validate_dependencies raises TaskSelectionError on cycle."""
        features = [
            Feature(id="f1", description="F1", passes=False, dependencies=("f2",)),
            Feature(id="f2", description="F2", passes=False, dependencies=("f1",)),
        ]
        prd = make_prd(features)

        with pytest.raises(TaskSelectionError) as exc_info:
            selector.validate_dependencies(prd)

        assert "Circular dependencies" in str(exc_info.value)

    def test_validate_dependencies_ok_without_cycle(self, selector):
        """validate_dependencies passes without cycles."""
        features = [
            Feature(id="f1", description="Base", passes=False),
            Feature(id="f2", description="Depends on f1", passes=False, dependencies=("f1",)),
        ]
        prd = make_prd(features)

        # Should not raise
        selector.validate_dependencies(prd)


# =============================================================================
# Convenience Method Tests
# =============================================================================


class TestConvenienceMethods:
    """Tests for convenience methods."""

    def test_get_next_task(self, selector):
        """get_next_task returns just the task."""
        features = [Feature(id="f1", description="Test", passes=False)]
        prd = make_prd(features)

        task = selector.get_next_task(prd)

        assert task is not None
        assert task.id == "f1"

    def test_get_next_task_none(self, selector):
        """get_next_task returns None when all complete."""
        features = [Feature(id="f1", description="Done", passes=True)]
        prd = make_prd(features)

        task = selector.get_next_task(prd)

        assert task is None

    def test_get_ready_tasks_empty(self, selector):
        """get_ready_tasks returns empty list when all blocked."""
        features = [
            Feature(id="f1", description="F1", passes=False, dependencies=("f2",)),
            Feature(id="f2", description="F2", passes=False, dependencies=("f1",)),
        ]
        prd = make_prd(features)

        ready = selector.get_ready_tasks(prd)

        assert len(ready) == 0


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge cases and integration tests."""

    def test_many_features(self, selector):
        """Handle many features efficiently."""
        features = [
            Feature(id=f"f{i}", description=f"Feature {i}", passes=i < 50, priority=i % 5)
            for i in range(100)
        ]
        prd = make_prd(features)

        result = selector.select(prd)

        assert result.next_task is not None
        # Should be the first incomplete P0 feature
        assert result.next_task.priority == 0

    def test_complex_dependency_chain(self, selector):
        """Handle complex dependency chains."""
        features = [
            Feature(id="base", description="Base", passes=True),
            Feature(id="l1-a", description="L1-A", passes=True, dependencies=("base",)),
            Feature(id="l1-b", description="L1-B", passes=False, dependencies=("base",)),
            Feature(id="l2", description="L2", passes=False, dependencies=("l1-a", "l1-b")),
        ]
        prd = make_prd(features)

        result = selector.select(prd)

        assert result.next_task.id == "l1-b"  # l2 is blocked

    def test_all_blocked_no_next_task(self, selector):
        """When all incomplete tasks are blocked, no next task."""
        features = [
            Feature(id="f1", description="F1", passes=False, dependencies=("missing",)),
        ]
        prd = make_prd(features)

        result = selector.select(prd)

        assert result.next_task is None
        assert result.all_complete is False
        assert result.has_blocked_tasks is True
