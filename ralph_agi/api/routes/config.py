"""Config API routes.

Provides endpoints for retrieving repository context and managing runtime settings.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ralph_agi.api.dependencies import get_project_root
from ralph_agi.api.schemas import (
    ConfigResponse,
    ConfigUpdate,
    RepoContext,
    RuntimeSettings,
    TaskPriority,
)

router = APIRouter(prefix="/config", tags=["config"])

# Runtime settings storage (in-memory for now)
_runtime_settings = RuntimeSettings()


def _get_git_info(project_root: Path) -> RepoContext:
    """Auto-detect repository information from .git directory.

    Args:
        project_root: Path to the project root.

    Returns:
        RepoContext with detected information.
    """
    git_dir = project_root / ".git"

    # Get repo name (directory name)
    repo_name = project_root.name

    # Get current branch
    current_branch = "main"
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            current_branch = result.stdout.strip()
    except Exception:
        pass

    # Get remote origin URL
    origin_url = None
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            origin_url = result.stdout.strip()
    except Exception:
        pass

    return RepoContext(
        name=repo_name,
        origin_url=origin_url,
        current_branch=current_branch,
        project_root=str(project_root),
    )


@router.get("", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """Get repository context and runtime settings.

    Returns:
        ConfigResponse with repo context and current settings.
    """
    project_root = get_project_root()
    repo_context = _get_git_info(project_root)

    return ConfigResponse(
        repo=repo_context,
        settings=_runtime_settings,
    )


@router.patch("", response_model=ConfigResponse)
async def update_config(config: ConfigUpdate) -> ConfigResponse:
    """Update runtime settings.

    Args:
        config: Fields to update.

    Returns:
        Updated ConfigResponse.
    """
    global _runtime_settings

    # Update provided fields
    if config.auto_merge_threshold is not None:
        _runtime_settings.auto_merge_threshold = config.auto_merge_threshold
    if config.default_priority is not None:
        _runtime_settings.default_priority = config.default_priority
    if config.require_approval is not None:
        _runtime_settings.require_approval = config.require_approval

    # Return updated config
    project_root = get_project_root()
    repo_context = _get_git_info(project_root)

    return ConfigResponse(
        repo=repo_context,
        settings=_runtime_settings,
    )


def get_runtime_settings() -> RuntimeSettings:
    """Get the current runtime settings.

    Returns:
        Current RuntimeSettings instance.
    """
    return _runtime_settings
