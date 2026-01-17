"""Tests for worktree cleanup automation."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ralph_agi.tasks.cleanup import (
    WORKTREE_PREFIX,
    CleanupConfig,
    CleanupResult,
    OrphanWorktree,
    WorktreeCleanup,
    create_cleanup_manager,
)
from ralph_agi.tools.git import GitTools, WorktreeInfo


class TestCleanupConfig:
    """Tests for CleanupConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CleanupConfig()
        assert config.cleanup_on_success is True
        assert config.cleanup_on_failure is False
        assert config.force_cleanup is False
        assert config.prune_orphans is True
        assert config.worktree_prefix == WORKTREE_PREFIX

    def test_custom_values(self):
        """Test custom configuration values."""
        config = CleanupConfig(
            cleanup_on_success=False,
            cleanup_on_failure=True,
            force_cleanup=True,
            prune_orphans=False,
            worktree_prefix="custom-",
        )
        assert config.cleanup_on_success is False
        assert config.cleanup_on_failure is True
        assert config.force_cleanup is True
        assert config.prune_orphans is False
        assert config.worktree_prefix == "custom-"


class TestCleanupResult:
    """Tests for CleanupResult."""

    def test_successful_result(self):
        """Test successful cleanup result."""
        result = CleanupResult(
            success=True,
            worktree_path=Path("/tmp/test"),
            method="git_remove",
            branch_deleted=True,
        )
        assert result.success is True
        assert result.method == "git_remove"
        assert result.branch_deleted is True
        assert result.error is None

    def test_failed_result(self):
        """Test failed cleanup result."""
        result = CleanupResult(
            success=False,
            worktree_path=Path("/tmp/test"),
            method="force_remove",
            error="Permission denied",
        )
        assert result.success is False
        assert result.error == "Permission denied"


class TestOrphanWorktree:
    """Tests for OrphanWorktree."""

    def test_basic_orphan(self):
        """Test basic orphan worktree info."""
        orphan = OrphanWorktree(path=Path("/tmp/ralph-test"))
        assert orphan.path == Path("/tmp/ralph-test")
        assert orphan.has_git_dir is False
        assert orphan.branch_hint is None

    def test_orphan_with_git_info(self):
        """Test orphan with git directory info."""
        orphan = OrphanWorktree(
            path=Path("/tmp/ralph-feature"),
            has_git_dir=True,
            branch_hint="ralph/feature",
        )
        assert orphan.has_git_dir is True
        assert orphan.branch_hint == "ralph/feature"


class TestWorktreeCleanupBasic:
    """Basic tests for WorktreeCleanup."""

    @pytest.fixture
    def mock_git(self):
        """Create a mock GitTools instance."""
        git = MagicMock(spec=GitTools)
        git.repo_path = Path("/fake/repo")
        return git

    @pytest.fixture
    def cleanup(self, mock_git):
        """Create a WorktreeCleanup instance with mock git."""
        return WorktreeCleanup(mock_git)

    def test_config_property(self, cleanup):
        """Test config property returns configuration."""
        assert isinstance(cleanup.config, CleanupConfig)

    def test_should_cleanup_on_success_default(self, cleanup):
        """Test should_cleanup_on_success with default config."""
        assert cleanup.should_cleanup_on_success() is True

    def test_should_cleanup_on_failure_default(self, cleanup):
        """Test should_cleanup_on_failure with default config."""
        assert cleanup.should_cleanup_on_failure() is False

    def test_should_cleanup_custom_config(self, mock_git):
        """Test cleanup methods with custom config."""
        config = CleanupConfig(
            cleanup_on_success=False,
            cleanup_on_failure=True,
        )
        cleanup = WorktreeCleanup(mock_git, config)
        assert cleanup.should_cleanup_on_success() is False
        assert cleanup.should_cleanup_on_failure() is True


