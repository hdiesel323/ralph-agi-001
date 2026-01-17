"""Tests for Git Worktree Manager.

Tests the worktree management for parallel task execution.
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from ralph_agi.tasks.worktree import (
    WorktreeManager,
    ActiveWorktree,
    WorktreeError,
    WorktreeExistsError,
    WorktreeNotFoundError,
)
from ralph_agi.tools.git import GitTools, GitCommandError, WorktreeInfo


class TestActiveWorktree:
    """Tests for ActiveWorktree dataclass."""

    def test_to_dict(self):
        """Test serialization to dict."""
        worktree = ActiveWorktree(
            task_id="test-task",
            path="/path/to/worktree",
            branch="ralph/test-task",
            commit="abc123",
            status="running",
        )

        data = worktree.to_dict()

        assert data["task_id"] == "test-task"
        assert data["path"] == "/path/to/worktree"
        assert data["branch"] == "ralph/test-task"
        assert data["commit"] == "abc123"
        assert data["status"] == "running"
        assert "created_at" in data

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "task_id": "test-task",
            "path": "/path/to/worktree",
            "branch": "ralph/test-task",
            "commit": "abc123",
            "created_at": "2026-01-17T10:00:00+00:00",
            "status": "created",
        }

        worktree = ActiveWorktree.from_dict(data)

        assert worktree.task_id == "test-task"
        assert worktree.path == "/path/to/worktree"
        assert worktree.branch == "ralph/test-task"
        assert worktree.commit == "abc123"
        assert worktree.status == "created"

    def test_from_dict_roundtrip(self):
        """Test dict serialization roundtrip."""
        original = ActiveWorktree(
            task_id="test-task",
            path="/path/to/worktree",
            branch="ralph/test-task",
            commit="abc123",
            status="running",
        )

        data = original.to_dict()
        restored = ActiveWorktree.from_dict(data)

        assert restored.task_id == original.task_id
        assert restored.path == original.path
        assert restored.branch == original.branch
        assert restored.commit == original.commit
        assert restored.status == original.status


class TestWorktreeManager:
    """Tests for WorktreeManager class."""

    @pytest.fixture
    def mock_git(self):
        """Create a mock GitTools instance."""
        return MagicMock(spec=GitTools)

    @pytest.fixture
    def manager(self, tmp_path, mock_git):
        """Create a WorktreeManager with mocked git."""
        manager = WorktreeManager(
            repo_path=tmp_path,
            worktree_dir=tmp_path / "worktrees",
            git=mock_git,
        )
        return manager

    def test_init_sets_paths(self, tmp_path):
        """Test initialization sets paths correctly."""
        mock_git = MagicMock(spec=GitTools)
        manager = WorktreeManager(
            repo_path=tmp_path,
            worktree_dir=tmp_path / "worktrees",
            git=mock_git,
        )

        assert manager.repo_path == tmp_path
        assert manager.worktree_dir == tmp_path / "worktrees"

    def test_init_creates_state_directory(self, tmp_path, mock_git):
        """Test initialization creates .ralph directory."""
        manager = WorktreeManager(repo_path=tmp_path, git=mock_git)
        assert (tmp_path / ".ralph").exists()

    def test_branch_name(self, manager):
        """Test branch name generation."""
        assert manager._branch_name("test-task") == "ralph/test-task"
        assert manager._branch_name("fix-bug-123") == "ralph/fix-bug-123"

    @patch('ralph_agi.tasks.worktree.GitTools')
    def test_create_calls_git_worktree_add(self, mock_git_class, manager, mock_git, tmp_path):
        """Test create calls git worktree add."""
        worktree_path = tmp_path / "worktrees/test-task"
        mock_git.worktree_add.return_value = str(worktree_path)

        mock_worktree_git = MagicMock()
        mock_worktree_git._run_git.return_value = "abc123"
        mock_git_class.return_value = mock_worktree_git

        path = manager.create("test-task")

        mock_git.worktree_add.assert_called_once()
        call_args = str(mock_git.worktree_add.call_args)
        assert "ralph/test-task" in call_args

    @patch('ralph_agi.tasks.worktree.GitTools')
    def test_create_records_in_state(self, mock_git_class, manager, mock_git, tmp_path):
        """Test create records worktree in state file."""
        worktree_path = tmp_path / "worktrees/test-task"
        mock_git.worktree_add.return_value = str(worktree_path)

        mock_worktree_git = MagicMock()
        mock_worktree_git._run_git.return_value = "abc123"
        mock_git_class.return_value = mock_worktree_git

        manager.create("test-task")

        # Check state file
        state_file = tmp_path / ".ralph/worktrees.json"
        assert state_file.exists()

        with open(state_file) as f:
            state = json.load(f)

        assert "test-task" in state["worktrees"]
        assert state["worktrees"]["test-task"]["branch"] == "ralph/test-task"

    @patch('ralph_agi.tasks.worktree.GitTools')
    def test_create_raises_if_exists(self, mock_git_class, manager, mock_git, tmp_path):
        """Test create raises WorktreeExistsError if already exists."""
        worktree_path = tmp_path / "worktrees/test-task"
        mock_git.worktree_add.return_value = str(worktree_path)

        mock_worktree_git = MagicMock()
        mock_worktree_git._run_git.return_value = "abc123"
        mock_git_class.return_value = mock_worktree_git

        # First create
        manager.create("test-task")

        # Second create should fail
        with pytest.raises(WorktreeExistsError):
            manager.create("test-task")

    @patch('ralph_agi.tasks.worktree.GitTools')
    def test_get_returns_worktree(self, mock_git_class, manager, mock_git, tmp_path):
        """Test get returns ActiveWorktree."""
        worktree_path = tmp_path / "worktrees/test-task"
        mock_git.worktree_add.return_value = str(worktree_path)

        mock_worktree_git = MagicMock()
        mock_worktree_git._run_git.return_value = "abc123"
        mock_git_class.return_value = mock_worktree_git

        # Create first
        manager.create("test-task")

        # Get
        worktree = manager.get("test-task")

        assert worktree.task_id == "test-task"
        assert worktree.branch == "ralph/test-task"

    def test_get_raises_if_not_found(self, manager):
        """Test get raises WorktreeNotFoundError."""
        with pytest.raises(WorktreeNotFoundError):
            manager.get("nonexistent")

    @patch('ralph_agi.tasks.worktree.GitTools')
    def test_list_active_returns_all(self, mock_git_class, manager, mock_git, tmp_path):
        """Test list_active returns all worktrees."""
        worktree_path = tmp_path / "worktrees"
        mock_git.worktree_add.side_effect = [
            str(worktree_path / "task-1"),
            str(worktree_path / "task-2"),
        ]

        mock_worktree_git = MagicMock()
        mock_worktree_git._run_git.return_value = "abc123"
        mock_git_class.return_value = mock_worktree_git

        manager.create("task-1")
        manager.create("task-2")

        active = manager.list_active()

        assert len(active) == 2
        task_ids = [w.task_id for w in active]
        assert "task-1" in task_ids
        assert "task-2" in task_ids

    @patch('ralph_agi.tasks.worktree.GitTools')
    def test_update_status(self, mock_git_class, manager, mock_git, tmp_path):
        """Test update_status changes status."""
        worktree_path = tmp_path / "worktrees/test-task"
        mock_git.worktree_add.return_value = str(worktree_path)

        mock_worktree_git = MagicMock()
        mock_worktree_git._run_git.return_value = "abc123"
        mock_git_class.return_value = mock_worktree_git

        manager.create("test-task")

        updated = manager.update_status("test-task", "running")

        assert updated.status == "running"

        # Verify persisted
        reloaded = manager.get("test-task")
        assert reloaded.status == "running"

    @patch('ralph_agi.tasks.worktree.GitTools')
    def test_cleanup_removes_worktree(self, mock_git_class, manager, mock_git, tmp_path):
        """Test cleanup removes worktree."""
        worktree_path = tmp_path / "worktrees/test-task"
        worktree_path.mkdir(parents=True)  # Create the directory so cleanup will call worktree_remove
        mock_git.worktree_add.return_value = str(worktree_path)

        mock_worktree_git = MagicMock()
        mock_worktree_git._run_git.return_value = "abc123"
        mock_git_class.return_value = mock_worktree_git

        manager.create("test-task")

        result = manager.cleanup("test-task")

        assert result is True
        mock_git.worktree_remove.assert_called_once()

        # Should be removed from state
        with pytest.raises(WorktreeNotFoundError):
            manager.get("test-task")

    def test_cleanup_raises_if_not_found(self, manager):
        """Test cleanup raises WorktreeNotFoundError."""
        with pytest.raises(WorktreeNotFoundError):
            manager.cleanup("nonexistent")

    @patch('ralph_agi.tasks.worktree.GitTools')
    def test_cleanup_all(self, mock_git_class, manager, mock_git, tmp_path):
        """Test cleanup_all removes all worktrees."""
        worktree_path = tmp_path / "worktrees"
        mock_git.worktree_add.side_effect = [
            str(worktree_path / "task-1"),
            str(worktree_path / "task-2"),
        ]

        mock_worktree_git = MagicMock()
        mock_worktree_git._run_git.return_value = "abc123"
        mock_git_class.return_value = mock_worktree_git

        manager.create("task-1")
        manager.create("task-2")

        removed = manager.cleanup_all()

        assert removed == 2
        assert len(manager.list_active()) == 0

    @patch('ralph_agi.tasks.worktree.GitTools')
    def test_prune_removes_missing_worktrees(self, mock_git_class, manager, mock_git, tmp_path):
        """Test prune removes worktrees with missing directories."""
        # Manually add a worktree to state that doesn't exist
        state_file = tmp_path / ".ralph/worktrees.json"
        state = {
            "worktrees": {
                "missing-task": {
                    "task_id": "missing-task",
                    "path": str(tmp_path / "nonexistent"),
                    "branch": "ralph/missing-task",
                    "status": "created",
                }
            }
        }
        with open(state_file, "w") as f:
            json.dump(state, f)

        # Also create a valid worktree
        worktree_path = tmp_path / "worktrees/valid-task"
        worktree_path.mkdir(parents=True)
        mock_git.worktree_add.return_value = str(worktree_path)

        mock_worktree_git = MagicMock()
        mock_worktree_git._run_git.return_value = "abc123"
        mock_git_class.return_value = mock_worktree_git

        manager.create("valid-task")

        # Prune
        pruned = manager.prune()

        assert "missing-task" in pruned
        assert len(manager.list_active()) == 1

    @patch('ralph_agi.tasks.worktree.GitTools')
    def test_stats(self, mock_git_class, manager, mock_git, tmp_path):
        """Test stats returns correct counts."""
        worktree_path = tmp_path / "worktrees"
        mock_git.worktree_add.side_effect = [
            str(worktree_path / "task-1"),
            str(worktree_path / "task-2"),
        ]

        mock_worktree_git = MagicMock()
        mock_worktree_git._run_git.return_value = "abc123"
        mock_git_class.return_value = mock_worktree_git

        manager.create("task-1")
        manager.create("task-2")
        manager.update_status("task-1", "running")

        stats = manager.stats()

        assert stats["total"] == 2
        assert stats["by_status"]["created"] == 1
        assert stats["by_status"]["running"] == 1


class TestWorktreeManagerExecute:
    """Tests for WorktreeManager.execute_in_worktree."""

    @pytest.fixture
    @patch('ralph_agi.tasks.worktree.GitTools')
    def manager_with_worktree(self, mock_git_class, tmp_path):
        """Create manager with a real worktree directory."""
        mock_git = MagicMock(spec=GitTools)
        manager = WorktreeManager(
            repo_path=tmp_path,
            worktree_dir=tmp_path / "worktrees",
            git=mock_git,
        )

        # Create worktree directory
        worktree_path = tmp_path / "worktrees/test-task"
        worktree_path.mkdir(parents=True)

        mock_git.worktree_add.return_value = str(worktree_path)

        mock_worktree_git = MagicMock()
        mock_worktree_git._run_git.return_value = "abc123"
        mock_git_class.return_value = mock_worktree_git

        manager.create("test-task")

        return manager, tmp_path

    def test_execute_changes_cwd(self, manager_with_worktree):
        """Test execute_in_worktree changes working directory."""
        manager, tmp_path = manager_with_worktree
        worktree_path = tmp_path / "worktrees/test-task"

        executed_in = []

        def callback(path):
            from pathlib import Path
            executed_in.append(Path.cwd())
            return "result"

        result = manager.execute_in_worktree("test-task", callback)

        assert result == "result"
        assert executed_in[0] == worktree_path

    def test_execute_restores_cwd_on_success(self, manager_with_worktree):
        """Test execute_in_worktree restores cwd on success."""
        manager, tmp_path = manager_with_worktree
        original_cwd = Path.cwd()

        def callback(path):
            return "result"

        manager.execute_in_worktree("test-task", callback)

        assert Path.cwd() == original_cwd

    def test_execute_restores_cwd_on_error(self, manager_with_worktree):
        """Test execute_in_worktree restores cwd on error."""
        manager, tmp_path = manager_with_worktree
        original_cwd = Path.cwd()

        def callback(path):
            raise ValueError("Test error")

        with pytest.raises(WorktreeError):
            manager.execute_in_worktree("test-task", callback)

        assert Path.cwd() == original_cwd

    def test_execute_updates_status_to_running(self, manager_with_worktree):
        """Test execute_in_worktree updates status to running."""
        manager, tmp_path = manager_with_worktree

        def callback(path):
            # Check status during execution
            worktree = manager.get("test-task")
            assert worktree.status == "running"
            return "result"

        manager.execute_in_worktree("test-task", callback)

    def test_execute_updates_status_to_error_on_failure(self, manager_with_worktree):
        """Test execute_in_worktree updates status to error on failure."""
        manager, tmp_path = manager_with_worktree

        def callback(path):
            raise ValueError("Test error")

        with pytest.raises(WorktreeError):
            manager.execute_in_worktree("test-task", callback)

        worktree = manager.get("test-task")
        assert worktree.status == "error"
