"""Git history integration for contextual learning.

Layer 3 of the Contextual Learning System - provides access to
git history for implementation evidence and concrete code changes.

Git history provides:
- Recent commit logs
- Detailed commit diffs
- Branch comparisons
- Task ID correlation
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommitInfo:
    """Information about a git commit.

    Attributes:
        hash: Full commit hash.
        short_hash: Abbreviated commit hash.
        author: Commit author name.
        email: Commit author email.
        date: Commit date as ISO string.
        subject: Commit subject line.
        body: Full commit message body.
        files_changed: List of changed file paths.
        task_ids: Extracted task IDs from message.
    """

    hash: str
    short_hash: str
    author: str
    email: str
    date: str
    subject: str
    body: str = ""
    files_changed: tuple[str, ...] = field(default_factory=tuple)
    task_ids: tuple[str, ...] = field(default_factory=tuple)

    @property
    def message(self) -> str:
        """Get full commit message."""
        if self.body:
            return f"{self.subject}\n\n{self.body}"
        return self.subject

    @property
    def is_merge(self) -> bool:
        """Check if this is a merge commit."""
        return self.subject.startswith("Merge ")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hash": self.hash,
            "short_hash": self.short_hash,
            "author": self.author,
            "email": self.email,
            "date": self.date,
            "subject": self.subject,
            "body": self.body,
            "files_changed": list(self.files_changed),
            "task_ids": list(self.task_ids),
        }


@dataclass
class FileDiff:
    """A diff for a single file.

    Attributes:
        path: File path.
        old_path: Previous path (for renames).
        status: Change status (A/M/D/R).
        additions: Lines added.
        deletions: Lines removed.
        content: Diff content.
    """

    path: str
    old_path: Optional[str] = None
    status: str = "M"
    additions: int = 0
    deletions: int = 0
    content: str = ""

    @property
    def is_rename(self) -> bool:
        """Check if this is a rename."""
        return self.old_path is not None

    @property
    def is_new(self) -> bool:
        """Check if this is a new file."""
        return self.status == "A"

    @property
    def is_deleted(self) -> bool:
        """Check if this is a deleted file."""
        return self.status == "D"


@dataclass
class CommitDiff:
    """Detailed diff for a commit.

    Attributes:
        commit: Commit info.
        files: List of file diffs.
        stats: Overall diff stats.
    """

    commit: CommitInfo
    files: list[FileDiff] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def total_additions(self) -> int:
        """Total lines added."""
        return sum(f.additions for f in self.files)

    @property
    def total_deletions(self) -> int:
        """Total lines deleted."""
        return sum(f.deletions for f in self.files)


class GitHistory:
    """Git history access for a repository.

    Provides methods to query git history, diffs, and correlate
    commits to task IDs.
    """

    # Pattern for extracting task IDs from commit messages
    TASK_ID_PATTERNS = (
        r"(?:US|T|TASK|ISSUE|BUG|FEAT|FIX)-\d+",  # US-123, T-456, etc.
        r"#\d+",  # GitHub issue #123
        r"[A-Z]+-\d+",  # Jira-style ABC-123
    )

    def __init__(self, repo_path: Optional[Path] = None) -> None:
        """Initialize git history.

        Args:
            repo_path: Path to git repository. Uses CWD if None.
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()

    def _run_git(
        self,
        *args: str,
        capture: bool = True,
    ) -> Optional[str]:
        """Run a git command.

        Args:
            *args: Git command arguments.
            capture: Whether to capture output.

        Returns:
            Command output or None if error.
        """
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.repo_path,
                capture_output=capture,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning(f"Git command failed: {result.stderr}")
                return None
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.warning("Git command timed out")
            return None
        except Exception as e:
            logger.warning(f"Git command error: {e}")
            return None

    def get_recent_commits(
        self,
        limit: int = 20,
        branch: Optional[str] = None,
        since: Optional[str] = None,
    ) -> list[CommitInfo]:
        """Get recent commits.

        Args:
            limit: Maximum number of commits.
            branch: Branch to query. Uses current if None.
            since: Only commits after this date (e.g., "2025-01-01").

        Returns:
            List of commit info.
        """
        args = [
            "log",
            f"-{limit}",
            "--format=%H|%h|%an|%ae|%aI|%s|%b|||",
            "--name-only",
        ]

        if branch:
            args.append(branch)

        if since:
            args.append(f"--since={since}")

        output = self._run_git(*args)
        if not output:
            return []

        commits = []
        for block in output.split("|||"):
            block = block.strip()
            if not block:
                continue

            lines = block.split("\n")
            if not lines or "|" not in lines[0]:
                continue

            # Parse commit info line
            parts = lines[0].split("|")
            if len(parts) < 6:
                continue

            # Extract files changed
            files = [f.strip() for f in lines[1:] if f.strip()]

            # Extract task IDs from message
            subject = parts[5]
            body = parts[6] if len(parts) > 6 else ""
            task_ids = self._extract_task_ids(subject + " " + body)

            commit = CommitInfo(
                hash=parts[0],
                short_hash=parts[1],
                author=parts[2],
                email=parts[3],
                date=parts[4],
                subject=subject,
                body=body,
                files_changed=tuple(files),
                task_ids=tuple(task_ids),
            )
            commits.append(commit)

        return commits

    def get_commit(self, ref: str = "HEAD") -> Optional[CommitInfo]:
        """Get info for a specific commit.

        Args:
            ref: Commit reference (hash, branch, tag).

        Returns:
            Commit info or None.
        """
        output = self._run_git(
            "log",
            "-1",
            "--format=%H|%h|%an|%ae|%aI|%s|%b",
            ref,
        )
        if not output:
            return None

        parts = output.strip().split("|")
        if len(parts) < 6:
            return None

        subject = parts[5]
        body = parts[6] if len(parts) > 6 else ""
        task_ids = self._extract_task_ids(subject + " " + body)

        # Get files changed
        files_output = self._run_git(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            ref,
        )
        files = tuple(files_output.strip().split("\n")) if files_output else ()

        return CommitInfo(
            hash=parts[0],
            short_hash=parts[1],
            author=parts[2],
            email=parts[3],
            date=parts[4],
            subject=subject,
            body=body,
            files_changed=files,
            task_ids=tuple(task_ids),
        )

    def get_commit_diff(self, ref: str = "HEAD") -> Optional[CommitDiff]:
        """Get detailed diff for a commit.

        Args:
            ref: Commit reference.

        Returns:
            Commit diff or None.
        """
        commit = self.get_commit(ref)
        if not commit:
            return None

        # Get diff stats
        stat_output = self._run_git(
            "diff",
            "--numstat",
            f"{ref}^..{ref}",
        )

        files = []
        if stat_output:
            for line in stat_output.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 3:
                    adds = int(parts[0]) if parts[0] != "-" else 0
                    dels = int(parts[1]) if parts[1] != "-" else 0
                    path = parts[2]
                    files.append(FileDiff(
                        path=path,
                        additions=adds,
                        deletions=dels,
                    ))

        return CommitDiff(
            commit=commit,
            files=files,
            stats={
                "files_changed": len(files),
                "additions": sum(f.additions for f in files),
                "deletions": sum(f.deletions for f in files),
            },
        )

    def get_diff_content(
        self,
        ref: str = "HEAD",
        file_path: Optional[str] = None,
    ) -> str:
        """Get raw diff content.

        Args:
            ref: Commit reference.
            file_path: Specific file to diff.

        Returns:
            Diff content.
        """
        args = ["show", "--format=", ref]
        if file_path:
            args.append("--")
            args.append(file_path)

        output = self._run_git(*args)
        return output or ""

    def get_branch_diff(
        self,
        base_branch: str = "main",
        head_branch: Optional[str] = None,
    ) -> list[CommitInfo]:
        """Get commits between branches.

        Args:
            base_branch: Base branch to compare from.
            head_branch: Head branch to compare. Uses current if None.

        Returns:
            Commits unique to head branch.
        """
        if head_branch is None:
            head_branch = "HEAD"

        output = self._run_git(
            "log",
            "--format=%H|%h|%an|%ae|%aI|%s|%b|||",
            f"{base_branch}..{head_branch}",
        )
        if not output:
            return []

        commits = []
        for block in output.split("|||"):
            block = block.strip()
            if not block or "|" not in block:
                continue

            parts = block.split("|")
            if len(parts) < 6:
                continue

            subject = parts[5]
            body = parts[6] if len(parts) > 6 else ""
            task_ids = self._extract_task_ids(subject + " " + body)

            commits.append(CommitInfo(
                hash=parts[0],
                short_hash=parts[1],
                author=parts[2],
                email=parts[3],
                date=parts[4],
                subject=subject,
                body=body,
                task_ids=tuple(task_ids),
            ))

        return commits

    def search_commits(
        self,
        query: str,
        limit: int = 10,
    ) -> list[CommitInfo]:
        """Search commits by message content.

        Args:
            query: Search query.
            limit: Maximum results.

        Returns:
            Matching commits.
        """
        output = self._run_git(
            "log",
            f"-{limit}",
            f"--grep={query}",
            "--format=%H|%h|%an|%ae|%aI|%s",
        )
        if not output:
            return []

        commits = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 6:
                continue

            commits.append(CommitInfo(
                hash=parts[0],
                short_hash=parts[1],
                author=parts[2],
                email=parts[3],
                date=parts[4],
                subject=parts[5],
            ))

        return commits

    def get_commits_for_task(self, task_id: str) -> list[CommitInfo]:
        """Get commits associated with a task ID.

        Args:
            task_id: Task identifier to search for.

        Returns:
            Commits mentioning the task.
        """
        return self.search_commits(task_id, limit=50)

    def get_file_history(
        self,
        file_path: str,
        limit: int = 10,
    ) -> list[CommitInfo]:
        """Get commit history for a file.

        Args:
            file_path: Path to file.
            limit: Maximum commits.

        Returns:
            Commits touching the file.
        """
        output = self._run_git(
            "log",
            f"-{limit}",
            "--format=%H|%h|%an|%ae|%aI|%s",
            "--",
            file_path,
        )
        if not output:
            return []

        commits = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 6:
                continue

            commits.append(CommitInfo(
                hash=parts[0],
                short_hash=parts[1],
                author=parts[2],
                email=parts[3],
                date=parts[4],
                subject=parts[5],
                files_changed=(file_path,),
            ))

        return commits

    def _extract_task_ids(self, text: str) -> list[str]:
        """Extract task IDs from text.

        Args:
            text: Text to search.

        Returns:
            Found task IDs.
        """
        task_ids = []
        for pattern in self.TASK_ID_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            task_ids.extend(matches)
        return list(set(task_ids))

    def get_current_branch(self) -> Optional[str]:
        """Get the current branch name.

        Returns:
            Branch name or None.
        """
        output = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        return output.strip() if output else None

    def get_changed_files(
        self,
        since_ref: str = "HEAD~10",
    ) -> list[str]:
        """Get files changed since a reference.

        Args:
            since_ref: Reference to compare from.

        Returns:
            List of changed file paths.
        """
        output = self._run_git(
            "diff",
            "--name-only",
            since_ref,
        )
        if not output:
            return []
        return [f for f in output.strip().split("\n") if f]


def inject_git_history(
    history: GitHistory,
    prompt: str,
    max_commits: int = 10,
    include_files: bool = True,
) -> str:
    """Inject git history context into a system prompt.

    Args:
        history: GitHistory instance.
        prompt: Base system prompt.
        max_commits: Maximum commits to include.
        include_files: Include changed files.

    Returns:
        Prompt with history injected.
    """
    commits = history.get_recent_commits(max_commits)
    if not commits:
        return prompt

    lines = ["\n\n## Recent Git History\n"]
    lines.append("Recent commits in this repository:\n")

    for commit in commits:
        # Format: [short_hash] subject (author, date)
        date_str = commit.date.split("T")[0] if "T" in commit.date else commit.date
        lines.append(f"- `{commit.short_hash}` {commit.subject}")

        if include_files and commit.files_changed:
            files = commit.files_changed[:5]
            if files:
                lines.append(f"  - Files: {', '.join(files)}")
                if len(commit.files_changed) > 5:
                    lines.append(f"  - ... and {len(commit.files_changed) - 5} more")

        if commit.task_ids:
            lines.append(f"  - Tasks: {', '.join(commit.task_ids)}")

    history_section = "\n".join(lines)
    return prompt + history_section
