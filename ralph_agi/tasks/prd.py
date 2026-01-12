"""PRD.json parser and dataclasses.

This module provides parsing and validation for PRD.json files,
which define project requirements and task definitions.

Design Principles:
- Strict validation (fail early with clear messages)
- Immutable dataclasses for parsed results
- Separate validation from I/O for testability
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)

# Valid category values
VALID_CATEGORIES = frozenset(
    ["functional", "ui", "performance", "security", "integration"]
)

# Valid priority range
PRIORITY_MIN = 0
PRIORITY_MAX = 4


class PRDError(Exception):
    """PRD parsing or validation error.

    Attributes:
        message: Human-readable error description.
        path: JSON path to the problematic field (e.g., "features[0].id").
        line: Line number for JSON syntax errors.
    """

    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        line: Optional[int] = None,
    ):
        self.message = message
        self.path = path
        self.line = line
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the full error message."""
        parts = [self.message]
        if self.path:
            parts.append(f"at {self.path}")
        if self.line:
            parts.append(f"(line {self.line})")
        return " ".join(parts)


@dataclass(frozen=True)
class Project:
    """Project metadata.

    Attributes:
        name: Project name (required).
        description: Project description (required).
        version: Optional version string.
    """

    name: str
    description: str
    version: Optional[str] = None


@dataclass(frozen=True)
class Feature:
    """A feature/task definition.

    Attributes:
        id: Unique identifier (required).
        description: Feature description (required).
        passes: Whether the feature is complete (required).
        category: Feature category (functional, ui, etc.).
        priority: Priority level 0-4 (0=P0 highest).
        steps: Implementation steps.
        acceptance_criteria: Verification criteria.
        dependencies: IDs of blocking features.
        completed_at: ISO datetime of completion.
    """

    id: str
    description: str
    passes: bool
    category: Optional[Literal["functional", "ui", "performance", "security", "integration"]] = None
    priority: Optional[int] = None
    steps: tuple[str, ...] = field(default_factory=tuple)
    acceptance_criteria: tuple[str, ...] = field(default_factory=tuple)
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    completed_at: Optional[str] = None

    @property
    def is_ready(self) -> bool:
        """Check if this feature is ready to work on.

        A feature is ready if it's not yet complete (passes=False).
        Note: Dependency checking requires full PRD context.
        """
        return not self.passes

    @property
    def priority_label(self) -> str:
        """Get priority as a label (P0, P1, etc.)."""
        if self.priority is None:
            return "P4"  # Default to lowest
        return f"P{self.priority}"


@dataclass(frozen=True)
class PRD:
    """Project Requirements Document.

    Container for project metadata and feature definitions.

    Attributes:
        project: Project metadata.
        features: Tuple of feature definitions.
    """

    project: Project
    features: tuple[Feature, ...]

    def get_feature(self, feature_id: str) -> Optional[Feature]:
        """Get a feature by ID.

        Args:
            feature_id: The feature ID to look up.

        Returns:
            The Feature if found, None otherwise.
        """
        for feature in self.features:
            if feature.id == feature_id:
                return feature
        return None

    def get_incomplete_features(self) -> tuple[Feature, ...]:
        """Get all features where passes=False."""
        return tuple(f for f in self.features if not f.passes)

    def get_complete_features(self) -> tuple[Feature, ...]:
        """Get all features where passes=True."""
        return tuple(f for f in self.features if f.passes)

    @property
    def is_complete(self) -> bool:
        """Check if all features are complete."""
        return all(f.passes for f in self.features)

    @property
    def completion_percentage(self) -> float:
        """Get completion percentage (0.0 to 100.0)."""
        if not self.features:
            return 100.0
        complete = sum(1 for f in self.features if f.passes)
        return (complete / len(self.features)) * 100


