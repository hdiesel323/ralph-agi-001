"""Codebase patterns layer for contextual learning.

Layer 1 of the Contextual Learning System - provides consolidated
project-specific patterns that Claude reads at the start of each iteration.

Patterns are stored in .ralph/patterns.md and include:
- Coding conventions discovered during execution
- Architecture patterns specific to this project
- Testing conventions and best practices
- Known gotchas and edge cases
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PatternCategory(Enum):
    """Categories of codebase patterns."""

    CODING = "coding"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    GOTCHAS = "gotchas"
    DEPENDENCIES = "dependencies"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    CUSTOM = "custom"

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        names = {
            PatternCategory.CODING: "Coding Conventions",
            PatternCategory.ARCHITECTURE: "Architecture Patterns",
            PatternCategory.TESTING: "Testing Conventions",
            PatternCategory.GOTCHAS: "Known Gotchas",
            PatternCategory.DEPENDENCIES: "Dependencies",
            PatternCategory.PERFORMANCE: "Performance",
            PatternCategory.SECURITY: "Security",
            PatternCategory.DOCUMENTATION: "Documentation",
            PatternCategory.CUSTOM: "Custom",
        }
        return names.get(self, self.value.title())


@dataclass
class CodebasePattern:
    """A single pattern or convention for the codebase.

    Attributes:
        content: The pattern description.
        category: Pattern category.
        source: Where this pattern was discovered (file, task, etc.).
        confidence: How confident we are in this pattern (0.0-1.0).
        discovered_at: When this pattern was discovered.
        examples: Example code or files demonstrating the pattern.
        tags: Additional tags for filtering.
    """

    content: str
    category: PatternCategory = PatternCategory.CODING
    source: Optional[str] = None
    confidence: float = 1.0
    discovered_at: Optional[str] = None
    examples: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Set discovered_at if not provided."""
        if self.discovered_at is None:
            self.discovered_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "category": self.category.value,
            "source": self.source,
            "confidence": self.confidence,
            "discovered_at": self.discovered_at,
            "examples": list(self.examples),
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodebasePattern:
        """Create from dictionary."""
        category = data.get("category", "coding")
        if isinstance(category, str):
            try:
                category = PatternCategory(category)
            except ValueError:
                category = PatternCategory.CUSTOM

        return cls(
            content=data.get("content", ""),
            category=category,
            source=data.get("source"),
            confidence=data.get("confidence", 1.0),
            discovered_at=data.get("discovered_at"),
            examples=tuple(data.get("examples", [])),
            tags=tuple(data.get("tags", [])),
        )


@dataclass
class CodebasePatterns:
    """Collection of patterns for a codebase.

    Attributes:
        patterns: List of patterns by category.
        project_name: Name of the project.
        last_updated: When patterns were last updated.
        version: Schema version.
    """

    patterns: dict[PatternCategory, list[CodebasePattern]] = field(
        default_factory=dict
    )
    project_name: str = ""
    last_updated: Optional[str] = None
    version: str = "1.0"

    def add(self, pattern: CodebasePattern) -> None:
        """Add a pattern.

        Args:
            pattern: Pattern to add.
        """
        if pattern.category not in self.patterns:
            self.patterns[pattern.category] = []
        self.patterns[pattern.category].append(pattern)
        self.last_updated = datetime.now().isoformat()

    def get_by_category(self, category: PatternCategory) -> list[CodebasePattern]:
        """Get patterns for a category.

        Args:
            category: Category to filter by.

        Returns:
            List of patterns in that category.
        """
        return self.patterns.get(category, [])

    def get_all(self) -> list[CodebasePattern]:
        """Get all patterns.

        Returns:
            All patterns flattened.
        """
        result = []
        for patterns in self.patterns.values():
            result.extend(patterns)
        return result

    def search(self, query: str) -> list[CodebasePattern]:
        """Search patterns by content.

        Args:
            query: Search query (case-insensitive).

        Returns:
            Matching patterns.
        """
        query_lower = query.lower()
        results = []
        for pattern in self.get_all():
            if query_lower in pattern.content.lower():
                results.append(pattern)
            elif any(query_lower in tag.lower() for tag in pattern.tags):
                results.append(pattern)
        return results

    def remove(self, pattern: CodebasePattern) -> bool:
        """Remove a pattern.

        Args:
            pattern: Pattern to remove.

        Returns:
            True if pattern was removed.
        """
        if pattern.category in self.patterns:
            try:
                self.patterns[pattern.category].remove(pattern)
                self.last_updated = datetime.now().isoformat()
                return True
            except ValueError:
                pass
        return False

    def __len__(self) -> int:
        """Get total number of patterns."""
        return sum(len(patterns) for patterns in self.patterns.values())

    def to_markdown(self) -> str:
        """Convert to markdown format.

        Returns:
            Markdown string for patterns.md file.
        """
        lines = ["# Codebase Patterns", ""]

        if self.project_name:
            lines.append(f"**Project:** {self.project_name}")
        if self.last_updated:
            lines.append(f"**Last Updated:** {self.last_updated}")
        lines.append("")

        # Sort categories for consistent output
        for category in sorted(self.patterns.keys(), key=lambda c: c.value):
            patterns = self.patterns[category]
            if not patterns:
                continue

            lines.append(f"## {category.display_name}")
            lines.append("")

            for pattern in patterns:
                # Main content as bullet point
                lines.append(f"- {pattern.content}")

                # Examples as sub-bullets
                for example in pattern.examples:
                    lines.append(f"  - Example: `{example}`")

                # Source info
                if pattern.source:
                    lines.append(f"  - Source: {pattern.source}")

            lines.append("")

        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, content: str) -> CodebasePatterns:
        """Parse markdown content into patterns.

        Args:
            content: Markdown content.

        Returns:
            CodebasePatterns instance.
        """
        patterns = cls()

        # Extract project name
        project_match = re.search(r"\*\*Project:\*\*\s*(.+)", content)
        if project_match:
            patterns.project_name = project_match.group(1).strip()

        # Extract last updated (save to restore later since add() updates it)
        parsed_last_updated = None
        updated_match = re.search(r"\*\*Last Updated:\*\*\s*(.+)", content)
        if updated_match:
            parsed_last_updated = updated_match.group(1).strip()

        # Parse sections
        current_category = None
        category_map = {cat.display_name.lower(): cat for cat in PatternCategory}

        for line in content.split("\n"):
            line = line.strip()

            # Check for section header
            if line.startswith("## "):
                section_name = line[3:].strip().lower()
                current_category = category_map.get(section_name)
                continue

            # Check for pattern bullet
            if line.startswith("- ") and current_category:
                pattern_content = line[2:].strip()

                # Skip sub-bullets (examples, source)
                if pattern_content.startswith("Example:"):
                    continue
                if pattern_content.startswith("Source:"):
                    continue

                pattern = CodebasePattern(
                    content=pattern_content,
                    category=current_category,
                )
                patterns.add(pattern)

        # Restore the parsed last_updated (add() updates it to current time)
        if parsed_last_updated:
            patterns.last_updated = parsed_last_updated

        return patterns


