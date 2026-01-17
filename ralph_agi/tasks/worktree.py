"""Git Worktree Manager for RALPH-AGI.

Provides isolated git worktrees for parallel task execution. Each task
runs in its own worktree, preventing conflicts and enabling concurrent
processing of multiple tasks.

Usage:
    from ralph_agi.tasks.worktree import WorktreeManager

    # Initialize manager
    manager = WorktreeManager(repo_path="/path/to/repo")

    # Create worktree for a task
    worktree_path = manager.create("dark-mode-toggle")

    # Execute callback in worktree
    def do_work(path):
        # ... implement task in isolated directory
        return result

    result = manager.execute_in_worktree("dark-mode-toggle", do_work)

    # Cleanup after merge
    manager.cleanup("dark-mode-toggle")

    # List active worktrees
    for info in manager.list_active():
        print(f"{info.task_id}: {info.path}")
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

from ralph_agi.tools.git import GitCommandError, GitTools, WorktreeInfo

logger = logging.getLogger(__name__)

T = TypeVar("T")


class WorktreeError(Exception):
    """Base exception for worktree operations."""

    pass


class WorktreeExistsError(WorktreeError):
    """Raised when worktree already exists."""

    def __init__(self, task_id: str, path: str):
        self.task_id = task_id
        self.path = path
        super().__init__(f"Worktree already exists for task {task_id}: {path}")


class WorktreeNotFoundError(WorktreeError):
    """Raised when worktree is not found."""

    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f"Worktree not found for task: {task_id}")


@dataclass
class ActiveWorktree:
    """Information about an active worktree.

    Attributes:
        task_id: Task this worktree is for
        path: Absolute path to worktree directory
        branch: Git branch name
        commit: Current commit hash
        created_at: When the worktree was created
        status: Current status (created, running, ready_to_merge, error)
    """

    task_id: str
    path: str
    branch: str
    commit: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "created"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "path": self.path,
            "branch": self.branch,
            "commit": self.commit,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActiveWorktree":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif created_at is None:
            created_at = datetime.now(timezone.utc)

        return cls(
            task_id=data["task_id"],
            path=data["path"],
            branch=data["branch"],
            commit=data.get("commit", ""),
            created_at=created_at,
            status=data.get("status", "created"),
        )


class WorktreeManager:
    """Manages git worktrees for parallel task execution.

    Each task gets its own isolated worktree with a dedicated branch.
    This enables parallel execution without merge conflicts, as each
    task works on its own copy of the codebase.

    Worktree layout:
        repo/                     # Main repository
        ../ralph-worktrees/       # Worktree parent directory
            task-id-1/            # Worktree for task 1
            task-id-2/            # Worktree for task 2

    State tracking:
        .ralph/worktrees.json     # Active worktree state

    Example:
        manager = WorktreeManager("/path/to/repo")

        # Create worktree for task
        path = manager.create("add-feature")
        # path = /path/to/ralph-worktrees/add-feature

        # Do work in worktree
        result = manager.execute_in_worktree("add-feature", my_callback)

        # After merge, cleanup
        manager.cleanup("add-feature")
    """

    STATE_FILE = ".ralph/worktrees.json"
    DEFAULT_WORKTREE_DIR = "../ralph-worktrees"
    BRANCH_PREFIX = "ralph/"

    def __init__(
        self,
        repo_path: str | Path | None = None,
        worktree_dir: str | Path | None = None,
        git: GitTools | None = None,
    ):
        """Initialize worktree manager.

        Args:
            repo_path: Path to main git repository (default: current dir)
            worktree_dir: Directory for worktrees (default: ../ralph-worktrees)
            git: GitTools instance to use (created if None)
        """
        self._repo_path = Path(repo_path).resolve() if repo_path else Path.cwd()
        self._git = git or GitTools(repo_path=self._repo_path)

        # Resolve worktree directory
        if worktree_dir:
            self._worktree_dir = Path(worktree_dir).resolve()
        else:
            self._worktree_dir = (self._repo_path / self.DEFAULT_WORKTREE_DIR).resolve()

        # State file path
        self._state_file = self._repo_path / self.STATE_FILE

        # Ensure state directory exists
        self._state_file.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(f"WorktreeManager initialized: repo={self._repo_path}, worktrees={self._worktree_dir}")

    @property
    def repo_path(self) -> Path:
        """Get main repository path."""
        return self._repo_path

    @property
    def worktree_dir(self) -> Path:
        """Get worktree parent directory."""
        return self._worktree_dir

    def _branch_name(self, task_id: str) -> str:
        """Get branch name for a task."""
        return f"{self.BRANCH_PREFIX}{task_id}"

    def _worktree_path(self, task_id: str) -> Path:
        """Get worktree path for a task."""
        return self._worktree_dir / task_id

    def _load_state(self) -> dict[str, ActiveWorktree]:
        """Load active worktree state from file."""
        if not self._state_file.exists():
            return {}

        try:
            with open(self._state_file) as f:
                data = json.load(f)

            return {
                k: ActiveWorktree.from_dict(v)
                for k, v in data.get("worktrees", {}).items()
            }
        except Exception as e:
            logger.warning(f"Failed to load worktree state: {e}")
            return {}

    def _save_state(self, worktrees: dict[str, ActiveWorktree]) -> None:
        """Save active worktree state to file."""
        data = {
            "worktrees": {k: v.to_dict() for k, v in worktrees.items()},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Write atomically
        temp_path = self._state_file.with_suffix(".json.tmp")
        try:
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self._state_file)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise WorktreeError(f"Failed to save state: {e}") from e

    def create(
        self,
        task_id: str,
        base_ref: str = "HEAD",
    ) -> Path:
        """Create a new worktree for a task.

        Creates an isolated worktree with a dedicated branch for the task.
        The worktree is ready for independent development work.

        Args:
            task_id: Unique task identifier
            base_ref: Git reference to base the branch on (default: HEAD)

        Returns:
            Absolute path to the created worktree

        Raises:
            WorktreeExistsError: If worktree already exists for this task
            WorktreeError: If worktree creation fails
        """
        branch = self._branch_name(task_id)
        worktree_path = self._worktree_path(task_id)

        # Check if already exists
        state = self._load_state()
        if task_id in state:
            raise WorktreeExistsError(task_id, str(state[task_id].path))

        # Ensure worktree directory parent exists
        self._worktree_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Create worktree with new branch
            result_path = self._git.worktree_add(
                path=str(worktree_path),
                branch=branch,
                create_branch=True,
                base_ref=base_ref,
            )

            # Get current commit
            worktree_git = GitTools(repo_path=worktree_path)
            commit = worktree_git._run_git("rev-parse", "HEAD").strip()

            # Record in state
            active = ActiveWorktree(
                task_id=task_id,
                path=result_path,
                branch=branch,
                commit=commit,
                status="created",
            )

            state[task_id] = active
            self._save_state(state)

            logger.info(f"WORKTREE_CREATE: {task_id} -> {result_path}")
            return Path(result_path)

        except GitCommandError as e:
            raise WorktreeError(f"Failed to create worktree for {task_id}: {e}") from e

    def get(self, task_id: str) -> ActiveWorktree:
        """Get worktree info for a task.

        Args:
            task_id: Task identifier

        Returns:
            ActiveWorktree info

        Raises:
            WorktreeNotFoundError: If worktree doesn't exist
        """
        state = self._load_state()

        if task_id not in state:
            raise WorktreeNotFoundError(task_id)

        return state[task_id]

    def list_active(self) -> list[ActiveWorktree]:
        """List all active worktrees.

        Returns:
            List of ActiveWorktree info, sorted by creation time
        """
        state = self._load_state()
        worktrees = list(state.values())
        worktrees.sort(key=lambda w: w.created_at)
        return worktrees

    def update_status(self, task_id: str, status: str) -> ActiveWorktree:
        """Update worktree status.

        Args:
            task_id: Task identifier
            status: New status (created, running, ready_to_merge, error)

        Returns:
            Updated ActiveWorktree

        Raises:
            WorktreeNotFoundError: If worktree doesn't exist
        """
        state = self._load_state()

        if task_id not in state:
            raise WorktreeNotFoundError(task_id)

        state[task_id].status = status
        self._save_state(state)

        logger.info(f"WORKTREE_STATUS: {task_id} -> {status}")
        return state[task_id]

    def execute_in_worktree(
        self,
        task_id: str,
        callback: Callable[[Path], T],
    ) -> T:
        """Execute a callback in the context of a worktree.

        Changes the current directory to the worktree, executes the
        callback, and restores the original directory afterward.

        Args:
            task_id: Task identifier
            callback: Function to execute, receives worktree path

        Returns:
            Result of the callback

        Raises:
            WorktreeNotFoundError: If worktree doesn't exist
            WorktreeError: If execution fails
        """
        worktree = self.get(task_id)
        worktree_path = Path(worktree.path)

        if not worktree_path.exists():
            raise WorktreeError(f"Worktree directory missing: {worktree_path}")

        # Update status
        self.update_status(task_id, "running")

        original_cwd = Path.cwd()
        try:
            os.chdir(worktree_path)
            logger.debug(f"Executing in worktree: {worktree_path}")

            result = callback(worktree_path)

            return result

        except Exception as e:
            self.update_status(task_id, "error")
            raise WorktreeError(f"Execution failed in worktree {task_id}: {e}") from e

        finally:
            os.chdir(original_cwd)

    def cleanup(self, task_id: str, force: bool = False) -> bool:
        """Remove a worktree after task completion.

        Removes the worktree directory and associated branch. Should be
        called after the branch has been merged.

        Args:
            task_id: Task identifier
            force: Force removal even if worktree has uncommitted changes

        Returns:
            True if cleanup succeeded

        Raises:
            WorktreeNotFoundError: If worktree doesn't exist
            WorktreeError: If cleanup fails
        """
        state = self._load_state()

        if task_id not in state:
            raise WorktreeNotFoundError(task_id)

        worktree = state[task_id]
        worktree_path = Path(worktree.path)

        try:
            # Remove worktree via git
            if worktree_path.exists():
                self._git.worktree_remove(str(worktree_path), force=force)

            # Optionally delete the branch
            branch = worktree.branch
            try:
                self._git.delete_branch(branch, force=True)
            except GitCommandError:
                # Branch might already be deleted or merged
                pass

            # Remove from state
            del state[task_id]
            self._save_state(state)

            logger.info(f"WORKTREE_CLEANUP: {task_id}")
            return True

        except GitCommandError as e:
            raise WorktreeError(f"Failed to cleanup worktree {task_id}: {e}") from e

    def cleanup_all(self, force: bool = False) -> int:
        """Remove all worktrees.

        Use with caution - this removes all active worktrees.

        Args:
            force: Force removal even if worktrees have uncommitted changes

        Returns:
            Number of worktrees removed
        """
        state = self._load_state()
        removed = 0

        for task_id in list(state.keys()):
            try:
                self.cleanup(task_id, force=force)
                removed += 1
            except WorktreeError as e:
                logger.warning(f"Failed to cleanup {task_id}: {e}")

        # Prune any stale worktree metadata
        self._git.worktree_prune()

        logger.info(f"WORKTREE_CLEANUP_ALL: Removed {removed} worktrees")
        return removed

    def prune(self) -> list[str]:
        """Clean up stale worktree metadata.

        Removes metadata for worktrees whose directories no longer exist.

        Returns:
            List of pruned task IDs
        """
        state = self._load_state()
        pruned = []

        for task_id, worktree in list(state.items()):
            if not Path(worktree.path).exists():
                del state[task_id]
                pruned.append(task_id)
                logger.info(f"WORKTREE_PRUNE: {task_id} (directory missing)")

        if pruned:
            self._save_state(state)

        # Also prune git's worktree metadata
        self._git.worktree_prune()

        return pruned

    def sync_with_git(self) -> dict[str, str]:
        """Synchronize state with actual git worktrees.

        Reconciles our state file with git's worktree list. Adds any
        worktrees that exist but aren't tracked, removes any that are
        tracked but don't exist.

        Returns:
            Dict of changes: {task_id: "added" | "removed"}
        """
        state = self._load_state()
        changes = {}

        # Get actual git worktrees
        git_worktrees = self._git.worktree_list()
        git_paths = {w.path: w for w in git_worktrees}

        # Remove tracked worktrees that don't exist
        for task_id, worktree in list(state.items()):
            if worktree.path not in git_paths:
                del state[task_id]
                changes[task_id] = "removed"

        # Add git worktrees that match our branch prefix but aren't tracked
        for path, git_info in git_paths.items():
            if git_info.is_main:
                continue  # Skip main worktree

            branch = git_info.branch
            if not branch.startswith(self.BRANCH_PREFIX):
                continue  # Not a ralph worktree

            task_id = branch[len(self.BRANCH_PREFIX):]
            if task_id not in state:
                state[task_id] = ActiveWorktree(
                    task_id=task_id,
                    path=path,
                    branch=branch,
                    commit=git_info.commit,
                    status="unknown",
                )
                changes[task_id] = "added"

        if changes:
            self._save_state(state)
            logger.info(f"WORKTREE_SYNC: {len(changes)} changes")

        return changes

    def stats(self) -> dict[str, Any]:
        """Get worktree statistics.

        Returns:
            Dict with counts and status breakdown
        """
        state = self._load_state()

        status_counts: dict[str, int] = {}
        for worktree in state.values():
            status_counts[worktree.status] = status_counts.get(worktree.status, 0) + 1

        return {
            "total": len(state),
            "by_status": status_counts,
            "worktree_dir": str(self._worktree_dir),
        }
