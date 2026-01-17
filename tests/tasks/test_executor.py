"""Tests for task executor and single-feature constraint."""

import json
import pytest
import subprocess
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
from ralph_agi.tasks.executor import ExecutionContext, _sanitize_branch_name


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


# =============================================================================
# Worktree Isolation Fixtures
# =============================================================================


@pytest.fixture
def git_repo(tmp_path):
    """Create a git repository for worktree testing."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Initialize repo
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return repo


@pytest.fixture
def git_repo_with_prd(git_repo, sample_prd_data):
    """Create a git repo with PRD.json file."""
    prd_file = git_repo / "PRD.json"
    prd_file.write_text(json.dumps(sample_prd_data, indent=2))
    subprocess.run(["git", "add", "PRD.json"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add PRD.json"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    return git_repo, prd_file


# =============================================================================
# Sanitize Branch Name Tests
# =============================================================================


class TestSanitizeBranchName:
    """Tests for _sanitize_branch_name helper."""

    def test_simple_name_unchanged(self):
        """Simple names pass through unchanged."""
        assert _sanitize_branch_name("feature-123") == "feature-123"

    def test_spaces_replaced(self):
        """Spaces are replaced with hyphens."""
        assert _sanitize_branch_name("my feature") == "my-feature"

    def test_special_chars_replaced(self):
        """Special git chars are replaced with hyphens."""
        assert _sanitize_branch_name("feature~1") == "feature-1"
        assert _sanitize_branch_name("feature^2") == "feature-2"
        assert _sanitize_branch_name("feature:name") == "feature-name"
        assert _sanitize_branch_name("feature?test") == "feature-test"
        assert _sanitize_branch_name("feature*name") == "feature-name"
        assert _sanitize_branch_name("feature[0]") == "feature-0"

    def test_consecutive_dots_replaced(self):
        """Consecutive dots are replaced."""
        assert _sanitize_branch_name("feature..name") == "feature-name"

    def test_leading_trailing_stripped(self):
        """Leading/trailing dots, hyphens, slashes stripped."""
        assert _sanitize_branch_name(".feature") == "feature"
        assert _sanitize_branch_name("feature.") == "feature"
        assert _sanitize_branch_name("-feature-") == "feature"
        assert _sanitize_branch_name("/feature/") == "feature"

    def test_empty_becomes_task(self):
        """Empty string becomes 'task'."""
        assert _sanitize_branch_name("") == "task"
        assert _sanitize_branch_name("...") == "task"


# =============================================================================
# ExecutionContext Worktree Tests
# =============================================================================


class TestExecutionContextWorktree:
    """Tests for ExecutionContext worktree properties."""

    def test_work_dir_without_worktree(self, sample_prd_file):
        """work_dir returns PRD parent when no worktree."""
        from datetime import datetime, timezone

        ctx = ExecutionContext(
            feature=Feature(id="test", description="Test", passes=False),
            started_at=datetime.now(timezone.utc),
            prd_path=sample_prd_file,
        )

        assert ctx.work_dir == sample_prd_file.parent
        assert ctx.is_isolated is False
        assert ctx.worktree_path is None

    def test_work_dir_with_worktree(self, sample_prd_file, tmp_path):
        """work_dir returns worktree path when set."""
        from datetime import datetime, timezone

        worktree = tmp_path / "worktree"
        ctx = ExecutionContext(
            feature=Feature(id="test", description="Test", passes=False),
            started_at=datetime.now(timezone.utc),
            prd_path=sample_prd_file,
            worktree_path=worktree,
            branch_name="ralph/test",
        )

        assert ctx.work_dir == worktree
        assert ctx.is_isolated is True
        assert ctx.branch_name == "ralph/test"


# =============================================================================
# TaskExecutor Worktree Isolation Tests
# =============================================================================


class TestTaskExecutorWorktreeIsolation:
    """Tests for TaskExecutor with worktree isolation."""

    def test_requires_repo_path_when_enabled(self):
        """Enabling isolation requires repo_path."""
        with pytest.raises(ValueError) as exc_info:
            TaskExecutor(enable_worktree_isolation=True)

        assert "repo_path is required" in str(exc_info.value)

    def test_disabled_by_default(self):
        """Worktree isolation is disabled by default."""
        executor = TaskExecutor()
        status = executor.get_status()

        assert status["worktree_isolation"] is False

    def test_status_includes_worktree_info(self, git_repo_with_prd):
        """Status includes worktree info when enabled."""
        repo, prd_file = git_repo_with_prd
        executor = TaskExecutor(
            enable_worktree_isolation=True,
            repo_path=repo,
        )

        ctx = executor.begin_task(prd_file)
        status = executor.get_status()

        assert status["worktree_isolation"] is True
        assert status["worktree_path"] is not None
        assert status["branch_name"] is not None
        assert "ralph/" in status["branch_name"]

        # Cleanup
        executor.abort_task(cleanup_worktree=True)

    def test_creates_worktree_on_begin(self, git_repo_with_prd):
        """begin_task creates worktree when isolation enabled."""
        repo, prd_file = git_repo_with_prd
        executor = TaskExecutor(
            enable_worktree_isolation=True,
            repo_path=repo,
        )

        ctx = executor.begin_task(prd_file)

        assert ctx.is_isolated is True
        assert ctx.worktree_path is not None
        assert ctx.worktree_path.exists()
        assert ctx.branch_name.startswith("ralph/")

        # Cleanup
        executor.abort_task(cleanup_worktree=True)

    def test_worktree_branch_naming(self, git_repo_with_prd):
        """Worktree branch follows ralph/<task-id> convention."""
        repo, prd_file = git_repo_with_prd
        executor = TaskExecutor(
            enable_worktree_isolation=True,
            repo_path=repo,
        )

        ctx = executor.begin_task(prd_file)

        # First task is feature-1 (P0)
        assert ctx.branch_name == "ralph/feature-1"

        # Cleanup
        executor.abort_task(cleanup_worktree=True)

    def test_worktree_path_naming(self, git_repo_with_prd):
        """Worktree path follows ralph-<task-id> convention."""
        repo, prd_file = git_repo_with_prd
        executor = TaskExecutor(
            enable_worktree_isolation=True,
            repo_path=repo,
        )

        ctx = executor.begin_task(prd_file)

        # Path should be in parent directory of repo
        assert ctx.worktree_path.parent == repo.parent
        assert ctx.worktree_path.name == "ralph-feature-1"

        # Cleanup
        executor.abort_task(cleanup_worktree=True)

    def test_custom_worktree_base(self, git_repo_with_prd, tmp_path):
        """Custom worktree_base changes worktree location."""
        repo, prd_file = git_repo_with_prd
        worktree_base = tmp_path / "worktrees"
        worktree_base.mkdir()

        executor = TaskExecutor(
            enable_worktree_isolation=True,
            repo_path=repo,
            worktree_base=worktree_base,
        )

        ctx = executor.begin_task(prd_file)

        assert ctx.worktree_path.parent == worktree_base
        assert ctx.worktree_path.exists()

        # Cleanup
        executor.abort_task(cleanup_worktree=True)

    def test_abort_with_cleanup_removes_worktree(self, git_repo_with_prd):
        """abort_task with cleanup_worktree removes the worktree."""
        repo, prd_file = git_repo_with_prd
        executor = TaskExecutor(
            enable_worktree_isolation=True,
            repo_path=repo,
        )

        ctx = executor.begin_task(prd_file)
        worktree_path = ctx.worktree_path

        assert worktree_path.exists()

        executor.abort_task(cleanup_worktree=True)

        # Worktree should be removed
        assert not worktree_path.exists()

    def test_abort_without_cleanup_preserves_worktree(self, git_repo_with_prd):
        """abort_task without cleanup preserves the worktree."""
        repo, prd_file = git_repo_with_prd
        executor = TaskExecutor(
            enable_worktree_isolation=True,
            repo_path=repo,
        )

        ctx = executor.begin_task(prd_file)
        worktree_path = ctx.worktree_path

        executor.abort_task(cleanup_worktree=False)

        # Worktree should still exist
        assert worktree_path.exists()

        # Manual cleanup for test
        from ralph_agi.tools.git import GitTools
        git = GitTools(repo_path=repo)
        git.worktree_remove(str(worktree_path), force=True)

    def test_complete_preserves_worktree(self, git_repo_with_prd):
        """complete_task preserves worktree for later merge."""
        repo, prd_file = git_repo_with_prd
        executor = TaskExecutor(
            enable_worktree_isolation=True,
            repo_path=repo,
        )

        ctx = executor.begin_task(prd_file)
        worktree_path = ctx.worktree_path

        executor.complete_task(ctx)

        # Worktree should still exist (for merge)
        assert worktree_path.exists()

        # Manual cleanup for test
        from ralph_agi.tools.git import GitTools
        git = GitTools(repo_path=repo)
        git.worktree_remove(str(worktree_path), force=True)

    def test_without_isolation_no_worktree(self, git_repo_with_prd):
        """Without isolation, no worktree is created."""
        repo, prd_file = git_repo_with_prd
        executor = TaskExecutor(
            enable_worktree_isolation=False,
            repo_path=repo,
        )

        ctx = executor.begin_task(prd_file)

        assert ctx.is_isolated is False
        assert ctx.worktree_path is None
        assert ctx.work_dir == prd_file.parent

        executor.abort_task()