def get_patterns_path(project_root: Optional[Path] = None) -> Path:
    """Get the path to patterns.md file.

    Args:
        project_root: Project root directory. Uses CWD if None.

    Returns:
        Path to .ralph/patterns.md
    """
    if project_root is None:
        project_root = Path.cwd()
    return project_root / ".ralph" / "patterns.md"


def load_patterns(path: Optional[Path] = None) -> CodebasePatterns:
    """Load patterns from file.

    Args:
        path: Path to patterns file. Uses default if None.

    Returns:
        CodebasePatterns instance (empty if file doesn't exist).
    """
    if path is None:
        path = get_patterns_path()

    if not path.exists():
        logger.debug(f"Patterns file not found: {path}")
        return CodebasePatterns()

    try:
        content = path.read_text(encoding="utf-8")
        patterns = CodebasePatterns.from_markdown(content)
        logger.debug(f"Loaded {len(patterns)} patterns from {path}")
        return patterns
    except Exception as e:
        logger.warning(f"Failed to load patterns: {e}")
        return CodebasePatterns()


def save_patterns(patterns: CodebasePatterns, path: Optional[Path] = None) -> None:
    """Save patterns to file.

    Args:
        patterns: Patterns to save.
        path: Path to save to. Uses default if None.
    """
    if path is None:
        path = get_patterns_path()

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Update last_updated
    patterns.last_updated = datetime.now().isoformat()

    content = patterns.to_markdown()
    path.write_text(content, encoding="utf-8")
    logger.debug(f"Saved {len(patterns)} patterns to {path}")


def analyze_codebase(
    project_root: Optional[Path] = None,
    include_tests: bool = True,
) -> CodebasePatterns:
    """Analyze codebase to discover patterns.

    Scans the project for:
    - File organization patterns
    - Import patterns
    - Testing conventions
    - Configuration files
    - Documentation patterns

    Args:
        project_root: Project root directory.
        include_tests: Whether to analyze test files.

    Returns:
        Discovered patterns.
    """
    if project_root is None:
        project_root = Path.cwd()

    patterns = CodebasePatterns()
    patterns.project_name = project_root.name

    # Detect project type and conventions
    _detect_project_type(project_root, patterns)
    _detect_file_organization(project_root, patterns)
    _detect_testing_conventions(project_root, patterns, include_tests)
    _detect_dependencies(project_root, patterns)
    _detect_documentation(project_root, patterns)

    return patterns


def _detect_project_type(root: Path, patterns: CodebasePatterns) -> None:
    """Detect project type based on config files."""
    # Python
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        patterns.add(
            CodebasePattern(
                content="Python project - use pyproject.toml or setup.py for configuration",
                category=PatternCategory.ARCHITECTURE,
                source="project root",
            )
        )

    # Check for requirements files
    if (root / "requirements.txt").exists():
        patterns.add(
            CodebasePattern(
                content="Dependencies listed in requirements.txt",
                category=PatternCategory.DEPENDENCIES,
                source="requirements.txt",
            )
        )

    # TypeScript/JavaScript
    if (root / "package.json").exists():
        patterns.add(
            CodebasePattern(
                content="Node.js/TypeScript project with package.json",
                category=PatternCategory.ARCHITECTURE,
                source="package.json",
            )
        )

    # Check for TypeScript
    if (root / "tsconfig.json").exists():
        patterns.add(
            CodebasePattern(
                content="Use TypeScript - check tsconfig.json for compiler options",
                category=PatternCategory.CODING,
                source="tsconfig.json",
            )
        )


