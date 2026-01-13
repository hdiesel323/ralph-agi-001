"""Tests for GitTools."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from ralph_agi.tools.git import (
    GitCommandError,
    GitCommit,
    GitError,
    GitStatus,
    GitTools,
    NotARepositoryError,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Initialize repo
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)

    # Configure git for tests
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

    return repo


@pytest.fixture
def git_repo_with_commits(git_repo: Path) -> Path:
    """Create a repo with some commits."""
    # Create initial file and commit
    (git_repo / "README.md").write_text("# Test Project\n")
    subprocess.run(["git", "add", "README.md"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Second commit
    (git_repo / "main.py").write_text("print('hello')\n")
    subprocess.run(["git", "add", "main.py"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add main.py"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    return git_repo


class TestGitStatus:
    """Tests for GitStatus dataclass."""

    def test_is_clean_empty(self) -> None:
        """Test clean status."""
        status = GitStatus(branch="main")
        assert status.is_clean is True

    def test_is_clean_with_staged(self) -> None:
        """Test not clean with staged files."""
        status = GitStatus(branch="main", staged=["file.txt"])
        assert status.is_clean is False

    def test_is_clean_with_modified(self) -> None:
        """Test not clean with modified files."""
        status = GitStatus(branch="main", modified=["file.txt"])
        assert status.is_clean is False

    def test_has_staged(self) -> None:
        """Test has_staged property."""
        status = GitStatus(branch="main", staged=["file.txt"])
        assert status.has_staged is True

    def test_no_staged(self) -> None:
        """Test no staged files."""
        status = GitStatus(branch="main")
        assert status.has_staged is False

    def test_to_dict(self) -> None:
        """Test serialization."""
        status = GitStatus(
            branch="main",
            staged=["a.txt"],
            modified=["b.txt"],
        )
        d = status.to_dict()

        assert d["branch"] == "main"
        assert d["staged"] == ["a.txt"]
        assert d["modified"] == ["b.txt"]
        assert "is_clean" in d


class TestGitCommit:
    """Tests for GitCommit dataclass."""

    def test_to_dict(self) -> None:
        """Test serialization."""
        commit = GitCommit(
            hash="abc123def456",
            short_hash="abc123d",
            message="Test commit\n\nWith body",
            subject="Test commit",
            author="Test User",
            author_email="test@example.com",
            date=datetime.now(),
        )
        d = commit.to_dict()

        assert d["hash"] == "abc123def456"
        assert d["subject"] == "Test commit"
        assert "date" in d


class TestGitToolsInit:
    """Tests for GitTools initialization."""

    def test_default_cwd(self) -> None:
        """Test default to current directory."""
        git = GitTools()
        assert git.repo_path == Path.cwd()

    def test_custom_path(self, tmp_path: Path) -> None:
        """Test custom repository path."""
        git = GitTools(repo_path=tmp_path)
        assert git.repo_path == tmp_path.resolve()


class TestIsRepo:
    """Tests for is_repo method."""

    def test_is_repo_true(self, git_repo: Path) -> None:
        """Test detecting a git repository."""
        git = GitTools(repo_path=git_repo)
        assert git.is_repo() is True

    def test_is_repo_false(self, tmp_path: Path) -> None:
        """Test non-repository directory."""
        git = GitTools(repo_path=tmp_path)
        assert git.is_repo() is False


class TestStatus:
    """Tests for status method."""

    def test_status_clean(self, git_repo_with_commits: Path) -> None:
        """Test status of clean repository."""
        git = GitTools(repo_path=git_repo_with_commits)
        status = git.status()

        assert status.branch == "main"
        assert status.is_clean is True

    def test_status_modified(self, git_repo_with_commits: Path) -> None:
        """Test status with modified file."""
        # Modify a file
        (git_repo_with_commits / "main.py").write_text("print('modified')\n")

        git = GitTools(repo_path=git_repo_with_commits)
        status = git.status()

        assert "main.py" in status.modified
        assert status.is_clean is False

    def test_status_staged(self, git_repo_with_commits: Path) -> None:
        """Test status with staged file."""
        # Create and stage a new file
        (git_repo_with_commits / "new.py").write_text("# new\n")
        subprocess.run(
            ["git", "add", "new.py"],
            cwd=git_repo_with_commits,
            check=True,
            capture_output=True,
        )

        git = GitTools(repo_path=git_repo_with_commits)
        status = git.status()

        assert "new.py" in status.staged
        assert status.has_staged is True

    def test_status_untracked(self, git_repo_with_commits: Path) -> None:
        """Test status with untracked file."""
        (git_repo_with_commits / "untracked.txt").write_text("untracked\n")

        git = GitTools(repo_path=git_repo_with_commits)
        status = git.status()

        assert "untracked.txt" in status.untracked

    def test_status_not_a_repo(self, tmp_path: Path) -> None:
        """Test status on non-repository."""
        git = GitTools(repo_path=tmp_path)

        with pytest.raises(NotARepositoryError):
            git.status()


class TestAdd:
    """Tests for add method."""

    def test_add_single_file(self, git_repo_with_commits: Path) -> None:
        """Test staging a single file."""
        # Create new file
        (git_repo_with_commits / "new.py").write_text("# new\n")

        git = GitTools(repo_path=git_repo_with_commits)
        result = git.add(["new.py"])

        assert result is True

        status = git.status()
        assert "new.py" in status.staged

    def test_add_multiple_files(self, git_repo_with_commits: Path) -> None:
        """Test staging multiple files."""
        (git_repo_with_commits / "a.py").write_text("# a\n")
        (git_repo_with_commits / "b.py").write_text("# b\n")

        git = GitTools(repo_path=git_repo_with_commits)
        git.add(["a.py", "b.py"])

        status = git.status()
        assert "a.py" in status.staged
        assert "b.py" in status.staged

    def test_add_all(self, git_repo_with_commits: Path) -> None:
        """Test staging all files."""
        (git_repo_with_commits / "x.py").write_text("# x\n")
        (git_repo_with_commits / "y.py").write_text("# y\n")

        git = GitTools(repo_path=git_repo_with_commits)
        git.add(".")

        status = git.status()
        assert len(status.staged) >= 2


class TestReset:
    """Tests for reset method."""

    def test_reset_unstages(self, git_repo_with_commits: Path) -> None:
        """Test unstaging files."""
        (git_repo_with_commits / "staged.py").write_text("# staged\n")
        subprocess.run(
            ["git", "add", "staged.py"],
            cwd=git_repo_with_commits,
            check=True,
            capture_output=True,
        )

        git = GitTools(repo_path=git_repo_with_commits)

        # Verify it's staged
        status = git.status()
        assert "staged.py" in status.staged

        # Reset
        git.reset(["staged.py"])

        # Verify unstaged
        status = git.status()
        assert "staged.py" not in status.staged
        assert "staged.py" in status.untracked


class TestCommit:
    """Tests for commit method."""

    def test_commit_staged_changes(self, git_repo_with_commits: Path) -> None:
        """Test committing staged changes."""
        (git_repo_with_commits / "commit_test.py").write_text("# test\n")

        git = GitTools(repo_path=git_repo_with_commits)
        git.add(["commit_test.py"])

        commit_hash = git.commit("Test commit message")

        assert commit_hash is not None
        assert len(commit_hash) >= 7

    def test_commit_nothing_staged(self, git_repo_with_commits: Path) -> None:
        """Test commit with nothing staged."""
        git = GitTools(repo_path=git_repo_with_commits)

        result = git.commit("Empty commit")

        assert result is None

    def test_commit_with_add_all(self, git_repo_with_commits: Path) -> None:
        """Test commit with -a flag."""
        # Modify tracked file
        (git_repo_with_commits / "main.py").write_text("print('modified')\n")

        git = GitTools(repo_path=git_repo_with_commits)

        # Commit with add_all (stages modified tracked files)
        commit_hash = git.commit("Commit all changes", add_all=True)

        assert commit_hash is not None

    def test_commit_allow_empty(self, git_repo_with_commits: Path) -> None:
        """Test empty commit."""
        git = GitTools(repo_path=git_repo_with_commits)

        commit_hash = git.commit("Empty commit", allow_empty=True)

        assert commit_hash is not None


class TestLog:
    """Tests for log method."""

    def test_log_returns_commits(self, git_repo_with_commits: Path) -> None:
        """Test getting commit history."""
        git = GitTools(repo_path=git_repo_with_commits)
        commits = git.log(limit=10)

        assert len(commits) >= 2  # Initial + Add main.py
        assert all(isinstance(c, GitCommit) for c in commits)

    def test_log_limit(self, git_repo_with_commits: Path) -> None:
        """Test log limit."""
        git = GitTools(repo_path=git_repo_with_commits)
        commits = git.log(limit=1)

        assert len(commits) == 1

    def test_log_newest_first(self, git_repo_with_commits: Path) -> None:
        """Test commits are newest first."""
        git = GitTools(repo_path=git_repo_with_commits)
        commits = git.log(limit=2)

        assert commits[0].subject == "Add main.py"
        assert commits[1].subject == "Initial commit"

    def test_log_empty_repo(self, git_repo: Path) -> None:
        """Test log on repo with no commits."""
        git = GitTools(repo_path=git_repo)
        commits = git.log()

        assert commits == []

    def test_commit_fields(self, git_repo_with_commits: Path) -> None:
        """Test commit fields are populated."""
        git = GitTools(repo_path=git_repo_with_commits)
        commits = git.log(limit=1)

        commit = commits[0]
        assert commit.hash is not None
        assert commit.short_hash is not None
        assert commit.subject is not None
        assert commit.author == "Test User"
        assert commit.author_email == "test@example.com"
        assert isinstance(commit.date, datetime)


class TestDiff:
    """Tests for diff method."""

    def test_diff_unstaged(self, git_repo_with_commits: Path) -> None:
        """Test diff of unstaged changes."""
        (git_repo_with_commits / "main.py").write_text("print('changed')\n")

        git = GitTools(repo_path=git_repo_with_commits)
        diff = git.diff()

        assert "changed" in diff

    def test_diff_staged(self, git_repo_with_commits: Path) -> None:
        """Test diff of staged changes."""
        (git_repo_with_commits / "main.py").write_text("print('staged change')\n")
        subprocess.run(
            ["git", "add", "main.py"],
            cwd=git_repo_with_commits,
            check=True,
            capture_output=True,
        )

        git = GitTools(repo_path=git_repo_with_commits)
        diff = git.diff(staged=True)

        assert "staged change" in diff

    def test_diff_no_changes(self, git_repo_with_commits: Path) -> None:
        """Test diff with no changes."""
        git = GitTools(repo_path=git_repo_with_commits)
        diff = git.diff()

        assert diff.strip() == ""


class TestCurrentBranch:
    """Tests for current_branch method."""

    def test_current_branch_main(self, git_repo_with_commits: Path) -> None:
        """Test getting current branch."""
        git = GitTools(repo_path=git_repo_with_commits)
        branch = git.current_branch()

        assert branch == "main"

    def test_current_branch_new_branch(self, git_repo_with_commits: Path) -> None:
        """Test getting branch after checkout."""
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo_with_commits,
            check=True,
            capture_output=True,
        )

        git = GitTools(repo_path=git_repo_with_commits)
        branch = git.current_branch()

        assert branch == "feature"


class TestCheckout:
    """Tests for checkout method."""

    def test_checkout_new_branch(self, git_repo_with_commits: Path) -> None:
        """Test creating and checking out new branch."""
        git = GitTools(repo_path=git_repo_with_commits)
        git.checkout("new-feature", create=True)

        assert git.current_branch() == "new-feature"

    def test_checkout_existing_branch(self, git_repo_with_commits: Path) -> None:
        """Test checking out existing branch."""
        # Create a branch
        subprocess.run(
            ["git", "checkout", "-b", "existing"],
            cwd=git_repo_with_commits,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo_with_commits,
            check=True,
            capture_output=True,
        )

        git = GitTools(repo_path=git_repo_with_commits)
        git.checkout("existing")

        assert git.current_branch() == "existing"


class TestStash:
    """Tests for stash operations."""

    def test_stash_and_pop(self, git_repo_with_commits: Path) -> None:
        """Test stashing and popping changes."""
        # Make changes
        (git_repo_with_commits / "main.py").write_text("print('stashed')\n")

        git = GitTools(repo_path=git_repo_with_commits)

        # Verify changes
        status = git.status()
        assert len(status.modified) > 0

        # Stash
        git.stash("Test stash")

        # Verify clean
        status = git.status()
        assert status.is_clean

        # Pop
        git.stash_pop()

        # Verify restored
        status = git.status()
        assert "main.py" in status.modified


class TestInit:
    """Tests for init method."""

    def test_init_creates_repo(self, tmp_path: Path) -> None:
        """Test initializing a new repository."""
        new_repo = tmp_path / "new_repo"
        new_repo.mkdir()

        git = GitTools(repo_path=new_repo)
        result = git.init()

        assert result is True
        assert git.is_repo() is True


class TestRemoteUrl:
    """Tests for get_remote_url method."""

    def test_no_remote(self, git_repo_with_commits: Path) -> None:
        """Test repo with no remote."""
        git = GitTools(repo_path=git_repo_with_commits)
        url = git.get_remote_url()

        assert url is None
