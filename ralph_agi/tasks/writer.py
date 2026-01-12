"""PRD.json writer for task completion marking.

This module provides functions for safely updating PRD.json files
with task completion status.

Design Principles:
- Atomic writes (no partial updates)
- Field protection (only passes/completed_at can change)
- Clear error messages
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ralph_agi.tasks.prd import Feature, PRD, PRDError, Project, load_prd

logger = logging.getLogger(__name__)


def mark_complete(prd_path: Path | str, feature_id: str) -> PRD:
    """Mark a feature as complete in the PRD.json file.

    Updates the feature's `passes` field to `True` and sets `completed_at`
    to the current UTC timestamp.

    Args:
        prd_path: Path to the PRD.json file.
        feature_id: ID of the feature to mark as complete.

    Returns:
        The updated PRD object.

    Raises:
        PRDError: If the feature is not found, already complete,
                  or the write fails.
    """
    prd_path = Path(prd_path)

    # Load current PRD
    prd = load_prd(prd_path)

    # Find feature
    feature = prd.get_feature(feature_id)
    if feature is None:
        raise PRDError(f"Feature not found: {feature_id}")
    if feature.passes:
        raise PRDError(f"Feature already complete: {feature_id}")

    # Create updated feature
    now = datetime.now(timezone.utc).isoformat()
    updated_feature = Feature(
        id=feature.id,
        description=feature.description,
        passes=True,
        category=feature.category,
        priority=feature.priority,
        steps=feature.steps,
        acceptance_criteria=feature.acceptance_criteria,
        dependencies=feature.dependencies,
        completed_at=now,
    )

    # Create new PRD with updated feature
    new_features = tuple(
        updated_feature if f.id == feature_id else f
        for f in prd.features
    )
    new_prd = PRD(project=prd.project, features=new_features)

    # Write atomically
    write_prd(prd_path, new_prd)

    logger.info(f"Marked feature '{feature_id}' as complete")
    return new_prd


def write_prd(prd_path: Path | str, prd: PRD) -> None:
    """Write a PRD to a JSON file atomically.

    Uses atomic write pattern: write to temp file, then rename.
    This ensures no partial writes on failure.

    Args:
        prd_path: Path to the PRD.json file.
        prd: The PRD object to write.

    Raises:
        PRDError: If the write fails.
    """
    prd_path = Path(prd_path)
    dir_path = prd_path.parent

    # Ensure directory exists
    dir_path.mkdir(parents=True, exist_ok=True)

    # Convert to dict
    data = prd_to_dict(prd)

    tmp_path = None
    try:
        # Write to temp file in same directory (for atomic rename)
        fd, tmp_path = tempfile.mkstemp(
            suffix=".json.tmp",
            dir=dir_path,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")  # Trailing newline
        except Exception:
            os.close(fd)
            raise

        # Atomic rename
        os.replace(tmp_path, prd_path)
        tmp_path = None  # Success, don't delete in finally

        logger.debug(f"Wrote PRD to {prd_path}")

    except OSError as e:
        raise PRDError(f"Failed to write PRD file: {e}") from e
    finally:
        # Clean up temp file on failure
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass  # Best effort cleanup


def prd_to_dict(prd: PRD) -> dict[str, Any]:
    """Convert a PRD object to a JSON-serializable dict.

    Args:
        prd: The PRD object.

    Returns:
        Dictionary representation matching PRD.json schema.
    """
    return {
        "project": project_to_dict(prd.project),
        "features": [feature_to_dict(f) for f in prd.features],
    }


def project_to_dict(project: Project) -> dict[str, Any]:
    """Convert a Project object to a dict."""
    result: dict[str, Any] = {
        "name": project.name,
        "description": project.description,
    }
    if project.version is not None:
        result["version"] = project.version
    return result


def feature_to_dict(feature: Feature) -> dict[str, Any]:
    """Convert a Feature object to a dict."""
    result: dict[str, Any] = {
        "id": feature.id,
        "description": feature.description,
        "passes": feature.passes,
    }

    # Add optional fields only if set
    if feature.category is not None:
        result["category"] = feature.category
    if feature.priority is not None:
        result["priority"] = feature.priority
    if feature.steps:
        result["steps"] = list(feature.steps)
    if feature.acceptance_criteria:
        result["acceptance_criteria"] = list(feature.acceptance_criteria)
    if feature.dependencies:
        result["dependencies"] = list(feature.dependencies)
    if feature.completed_at is not None:
        result["completed_at"] = feature.completed_at

    return result


def validate_prd_changes(old_prd: PRD, new_prd: PRD, feature_id: str) -> None:
    """Validate that only allowed changes were made to the PRD.

    Only the specified feature's `passes` and `completed_at` fields
    may be changed.

    Args:
        old_prd: The original PRD.
        new_prd: The updated PRD.
        feature_id: The feature ID that was being updated.

    Raises:
        PRDError: If any disallowed changes were detected.
    """
    # Check project unchanged
    if old_prd.project != new_prd.project:
        raise PRDError("Project metadata was unexpectedly modified")

    # Check same number of features
    if len(old_prd.features) != len(new_prd.features):
        raise PRDError("Number of features changed unexpectedly")

    # Check each feature
    for old_f, new_f in zip(old_prd.features, new_prd.features):
        if old_f.id != new_f.id:
            raise PRDError(f"Feature order changed: expected {old_f.id}, got {new_f.id}")

        if old_f.id == feature_id:
            # This feature can have passes and completed_at changed
            _validate_allowed_feature_changes(old_f, new_f)
        else:
            # Other features must be unchanged
            if old_f != new_f:
                raise PRDError(f"Unexpected changes to feature {old_f.id}")


def _validate_allowed_feature_changes(old_f: Feature, new_f: Feature) -> None:
    """Validate that only passes and completed_at changed."""
    # Check fields that should NOT change
    if old_f.id != new_f.id:
        raise PRDError(f"Feature ID changed from {old_f.id} to {new_f.id}")
    if old_f.description != new_f.description:
        raise PRDError(f"Feature {old_f.id} description was modified")
    if old_f.category != new_f.category:
        raise PRDError(f"Feature {old_f.id} category was modified")
    if old_f.priority != new_f.priority:
        raise PRDError(f"Feature {old_f.id} priority was modified")
    if old_f.steps != new_f.steps:
        raise PRDError(f"Feature {old_f.id} steps were modified")
    if old_f.acceptance_criteria != new_f.acceptance_criteria:
        raise PRDError(f"Feature {old_f.id} acceptance_criteria were modified")
    if old_f.dependencies != new_f.dependencies:
        raise PRDError(f"Feature {old_f.id} dependencies were modified")