class TestWorktreeCleanupOperations:
    """Tests for cleanup operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        # Cleanup
        if Path(tmpdir).exists():
            shutil.rmtree(tmpdir)

    @pytest.fixture
    def mock_git(self, temp_dir):
        """Create a mock GitTools with temp directory."""
        git = MagicMock(spec=GitTools)
        git.repo_path = temp_dir / "repo"
        (temp_dir / "repo").mkdir(exist_ok=True)
        return git

    def test_cleanup_already_gone(self, mock_git):
        """Test cleanup of non-existent worktree."""
        cleanup = WorktreeCleanup(mock_git)
        result = cleanup.cleanup_worktree(Path("/nonexistent/path"))

        assert result.success is True
        assert result.method == "already_gone"
        mock_git.worktree_remove.assert_not_called()

    def test_cleanup_via_git_remove(self, mock_git, temp_dir):
        """Test cleanup using git worktree remove."""
        # Create a fake worktree directory
        worktree = temp_dir / "ralph-test"
        worktree.mkdir()

        # Mock successful git removal
        def remove_worktree(path, force=False):
            shutil.rmtree(path)

        mock_git.worktree_remove.side_effect = remove_worktree
        mock_git.worktree_list.return_value = []

        cleanup = WorktreeCleanup(mock_git)
        result = cleanup.cleanup_worktree(worktree)

        assert result.success is True
        assert result.method == "git_remove"
        assert not worktree.exists()

    def test_cleanup_fallback_to_force(self, mock_git, temp_dir):
        """Test fallback to force removal when git fails."""
        # Create a fake worktree directory
        worktree = temp_dir / "ralph-test"
        worktree.mkdir()
        (worktree / "file.txt").write_text("test")

        # Mock git failure
        mock_git.worktree_remove.side_effect = Exception("Git error")
        mock_git.worktree_list.return_value = []

        cleanup = WorktreeCleanup(mock_git)
        result = cleanup.cleanup_worktree(worktree)

        assert result.success is True
        assert result.method == "force_remove"
        assert not worktree.exists()

    def test_cleanup_branch_deletion(self, mock_git, temp_dir):
        """Test branch deletion during cleanup."""
        worktree = temp_dir / "ralph-test"
        worktree.mkdir()

        # Mock git with branch info
        mock_git.worktree_list.return_value = [
            MagicMock(
                path=str(worktree),
                branch="ralph/test",
                is_detached=False,
            )
        ]

        def remove_worktree(path, force=False):
            shutil.rmtree(path)

        mock_git.worktree_remove.side_effect = remove_worktree

        cleanup = WorktreeCleanup(mock_git)
        result = cleanup.cleanup_worktree(worktree, delete_branch=True)

        assert result.success is True
        mock_git.delete_branch.assert_called_once_with("ralph/test", force=True)

    def test_cleanup_skip_main_branch_deletion(self, mock_git, temp_dir):
        """Test that main/master branches are not deleted."""
        worktree = temp_dir / "ralph-test"
        worktree.mkdir()

        # Mock git with main branch (edge case)
        mock_git.worktree_list.return_value = [
            MagicMock(
                path=str(worktree),
                branch="main",
                is_detached=False,
            )
        ]

        def remove_worktree(path, force=False):
            shutil.rmtree(path)

        mock_git.worktree_remove.side_effect = remove_worktree

        cleanup = WorktreeCleanup(mock_git)
        result = cleanup.cleanup_worktree(worktree, delete_branch=True)

        assert result.success is True
        assert result.branch_deleted is False
        mock_git.delete_branch.assert_not_called()


class TestOrphanDetection:
    """Tests for orphan worktree detection."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        if Path(tmpdir).exists():
            shutil.rmtree(tmpdir)

    @pytest.fixture
    def mock_git(self, temp_dir):
        """Create a mock GitTools with temp directory."""
        git = MagicMock(spec=GitTools)
        git.repo_path = temp_dir / "repo"
        (temp_dir / "repo").mkdir(exist_ok=True)
        return git

    def test_find_orphans_none_exist(self, mock_git, temp_dir):
        """Test find_orphan_worktrees when none exist."""
        mock_git.worktree_list.return_value = []

        cleanup = WorktreeCleanup(mock_git)
        orphans = cleanup.find_orphan_worktrees(temp_dir)

        assert orphans == []

    def test_find_orphans_all_tracked(self, mock_git, temp_dir):
        """Test find_orphan_worktrees when all are tracked."""
        worktree = temp_dir / "ralph-feature"
        worktree.mkdir()

        mock_git.worktree_list.return_value = [
            MagicMock(path=str(worktree.resolve()))
        ]

        cleanup = WorktreeCleanup(mock_git)
        orphans = cleanup.find_orphan_worktrees(temp_dir)

        assert orphans == []

    def test_find_orphans_detects_untracked(self, mock_git, temp_dir):
        """Test find_orphan_worktrees detects untracked directories."""
        # Create an orphan worktree directory
        orphan = temp_dir / "ralph-orphan"
        orphan.mkdir()

        mock_git.worktree_list.return_value = []

        cleanup = WorktreeCleanup(mock_git)
        orphans = cleanup.find_orphan_worktrees(temp_dir)

        assert len(orphans) == 1
        # Use resolve() to handle macOS /var -> /private/var symlinks
        assert orphans[0].path.resolve() == orphan.resolve()

    def test_find_orphans_ignores_non_ralph(self, mock_git, temp_dir):
        """Test find_orphan_worktrees ignores non-ralph directories."""
        # Create non-ralph directories
        (temp_dir / "other-dir").mkdir()
        (temp_dir / "not-ralph").mkdir()

        mock_git.worktree_list.return_value = []

        cleanup = WorktreeCleanup(mock_git)
        orphans = cleanup.find_orphan_worktrees(temp_dir)

        assert orphans == []

    def test_find_orphans_detects_git_dir(self, mock_git, temp_dir):
        """Test find_orphan_worktrees detects .git file."""
        orphan = temp_dir / "ralph-test"
        orphan.mkdir()
        (orphan / ".git").write_text("gitdir: /fake/repo/.git/worktrees/test")

        mock_git.worktree_list.return_value = []

        cleanup = WorktreeCleanup(mock_git)
        orphans = cleanup.find_orphan_worktrees(temp_dir)

        assert len(orphans) == 1
        assert orphans[0].has_git_dir is True
        assert orphans[0].branch_hint == "test"

    def test_cleanup_orphans(self, mock_git, temp_dir):
        """Test cleanup_orphans removes orphan directories."""
        # Create orphan directories
        orphan1 = temp_dir / "ralph-orphan1"
        orphan2 = temp_dir / "ralph-orphan2"
        orphan1.mkdir()
        orphan2.mkdir()

        mock_git.worktree_list.return_value = []

        cleanup = WorktreeCleanup(mock_git)
        results = cleanup.cleanup_orphans(temp_dir)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert not orphan1.exists()
        assert not orphan2.exists()


