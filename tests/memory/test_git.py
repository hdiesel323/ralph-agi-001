"""Tests for git integration in memory system.

Tests cover:
- Auto-commit after task completion
- Store commit metadata in memory frames
- Commit message templates
- Query memory by git commit reference
- Link frames to commits
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ralph_agi.memory.git import GitCommit, GitError, GitMemory


# Fixtures


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    # Configure git user
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repo")
    subprocess.run(
        ["git", "add", "."],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    return repo_path


@pytest.fixture
def git_memory(temp_git_repo):
    """Create a GitMemory instance with temp repo."""
    return GitMemory(repo_path=temp_git_repo)


@pytest.fixture
def mock_memory_store():
    """Create a mock MemoryStore."""
    store = MagicMock()
    store.append.return_value = "frame-123"
    store.search.return_value = []
    return store


@pytest.fixture
def git_memory_with_store(temp_git_repo, mock_memory_store):
    """Create a GitMemory instance with mock memory store."""
    return GitMemory(repo_path=temp_git_repo, memory_store=mock_memory_store)


# GitCommit Tests


class TestGitCommit:
    """Tests for GitCommit dataclass."""

    def test_git_commit_attributes(self):
        """Test GitCommit stores all attributes."""
        commit = GitCommit(
            sha="abc123def456",
            short_sha="abc123d",
            message="feat: Add user authentication",
            author="Test User",
            author_email="test@example.com",
            timestamp="2026-01-11T10:30:00+00:00",
            files_changed=5,
        )

        assert commit.sha == "abc123def456"
        assert commit.short_sha == "abc123d"
        assert commit.message == "feat: Add user authentication"
        assert commit.author == "Test User"
        assert commit.author_email == "test@example.com"
        assert commit.timestamp == "2026-01-11T10:30:00+00:00"
        assert commit.files_changed == 5

    def test_git_commit_summary(self):
        """Test GitCommit summary property."""
        commit = GitCommit(
            sha="abc123def456",
            short_sha="abc123d",
            message="feat: Add user authentication\n\nDetailed description",
            author="Test User",
            author_email="test@example.com",
            timestamp="2026-01-11T10:30:00+00:00",
        )

        assert commit.summary == "abc123d: feat: Add user authentication"

    def test_git_commit_summary_single_line(self):
        """Test summary with single-line message."""
        commit = GitCommit(
            sha="abc123def456",
            short_sha="abc123d",
            message="fix: Quick bug fix",
            author="Test User",
            author_email="test@example.com",
            timestamp="2026-01-11T10:30:00+00:00",
        )

        assert commit.summary == "abc123d: fix: Quick bug fix"

    def test_git_commit_frozen(self):
        """Test GitCommit is immutable."""
        commit = GitCommit(
            sha="abc123",
            short_sha="abc",
            message="test",
            author="test",
            author_email="test@test.com",
            timestamp="2026-01-11",
        )

        with pytest.raises(AttributeError):
            commit.sha = "new_sha"


# GitMemory Initialization Tests


class TestGitMemoryInit:
    """Tests for GitMemory initialization."""

    def test_init_default_path(self):
        """Test initialization with default path."""
        git_mem = GitMemory()
        assert git_mem.repo_path == Path.cwd().resolve()

    def test_init_custom_path(self, temp_git_repo):
        """Test initialization with custom path."""
        git_mem = GitMemory(repo_path=temp_git_repo)
        assert git_mem.repo_path == temp_git_repo.resolve()

    def test_init_with_memory_store(self, temp_git_repo, mock_memory_store):
        """Test initialization with memory store."""
        git_mem = GitMemory(
            repo_path=temp_git_repo,
            memory_store=mock_memory_store,
        )
        assert git_mem._memory_store is mock_memory_store

    def test_init_with_author(self, temp_git_repo):
        """Test initialization with author info."""
        git_mem = GitMemory(
            repo_path=temp_git_repo,
            author_name="RALPH",
            author_email="ralph@test.com",
        )
        assert git_mem._author_name == "RALPH"
        assert git_mem._author_email == "ralph@test.com"


# Repository Detection Tests


class TestGitMemoryRepoDetection:
    """Tests for repository detection."""

    def test_is_repo_true(self, git_memory):
        """Test is_repo returns True for valid repo."""
        assert git_memory.is_repo() is True

    def test_is_repo_false(self, tmp_path):
        """Test is_repo returns False for non-repo."""
        git_mem = GitMemory(repo_path=tmp_path)
        assert git_mem.is_repo() is False


# Status Tests


class TestGitMemoryStatus:
    """Tests for git status operations."""

    def test_has_changes_false(self, git_memory):
        """Test has_changes returns False when clean."""
        assert git_memory.has_changes() is False

    def test_has_changes_true(self, git_memory, temp_git_repo):
        """Test has_changes returns True when modified."""
        (temp_git_repo / "new_file.txt").write_text("content")
        assert git_memory.has_changes() is True

    def test_has_changes_staged_only(self, git_memory, temp_git_repo):
        """Test has_changes with staged_only flag."""
        # Create untracked file
        (temp_git_repo / "new_file.txt").write_text("content")

        # No staged changes yet
        assert git_memory.has_changes(staged_only=True) is False

        # Stage the file
        subprocess.run(
            ["git", "add", "new_file.txt"],
            cwd=temp_git_repo,
            capture_output=True,
            check=True,
        )

        # Now has staged changes
        assert git_memory.has_changes(staged_only=True) is True

    def test_get_status_empty(self, git_memory):
        """Test get_status with clean repo."""
        status = git_memory.get_status()
        assert status["staged"] == []
        assert status["modified"] == []
        assert status["untracked"] == []

    def test_get_status_with_changes(self, git_memory, temp_git_repo):
        """Test get_status with various changes."""
        # Create untracked file
        (temp_git_repo / "untracked.txt").write_text("untracked")

        # Modify existing file
        (temp_git_repo / "README.md").write_text("# Modified")

        status = git_memory.get_status()

        assert "untracked.txt" in status["untracked"]
        assert "README.md" in status["modified"]

    def test_get_status_staged(self, git_memory, temp_git_repo):
        """Test get_status with staged files."""
        # Create and stage file
        (temp_git_repo / "staged.txt").write_text("staged")
        subprocess.run(
            ["git", "add", "staged.txt"],
            cwd=temp_git_repo,
            capture_output=True,
            check=True,
        )

        status = git_memory.get_status()
        assert "staged.txt" in status["staged"]


# Staging Tests


class TestGitMemoryStaging:
    """Tests for staging operations."""

    def test_stage_all(self, git_memory, temp_git_repo):
        """Test stage_all stages all changes."""
        # Create multiple files
        (temp_git_repo / "file1.txt").write_text("content1")
        (temp_git_repo / "file2.txt").write_text("content2")

        count = git_memory.stage_all()

        assert count >= 2
        status = git_memory.get_status()
        assert "file1.txt" in status["staged"]
        assert "file2.txt" in status["staged"]

    def test_stage_all_no_changes(self, git_memory):
        """Test stage_all with no changes returns 0."""
        count = git_memory.stage_all()
        assert count == 0

    def test_stage_files(self, git_memory, temp_git_repo):
        """Test staging specific files."""
        (temp_git_repo / "file1.txt").write_text("content1")
        (temp_git_repo / "file2.txt").write_text("content2")

        count = git_memory.stage_files("file1.txt")

        assert count == 1
        status = git_memory.get_status()
        assert "file1.txt" in status["staged"]
        assert "file2.txt" not in status["staged"]

    def test_stage_files_empty(self, git_memory):
        """Test staging no files returns 0."""
        count = git_memory.stage_files()
        assert count == 0


# Commit Tests


class TestGitMemoryCommit:
    """Tests for commit operations."""

    def test_commit_basic(self, git_memory, temp_git_repo):
        """Test basic commit operation."""
        (temp_git_repo / "new_file.txt").write_text("content")
        git_memory.stage_all()

        commit = git_memory.commit("test: Add new file")

        assert commit is not None
        assert commit.message == "test: Add new file"
        assert len(commit.sha) == 40
        assert len(commit.short_sha) == 7

    def test_commit_no_changes(self, git_memory):
        """Test commit with no staged changes returns None."""
        commit = git_memory.commit("test: Should not commit")
        assert commit is None

    def test_commit_allow_empty(self, git_memory):
        """Test commit with allow_empty flag."""
        commit = git_memory.commit("test: Empty commit", allow_empty=True)

        assert commit is not None
        assert commit.message == "test: Empty commit"

    def test_commit_changes_feat(self, git_memory, temp_git_repo):
        """Test commit_changes with feat type."""
        (temp_git_repo / "feature.py").write_text("# New feature")

        commit = git_memory.commit_changes(
            description="Add user authentication",
            commit_type="feat",
        )

        assert commit is not None
        assert commit.message.startswith("feat: Add user authentication")

    def test_commit_changes_fix(self, git_memory, temp_git_repo):
        """Test commit_changes with fix type."""
        (temp_git_repo / "bugfix.py").write_text("# Bug fix")

        commit = git_memory.commit_changes(
            description="Fix null pointer exception",
            commit_type="fix",
        )

        assert commit is not None
        assert commit.message.startswith("fix: Fix null pointer exception")

    def test_commit_changes_with_task_id(self, git_memory, temp_git_repo):
        """Test commit_changes includes task ID."""
        (temp_git_repo / "task.py").write_text("# Task implementation")

        commit = git_memory.commit_changes(
            description="Implement login flow",
            task_id="TASK-001",
            commit_type="feat",
        )

        assert commit is not None
        assert "Task: TASK-001" in commit.message

    def test_commit_changes_no_files(self, git_memory):
        """Test commit_changes with no changes returns None."""
        commit = git_memory.commit_changes(description="Nothing to commit")
        assert commit is None

    def test_commit_types(self, git_memory, temp_git_repo):
        """Test all commit type templates."""
        types = ["feat", "fix", "refactor", "docs", "test", "chore"]

        for commit_type in types:
            # Create a file for each type
            (temp_git_repo / f"{commit_type}_file.txt").write_text(f"# {commit_type}")

            commit = git_memory.commit_changes(
                description=f"Test {commit_type}",
                commit_type=commit_type,
            )

            assert commit is not None
            assert commit.message.startswith(f"{commit_type}: Test {commit_type}")


# Memory Integration Tests


class TestGitMemoryMemoryIntegration:
    """Tests for memory store integration."""

    def test_commit_stores_frame(self, git_memory_with_store, temp_git_repo, mock_memory_store):
        """Test commit_changes stores a memory frame."""
        (temp_git_repo / "feature.py").write_text("# Feature")

        commit = git_memory_with_store.commit_changes(
            description="Add feature",
            task_id="TASK-001",
            session_id="session-123",
        )

        assert commit is not None
        mock_memory_store.append.assert_called_once()

        call_kwargs = mock_memory_store.append.call_args[1]
        assert "git_commit" == call_kwargs["frame_type"]
        assert "session-123" == call_kwargs["session_id"]
        assert "git" in call_kwargs["tags"]
        assert "commit" in call_kwargs["tags"]
        assert f"sha:{commit.short_sha}" in call_kwargs["tags"]
        assert "task:TASK-001" in call_kwargs["tags"]

    def test_commit_stores_metadata(self, git_memory_with_store, temp_git_repo, mock_memory_store):
        """Test commit_changes stores commit metadata."""
        (temp_git_repo / "feature.py").write_text("# Feature")

        commit = git_memory_with_store.commit_changes(
            description="Add feature",
            task_id="TASK-002",
        )

        call_kwargs = mock_memory_store.append.call_args[1]
        metadata = call_kwargs["metadata"]

        assert metadata["commit_sha"] == commit.sha
        assert metadata["commit_short_sha"] == commit.short_sha
        assert metadata["task_id"] == "TASK-002"
        assert "author" in metadata
        assert "author_email" in metadata

    def test_no_store_no_error(self, git_memory, temp_git_repo):
        """Test commit_changes works without memory store."""
        (temp_git_repo / "feature.py").write_text("# Feature")

        # Should not raise
        commit = git_memory.commit_changes(description="Add feature")
        assert commit is not None


# Commit Query Tests


class TestGitMemoryCommitQuery:
    """Tests for querying commits."""

    def test_get_head_commit(self, git_memory, temp_git_repo):
        """Test get_head_commit returns HEAD."""
        commit = git_memory.get_head_commit()

        assert commit is not None
        assert commit.message == "Initial commit"

    def test_get_commit_by_sha(self, git_memory, temp_git_repo):
        """Test get_commit by SHA."""
        head = git_memory.get_head_commit()
        commit = git_memory.get_commit(head.sha)

        assert commit.sha == head.sha
        assert commit.message == head.message

    def test_get_commit_invalid_ref(self, git_memory):
        """Test get_commit with invalid reference."""
        with pytest.raises(GitError):
            git_memory.get_commit("nonexistent-ref")

    def test_get_commits_since(self, git_memory, temp_git_repo):
        """Test get_commits_since."""
        # Get initial commit
        initial = git_memory.get_head_commit()

        # Make more commits
        (temp_git_repo / "file1.txt").write_text("1")
        git_memory.commit_changes(description="First change")
        (temp_git_repo / "file2.txt").write_text("2")
        git_memory.commit_changes(description="Second change")

        commits = git_memory.get_commits_since(initial.sha)

        assert len(commits) == 2
        # Newest first
        assert "Second change" in commits[0].message
        assert "First change" in commits[1].message

    def test_get_commits_for_file(self, git_memory, temp_git_repo):
        """Test get_commits_for_file."""
        # Create and modify a file multiple times
        (temp_git_repo / "tracked.txt").write_text("v1")
        git_memory.commit_changes(description="Create file")
        (temp_git_repo / "tracked.txt").write_text("v2")
        git_memory.commit_changes(description="Update file")

        commits = git_memory.get_commits_for_file("tracked.txt")

        assert len(commits) == 2

    def test_search_commits(self, git_memory, temp_git_repo):
        """Test search_commits by message."""
        (temp_git_repo / "auth.py").write_text("# Auth")
        git_memory.commit_changes(description="Add authentication")
        (temp_git_repo / "db.py").write_text("# DB")
        git_memory.commit_changes(description="Add database")

        commits = git_memory.search_commits("auth")

        assert len(commits) == 1
        assert "authentication" in commits[0].message


# Memory Query Tests


class TestGitMemoryMemoryQuery:
    """Tests for querying memory by commit."""

    def test_get_memory_by_commit(self, git_memory_with_store, temp_git_repo, mock_memory_store):
        """Test get_memory_by_commit searches by SHA tag."""
        (temp_git_repo / "feature.py").write_text("# Feature")
        commit = git_memory_with_store.commit_changes(description="Add feature")

        # Configure mock to return frames
        mock_frame = MagicMock()
        mock_memory_store.search.return_value = [mock_frame]

        frames = git_memory_with_store.get_memory_by_commit(commit.sha)

        assert len(frames) == 1
        mock_memory_store.search.assert_called_once()
        search_call = mock_memory_store.search.call_args
        assert f"sha:{commit.short_sha}" in search_call[0][0]

    def test_get_memory_by_commit_no_store(self, git_memory, temp_git_repo):
        """Test get_memory_by_commit without store returns empty."""
        (temp_git_repo / "feature.py").write_text("# Feature")
        commit = git_memory.commit_changes(description="Add feature")

        frames = git_memory.get_memory_by_commit(commit.sha)
        assert frames == []

    def test_get_memory_by_commit_invalid_ref(self, git_memory_with_store, mock_memory_store):
        """Test get_memory_by_commit with invalid ref returns empty."""
        frames = git_memory_with_store.get_memory_by_commit("nonexistent")
        assert frames == []


# Revert Tests


class TestGitMemoryRevert:
    """Tests for revert operations."""

    def test_revert_commit(self, git_memory, temp_git_repo):
        """Test revert_commit reverts HEAD."""
        # Make a commit to revert
        (temp_git_repo / "to_revert.txt").write_text("content")
        git_memory.commit_changes(description="Will revert")

        # Revert it
        revert_commit = git_memory.revert_commit()

        assert revert_commit is not None
        assert "Revert" in revert_commit.message

    def test_revert_specific_commit(self, git_memory, temp_git_repo):
        """Test revert_commit with specific ref."""
        # Make commits
        (temp_git_repo / "file1.txt").write_text("1")
        first_commit = git_memory.commit_changes(description="First")
        (temp_git_repo / "file2.txt").write_text("2")
        git_memory.commit_changes(description="Second")

        # Revert first commit
        revert_commit = git_memory.revert_commit(first_commit.sha)

        assert revert_commit is not None
        assert "Revert" in revert_commit.message


# Diff Tests


class TestGitMemoryDiff:
    """Tests for diff operations."""

    def test_get_diff(self, git_memory, temp_git_repo):
        """Test get_diff between commits."""
        (temp_git_repo / "README.md").write_text("# Modified Content")
        git_memory.commit_changes(description="Modify README")

        diff = git_memory.get_diff("HEAD~1", "HEAD")

        assert "Modified Content" in diff
        assert "README.md" in diff

    def test_get_diff_specific_file(self, git_memory, temp_git_repo):
        """Test get_diff for specific file."""
        (temp_git_repo / "file1.txt").write_text("file1 content")
        (temp_git_repo / "file2.txt").write_text("file2 content")
        git_memory.commit_changes(description="Add files")

        diff = git_memory.get_diff("HEAD~1", "HEAD", filepath="file1.txt")

        assert "file1 content" in diff
        assert "file2 content" not in diff


# Error Handling Tests


class TestGitMemoryErrors:
    """Tests for error handling."""

    def test_run_git_invalid_command(self, git_memory):
        """Test _run_git with invalid command raises GitError."""
        with pytest.raises(GitError):
            git_memory._run_git("invalid-command")

    def test_commit_in_non_repo(self, tmp_path):
        """Test commit in non-repo raises GitError."""
        git_mem = GitMemory(repo_path=tmp_path)

        with pytest.raises(GitError):
            git_mem.commit("test", allow_empty=True)

    def test_store_commit_frame_handles_error(self, temp_git_repo, mock_memory_store):
        """Test _store_commit_frame handles store errors gracefully."""
        mock_memory_store.append.side_effect = Exception("Store error")
        git_mem = GitMemory(repo_path=temp_git_repo, memory_store=mock_memory_store)

        (temp_git_repo / "file.txt").write_text("content")

        # Should not raise, just log warning
        commit = git_mem.commit_changes(description="Test")
        assert commit is not None
