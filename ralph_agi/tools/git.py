"""Git tools for RALPH-AGI.

Provides git operations for version control, including
status, staging, committing, and history viewing.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Sequence

from ralph_agi.tools.shell import ShellTools

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Base exception for git operations."""

    pass


class NotARepositoryError(GitError):
    """Raised when path is not a git repository."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Not a git repository: {path}")


class GitCommandError(GitError):
    """Raised when a git command fails."""

    def __init__(self, command: str, stderr: str, exit_code: int):
        self.command = command
        self.stderr = stderr
        self.exit_code = exit_code
        super().__init__(f"Git command failed: {command}\n{stderr}")


class GitWorkflowError(GitError):
    """Raised when git workflow rules are violated."""

    def __init__(self, message: str, branch: str, protected_branches: list[str]):
        self.branch = branch
        self.protected_branches = protected_branches
        super().__init__(message)


@dataclass
class GitStatus:
    """Repository status information.

    Attributes:
        branch: Current branch name
        staged: List of staged file paths
        modified: List of modified (unstaged) file paths
        untracked: List of untracked file paths
        deleted: List of deleted file paths
        renamed: List of renamed file paths (as "old -> new")
        ahead: Commits ahead of remote (or 0)
        behind: Commits behind remote (or 0)
        is_clean: True if no changes to commit
    """

    branch: str
    staged: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    renamed: list[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0

    @property
    def is_clean(self) -> bool:
        """Check if working tree is clean."""
        return (
            len(self.staged) == 0
            and len(self.modified) == 0
            and len(self.untracked) == 0
            and len(self.deleted) == 0
        )

    @property
    def has_staged(self) -> bool:
        """Check if there are staged changes."""
        return len(self.staged) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "branch": self.branch,
            "staged": self.staged,
            "modified": self.modified,
            "untracked": self.untracked,
            "deleted": self.deleted,
            "renamed": self.renamed,
            "ahead": self.ahead,
            "behind": self.behind,
            "is_clean": self.is_clean,
        }


@dataclass
class GitCommit:
    """Commit information.

    Attributes:
        hash: Full commit SHA
        short_hash: Short commit SHA (7 chars)
        message: Full commit message
        subject: First line of commit message
        author: Author name
        author_email: Author email
        date: Commit date
    """

    hash: str
    short_hash: str
    message: str
    subject: str
    author: str
    author_email: str
    date: datetime

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "hash": self.hash,
            "short_hash": self.short_hash,
            "message": self.message,
            "subject": self.subject,
            "author": self.author,
            "author_email": self.author_email,
            "date": self.date.isoformat(),
        }


class GitTools:
    """Git operations for version control.

    Provides a high-level interface for common git operations
    including status, staging, committing, and history viewing.

    Usage:
        # Initialize for a repository
        git = GitTools(repo_path="/path/to/repo")

        # Check status
        status = git.status()
        print(f"On branch: {status.branch}")
        print(f"Modified files: {status.modified}")

        # Stage and commit changes
        git.add(["src/main.py", "tests/test_main.py"])
        git.commit("Add main module with tests")

        # View history
        for commit in git.log(limit=5):
            print(f"{commit.short_hash} {commit.subject}")

        # Get diff
        diff = git.diff()
        print(diff)
    """

    def __init__(
        self,
        repo_path: str | Path | None = None,
        shell: ShellTools | None = None,
    ):
        """Initialize git tools.

        Args:
            repo_path: Path to git repository (default: current directory)
            shell: ShellTools instance to use (created if None)
        """
        self._repo_path = Path(repo_path).resolve() if repo_path else Path.cwd()
        self._shell = shell or ShellTools(default_cwd=self._repo_path)

        logger.debug(f"GitTools initialized for: {self._repo_path}")

    @property
    def repo_path(self) -> Path:
        """Get repository path."""
        return self._repo_path

    def _run_git(self, *args: str, check: bool = True) -> str:
        """Run a git command.

        Args:
            *args: Git command arguments
            check: Whether to raise on failure

        Returns:
            Command stdout

        Raises:
            GitCommandError: If command fails and check=True
        """
        cmd = "git " + " ".join(args)
        result = self._shell.execute(cmd, cwd=self._repo_path)

        if check and not result.success:
            raise GitCommandError(cmd, result.stderr, result.exit_code)

        return result.stdout

    def is_repo(self) -> bool:
        """Check if path is a git repository.

        Returns:
            True if path is inside a git repository
        """
        result = self._shell.execute(
            "git rev-parse --git-dir",
            cwd=self._repo_path,
        )
        return result.success

    def _ensure_repo(self) -> None:
        """Ensure path is a git repository.

        Raises:
            NotARepositoryError: If not a repository
        """
        if not self.is_repo():
            raise NotARepositoryError(str(self._repo_path))

    def validate_workflow(
        self,
        workflow: str,
        protected_branches: list[str] | None = None,
    ) -> None:
        """Validate that current branch is allowed for commits.

        In 'branch' or 'pr' workflow modes, commits to protected branches
        are not allowed. This should be called before committing.

        Args:
            workflow: Workflow mode ('direct', 'branch', or 'pr')
            protected_branches: List of protected branch names.
                Defaults to ['main', 'master']

        Raises:
            GitWorkflowError: If on protected branch in branch/pr mode
            NotARepositoryError: If not a repository
        """
        if workflow == "direct":
            # Direct mode allows commits anywhere
            return

        if protected_branches is None:
            protected_branches = ["main", "master"]

        self._ensure_repo()
        current = self.current_branch()

        if current in protected_branches:
            raise GitWorkflowError(
                f"Cannot commit to protected branch '{current}' in '{workflow}' mode. "
                f"Create a feature branch first with: git.checkout('feature-name', create=True)",
                branch=current,
                protected_branches=protected_branches,
            )

    def status(self) -> GitStatus:
        """Get repository status.

        Returns:
            GitStatus with branch and file states

        Raises:
            NotARepositoryError: If not a repository
        """
        self._ensure_repo()

        # Get current branch
        branch = self._run_git("branch", "--show-current").strip()
        if not branch:
            # Detached HEAD
            branch = self._run_git("rev-parse", "--short", "HEAD").strip()
            branch = f"HEAD detached at {branch}"

        # Get status with porcelain format (machine-readable)
        status_output = self._run_git("status", "--porcelain=v1", "-b")

        staged = []
        modified = []
        untracked = []
        deleted = []
        renamed = []
        ahead = 0
        behind = 0

        for line in status_output.split("\n"):
            if not line:
                continue

            # Branch line (## branch...origin/branch [ahead N, behind M])
            if line.startswith("##"):
                # Parse ahead/behind
                match = re.search(r"\[ahead (\d+)", line)
                if match:
                    ahead = int(match.group(1))
                match = re.search(r"behind (\d+)", line)
                if match:
                    behind = int(match.group(1))
                continue

            # File status (XY filename)
            if len(line) >= 3:
                index_status = line[0]
                worktree_status = line[1]
                filename = line[3:]

                # Handle renames (R  old -> new)
                if index_status == "R":
                    renamed.append(filename)
                    staged.append(filename.split(" -> ")[-1])
                elif index_status in "MADC":
                    # Staged changes
                    staged.append(filename)

                if worktree_status == "M":
                    # Modified in worktree
                    modified.append(filename)
                elif worktree_status == "D":
                    deleted.append(filename)
                elif worktree_status == "?":
                    untracked.append(filename)

        return GitStatus(
            branch=branch,
            staged=staged,
            modified=modified,
            untracked=untracked,
            deleted=deleted,
            renamed=renamed,
            ahead=ahead,
            behind=behind,
        )

    def add(self, files: Sequence[str] | str = ".") -> bool:
        """Stage files for commit.

        Args:
            files: File paths to stage, or "." for all changes

        Returns:
            True if successful

        Raises:
            NotARepositoryError: If not a repository
            GitCommandError: If staging fails
        """
        self._ensure_repo()

        if isinstance(files, str):
            files = [files]

        # Quote file paths to handle spaces
        file_args = " ".join(f'"{f}"' for f in files)
        self._run_git("add", file_args)

        logger.info(f"GIT_ADD: {files}")
        return True

    def reset(self, files: Sequence[str] | str | None = None) -> bool:
        """Unstage files.

        Args:
            files: Files to unstage, or None for all

        Returns:
            True if successful
        """
        self._ensure_repo()

        if files is None:
            self._run_git("reset")
        else:
            if isinstance(files, str):
                files = [files]
            file_args = " ".join(f'"{f}"' for f in files)
            self._run_git("reset", file_args)

        return True

    def commit(
        self,
        message: str,
        allow_empty: bool = False,
        add_all: bool = False,
    ) -> str | None:
        """Create a commit.

        Args:
            message: Commit message
            allow_empty: Allow commits with no changes
            add_all: Stage all changes before committing (-a flag)

        Returns:
            Commit hash if successful, None if nothing to commit

        Raises:
            NotARepositoryError: If not a repository
            GitCommandError: If commit fails
        """
        self._ensure_repo()

        # Check if there's anything to commit
        status = self.status()
        if not status.has_staged and not add_all and not allow_empty:
            logger.warning("GIT_COMMIT: Nothing staged to commit")
            return None

        # Build commit command
        args = ["commit"]
        if add_all:
            args.append("-a")
        if allow_empty:
            args.append("--allow-empty")

        # Use -m with quoted message
        # Handle multi-line messages
        message = message.replace('"', '\\"')
        args.append(f'-m "{message}"')

        result = self._shell.execute(
            "git " + " ".join(args),
            cwd=self._repo_path,
        )

        if not result.success:
            if "nothing to commit" in result.stdout + result.stderr:
                return None
            raise GitCommandError("git commit", result.stderr, result.exit_code)

        # Extract commit hash from output
        # Format: [branch hash] message
        match = re.search(r"\[[\w/\-]+ ([a-f0-9]+)\]", result.stdout)
        commit_hash = match.group(1) if match else None

        logger.info(f"GIT_COMMIT: {commit_hash} - {message[:50]}")
        return commit_hash

    def log(self, limit: int = 10) -> list[GitCommit]:
        """Get recent commit history.

        Args:
            limit: Maximum number of commits to return

        Returns:
            List of GitCommit objects (newest first)

        Raises:
            NotARepositoryError: If not a repository
        """
        self._ensure_repo()

        # Use custom format for easy parsing
        # %H = hash, %h = short hash, %s = subject, %b = body
        # %an = author name, %ae = author email, %ai = author date ISO
        fmt = "%H%x00%h%x00%s%x00%b%x00%an%x00%ae%x00%ai%x00"

        result = self._shell.execute(
            f'git log -{limit} --format="{fmt}" --',
            cwd=self._repo_path,
        )

        if not result.success:
            # No commits yet
            if "does not have any commits" in result.stderr:
                return []
            raise GitCommandError("git log", result.stderr, result.exit_code)

        commits = []
        # Split by record separator and parse each
        entries = result.stdout.split("\x00\n")

        current_parts = []
        for entry in result.stdout.split("\x00"):
            current_parts.append(entry)
            if len(current_parts) == 7:
                hash_full, short_hash, subject, body, author, email, date_str = (
                    current_parts
                )

                # Parse date
                try:
                    # Git ISO format: 2024-01-15 10:30:00 -0800
                    date = datetime.fromisoformat(date_str.strip().replace(" ", "T", 1))
                except ValueError:
                    date = datetime.now()

                # Combine subject and body for full message
                message = subject
                if body.strip():
                    message = f"{subject}\n\n{body.strip()}"

                commits.append(
                    GitCommit(
                        hash=hash_full.strip(),
                        short_hash=short_hash.strip(),
                        message=message,
                        subject=subject.strip(),
                        author=author.strip(),
                        author_email=email.strip(),
                        date=date,
                    )
                )
                current_parts = []

        return commits

    def diff(self, staged: bool = False, file: str | None = None) -> str:
        """Get diff of changes.

        Args:
            staged: If True, show staged changes (--cached)
            file: Specific file to diff (optional)

        Returns:
            Diff output as string

        Raises:
            NotARepositoryError: If not a repository
        """
        self._ensure_repo()

        args = ["diff"]
        if staged:
            args.append("--cached")
        if file:
            args.append(f'"{file}"')

        return self._run_git(*args)

    def current_branch(self) -> str:
        """Get current branch name.

        Returns:
            Branch name, or "HEAD" if detached

        Raises:
            NotARepositoryError: If not a repository
        """
        self._ensure_repo()

        branch = self._run_git("branch", "--show-current").strip()
        if not branch:
            # Detached HEAD - return short hash
            return self._run_git("rev-parse", "--short", "HEAD").strip()
        return branch

    def checkout(self, target: str, create: bool = False) -> bool:
        """Checkout a branch or commit.

        Args:
            target: Branch name or commit hash
            create: Create new branch if True (-b flag)

        Returns:
            True if successful

        Raises:
            NotARepositoryError: If not a repository
            GitCommandError: If checkout fails
        """
        self._ensure_repo()

        args = ["checkout"]
        if create:
            args.append("-b")
        args.append(target)

        self._run_git(*args)
        logger.info(f"GIT_CHECKOUT: {target}")
        return True

    def stash(self, message: str | None = None) -> bool:
        """Stash current changes.

        Args:
            message: Optional stash message

        Returns:
            True if changes were stashed
        """
        self._ensure_repo()

        if message:
            self._run_git("stash", "push", "-m", f'"{message}"')
        else:
            self._run_git("stash")

        return True

    def stash_pop(self) -> bool:
        """Pop most recent stash.

        Returns:
            True if stash was applied
        """
        self._ensure_repo()

        result = self._shell.execute("git stash pop", cwd=self._repo_path)
        return result.success

    def get_remote_url(self, remote: str = "origin") -> str | None:
        """Get URL of a remote.

        Args:
            remote: Remote name (default: origin)

        Returns:
            Remote URL or None if not found
        """
        self._ensure_repo()

        result = self._shell.execute(
            f"git remote get-url {remote}",
            cwd=self._repo_path,
        )

        if result.success:
            return result.stdout.strip()
        return None

    def init(self, initial_branch: str = "main") -> bool:
        """Initialize a new git repository.

        Args:
            initial_branch: Name for initial branch

        Returns:
            True if successful
        """
        result = self._shell.execute(
            f"git init -b {initial_branch}",
            cwd=self._repo_path,
        )
        return result.success

    def clone(self, url: str, target_dir: str | None = None) -> bool:
        """Clone a repository.

        Args:
            url: Repository URL
            target_dir: Target directory (optional)

        Returns:
            True if successful
        """
        args = ["clone", f'"{url}"']
        if target_dir:
            args.append(f'"{target_dir}"')

        result = self._shell.execute(
            "git " + " ".join(args),
            cwd=self._repo_path,
        )
        return result.success

    def push(
        self,
        remote: str = "origin",
        branch: str | None = None,
        set_upstream: bool = False,
        force: bool = False,
    ) -> str:
        """Push commits to remote.

        Args:
            remote: Remote name (default: origin)
            branch: Branch to push (default: current branch)
            set_upstream: Set upstream tracking (-u flag)
            force: Force push (use with caution!)

        Returns:
            Push output message

        Raises:
            NotARepositoryError: If not a repository
            GitCommandError: If push fails
        """
        self._ensure_repo()

        args = ["push"]
        if set_upstream:
            args.append("-u")
        if force:
            args.append("--force")
        args.append(remote)
        if branch:
            args.append(branch)

        output = self._run_git(*args)
        logger.info(f"GIT_PUSH: {remote}/{branch or 'current'}")
        return output

    def pull(
        self,
        remote: str = "origin",
        branch: str | None = None,
    ) -> str:
        """Pull from remote.

        Args:
            remote: Remote name (default: origin)
            branch: Branch to pull (default: current tracking branch)

        Returns:
            Pull output message

        Raises:
            NotARepositoryError: If not a repository
            GitCommandError: If pull fails
        """
        self._ensure_repo()

        args = ["pull", remote]
        if branch:
            args.append(branch)

        output = self._run_git(*args)
        logger.info(f"GIT_PULL: {remote}/{branch or 'tracking'}")
        return output

    def list_branches(self, remote: bool = False, all: bool = False) -> list[str]:
        """List branches.

        Args:
            remote: List remote branches only
            all: List all branches (local and remote)

        Returns:
            List of branch names

        Raises:
            NotARepositoryError: If not a repository
        """
        self._ensure_repo()

        args = ["branch"]
        if all:
            args.append("-a")
        elif remote:
            args.append("-r")

        output = self._run_git(*args)

        # Parse output: each line is "  branch" or "* current-branch"
        branches = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            # Remove leading whitespace and * marker for current branch
            branch = line.strip().lstrip("* ").strip()
            # Skip remotes/origin/HEAD -> origin/main type lines
            if " -> " in branch:
                continue
            if branch:
                branches.append(branch)

        return branches

    def delete_branch(self, branch: str, force: bool = False) -> bool:
        """Delete a branch.

        Args:
            branch: Branch name to delete
            force: Force delete even if not merged (-D flag)

        Returns:
            True if successful

        Raises:
            NotARepositoryError: If not a repository
            GitCommandError: If delete fails (e.g., branch doesn't exist)
        """
        self._ensure_repo()

        flag = "-D" if force else "-d"
        self._run_git("branch", flag, branch)
        logger.info(f"GIT_DELETE_BRANCH: {branch}")
        return True

    def create_pr(
        self,
        title: str,
        body: str = "",
        base: str = "main",
        draft: bool = False,
    ) -> dict:
        """Create a pull request via GitHub CLI (gh).

        Requires gh CLI to be installed and authenticated.

        Args:
            title: PR title
            body: PR description/body
            base: Base branch to merge into (default: main)
            draft: Create as draft PR

        Returns:
            Dict with PR info: {number, url, state, title}

        Raises:
            NotARepositoryError: If not a repository
            GitCommandError: If PR creation fails (gh not installed, auth issues, etc.)
        """
        self._ensure_repo()

        # Build gh pr create command
        args = ["gh", "pr", "create"]
        args.extend(["--title", f'"{title}"'])
        if body:
            # Escape quotes in body
            escaped_body = body.replace('"', '\\"')
            args.extend(["--body", f'"{escaped_body}"'])
        args.extend(["--base", base])
        if draft:
            args.append("--draft")

        cmd = " ".join(args)
        result = self._shell.execute(cmd, cwd=self._repo_path)

        if not result.success:
            raise GitCommandError(cmd, result.stderr, result.exit_code)

        # gh pr create outputs the PR URL on success
        pr_url = result.stdout.strip()

        # Extract PR number from URL (e.g., .../pull/123)
        pr_number = None
        match = re.search(r"/pull/(\d+)", pr_url)
        if match:
            pr_number = int(match.group(1))

        logger.info(f"GIT_CREATE_PR: #{pr_number} - {title}")

        return {
            "number": pr_number,
            "url": pr_url,
            "state": "draft" if draft else "open",
            "title": title,
        }

    def get_pr_status(self, pr_number: int | None = None) -> dict | None:
        """Get pull request status via GitHub CLI (gh).

        Args:
            pr_number: PR number (default: PR for current branch)

        Returns:
            Dict with PR info or None if no PR found

        Raises:
            NotARepositoryError: If not a repository
        """
        self._ensure_repo()

        if pr_number:
            cmd = f"gh pr view {pr_number} --json number,url,state,title,mergeable"
        else:
            cmd = "gh pr view --json number,url,state,title,mergeable"

        result = self._shell.execute(cmd, cwd=self._repo_path)

        if not result.success:
            # No PR found for current branch
            return None

        # Parse JSON output
        import json

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
