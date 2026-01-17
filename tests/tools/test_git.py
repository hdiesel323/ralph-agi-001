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
    GitWorkflowError,
    NotARepositoryError,
    WorktreeInfo,
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


class TestListBranches:
    """Tests for list_branches method."""

    def test_list_single_branch(self, git_repo_with_commits: Path) -> None:
        """Test listing branches in repo with only main."""
        git = GitTools(repo_path=git_repo_with_commits)
        branches = git.list_branches()

        assert "main" in branches

    def test_list_multiple_branches(self, git_repo_with_commits: Path) -> None:
        """Test listing branches after creating new ones."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Create new branches
        git.checkout("feature-a", create=True)
        git.checkout("feature-b", create=True)
        git.checkout("main")

        branches = git.list_branches()

        assert "main" in branches
        assert "feature-a" in branches
        assert "feature-b" in branches


class TestDeleteBranch:
    """Tests for delete_branch method."""

    def test_delete_branch(self, git_repo_with_commits: Path) -> None:
        """Test deleting a branch."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Create and switch to feature branch
        git.checkout("to-delete", create=True)
        git.checkout("main")

        # Delete the branch
        result = git.delete_branch("to-delete")

        assert result is True
        assert "to-delete" not in git.list_branches()

    def test_delete_nonexistent_branch(self, git_repo_with_commits: Path) -> None:
        """Test deleting a branch that doesn't exist."""
        git = GitTools(repo_path=git_repo_with_commits)

        with pytest.raises(GitCommandError):
            git.delete_branch("nonexistent-branch")

    def test_delete_unmerged_branch_fails(self, git_repo_with_commits: Path) -> None:
        """Test that deleting unmerged branch fails without force."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Create branch with unique commit
        git.checkout("unmerged", create=True)
        (git_repo_with_commits / "unmerged.txt").write_text("unmerged content")
        git.add(["unmerged.txt"])
        git.commit("Unmerged commit")
        git.checkout("main")

        # Should fail without force
        with pytest.raises(GitCommandError):
            git.delete_branch("unmerged")

    def test_delete_unmerged_branch_with_force(self, git_repo_with_commits: Path) -> None:
        """Test force deleting unmerged branch."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Create branch with unique commit
        git.checkout("unmerged", create=True)
        (git_repo_with_commits / "unmerged.txt").write_text("unmerged content")
        git.add(["unmerged.txt"])
        git.commit("Unmerged commit")
        git.checkout("main")

        # Force delete should work
        result = git.delete_branch("unmerged", force=True)
        assert result is True


