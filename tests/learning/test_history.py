"""Tests for git history integration module."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ralph_agi.learning.history import (
    CommitInfo,
    CommitDiff,
    FileDiff,
    GitHistory,
    inject_git_history,
)


class TestCommitInfo:
    """Tests for CommitInfo dataclass."""

    def test_commit_creation(self):
        """Test creating commit info."""
        commit = CommitInfo(
            hash="abc123def456",
            short_hash="abc123d",
            author="Test Author",
            email="test@example.com",
            date="2025-01-16T12:00:00",
            subject="Fix: Update the thing",
        )
        assert commit.hash == "abc123def456"
        assert commit.author == "Test Author"
        assert commit.subject == "Fix: Update the thing"

    def test_commit_with_body(self):
        """Test commit with body."""
        commit = CommitInfo(
            hash="abc123",
            short_hash="abc",
            author="Test",
            email="test@test.com",
            date="2025-01-16",
            subject="Subject line",
            body="This is the body\nwith multiple lines",
        )
        assert "Subject line" in commit.message
        assert "body" in commit.message

    def test_message_property(self):
        """Test message property."""
        commit = CommitInfo(
            hash="abc",
            short_hash="a",
            author="Test",
            email="t@t.com",
            date="2025-01-16",
            subject="Subject",
            body="Body text",
        )
        assert commit.message == "Subject\n\nBody text"

    def test_message_without_body(self):
        """Test message without body."""
        commit = CommitInfo(
            hash="abc",
            short_hash="a",
            author="Test",
            email="t@t.com",
            date="2025-01-16",
            subject="Subject only",
        )
        assert commit.message == "Subject only"

    def test_is_merge(self):
        """Test merge detection."""
        merge_commit = CommitInfo(
            hash="abc",
            short_hash="a",
            author="Test",
            email="t@t.com",
            date="2025-01-16",
            subject="Merge pull request #123",
        )
        regular_commit = CommitInfo(
            hash="def",
            short_hash="d",
            author="Test",
            email="t@t.com",
            date="2025-01-16",
            subject="Fix: Regular commit",
        )
        assert merge_commit.is_merge is True
        assert regular_commit.is_merge is False

    def test_to_dict(self):
        """Test converting to dictionary."""
        commit = CommitInfo(
            hash="abc123",
            short_hash="abc",
            author="Test Author",
            email="test@example.com",
            date="2025-01-16",
            subject="Test commit",
            files_changed=("file1.py", "file2.py"),
            task_ids=("US-123",),
        )
        data = commit.to_dict()

        assert data["hash"] == "abc123"
        assert data["author"] == "Test Author"
        assert data["files_changed"] == ["file1.py", "file2.py"]
        assert data["task_ids"] == ["US-123"]


class TestFileDiff:
    """Tests for FileDiff dataclass."""

    def test_file_diff_creation(self):
        """Test creating file diff."""
        diff = FileDiff(
            path="src/main.py",
            status="M",
            additions=10,
            deletions=5,
        )
        assert diff.path == "src/main.py"
        assert diff.additions == 10
        assert diff.deletions == 5

    def test_is_rename(self):
        """Test rename detection."""
        rename = FileDiff(path="new.py", old_path="old.py", status="R")
        not_rename = FileDiff(path="file.py", status="M")

        assert rename.is_rename is True
        assert not_rename.is_rename is False

    def test_is_new(self):
        """Test new file detection."""
        new_file = FileDiff(path="new.py", status="A")
        existing = FileDiff(path="old.py", status="M")

        assert new_file.is_new is True
        assert existing.is_new is False

    def test_is_deleted(self):
        """Test deleted file detection."""
        deleted = FileDiff(path="old.py", status="D")
        existing = FileDiff(path="current.py", status="M")

        assert deleted.is_deleted is True
        assert existing.is_deleted is False


class TestCommitDiff:
    """Tests for CommitDiff dataclass."""

    def test_commit_diff_creation(self):
        """Test creating commit diff."""
        commit = CommitInfo(
            hash="abc",
            short_hash="a",
            author="Test",
            email="t@t.com",
            date="2025-01-16",
            subject="Test",
        )
        diff = CommitDiff(
            commit=commit,
            files=[
                FileDiff(path="a.py", additions=10, deletions=5),
                FileDiff(path="b.py", additions=20, deletions=10),
            ],
        )
        assert diff.commit == commit
        assert len(diff.files) == 2

    def test_total_additions(self):
        """Test total additions calculation."""
        commit = CommitInfo(
            hash="abc", short_hash="a", author="T", email="t@t.com",
            date="2025-01-16", subject="Test",
        )
        diff = CommitDiff(
            commit=commit,
            files=[
                FileDiff(path="a.py", additions=10, deletions=0),
                FileDiff(path="b.py", additions=20, deletions=0),
            ],
        )
        assert diff.total_additions == 30

    def test_total_deletions(self):
        """Test total deletions calculation."""
        commit = CommitInfo(
            hash="abc", short_hash="a", author="T", email="t@t.com",
            date="2025-01-16", subject="Test",
        )
        diff = CommitDiff(
            commit=commit,
            files=[
                FileDiff(path="a.py", additions=0, deletions=5),
                FileDiff(path="b.py", additions=0, deletions=15),
            ],
        )
        assert diff.total_deletions == 20


class TestGitHistory:
    """Tests for GitHistory class."""

    def test_init_default_path(self):
        """Test initialization with default path."""
        history = GitHistory()
        assert history.repo_path == Path.cwd()

    def test_init_custom_path(self, tmp_path):
        """Test initialization with custom path."""
        history = GitHistory(tmp_path)
        assert history.repo_path == tmp_path

    def test_extract_task_ids(self):
        """Test task ID extraction from text."""
        history = GitHistory()

        # Standard patterns
        assert "US-123" in history._extract_task_ids("Fixed US-123")
        assert "#456" in history._extract_task_ids("Closes #456")
        assert "JIRA-789" in history._extract_task_ids("JIRA-789 implementation")

        # Multiple IDs
        ids = history._extract_task_ids("US-1 and US-2 fixed")
        assert "US-1" in ids
        assert "US-2" in ids

        # No IDs
        assert len(history._extract_task_ids("No task IDs here")) == 0


class TestGitHistoryIntegration:
    """Integration tests that run against the actual repository."""

    @pytest.fixture
    def history(self):
        """Create history for current repository."""
        return GitHistory()

    def test_get_current_branch(self, history):
        """Test getting current branch."""
        branch = history.get_current_branch()
        assert branch is not None
        assert isinstance(branch, str)

    def test_get_recent_commits(self, history):
        """Test getting recent commits."""
        commits = history.get_recent_commits(5)
        assert isinstance(commits, list)
        # Should have at least some commits in this repo
        if commits:
            assert isinstance(commits[0], CommitInfo)
            assert commits[0].hash is not None
            assert commits[0].author is not None

    def test_get_commit_head(self, history):
        """Test getting HEAD commit."""
        commit = history.get_commit("HEAD")
        assert commit is not None
        assert len(commit.hash) == 40  # Full hash

    def test_get_commit_nonexistent(self, history):
        """Test getting nonexistent commit."""
        commit = history.get_commit("nonexistent123456")
        assert commit is None

    def test_search_commits(self, history):
        """Test searching commits."""
        # Search for a common word that should be in commits
        results = history.search_commits("feat", limit=3)
        assert isinstance(results, list)

    def test_get_changed_files(self, history):
        """Test getting changed files."""
        files = history.get_changed_files("HEAD~5")
        assert isinstance(files, list)


class TestInjectGitHistory:
    """Tests for git history injection."""

    def test_inject_empty_history(self):
        """Test injecting when no commits."""
        history = MagicMock()
        history.get_recent_commits.return_value = []

        prompt = "Base prompt."
        result = inject_git_history(history, prompt)
        assert result == prompt

    def test_inject_with_commits(self):
        """Test injecting commits."""
        commits = [
            CommitInfo(
                hash="abc123",
                short_hash="abc123d",
                author="Test",
                email="t@t.com",
                date="2025-01-16T12:00:00",
                subject="Add new feature",
                files_changed=("src/main.py",),
            ),
            CommitInfo(
                hash="def456",
                short_hash="def456e",
                author="Test",
                email="t@t.com",
                date="2025-01-15T12:00:00",
                subject="Fix bug",
                task_ids=("US-123",),
            ),
        ]
        history = MagicMock()
        history.get_recent_commits.return_value = commits

        prompt = "Base prompt."
        result = inject_git_history(history, prompt)

        assert "Base prompt." in result
        assert "## Recent Git History" in result
        assert "abc123d" in result
        assert "Add new feature" in result
        assert "src/main.py" in result
        assert "US-123" in result

    def test_inject_respects_max_commits(self):
        """Test that max_commits is respected."""
        history = MagicMock()
        history.get_recent_commits.return_value = []

        prompt = "Base."
        inject_git_history(history, prompt, max_commits=5)

        history.get_recent_commits.assert_called_once_with(5)

    def test_inject_without_files(self):
        """Test injecting without file details."""
        commits = [
            CommitInfo(
                hash="abc",
                short_hash="abc",
                author="T",
                email="t@t.com",
                date="2025-01-16",
                subject="Test commit",
                files_changed=("file1.py", "file2.py"),
            ),
        ]
        history = MagicMock()
        history.get_recent_commits.return_value = commits

        prompt = "Base."
        result = inject_git_history(history, prompt, include_files=False)

        assert "file1.py" not in result
        assert "Test commit" in result
