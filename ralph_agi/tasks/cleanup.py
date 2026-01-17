"""Worktree cleanup automation for RALPH-AGI.

This module provides automated cleanup of git worktrees created
for task isolation, including orphan detection and fallback strategies.

Design Principles:
- Graceful degradation with fallback cleanup methods
- Configurable behavior for different scenarios
- Non-destructive by default (preserves on failure for debugging)
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ralph_agi.tools.git import GitTools, WorktreeInfo

logger = logging.getLogger(__name__)

# Default prefix for ralph worktrees
WORKTREE_PREFIX = "ralph-"


@dataclass
class CleanupConfig:
    """Configuration for worktree cleanup behavior.

    Attributes:
        cleanup_on_success: If True, cleanup worktree after successful merge.
        cleanup_on_failure: If True, cleanup worktree after task failure.
        force_cleanup: If True, force remove even if worktree has uncommitted changes.
        prune_orphans: If True, auto-detect and clean orphan worktrees.
        worktree_prefix: Prefix used for ralph worktree directories.
    """

    cleanup_on_success: bool = True
    cleanup_on_failure: bool = False
    force_cleanup: bool = False
    prune_orphans: bool = True
    worktree_prefix: str = WORKTREE_PREFIX


@dataclass
class CleanupResult:
    """Result of a cleanup operation.

    Attributes:
        success: Whether the cleanup succeeded.
        worktree_path: Path to the worktree that was cleaned up.
        method: Method used for cleanup (git_remove, force_remove, already_gone).
        branch_deleted: Whether the associated branch was deleted.
        error: Error message if cleanup failed.
    """

    success: bool
    worktree_path: Path
    method: str  # "git_remove", "force_remove", "already_gone", "skipped"
    branch_deleted: bool = False
    error: Optional[str] = None


@dataclass
class OrphanWorktree:
    """Information about an orphan worktree.

    Attributes:
        path: Path to the orphan worktree directory.
        has_git_dir: Whether the directory contains a .git file/directory.
        branch_hint: Possible branch name from .git file if readable.
    """

    path: Path
    has_git_dir: bool = False
    branch_hint: Optional[str] = None


class WorktreeCleanup:
    """Manages worktree cleanup automation.

    Provides comprehensive cleanup functionality including:
    - Git worktree removal with proper cleanup
    - Fallback to force removal when git cleanup fails
    - Orphan worktree detection and cleanup
    - Batch cleanup operations

    Example:
        >>> from ralph_agi.tools.git import GitTools
        >>> git = GitTools(repo_path=Path("."))
        >>> cleanup = WorktreeCleanup(git)
        >>> result = cleanup.cleanup_worktree(Path("../ralph-feature-123"))
        >>> if result.success:
        ...     print(f"Cleaned up via {result.method}")
    """

    def __init__(
        self,
        git_tools: GitTools,
        config: Optional[CleanupConfig] = None,
    ):
        """Initialize the cleanup manager.

        Args:
            git_tools: GitTools instance for git operations.
            config: Cleanup configuration. Uses defaults if not provided.
        """
        self._git = git_tools
        self._config = config or CleanupConfig()

    @property
    def config(self) -> CleanupConfig:
        """Get the cleanup configuration."""
        return self._config

    def cleanup_worktree(
        self,
        worktree_path: Path,
        force: bool = False,
        delete_branch: bool = True,
    ) -> CleanupResult:
        """Clean up a worktree with fallback to force removal.

        Attempts cleanup in order:
        1. git worktree remove (clean method)
        2. git worktree remove --force (if force=True or config.force_cleanup)
        3. rm -rf (fallback for stubborn cases)

        Args:
            worktree_path: Path to the worktree to clean up.
            force: Override config to force cleanup.
            delete_branch: If True, also delete the associated branch.

        Returns:
            CleanupResult with success status and method used.
        """
        worktree_path = Path(worktree_path).resolve()

        # Check if already gone
        if not worktree_path.exists():
            logger.debug(f"Worktree already gone: {worktree_path}")
            return CleanupResult(
                success=True,
                worktree_path=worktree_path,
                method="already_gone",
            )

        # Get branch info before removal
        branch_name = self._get_worktree_branch(worktree_path)
        use_force = force or self._config.force_cleanup

        # Try git worktree remove first
        try:
            self._git.worktree_remove(str(worktree_path), force=use_force)
            logger.info(f"Removed worktree via git: {worktree_path}")

            # Try to delete branch
            branch_deleted = False
            if delete_branch and branch_name:
                branch_deleted = self._try_delete_branch(branch_name)

            return CleanupResult(
                success=True,
                worktree_path=worktree_path,
                method="git_remove",
                branch_deleted=branch_deleted,
            )

        except Exception as git_error:
            logger.warning(f"Git worktree remove failed: {git_error}")

            # Fallback to force removal
            return self._force_remove_worktree(
                worktree_path,
                branch_name,
                delete_branch,
                str(git_error),
            )

    def _force_remove_worktree(
        self,
        worktree_path: Path,
        branch_name: Optional[str],
        delete_branch: bool,
        original_error: str,
    ) -> CleanupResult:
        """Force remove a worktree using shutil.rmtree.

        Args:
            worktree_path: Path to worktree to remove.
            branch_name: Branch name for cleanup.
            delete_branch: Whether to delete the branch.
            original_error: Error message from git removal attempt.

        Returns:
            CleanupResult with outcome.
        """
        try:
            # Remove the directory tree
            shutil.rmtree(worktree_path)
            logger.info(f"Force removed worktree: {worktree_path}")

            # Prune git worktree metadata
            try:
                self._git.worktree_prune()
            except Exception as prune_error:
                logger.debug(f"Prune after force remove: {prune_error}")

            # Try to delete branch
            branch_deleted = False
            if delete_branch and branch_name:
                branch_deleted = self._try_delete_branch(branch_name)

            return CleanupResult(
                success=True,
                worktree_path=worktree_path,
                method="force_remove",
                branch_deleted=branch_deleted,
            )

        except Exception as e:
            logger.error(f"Force remove failed for {worktree_path}: {e}")
            return CleanupResult(
                success=False,
                worktree_path=worktree_path,
                method="force_remove",
                error=f"Git: {original_error}; Force: {e}",
            )

    def _get_worktree_branch(self, worktree_path: Path) -> Optional[str]:
        """Get the branch name for a worktree.

        Args:
            worktree_path: Path to the worktree.

        Returns:
            Branch name or None if not found.
        """
        try:
            worktrees = self._git.worktree_list()
            for wt in worktrees:
                if Path(wt.path).resolve() == worktree_path.resolve():
                    return wt.branch if not wt.is_detached else None
            return None
        except Exception:
            return None

    def _try_delete_branch(self, branch_name: str) -> bool:
        """Try to delete a branch, ignoring errors.

        Args:
            branch_name: Name of branch to delete.

        Returns:
            True if branch was deleted, False otherwise.
        """
        try:
            # Don't delete main/master branches
            if branch_name in ("main", "master", "develop"):
                return False

            self._git.delete_branch(branch_name, force=True)
            logger.info(f"Deleted branch: {branch_name}")
            return True
        except Exception as e:
            logger.debug(f"Could not delete branch {branch_name}: {e}")
            return False

    def find_orphan_worktrees(
        self,
        base_path: Optional[Path] = None,
    ) -> list[OrphanWorktree]:
        """Find worktrees that exist on disk but aren't tracked by git.

        Orphan worktrees can occur when:
        - Git worktree remove failed but directory remains
        - Process crashed during worktree creation/removal
        - Manual directory operations

        Args:
            base_path: Directory to search for orphan worktrees.
                      Defaults to parent of repository.

        Returns:
            List of OrphanWorktree objects found.
        """
        if base_path is None:
            base_path = Path(self._git.repo_path).parent

        base_path = Path(base_path).resolve()

        # Get known worktrees from git
        try:
            known_worktrees = {
                Path(wt.path).resolve() for wt in self._git.worktree_list()
            }
        except Exception:
            known_worktrees = set()

        orphans = []
        prefix = self._config.worktree_prefix

        # Scan for directories matching the worktree prefix
        if not base_path.exists():
            return orphans

        for item in base_path.iterdir():
            if not item.is_dir():
                continue

            if not item.name.startswith(prefix):
                continue

            resolved = item.resolve()

            # Check if this is a known worktree
            if resolved in known_worktrees:
                continue

            # This is an orphan - gather info
            git_path = item / ".git"
            has_git = git_path.exists()
            branch_hint = None

            if has_git and git_path.is_file():
                # .git file points to actual git dir
                try:
                    content = git_path.read_text().strip()
                    # Extract branch hint from gitdir path
                    if "worktrees/" in content:
                        parts = content.split("worktrees/")
                        if len(parts) > 1:
                            branch_hint = parts[1].split("/")[0]
                except Exception:
                    pass

            orphans.append(
                OrphanWorktree(
                    path=item,
                    has_git_dir=has_git,
                    branch_hint=branch_hint,
                )
            )

        return orphans

    def cleanup_orphans(
        self,
        base_path: Optional[Path] = None,
    ) -> list[CleanupResult]:
        """Clean up all orphan worktrees.

        Args:
            base_path: Directory to search for orphans.

        Returns:
            List of CleanupResult for each orphan processed.
        """
        orphans = self.find_orphan_worktrees(base_path)
        results = []

        for orphan in orphans:
            logger.info(f"Cleaning up orphan worktree: {orphan.path}")
            result = self._force_remove_worktree(
                orphan.path,
                orphan.branch_hint,
                delete_branch=True,
                original_error="orphan worktree",
            )
            results.append(result)

        # Prune git worktree metadata
        if results:
            try:
                self._git.worktree_prune()
            except Exception as e:
                logger.debug(f"Prune after orphan cleanup: {e}")

        return results

    def cleanup_all_ralph_worktrees(
        self,
        include_active: bool = False,
        base_path: Optional[Path] = None,
    ) -> list[CleanupResult]:
        """Clean up all ralph worktrees.

        Useful for resetting to a clean state.

        Args:
            include_active: If True, remove worktrees currently tracked by git.
                           If False, only remove orphans.
            base_path: Directory to search for worktrees.

        Returns:
            List of CleanupResult for each worktree processed.
        """
        if base_path is None:
            base_path = Path(self._git.repo_path).parent

        results = []
        prefix = self._config.worktree_prefix

        # First, handle tracked worktrees if requested
        if include_active:
            try:
                worktrees = self._git.worktree_list()
                for wt in worktrees:
                    if wt.is_main:
                        continue  # Never remove main worktree

                    wt_path = Path(wt.path)
                    if wt_path.name.startswith(prefix):
                        result = self.cleanup_worktree(wt_path)
                        results.append(result)
            except Exception as e:
                logger.warning(f"Error listing worktrees: {e}")

        # Then handle orphans
        orphan_results = self.cleanup_orphans(base_path)
        results.extend(orphan_results)

        return results

    def should_cleanup_on_success(self) -> bool:
        """Check if cleanup should happen after successful completion."""
        return self._config.cleanup_on_success

    def should_cleanup_on_failure(self) -> bool:
        """Check if cleanup should happen after task failure."""
        return self._config.cleanup_on_failure


def create_cleanup_manager(
    repo_path: Path,
    config: Optional[CleanupConfig] = None,
) -> WorktreeCleanup:
    """Create a WorktreeCleanup instance.

    Convenience function that creates the required GitTools instance.

    Args:
        repo_path: Path to the git repository.
        config: Cleanup configuration.

    Returns:
        Configured WorktreeCleanup instance.
    """
    from ralph_agi.tools.git import GitTools

    git = GitTools(repo_path=repo_path)
    return WorktreeCleanup(git, config)