def _detect_file_organization(root: Path, patterns: CodebasePatterns) -> None:
    """Detect file organization patterns."""
    # Common directories
    common_dirs = {
        "src": "Source code in src/ directory",
        "lib": "Library code in lib/ directory",
        "tests": "Tests in tests/ directory",
        "test": "Tests in test/ directory",
        "docs": "Documentation in docs/ directory",
        "config": "Configuration in config/ directory",
        "scripts": "Scripts in scripts/ directory",
    }

    for dir_name, description in common_dirs.items():
        if (root / dir_name).is_dir():
            patterns.add(
                CodebasePattern(
                    content=description,
                    category=PatternCategory.ARCHITECTURE,
                    source=f"{dir_name}/",
                )
            )

    # Python package detection
    for item in root.iterdir():
        if item.is_dir() and (item / "__init__.py").exists():
            patterns.add(
                CodebasePattern(
                    content=f"Python package: {item.name}/ (has __init__.py)",
                    category=PatternCategory.ARCHITECTURE,
                    source=f"{item.name}/__init__.py",
                )
            )
            break  # Only note the first package


def _detect_testing_conventions(
    root: Path, patterns: CodebasePatterns, include_tests: bool
) -> None:
    """Detect testing conventions."""
    if not include_tests:
        return

    # Pytest
    if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists():
        patterns.add(
            CodebasePattern(
                content="Use pytest for testing",
                category=PatternCategory.TESTING,
                source="pytest.ini or pyproject.toml",
            )
        )

    # Jest
    if (root / "jest.config.js").exists() or (root / "jest.config.ts").exists():
        patterns.add(
            CodebasePattern(
                content="Use Jest for testing",
                category=PatternCategory.TESTING,
                source="jest.config",
            )
        )

    # Test directories
    test_dirs = ["tests", "test", "__tests__", "spec"]
    for test_dir in test_dirs:
        if (root / test_dir).is_dir():
            patterns.add(
                CodebasePattern(
                    content=f"Test files in {test_dir}/ directory",
                    category=PatternCategory.TESTING,
                    source=f"{test_dir}/",
                )
            )
            break


def _detect_dependencies(root: Path, patterns: CodebasePatterns) -> None:
    """Detect dependency patterns."""
    # Python dependencies
    if (root / "pyproject.toml").exists():
        try:
            content = (root / "pyproject.toml").read_text()
            if "pytest" in content:
                patterns.add(
                    CodebasePattern(
                        content="pytest is a project dependency",
                        category=PatternCategory.DEPENDENCIES,
                        source="pyproject.toml",
                    )
                )
            if "black" in content or "ruff" in content:
                patterns.add(
                    CodebasePattern(
                        content="Code formatting enforced (black/ruff)",
                        category=PatternCategory.CODING,
                        source="pyproject.toml",
                    )
                )
        except Exception:
            pass


def _detect_documentation(root: Path, patterns: CodebasePatterns) -> None:
    """Detect documentation patterns."""
    if (root / "README.md").exists():
        patterns.add(
            CodebasePattern(
                content="Project documentation in README.md",
                category=PatternCategory.DOCUMENTATION,
                source="README.md",
            )
        )

    if (root / "docs").is_dir():
        patterns.add(
            CodebasePattern(
                content="Extended documentation in docs/ directory",
                category=PatternCategory.DOCUMENTATION,
                source="docs/",
            )
        )

    # API docs
    if (root / "docs" / "api").is_dir() or (root / "api-docs").is_dir():
        patterns.add(
            CodebasePattern(
                content="API documentation available",
                category=PatternCategory.DOCUMENTATION,
                source="docs/api/ or api-docs/",
            )
        )


def inject_patterns(
    patterns: CodebasePatterns,
    prompt: str,
    max_patterns: int = 20,
) -> str:
    """Inject patterns into a system prompt.

    Args:
        patterns: Patterns to inject.
        prompt: Base system prompt.
        max_patterns: Maximum number of patterns to include.

    Returns:
        Prompt with patterns injected.
    """
    if len(patterns) == 0:
        return prompt

    # Build patterns section
    lines = ["\n\n## Project Patterns\n"]
    lines.append("The following patterns have been learned about this codebase:\n")

    count = 0
    for category in sorted(patterns.patterns.keys(), key=lambda c: c.value):
        category_patterns = patterns.get_by_category(category)
        if not category_patterns:
            continue

        lines.append(f"\n### {category.display_name}")
        for pattern in category_patterns:
            if count >= max_patterns:
                break
            lines.append(f"- {pattern.content}")
            count += 1

        if count >= max_patterns:
            break

    patterns_section = "\n".join(lines)
    return prompt + patterns_section