def load_prd(path: Path | str) -> PRD:
    """Load and validate PRD.json from file.

    Args:
        path: Path to the PRD.json file.

    Returns:
        Validated PRD object.

    Raises:
        PRDError: If file not found, invalid JSON, or validation fails.
    """
    path = Path(path)

    if not path.exists():
        raise PRDError(f"PRD file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except PermissionError as e:
        raise PRDError(f"Permission denied reading PRD file: {path}") from e
    except OSError as e:
        raise PRDError(f"Error reading PRD file: {e}") from e

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise PRDError(
            f"Invalid JSON: {e.msg}",
            line=e.lineno,
        ) from e

    return parse_prd(data)


def parse_prd(data: dict[str, Any]) -> PRD:
    """Parse and validate PRD from dict.

    Args:
        data: Dictionary from parsed JSON.

    Returns:
        Validated PRD object.

    Raises:
        PRDError: If validation fails.
    """
    if not isinstance(data, dict):
        raise PRDError("PRD must be a JSON object", path="(root)")

    # Validate project
    if "project" not in data:
        raise PRDError("Missing required field 'project'", path="project")
    project = _validate_project(data["project"])

    # Validate features
    if "features" not in data:
        raise PRDError("Missing required field 'features'", path="features")
    if not isinstance(data["features"], list):
        raise PRDError("'features' must be an array", path="features")

    features = []
    for i, feature_data in enumerate(data["features"]):
        feature = _validate_feature(feature_data, i)
        features.append(feature)

    return PRD(project=project, features=tuple(features))


def _validate_project(data: Any) -> Project:
    """Validate and parse project metadata.

    Args:
        data: Project data from JSON.

    Returns:
        Validated Project object.

    Raises:
        PRDError: If validation fails.
    """
    if not isinstance(data, dict):
        raise PRDError("'project' must be an object", path="project")

    # Required: name
    if "name" not in data:
        raise PRDError("Missing required field 'name'", path="project.name")
    if not isinstance(data["name"], str):
        raise PRDError(
            f"'name' must be a string, got {type(data['name']).__name__}",
            path="project.name",
        )
    if not data["name"].strip():
        raise PRDError("'name' cannot be empty", path="project.name")

    # Required: description
    if "description" not in data:
        raise PRDError("Missing required field 'description'", path="project.description")
    if not isinstance(data["description"], str):
        raise PRDError(
            f"'description' must be a string, got {type(data['description']).__name__}",
            path="project.description",
        )

    # Optional: version
    version = data.get("version")
    if version is not None and not isinstance(version, str):
        raise PRDError(
            f"'version' must be a string, got {type(version).__name__}",
            path="project.version",
        )

    return Project(
        name=data["name"],
        description=data["description"],
        version=version,
    )


def _validate_feature(data: Any, index: int) -> Feature:
    """Validate and parse a feature definition.

    Args:
        data: Feature data from JSON.
        index: Index in the features array (for error messages).

    Returns:
        Validated Feature object.

    Raises:
        PRDError: If validation fails.
    """
    path_prefix = f"features[{index}]"

    if not isinstance(data, dict):
        raise PRDError(f"Feature must be an object", path=path_prefix)

    # Required: id
    if "id" not in data:
        raise PRDError("Missing required field 'id'", path=f"{path_prefix}.id")
    if not isinstance(data["id"], str):
        raise PRDError(
            f"'id' must be a string, got {type(data['id']).__name__}",
            path=f"{path_prefix}.id",
        )
    if not data["id"].strip():
        raise PRDError("'id' cannot be empty", path=f"{path_prefix}.id")

    # Required: description
    if "description" not in data:
        raise PRDError("Missing required field 'description'", path=f"{path_prefix}.description")
    if not isinstance(data["description"], str):
        raise PRDError(
            f"'description' must be a string, got {type(data['description']).__name__}",
            path=f"{path_prefix}.description",
        )

    # Required: passes
    if "passes" not in data:
        raise PRDError("Missing required field 'passes'", path=f"{path_prefix}.passes")
    if not isinstance(data["passes"], bool):
        raise PRDError(
            f"'passes' must be a boolean, got {type(data['passes']).__name__}",
            path=f"{path_prefix}.passes",
        )

    # Optional: category
    category = data.get("category")
    if category is not None:
        if not isinstance(category, str):
            raise PRDError(
                f"'category' must be a string, got {type(category).__name__}",
                path=f"{path_prefix}.category",
            )
        if category not in VALID_CATEGORIES:
            raise PRDError(
                f"Invalid category '{category}'. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}",
                path=f"{path_prefix}.category",
            )

    # Optional: priority
    priority = data.get("priority")
    if priority is not None:
        if not isinstance(priority, int):
            raise PRDError(
                f"'priority' must be an integer, got {type(priority).__name__}",
                path=f"{path_prefix}.priority",
            )
        if not (PRIORITY_MIN <= priority <= PRIORITY_MAX):
            raise PRDError(
                f"'priority' must be between {PRIORITY_MIN} and {PRIORITY_MAX}, got {priority}",
                path=f"{path_prefix}.priority",
            )

    # Optional: steps (array of strings)
    steps = _validate_string_array(data.get("steps"), f"{path_prefix}.steps", "steps")

    # Optional: acceptance_criteria (array of strings)
    acceptance_criteria = _validate_string_array(
        data.get("acceptance_criteria"),
        f"{path_prefix}.acceptance_criteria",
        "acceptance_criteria",
    )

    # Optional: dependencies (array of strings)
    dependencies = _validate_string_array(
        data.get("dependencies"),
        f"{path_prefix}.dependencies",
        "dependencies",
    )

    # Optional: completed_at
    completed_at = data.get("completed_at")
    if completed_at is not None and not isinstance(completed_at, str):
        raise PRDError(
            f"'completed_at' must be a string, got {type(completed_at).__name__}",
            path=f"{path_prefix}.completed_at",
        )

    return Feature(
        id=data["id"],
        description=data["description"],
        passes=data["passes"],
        category=category,
        priority=priority,
        steps=tuple(steps),
        acceptance_criteria=tuple(acceptance_criteria),
        dependencies=tuple(dependencies),
        completed_at=completed_at,
    )


def _validate_string_array(
    data: Any,
    path: str,
    field_name: str,
) -> list[str]:
    """Validate an optional array of strings.

    Args:
        data: The data to validate (may be None).
        path: JSON path for error messages.
        field_name: Field name for error messages.

    Returns:
        List of strings (empty if data is None).

    Raises:
        PRDError: If validation fails.
    """
    if data is None:
        return []

    if not isinstance(data, list):
        raise PRDError(
            f"'{field_name}' must be an array, got {type(data).__name__}",
            path=path,
        )

    result = []
    for i, item in enumerate(data):
        if not isinstance(item, str):
            raise PRDError(
                f"'{field_name}[{i}]' must be a string, got {type(item).__name__}",
                path=f"{path}[{i}]",
            )
        result.append(item)

    return result
