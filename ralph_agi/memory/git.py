"""Git integration for medium-term memory.

This module provides git-based memory operations, linking code changes
to memory frames for comprehensive history tracking.

Design Principles:
- Auto-commit after successful task completion
- Link memory frames to git commits
- Query memory by commit reference
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ralph_agi.memory.store import MemoryStore

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Git operation error."""

    pass


@dataclass(frozen=True)
class GitCommit:
    """A git commit with metadata.

    Attributes:
        sha: Full commit SHA hash.
        short_sha: Short (7 char) commit SHA.
        message: Commit message.
        author: Author name.
        author_email: Author email.
        timestamp: Commit timestamp (ISO format).
        files_changed: Number of files changed.
    """

    sha: str
    short_sha: str
    message: str
    author: str
    author_email: str
    timestamp: str
    files_changed: int = 0

    @property
    def summary(self) -> str:
        """Get a one-line summary of the commit."""
        first_line = self.message.split("\n")[0]
        return f"{self.short_sha}: {first_line}"


class GitMemory:
    """Git integration for memory system.

    Provides functionality for:
    - Auto-committing after task completion
    - Storing commit metadata in memory frames
    - Querying memory by commit reference

    Example:
        >>> git_mem = GitMemory(repo_path=".", memory_store=store)
        >>> commit = git_mem.commit_changes(
        ...     description="Add user authentication",
        ...     task_id="TASK-001"
        ... )
        >>> print(f"Committed: {commit.short_sha}")
    """

    # Commit message templates
    FEAT_TEMPLATE = "feat: {description}"
    FIX_TEMPLATE = "fix: {description}"
    REFACTOR_TEMPLATE = "refactor: {description}"
    DOCS_TEMPLATE = "docs: {description}"
    TEST_TEMPLATE = "test: {description}"
    CHORE_TEMPLATE = "chore: {description}"

    def __init__(
        self,
        repo_path: str | Path = ".",
        memory_store: Optional[MemoryStore] = None,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
    ):
        """Initialize GitMemory.

        Args:
            repo_path: Path to git repository. Default: current directory.
            memory_store: Optional MemoryStore for linking commits to frames.
            author_name: Optional author name for commits.
            author_email: Optional author email for commits.
        """
        self.repo_path = Path(repo_path).resolve()
        self._memory_store = memory_store
        self._author_name = author_name
        self._author_email = author_email

    def _run_git(
        self,
        *args: str,
        capture: bool = True,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a git command.

        Args:
            *args: Git command arguments.
            capture: Whether to capture output. Default: True.
            check: Whether to check return code. Default: True.

        Returns:
            CompletedProcess with command result.

        Raises:
            GitError: If command fails and check=True.
        """
        cmd = ["git", "-C", str(self.repo_path), *args]
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture,
                text=True,
                check=check,
            )
            return result
        except subprocess.CalledProcessError as e:
            raise GitError(f"Git command failed: {' '.join(args)}\n{e.stderr}") from e

    def is_repo(self) -> bool:
        """Check if the path is a git repository.

        Returns:
            True if path is a git repo, False otherwise.
        """
        try:
            self._run_git("rev-parse", "--git-dir", check=True)
            return True
        except GitError:
            return False

    def has_changes(self, staged_only: bool = False) -> bool:
        """Check if there are uncommitted changes.

        Args:
            staged_only: If True, only check staged changes.

        Returns:
            True if there are changes to commit.
        """
        try:
            if staged_only:
                result = self._run_git("diff", "--cached", "--quiet", check=False)
            else:
                result = self._run_git("status", "--porcelain", check=True)
                return bool(result.stdout.strip())
            return result.returncode != 0
        except GitError:
            return False

    def get_status(self) -> dict[str, list[str]]:
        """Get current git status.

        Returns:
            Dictionary with keys: staged, modified, untracked.
        """
        result = self._run_git("status", "--porcelain")

        staged = []
        modified = []
        untracked = []

        # Don't strip() - it removes leading spaces which are meaningful in porcelain output
        for line in result.stdout.rstrip("\n").split("\n"):
            if not line:
                continue
            status = line[:2]
            filepath = line[3:]

            # First column: index status (staged changes)
            if status[0] in "MADRC":
                staged.append(filepath)
            # Second column: worktree status (unstaged modifications)
            if status[1] in "MD":
                modified.append(filepath)
            # Untracked files
            if status == "??":
                untracked.append(filepath)

        return {
            "staged": staged,
            "modified": modified,
            "untracked": untracked,
        }

    def stage_all(self) -> int:
        """Stage all changes (git add -A).

        Returns:
            Number of files staged.
        """
        status_before = self.get_status()
        total_before = (
            len(status_before["staged"])
            + len(status_before["modified"])
            + len(status_before["untracked"])
        )

        self._run_git("add", "-A")

        status_after = self.get_status()
        return len(status_after["staged"])

    def stage_files(self, *files: str) -> int:
        """Stage specific files.

        Args:
            *files: File paths to stage.

        Returns:
            Number of files staged.
        """
        if not files:
            return 0

        self._run_git("add", "--", *files)
        return len(files)

    def commit(
        self,
        message: str,
        allow_empty: bool = False,
    ) -> Optional[GitCommit]:
        """Create a git commit.

        Args:
            message: Commit message.
            allow_empty: Allow commits with no changes.

        Returns:
            GitCommit if successful, None if no changes and allow_empty=False.

        Raises:
            GitError: If commit fails.
        """
        if not self.has_changes(staged_only=True) and not allow_empty:
            logger.debug("No staged changes to commit")
            return None

        # Build commit command
        args = ["commit", "-m", message]
        if allow_empty:
            args.append("--allow-empty")

        # Set author if configured
        env_args = []
        if self._author_name:
            env_args.extend(["-c", f"user.name={self._author_name}"])
        if self._author_email:
            env_args.extend(["-c", f"user.email={self._author_email}"])

        self._run_git(*env_args, *args)

        # Get commit info
        return self.get_head_commit()

    def commit_changes(
        self,
        description: str,
        task_id: Optional[str] = None,
        commit_type: str = "feat",
        stage_all: bool = True,
        session_id: Optional[str] = None,
    ) -> Optional[GitCommit]:
        """Auto-commit with generated message and memory linkage.

        This is the main method for task completion commits.

        Args:
            description: Task/feature description for commit message.
            task_id: Optional task ID to include in commit.
            commit_type: Type of commit (feat, fix, refactor, docs, test, chore).
            stage_all: Whether to stage all changes first.
            session_id: Optional session ID for memory frame.

        Returns:
            GitCommit if successful, None if no changes.
        """
        if stage_all:
            staged = self.stage_all()
            if staged == 0:
                logger.debug("No files to stage")
                return None

        # Generate commit message
        templates = {
            "feat": self.FEAT_TEMPLATE,
            "fix": self.FIX_TEMPLATE,
            "refactor": self.REFACTOR_TEMPLATE,
            "docs": self.DOCS_TEMPLATE,
            "test": self.TEST_TEMPLATE,
            "chore": self.CHORE_TEMPLATE,
        }
        template = templates.get(commit_type, self.FEAT_TEMPLATE)
        message = template.format(description=description)

        # Add task ID if provided
        if task_id:
            message += f"\n\nTask: {task_id}"

        # Create commit
        commit = self.commit(message)
        if commit is None:
            return None

        # Store in memory
        if self._memory_store is not None:
            self._store_commit_frame(commit, task_id, session_id)

        logger.info(f"Committed: {commit.summary}")
        return commit

    def _store_commit_frame(
        self,
        commit: GitCommit,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        """Store a commit as a memory frame.

        Args:
            commit: The GitCommit to store.
            task_id: Optional task ID associated with commit.
            session_id: Optional session ID.

        Returns:
            Frame ID if stored, None otherwise.
        """
        if self._memory_store is None:
            return None

        content = f"Git commit: {commit.summary}\n\n{commit.message}"

        metadata = {
            "commit_sha": commit.sha,
            "commit_short_sha": commit.short_sha,
            "author": commit.author,
            "author_email": commit.author_email,
            "commit_timestamp": commit.timestamp,
            "files_changed": commit.files_changed,
        }
        if task_id:
            metadata["task_id"] = task_id

        tags = ["git", "commit", f"sha:{commit.short_sha}"]
        if task_id:
            tags.append(f"task:{task_id}")

        try:
            frame_id = self._memory_store.append(
                content=content,
                frame_type="git_commit",
                metadata=metadata,
                session_id=session_id,
                tags=tags,
            )
            logger.debug(f"Stored commit {commit.short_sha} as frame {frame_id[:8]}")
            return frame_id
        except Exception as e:
            logger.warning(f"Failed to store commit in memory: {e}")
            return None

    def get_head_commit(self) -> GitCommit:
        """Get the HEAD commit.

        Returns:
            GitCommit for HEAD.

        Raises:
            GitError: If no commits exist.
        """
        return self.get_commit("HEAD")

    def get_commit(self, ref: str) -> GitCommit:
        """Get commit information by reference.

        Args:
            ref: Git reference (SHA, branch, tag, HEAD, etc.)

        Returns:
            GitCommit with commit details.

        Raises:
            GitError: If reference not found.
        """
        # Get commit details - use separate queries for structured data vs message
        # Format: SHA, short SHA, author, email, timestamp (use %x00 as separator)
        format_str = "%H%x00%h%x00%an%x00%ae%x00%aI"
        result = self._run_git("log", "-1", f"--format={format_str}", ref)

        parts = result.stdout.strip().split("\x00")
        if len(parts) < 5:
            raise GitError(f"Invalid commit reference: {ref}")

        # Get full message body separately
        msg_result = self._run_git("log", "-1", "--format=%B", ref)
        message = msg_result.stdout.strip()

        # Get files changed count
        stat_result = self._run_git(
            "diff-tree", "--no-commit-id", "--name-only", "-r", ref
        )
        files_changed = len([l for l in stat_result.stdout.strip().split("\n") if l])

        return GitCommit(
            sha=parts[0],
            short_sha=parts[1],
            message=message,
            author=parts[2],
            author_email=parts[3],
            timestamp=parts[4],
            files_changed=files_changed,
        )

    def get_commits_since(
        self,
        since: str,
        limit: int = 50,
    ) -> list[GitCommit]:
        """Get commits since a reference.

        Args:
            since: Git reference to start from.
            limit: Maximum commits to return.

        Returns:
            List of GitCommit objects, newest first.
        """
        result = self._run_git(
            "log",
            f"--max-count={limit}",
            "--format=%H",
            f"{since}..HEAD",
        )

        commits = []
        for sha in result.stdout.strip().split("\n"):
            if sha:
                try:
                    commits.append(self.get_commit(sha))
                except GitError:
                    continue

        return commits

    def get_commits_for_file(
        self,
        filepath: str,
        limit: int = 20,
    ) -> list[GitCommit]:
        """Get commits that modified a specific file.

        Args:
            filepath: Path to file (relative to repo root).
            limit: Maximum commits to return.

        Returns:
            List of GitCommit objects, newest first.
        """
        result = self._run_git(
            "log",
            f"--max-count={limit}",
            "--format=%H",
            "--",
            filepath,
        )

        commits = []
        for sha in result.stdout.strip().split("\n"):
            if sha:
                try:
                    commits.append(self.get_commit(sha))
                except GitError:
                    continue

        return commits

    def search_commits(
        self,
        query: str,
        limit: int = 20,
    ) -> list[GitCommit]:
        """Search commits by message content.

        Args:
            query: Search string for commit messages.
            limit: Maximum commits to return.

        Returns:
            List of matching GitCommit objects.
        """
        result = self._run_git(
            "log",
            f"--max-count={limit}",
            "--format=%H",
            f"--grep={query}",
            "--regexp-ignore-case",
        )

        commits = []
        for sha in result.stdout.strip().split("\n"):
            if sha:
                try:
                    commits.append(self.get_commit(sha))
                except GitError:
                    continue

        return commits

    def get_memory_by_commit(
        self,
        commit_ref: str,
        limit: int = 10,
    ) -> list:
        """Query memory frames linked to a commit.

        Args:
            commit_ref: Git reference (SHA, branch, etc.)
            limit: Maximum frames to return.

        Returns:
            List of MemoryFrame objects linked to the commit.
        """
        if self._memory_store is None:
            return []

        try:
            commit = self.get_commit(commit_ref)
            # Search by short SHA tag
            return self._memory_store.search(
                f"sha:{commit.short_sha}",
                limit=limit,
                mode="keyword",
            )
        except GitError:
            return []

    def revert_commit(self, ref: str = "HEAD") -> Optional[GitCommit]:
        """Revert a commit.

        Args:
            ref: Git reference to revert. Default: HEAD.

        Returns:
            The revert commit if successful.

        Raises:
            GitError: If revert fails.
        """
        self._run_git("revert", "--no-edit", ref)
        return self.get_head_commit()

    def get_diff(
        self,
        ref1: str = "HEAD~1",
        ref2: str = "HEAD",
        filepath: Optional[str] = None,
    ) -> str:
        """Get diff between two references.

        Args:
            ref1: First reference.
            ref2: Second reference.
            filepath: Optional file to diff.

        Returns:
            Diff output as string.
        """
        args = ["diff", ref1, ref2]
        if filepath:
            args.extend(["--", filepath])

        result = self._run_git(*args)
        return result.stdout
