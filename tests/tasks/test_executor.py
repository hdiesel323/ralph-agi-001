"""Tests for task executor and single-feature constraint."""

import json
import pytest
import threading
import time
from pathlib import Path

from ralph_agi.tasks import (
    Feature,
    PRD,
    Project,
    TaskAnalysis,
    TaskExecutionError,
    TaskExecutor,
    analyze_task_size,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_prd_data():
    """Sample PRD data for testing."""
    return {
        "project": {
            "name": "Test Project",
            "description": "A test project",
        },
        "features": [
            {
                "id": "feature-1",
                "description": "First feature (P0)",
                "passes": False,
                "priority": 0,
            },
            {
                "id": "feature-2",
                "description": "Second feature (P1)",
                "passes": False,
                "priority": 1,
            },
            {
                "id": "feature-3",
                "description": "Third feature (complete)",
                "passes": True,
            },
        ],
    }


@pytest.fixture
def sample_prd_file(tmp_path, sample_prd_data):
    """Create a sample PRD.json file."""
    prd_file = tmp_path / "PRD.json"
    prd_file.write_text(json.dumps(sample_prd_data, indent=2))
    return prd_file


@pytest.fixture
def executor():
    """Create a TaskExecutor instance."""
    return TaskExecutor()


# =============================================================================
# TaskAnalysis Tests
# =============================================================================


class TestTaskAnalysis:
    """Tests for TaskAnalysis dataclass."""

    def test_analysis_attributes(self):
        """TaskAnalysis stores analysis results."""
        analysis = TaskAnalysis(
            is_large=True,
            warnings=("Warning 1", "Warning 2"),
            suggestions=("Suggestion 1",),
        )
        assert analysis.is_large is True
        assert len(analysis.warnings) == 2
        assert len(analysis.suggestions) == 1


# =============================================================================
# analyze_task_size Tests
# =============================================================================


class TestAnalyzeTaskSize:
    """Tests for analyze_task_size function."""

    def test_small_task_not_large(self):
        """Small task is not marked as large."""
        feature = Feature(
            id="f1",
            description="Short description",
            passes=False,
            steps=("Step 1", "Step 2"),
            acceptance_criteria=("AC 1",),
        )

        analysis = analyze_task_size(feature)

        assert analysis.is_large is False
        assert len(analysis.warnings) == 0

    def test_many_steps_triggers_warning(self):
        """More than 10 steps triggers warning."""
        feature = Feature(
            id="f1",
            description="Test",
            passes=False,
            steps=tuple(f"Step {i}" for i in range(15)),
        )

        analysis = analyze_task_size(feature)

        assert analysis.is_large is True
        assert any("15 steps" in w for w in analysis.warnings)
        assert any("Break into smaller" in s for s in analysis.suggestions)

    def test_long_description_triggers_warning(self):
        """Description over 500 chars triggers warning."""
        feature = Feature(
            id="f1",
            description="x" * 600,
            passes=False,
        )

        analysis = analyze_task_size(feature)

        assert analysis.is_large is True
        assert any("600 chars" in w for w in analysis.warnings)

    def test_many_acceptance_criteria_triggers_warning(self):
        """More than 8 acceptance criteria triggers warning."""
        feature = Feature(
            id="f1",
            description="Test",
            passes=False,
            acceptance_criteria=tuple(f"AC {i}" for i in range(10)),
        )

        analysis = analyze_task_size(feature)

        assert analysis.is_large is True
        assert any("10 acceptance criteria" in w for w in analysis.warnings)

    def test_multiple_warnings(self):
        """Multiple issues produce multiple warnings."""
        feature = Feature(
            id="f1",
            description="x" * 600,
            passes=False,
            steps=tuple(f"Step {i}" for i in range(15)),
            acceptance_criteria=tuple(f"AC {i}" for i in range(10)),
        )

        analysis = analyze_task_size(feature)

        assert analysis.is_large is True
        assert len(analysis.warnings) == 3
        assert len(analysis.suggestions) == 3


# =============================================================================
# TaskExecutor Basic Tests
# =============================================================================


class TestTaskExecutorBasic:
    """Basic tests for TaskExecutor."""

    def test_initial_state(self, executor):
        """Executor starts with no task."""
        assert executor.is_executing is False
        assert executor.current_task is None

    def test_begin_task_selects_task(self, executor, sample_prd_file):
        """begin_task selects highest priority task."""
        ctx = executor.begin_task(sample_prd_file)

        assert ctx is not None
        assert ctx.feature.id == "feature-1"  # P0 highest priority
        assert executor.is_executing is True

    def test_begin_task_returns_context(self, executor, sample_prd_file):
        """begin_task returns ExecutionContext with all info."""
        ctx = executor.begin_task(sample_prd_file)

        assert ctx.feature.id == "feature-1"
        assert ctx.prd_path == sample_prd_file
        assert ctx.started_at is not None
        assert isinstance(ctx.analysis, TaskAnalysis)

    def test_complete_task_updates_prd(self, executor, sample_prd_file):
        """complete_task marks task as done in PRD."""
        ctx = executor.begin_task(sample_prd_file)
        prd = executor.complete_task(ctx)

        assert prd.get_feature("feature-1").passes is True
        assert executor.is_executing is False

    def test_complete_task_persists(self, executor, sample_prd_file):
        """complete_task persists changes to file."""
        ctx = executor.begin_task(sample_prd_file)
        executor.complete_task(ctx)

        # Reload and verify
        data = json.loads(sample_prd_file.read_text())
        f1 = next(f for f in data["features"] if f["id"] == "feature-1")
        assert f1["passes"] is True

    def test_abort_task_releases_lock(self, executor, sample_prd_file):
        """abort_task releases the task without marking complete."""
        ctx = executor.begin_task(sample_prd_file)
        aborted = executor.abort_task("test abort")

        assert aborted.id == "feature-1"
        assert executor.is_executing is False

        # PRD unchanged
        data = json.loads(sample_prd_file.read_text())
        f1 = next(f for f in data["features"] if f["id"] == "feature-1")
        assert f1["passes"] is False


# =============================================================================
# TaskExecutor Lock Tests
# =============================================================================


class TestTaskExecutorLocking:
    """Tests for task locking behavior."""

    def test_cannot_begin_while_executing(self, executor, sample_prd_file):
        """Cannot begin a new task while one is executing."""
        executor.begin_task(sample_prd_file)

        with pytest.raises(TaskExecutionError) as exc_info:
            executor.begin_task(sample_prd_file)

        assert "Already executing" in str(exc_info.value)

    def test_cannot_complete_wrong_task(self, executor, sample_prd_file, tmp_path):
        """Cannot complete with mismatched context."""
        from ralph_agi.tasks import ExecutionContext
        from datetime import datetime, timezone

        ctx = executor.begin_task(sample_prd_file)

        # Create fake context for different task
        fake_feature = Feature(id="fake", description="Fake", passes=False)
        fake_ctx = ExecutionContext(
            feature=fake_feature,
            started_at=datetime.now(timezone.utc),
            prd_path=sample_prd_file,
        )

        with pytest.raises(TaskExecutionError) as exc_info:
            executor.complete_task(fake_ctx)

        assert "Context mismatch" in str(exc_info.value)

    def test_cannot_complete_without_begin(self, executor, sample_prd_file):
        """Cannot complete without starting a task."""
        from ralph_agi.tasks import ExecutionContext
        from datetime import datetime, timezone

        feature = Feature(id="f1", description="Test", passes=False)
        ctx = ExecutionContext(
            feature=feature,
            started_at=datetime.now(timezone.utc),
            prd_path=sample_prd_file,
        )

        with pytest.raises(TaskExecutionError) as exc_info:
            executor.complete_task(ctx)

        assert "No task is currently being executed" in str(exc_info.value)

    def test_abort_when_not_executing(self, executor):
        """Abort when not executing returns None."""
        result = executor.abort_task()

        assert result is None


# =============================================================================
# TaskExecutor All Complete Tests
# =============================================================================


class TestTaskExecutorAllComplete:
    """Tests for when all tasks are complete."""

    def test_begin_returns_none_when_all_complete(self, executor, tmp_path):
        """begin_task returns None when all tasks complete."""
        prd_file = tmp_path / "PRD.json"
        data = {
            "project": {"name": "Test", "description": "Test"},
            "features": [
                {"id": "f1", "description": "Done", "passes": True},
            ],
        }
        prd_file.write_text(json.dumps(data))

        ctx = executor.begin_task(prd_file)

        assert ctx is None
        assert executor.is_executing is False


# =============================================================================
# TaskExecutor Status Tests
# =============================================================================


class TestTaskExecutorStatus:
    """Tests for executor status reporting."""

    def test_status_not_executing(self, executor):
        """Status when not executing."""
        status = executor.get_status()

        assert status["executing"] is False
        assert status["task_id"] is None

    def test_status_executing(self, executor, sample_prd_file):
        """Status when executing."""
        executor.begin_task(sample_prd_file)
        status = executor.get_status()

        assert status["executing"] is True
        assert status["task_id"] == "feature-1"
        assert status["priority"] == "P0"
        assert status["elapsed_seconds"] is not None


# =============================================================================
# ExecutionContext Tests
# =============================================================================


class TestExecutionContext:
    """Tests for ExecutionContext."""

    def test_elapsed_seconds(self, executor, sample_prd_file):
        """elapsed_seconds tracks time."""
        ctx = executor.begin_task(sample_prd_file)
        time.sleep(0.1)

        assert ctx.elapsed_seconds >= 0.1


# =============================================================================
# Thread Safety Tests
# =============================================================================


class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_begin_fails(self, executor, sample_prd_file):
        """Concurrent begin attempts should fail gracefully."""
        results = []
        errors = []

        def try_begin():
            try:
                ctx = executor.begin_task(sample_prd_file)
                results.append(ctx)
            except TaskExecutionError as e:
                errors.append(e)

        threads = [threading.Thread(target=try_begin) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one should succeed
        assert len(results) == 1
        assert len(errors) == 4


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge cases and integration tests."""

    def test_accepts_string_path(self, executor, sample_prd_file):
        """begin_task accepts string path."""
        ctx = executor.begin_task(str(sample_prd_file))

        assert ctx is not None

    def test_sequential_task_execution(self, executor, sample_prd_file):
        """Can execute tasks sequentially."""
        # First task
        ctx1 = executor.begin_task(sample_prd_file)
        assert ctx1.feature.id == "feature-1"
        executor.complete_task(ctx1)

        # Second task
        ctx2 = executor.begin_task(sample_prd_file)
        assert ctx2.feature.id == "feature-2"  # Next priority
        executor.complete_task(ctx2)

        # All complete
        ctx3 = executor.begin_task(sample_prd_file)
        assert ctx3 is None

    def test_large_task_warning_logged(self, executor, tmp_path, caplog):
        """Large task warnings are logged."""
        import logging

        prd_file = tmp_path / "PRD.json"
        data = {
            "project": {"name": "Test", "description": "Test"},
            "features": [{
                "id": "f1",
                "description": "Test",
                "passes": False,
                "steps": [f"Step {i}" for i in range(15)],
            }],
        }
        prd_file.write_text(json.dumps(data))

        with caplog.at_level(logging.WARNING):
            executor.begin_task(prd_file)

        assert any("Large task warning" in r.message for r in caplog.records)