class TestCleanupAllWorktrees:
    """Tests for cleanup_all_ralph_worktrees."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        if Path(tmpdir).exists():
            shutil.rmtree(tmpdir)

    @pytest.fixture
    def mock_git(self, temp_dir):
        """Create a mock GitTools with temp directory."""
        git = MagicMock(spec=GitTools)
        git.repo_path = temp_dir / "repo"
        (temp_dir / "repo").mkdir(exist_ok=True)
        return git

    def test_cleanup_all_orphans_only(self, mock_git, temp_dir):
        """Test cleanup_all with include_active=False."""
        # Create an orphan
        orphan = temp_dir / "ralph-orphan"
        orphan.mkdir()

        # Create a tracked worktree
        tracked = temp_dir / "ralph-tracked"
        tracked.mkdir()

        mock_git.worktree_list.return_value = [
            MagicMock(
                path=str(tracked.resolve()),
                branch="ralph/tracked",
                is_main=False,
            )
        ]

        cleanup = WorktreeCleanup(mock_git)
        results = cleanup.cleanup_all_ralph_worktrees(include_active=False)

        # Only orphan should be cleaned
        assert len(results) == 1
        assert not orphan.exists()
        assert tracked.exists()  # Still exists

    def test_cleanup_all_including_active(self, mock_git, temp_dir):
        """Test cleanup_all with include_active=True."""
        # Create tracked worktrees
        tracked = temp_dir / "ralph-tracked"
        tracked.mkdir()

        def remove_worktree(path, force=False):
            shutil.rmtree(path)

        mock_git.worktree_remove.side_effect = remove_worktree
        mock_git.worktree_list.return_value = [
            MagicMock(
                path=str(tracked.resolve()),
                branch="ralph/tracked",
                is_main=False,
            )
        ]

        cleanup = WorktreeCleanup(mock_git)
        results = cleanup.cleanup_all_ralph_worktrees(include_active=True)

        assert len(results) == 1
        assert not tracked.exists()

    def test_cleanup_all_skips_main_worktree(self, mock_git, temp_dir):
        """Test cleanup_all never removes main worktree."""
        main = temp_dir / "repo"  # Main repo dir

        mock_git.worktree_list.return_value = [
            MagicMock(
                path=str(main.resolve()),
                branch="main",
                is_main=True,
            )
        ]

        cleanup = WorktreeCleanup(mock_git)
        results = cleanup.cleanup_all_ralph_worktrees(include_active=True)

        # Main should not be touched
        assert len(results) == 0
        assert main.exists()


class TestCreateCleanupManager:
    """Tests for create_cleanup_manager factory function."""

    def test_creates_manager(self, tmp_path):
        """Test factory creates WorktreeCleanup instance."""
        # Initialize a git repo
        import subprocess

        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

        manager = create_cleanup_manager(tmp_path)

        assert isinstance(manager, WorktreeCleanup)
        assert isinstance(manager.config, CleanupConfig)

    def test_creates_manager_with_config(self, tmp_path):
        """Test factory accepts custom config."""
        import subprocess

        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

        config = CleanupConfig(cleanup_on_failure=True)
        manager = create_cleanup_manager(tmp_path, config=config)

        assert manager.should_cleanup_on_failure() is True


class TestExecutorCleanupIntegration:
    """Integration tests for executor cleanup methods."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary git repository."""
        import subprocess

        repo = tmp_path / "repo"
        repo.mkdir()

        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            capture_output=True,
            check=True,
        )

        # Create initial commit
        (repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=repo,
            capture_output=True,
            check=True,
        )

        return repo

    def test_executor_cleanup_config(self, temp_repo):
        """Test executor accepts cleanup config."""
        from ralph_agi.tasks.executor import TaskExecutor

        config = CleanupConfig(cleanup_on_failure=True)
        executor = TaskExecutor(
            enable_worktree_isolation=True,
            repo_path=temp_repo,
            cleanup_config=config,
        )

        assert executor.cleanup_config.cleanup_on_failure is True

    def test_executor_cleanup_orphans(self, temp_repo, tmp_path):
        """Test executor cleanup_orphans method."""
        from ralph_agi.tasks.executor import TaskExecutor

        # Create an orphan
        orphan = tmp_path / "ralph-orphan"
        orphan.mkdir()

        executor = TaskExecutor(
            enable_worktree_isolation=True,
            repo_path=temp_repo,
            worktree_base=tmp_path,
        )

        results = executor.cleanup_orphans()

        assert len(results) == 1
        assert results[0].success
        assert not orphan.exists()

    def test_executor_cleanup_all(self, temp_repo, tmp_path):
        """Test executor cleanup_all method."""
        from ralph_agi.tasks.executor import TaskExecutor

        # Create an orphan
        orphan = tmp_path / "ralph-orphan"
        orphan.mkdir()

        executor = TaskExecutor(
            enable_worktree_isolation=True,
            repo_path=temp_repo,
            worktree_base=tmp_path,
        )

        results = executor.cleanup_all()

        assert len(results) == 1
        assert not orphan.exists()

    def test_executor_cleanup_disabled_returns_empty(self, temp_repo):
        """Test cleanup methods return empty when isolation disabled."""
        from ralph_agi.tasks.executor import TaskExecutor

        executor = TaskExecutor(
            enable_worktree_isolation=False,
        )

        assert executor.cleanup_orphans() == []
        assert executor.cleanup_all() == []