class TestValidateWorkflow:
    """Tests for validate_workflow method and GitWorkflowError."""

    def test_direct_mode_allows_main(self, git_repo_with_commits: Path) -> None:
        """Test that direct mode allows commits to main."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Should not raise
        git.validate_workflow("direct")
        git.validate_workflow("direct", protected_branches=["main", "master"])

    def test_branch_mode_blocks_main(self, git_repo_with_commits: Path) -> None:
        """Test that branch mode blocks commits to main."""
        git = GitTools(repo_path=git_repo_with_commits)

        with pytest.raises(GitWorkflowError) as exc_info:
            git.validate_workflow("branch")

        assert exc_info.value.branch == "main"
        assert "main" in exc_info.value.protected_branches

    def test_pr_mode_blocks_main(self, git_repo_with_commits: Path) -> None:
        """Test that pr mode blocks commits to main."""
        git = GitTools(repo_path=git_repo_with_commits)

        with pytest.raises(GitWorkflowError) as exc_info:
            git.validate_workflow("pr")

        assert "Cannot commit to protected branch" in str(exc_info.value)

    def test_branch_mode_allows_feature_branch(self, git_repo_with_commits: Path) -> None:
        """Test that branch mode allows commits to feature branches."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Create and switch to feature branch
        git.checkout("feature/test", create=True)

        # Should not raise
        git.validate_workflow("branch")
        git.validate_workflow("pr")

    def test_custom_protected_branches(self, git_repo_with_commits: Path) -> None:
        """Test with custom protected branches list."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Main is not in custom list
        git.validate_workflow("branch", protected_branches=["develop", "release"])

        # Create develop branch
        git.checkout("develop", create=True)

        with pytest.raises(GitWorkflowError):
            git.validate_workflow("branch", protected_branches=["develop", "release"])

    def test_error_includes_helpful_message(self, git_repo_with_commits: Path) -> None:
        """Test that error message includes instructions."""
        git = GitTools(repo_path=git_repo_with_commits)

        with pytest.raises(GitWorkflowError) as exc_info:
            git.validate_workflow("branch")

        error_msg = str(exc_info.value)
        assert "checkout" in error_msg.lower()
        assert "create=True" in error_msg or "feature" in error_msg.lower()


class TestPush:
    """Tests for push method (basic validation, no remote)."""

    def test_push_fails_without_remote(self, git_repo_with_commits: Path) -> None:
        """Test that push fails when no remote is configured."""
        git = GitTools(repo_path=git_repo_with_commits)

        with pytest.raises(GitCommandError):
            git.push()


class TestPull:
    """Tests for pull method (basic validation, no remote)."""

    def test_pull_fails_without_remote(self, git_repo_with_commits: Path) -> None:
        """Test that pull fails when no remote is configured."""
        git = GitTools(repo_path=git_repo_with_commits)

        with pytest.raises(GitCommandError):
            git.pull()


class TestCreatePr:
    """Tests for create_pr method (basic validation, no gh)."""

    def test_create_pr_fails_without_gh(self, git_repo_with_commits: Path) -> None:
        """Test that create_pr fails when gh is not available or not authenticated."""
        git = GitTools(repo_path=git_repo_with_commits)

        # This will fail because either gh isn't installed, or repo has no remote
        # Either way, it should raise GitCommandError
        with pytest.raises(GitCommandError):
            git.create_pr("Test PR", body="Test body")


class TestGetPrStatus:
    """Tests for get_pr_status method."""

    def test_get_pr_status_no_pr(self, git_repo_with_commits: Path) -> None:
        """Test get_pr_status returns None when no PR exists."""
        git = GitTools(repo_path=git_repo_with_commits)

        # No remote/PR, should return None
        result = git.get_pr_status()
        assert result is None


class TestWorktreeInfo:
    """Tests for WorktreeInfo dataclass."""

    def test_worktree_info_creation(self) -> None:
        """Test creating WorktreeInfo."""
        wt = WorktreeInfo(
            path="/path/to/worktree",
            branch="feature-branch",
            commit="abc123def456",
            is_main=False,
        )
        assert wt.path == "/path/to/worktree"
        assert wt.branch == "feature-branch"
        assert wt.commit == "abc123def456"
        assert wt.is_main is False
        assert wt.is_bare is False
        assert wt.is_detached is False

    def test_worktree_info_frozen(self) -> None:
        """Test that WorktreeInfo is immutable."""
        wt = WorktreeInfo(
            path="/path",
            branch="main",
            commit="abc123",
            is_main=True,
        )
        with pytest.raises(AttributeError):
            wt.path = "/new/path"  # type: ignore

    def test_worktree_info_to_dict(self) -> None:
        """Test WorktreeInfo serialization."""
        wt = WorktreeInfo(
            path="/path/to/worktree",
            branch="feature",
            commit="abc123",
            is_main=False,
            is_bare=False,
            is_detached=True,
        )
        d = wt.to_dict()
        assert d["path"] == "/path/to/worktree"
        assert d["branch"] == "feature"
        assert d["commit"] == "abc123"
        assert d["is_main"] is False
        assert d["is_bare"] is False
        assert d["is_detached"] is True


class TestWorktreeAdd:
    """Tests for worktree_add method."""

    def test_worktree_add_creates_worktree(self, git_repo_with_commits: Path, tmp_path: Path) -> None:
        """Test creating a new worktree."""
        git = GitTools(repo_path=git_repo_with_commits)
        worktree_path = tmp_path / "worktree1"

        result = git.worktree_add(str(worktree_path), "test-branch")

        assert result == str(worktree_path)
        assert worktree_path.exists()
        assert (worktree_path / ".git").exists()

    def test_worktree_add_with_new_branch(self, git_repo_with_commits: Path, tmp_path: Path) -> None:
        """Test creating worktree with new branch."""
        git = GitTools(repo_path=git_repo_with_commits)
        worktree_path = tmp_path / "worktree-new-branch"

        git.worktree_add(str(worktree_path), "new-feature", create_branch=True)

        # Verify branch was created
        branches = git.list_branches()
        assert "new-feature" in branches

    def test_worktree_add_with_existing_branch(self, git_repo_with_commits: Path, tmp_path: Path) -> None:
        """Test creating worktree with existing branch."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Create a branch first
        git.checkout("existing-branch", create=True)
        git.checkout("main")

        worktree_path = tmp_path / "worktree-existing"
        git.worktree_add(str(worktree_path), "existing-branch", create_branch=True)

        assert worktree_path.exists()

    def test_worktree_add_path_exists_raises(self, git_repo_with_commits: Path, tmp_path: Path) -> None:
        """Test that adding worktree to existing path raises error."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Create directory first
        existing_dir = tmp_path / "existing-dir"
        existing_dir.mkdir()

        with pytest.raises(GitCommandError) as exc_info:
            git.worktree_add(str(existing_dir), "test-branch")

        assert "already exists" in str(exc_info.value)

    def test_worktree_add_branch_conflict_raises(self, git_repo_with_commits: Path, tmp_path: Path) -> None:
        """Test that adding worktree for branch already checked out raises error."""
        git = GitTools(repo_path=git_repo_with_commits)

        # First worktree
        wt1_path = tmp_path / "worktree1"
        git.worktree_add(str(wt1_path), "conflict-branch")

        # Second worktree with same branch should fail
        wt2_path = tmp_path / "worktree2"
        with pytest.raises(GitCommandError):
            git.worktree_add(str(wt2_path), "conflict-branch", create_branch=False)

    def test_worktree_add_relative_path(self, git_repo_with_commits: Path) -> None:
        """Test creating worktree with relative path."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Use relative path
        result = git.worktree_add("../relative-worktree", "relative-branch")

        # Should resolve to absolute path
        assert Path(result).is_absolute()
        assert Path(result).exists()

        # Cleanup
        git.worktree_remove(result, force=True)

    def test_worktree_add_absolute_path(self, git_repo_with_commits: Path, tmp_path: Path) -> None:
        """Test creating worktree with absolute path."""
        git = GitTools(repo_path=git_repo_with_commits)
        abs_path = tmp_path / "absolute-worktree"

        result = git.worktree_add(str(abs_path), "absolute-branch")

        assert result == str(abs_path)
        assert abs_path.exists()


class TestWorktreeList:
    """Tests for worktree_list method."""

    def test_worktree_list_returns_all_worktrees(self, git_repo_with_commits: Path, tmp_path: Path) -> None:
        """Test listing all worktrees."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Create some worktrees
        wt1 = tmp_path / "wt1"
        wt2 = tmp_path / "wt2"
        git.worktree_add(str(wt1), "branch1")
        git.worktree_add(str(wt2), "branch2")

        worktrees = git.worktree_list()

        # Should have main + 2 worktrees
        assert len(worktrees) == 3

        # All should be WorktreeInfo instances
        assert all(isinstance(wt, WorktreeInfo) for wt in worktrees)

    def test_worktree_list_main_worktree_marked(self, git_repo_with_commits: Path, tmp_path: Path) -> None:
        """Test that main worktree is correctly marked."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Create a worktree
        wt_path = tmp_path / "secondary"
        git.worktree_add(str(wt_path), "secondary-branch")

        worktrees = git.worktree_list()

        # First should be main
        main_wt = worktrees[0]
        assert main_wt.is_main is True

        # Others should not be main
        for wt in worktrees[1:]:
            assert wt.is_main is False

    def test_worktree_list_detached_head(self, git_repo_with_commits: Path, tmp_path: Path) -> None:
        """Test listing worktree with detached HEAD."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Get current commit hash
        commits = git.log(limit=1)
        commit_hash = commits[0].hash

        # Create worktree at specific commit (detached)
        wt_path = tmp_path / "detached"
        git.worktree_add(str(wt_path), commit_hash, create_branch=False)

        worktrees = git.worktree_list()

        # Find the detached worktree
        detached_wt = next((wt for wt in worktrees if str(wt_path) == wt.path), None)
        assert detached_wt is not None
        assert detached_wt.is_detached is True

    def test_worktree_list_empty_repo(self, git_repo: Path) -> None:
        """Test listing worktrees in repo with no commits."""
        git = GitTools(repo_path=git_repo)

        # Even empty repo has one worktree (the main one)
        worktrees = git.worktree_list()
        assert len(worktrees) >= 1


class TestWorktreeRemove:
    """Tests for worktree_remove method."""

    def test_worktree_remove_deletes_worktree(self, git_repo_with_commits: Path, tmp_path: Path) -> None:
        """Test removing a worktree."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Create worktree
        wt_path = tmp_path / "to-remove"
        git.worktree_add(str(wt_path), "to-remove-branch")

        # Verify it exists
        assert wt_path.exists()
        worktrees_before = git.worktree_list()
        assert len(worktrees_before) == 2

        # Remove it
        git.worktree_remove(str(wt_path))

        # Verify it's gone
        worktrees_after = git.worktree_list()
        assert len(worktrees_after) == 1
        assert worktrees_after[0].is_main is True

    def test_worktree_remove_not_exists_raises(self, git_repo_with_commits: Path, tmp_path: Path) -> None:
        """Test removing non-existent worktree raises error."""
        git = GitTools(repo_path=git_repo_with_commits)

        non_existent = tmp_path / "non-existent"

        with pytest.raises(GitCommandError):
            git.worktree_remove(str(non_existent))

    def test_worktree_remove_dirty_requires_force(self, git_repo_with_commits: Path, tmp_path: Path) -> None:
        """Test that removing dirty worktree requires force."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Create worktree
        wt_path = tmp_path / "dirty-worktree"
        git.worktree_add(str(wt_path), "dirty-branch")

        # Make changes in worktree (don't commit)
        (wt_path / "new-file.txt").write_text("uncommitted changes")

        # Should fail without force
        with pytest.raises(GitCommandError):
            git.worktree_remove(str(wt_path))

        # Should succeed with force
        git.worktree_remove(str(wt_path), force=True)


class TestWorktreePrune:
    """Tests for worktree_prune method."""

    def test_worktree_prune_cleans_stale(self, git_repo_with_commits: Path, tmp_path: Path) -> None:
        """Test that prune cleans up stale worktree metadata."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Create worktree
        wt_path = tmp_path / "stale-worktree"
        git.worktree_add(str(wt_path), "stale-branch")

        # Verify worktree exists
        worktrees_before = git.worktree_list()
        assert len(worktrees_before) == 2

        # Manually delete the directory (simulating external deletion)
        import shutil

        shutil.rmtree(wt_path)

        # Worktree list may still show it (stale entry)
        # Prune should clean it up
        pruned = git.worktree_prune()

        # Verify pruned
        worktrees_after = git.worktree_list()
        assert len(worktrees_after) == 1

    def test_worktree_prune_dry_run(self, git_repo_with_commits: Path, tmp_path: Path) -> None:
        """Test prune dry run mode."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Create and manually delete worktree
        wt_path = tmp_path / "dry-run-worktree"
        git.worktree_add(str(wt_path), "dry-run-branch")

        import shutil

        shutil.rmtree(wt_path)

        # Dry run should report but not actually prune
        pruned = git.worktree_prune(dry_run=True)

        # Should report something (may be empty if git version doesn't report)
        # The important thing is it doesn't raise an error
        assert isinstance(pruned, list)

    def test_worktree_prune_nothing_to_prune(self, git_repo_with_commits: Path) -> None:
        """Test prune when nothing needs pruning."""
        git = GitTools(repo_path=git_repo_with_commits)

        # Prune should return empty list
        pruned = git.worktree_prune()

        assert pruned == []
