"""Tests for codebase patterns module."""

from __future__ import annotations

import pytest
from pathlib import Path

from ralph_agi.learning.patterns import (
    CodebasePattern,
    CodebasePatterns,
    PatternCategory,
    load_patterns,
    save_patterns,
    get_patterns_path,
    analyze_codebase,
    inject_patterns,
)


class TestPatternCategory:
    """Tests for PatternCategory enum."""

    def test_all_categories_exist(self):
        """Test all expected categories exist."""
        assert PatternCategory.CODING.value == "coding"
        assert PatternCategory.ARCHITECTURE.value == "architecture"
        assert PatternCategory.TESTING.value == "testing"
        assert PatternCategory.GOTCHAS.value == "gotchas"
        assert PatternCategory.DEPENDENCIES.value == "dependencies"
        assert PatternCategory.PERFORMANCE.value == "performance"
        assert PatternCategory.SECURITY.value == "security"
        assert PatternCategory.DOCUMENTATION.value == "documentation"
        assert PatternCategory.CUSTOM.value == "custom"

    def test_display_names(self):
        """Test display names are human-readable."""
        assert PatternCategory.CODING.display_name == "Coding Conventions"
        assert PatternCategory.ARCHITECTURE.display_name == "Architecture Patterns"
        assert PatternCategory.TESTING.display_name == "Testing Conventions"
        assert PatternCategory.GOTCHAS.display_name == "Known Gotchas"


class TestCodebasePattern:
    """Tests for CodebasePattern dataclass."""

    def test_pattern_creation_minimal(self):
        """Test creating pattern with minimal fields."""
        pattern = CodebasePattern(content="Use type hints")
        assert pattern.content == "Use type hints"
        assert pattern.category == PatternCategory.CODING
        assert pattern.confidence == 1.0
        assert pattern.discovered_at is not None

    def test_pattern_creation_full(self):
        """Test creating pattern with all fields."""
        pattern = CodebasePattern(
            content="Tests in tests/ directory",
            category=PatternCategory.TESTING,
            source="project structure",
            confidence=0.9,
            discovered_at="2025-01-01T00:00:00",
            examples=("tests/test_main.py",),
            tags=("testing", "pytest"),
        )
        assert pattern.content == "Tests in tests/ directory"
        assert pattern.category == PatternCategory.TESTING
        assert pattern.source == "project structure"
        assert pattern.confidence == 0.9
        assert pattern.discovered_at == "2025-01-01T00:00:00"
        assert len(pattern.examples) == 1
        assert len(pattern.tags) == 2

    def test_to_dict(self):
        """Test converting pattern to dictionary."""
        pattern = CodebasePattern(
            content="Use black for formatting",
            category=PatternCategory.CODING,
            source="pyproject.toml",
            confidence=1.0,
        )
        data = pattern.to_dict()

        assert data["content"] == "Use black for formatting"
        assert data["category"] == "coding"
        assert data["source"] == "pyproject.toml"
        assert data["confidence"] == 1.0

    def test_from_dict(self):
        """Test creating pattern from dictionary."""
        data = {
            "content": "API endpoints in /api",
            "category": "architecture",
            "source": "router.py",
            "confidence": 0.8,
            "examples": ["api/users.py", "api/posts.py"],
            "tags": ["api", "rest"],
        }
        pattern = CodebasePattern.from_dict(data)

        assert pattern.content == "API endpoints in /api"
        assert pattern.category == PatternCategory.ARCHITECTURE
        assert pattern.source == "router.py"
        assert pattern.confidence == 0.8
        assert len(pattern.examples) == 2
        assert len(pattern.tags) == 2

    def test_from_dict_defaults(self):
        """Test creating pattern from minimal dictionary."""
        data = {"content": "Use async/await"}
        pattern = CodebasePattern.from_dict(data)

        assert pattern.content == "Use async/await"
        assert pattern.category == PatternCategory.CODING  # Defaults to CODING when not specified
        assert pattern.confidence == 1.0

    def test_from_dict_invalid_category(self):
        """Test handling invalid category."""
        data = {"content": "Test", "category": "invalid_category"}
        pattern = CodebasePattern.from_dict(data)
        assert pattern.category == PatternCategory.CUSTOM


class TestCodebasePatterns:
    """Tests for CodebasePatterns collection."""

    def test_patterns_creation(self):
        """Test creating empty patterns collection."""
        patterns = CodebasePatterns()
        assert len(patterns) == 0
        assert patterns.project_name == ""

    def test_add_pattern(self):
        """Test adding a pattern."""
        patterns = CodebasePatterns()
        pattern = CodebasePattern(content="Test pattern")
        patterns.add(pattern)

        assert len(patterns) == 1
        assert patterns.last_updated is not None

    def test_add_multiple_categories(self):
        """Test adding patterns to different categories."""
        patterns = CodebasePatterns()
        patterns.add(CodebasePattern(content="Coding", category=PatternCategory.CODING))
        patterns.add(CodebasePattern(content="Testing", category=PatternCategory.TESTING))
        patterns.add(CodebasePattern(content="Coding 2", category=PatternCategory.CODING))

        assert len(patterns) == 3
        assert len(patterns.get_by_category(PatternCategory.CODING)) == 2
        assert len(patterns.get_by_category(PatternCategory.TESTING)) == 1

    def test_get_by_category_empty(self):
        """Test getting patterns for empty category."""
        patterns = CodebasePatterns()
        result = patterns.get_by_category(PatternCategory.GOTCHAS)
        assert result == []

    def test_get_all(self):
        """Test getting all patterns."""
        patterns = CodebasePatterns()
        patterns.add(CodebasePattern(content="P1", category=PatternCategory.CODING))
        patterns.add(CodebasePattern(content="P2", category=PatternCategory.TESTING))

        all_patterns = patterns.get_all()
        assert len(all_patterns) == 2

    def test_search(self):
        """Test searching patterns."""
        patterns = CodebasePatterns()
        patterns.add(CodebasePattern(content="Use TypeScript strict mode"))
        patterns.add(CodebasePattern(content="Use pytest for testing"))
        patterns.add(CodebasePattern(content="Format with black", tags=("formatter",)))

        results = patterns.search("typescript")
        assert len(results) == 1
        assert "TypeScript" in results[0].content

        # Search by tag
        results = patterns.search("formatter")
        assert len(results) == 1

    def test_remove(self):
        """Test removing a pattern."""
        patterns = CodebasePatterns()
        pattern = CodebasePattern(content="To remove")
        patterns.add(pattern)
        assert len(patterns) == 1

        removed = patterns.remove(pattern)
        assert removed is True
        assert len(patterns) == 0

    def test_remove_nonexistent(self):
        """Test removing nonexistent pattern."""
        patterns = CodebasePatterns()
        pattern = CodebasePattern(content="Not added")
        removed = patterns.remove(pattern)
        assert removed is False

    def test_to_markdown(self):
        """Test converting to markdown."""
        patterns = CodebasePatterns(project_name="test-project")
        patterns.add(
            CodebasePattern(
                content="Use type hints",
                category=PatternCategory.CODING,
                source="style guide",
            )
        )
        patterns.add(
            CodebasePattern(
                content="Tests in tests/",
                category=PatternCategory.TESTING,
                examples=("tests/test_main.py",),
            )
        )

        md = patterns.to_markdown()

        assert "# Codebase Patterns" in md
        assert "**Project:** test-project" in md
        assert "## Coding Conventions" in md
        assert "- Use type hints" in md
        assert "## Testing Conventions" in md
        assert "- Tests in tests/" in md
        assert "Example: `tests/test_main.py`" in md
        assert "Source: style guide" in md

    def test_from_markdown(self):
        """Test parsing from markdown."""
        md = """# Codebase Patterns

**Project:** my-project
**Last Updated:** 2025-01-01T00:00:00

## Coding Conventions

- Use strict TypeScript
- Prefer functional components
  - Example: `src/Button.tsx`

## Testing Conventions

- Tests in __tests__/ directory
"""
        patterns = CodebasePatterns.from_markdown(md)

        assert patterns.project_name == "my-project"
        assert patterns.last_updated == "2025-01-01T00:00:00"
        assert len(patterns) == 3

        coding = patterns.get_by_category(PatternCategory.CODING)
        assert len(coding) == 2

    def test_markdown_roundtrip(self):
        """Test markdown save and load roundtrip."""
        original = CodebasePatterns(project_name="roundtrip-test")
        original.add(CodebasePattern(content="Pattern 1", category=PatternCategory.CODING))
        original.add(CodebasePattern(content="Pattern 2", category=PatternCategory.TESTING))

        md = original.to_markdown()
        loaded = CodebasePatterns.from_markdown(md)

        assert loaded.project_name == original.project_name
        assert len(loaded) == len(original)


class TestPersistence:
    """Tests for patterns persistence functions."""

    def test_get_patterns_path(self, tmp_path):
        """Test getting patterns path."""
        path = get_patterns_path(tmp_path)
        assert path.name == "patterns.md"
        assert ".ralph" in str(path)

    def test_get_patterns_path_default(self):
        """Test getting default patterns path."""
        path = get_patterns_path()
        assert path.name == "patterns.md"
        assert ".ralph" in str(path)

    def test_load_nonexistent(self, tmp_path):
        """Test loading from nonexistent file."""
        path = tmp_path / ".ralph" / "patterns.md"
        patterns = load_patterns(path)

        assert isinstance(patterns, CodebasePatterns)
        assert len(patterns) == 0

    def test_save_and_load(self, tmp_path):
        """Test saving and loading patterns."""
        path = tmp_path / ".ralph" / "patterns.md"

        # Create and save
        patterns = CodebasePatterns(project_name="test")
        patterns.add(CodebasePattern(content="Test pattern"))
        save_patterns(patterns, path)

        assert path.exists()

        # Load and verify
        loaded = load_patterns(path)
        assert loaded.project_name == "test"
        assert len(loaded) == 1

    def test_save_creates_directory(self, tmp_path):
        """Test that save creates parent directory."""
        path = tmp_path / "deep" / "nested" / ".ralph" / "patterns.md"
        patterns = CodebasePatterns()
        patterns.add(CodebasePattern(content="Test"))

        save_patterns(patterns, path)

        assert path.exists()

    def test_load_invalid_content(self, tmp_path):
        """Test loading from file with invalid content."""
        path = tmp_path / "patterns.md"
        path.write_text("This is not valid patterns markdown")

        patterns = load_patterns(path)
        assert len(patterns) == 0  # Should return empty, not raise


class TestCodebaseAnalysis:
    """Tests for codebase analysis functions."""

    def test_analyze_python_project(self, tmp_path):
        """Test analyzing a Python project."""
        # Create Python project structure
        (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]")
        (tmp_path / "requirements.txt").write_text("requests==2.28.0")
        (tmp_path / "tests").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "__init__.py").touch()
        (tmp_path / "README.md").write_text("# Test Project")

        patterns = analyze_codebase(tmp_path)

        assert patterns.project_name == tmp_path.name
        assert len(patterns) > 0

        # Check for expected patterns
        all_content = " ".join(p.content for p in patterns.get_all())
        assert "Python" in all_content or "pyproject" in all_content
        assert "requirements.txt" in all_content
        assert "tests/" in all_content or "test" in all_content.lower()

    def test_analyze_typescript_project(self, tmp_path):
        """Test analyzing a TypeScript project."""
        # Create TypeScript project structure
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {}}')
        (tmp_path / "src").mkdir()

        patterns = analyze_codebase(tmp_path)

        all_content = " ".join(p.content for p in patterns.get_all())
        assert "package.json" in all_content or "Node" in all_content
        assert "TypeScript" in all_content or "tsconfig" in all_content

    def test_analyze_empty_directory(self, tmp_path):
        """Test analyzing an empty directory."""
        patterns = analyze_codebase(tmp_path)
        assert patterns.project_name == tmp_path.name
        # Should have at least project name set


class TestInjectPatterns:
    """Tests for pattern injection into prompts."""

    def test_inject_empty_patterns(self):
        """Test injecting empty patterns."""
        patterns = CodebasePatterns()
        prompt = "You are a helpful assistant."
        result = inject_patterns(patterns, prompt)
        assert result == prompt  # No change

    def test_inject_patterns(self):
        """Test injecting patterns into prompt."""
        patterns = CodebasePatterns()
        patterns.add(CodebasePattern(content="Use type hints", category=PatternCategory.CODING))
        patterns.add(CodebasePattern(content="Tests in tests/", category=PatternCategory.TESTING))

        prompt = "You are a helpful assistant."
        result = inject_patterns(patterns, prompt)

        assert "You are a helpful assistant." in result
        assert "## Project Patterns" in result
        assert "Use type hints" in result
        assert "Tests in tests/" in result
        assert "Coding Conventions" in result

    def test_inject_max_patterns(self):
        """Test respecting max_patterns limit."""
        patterns = CodebasePatterns()
        for i in range(30):
            patterns.add(CodebasePattern(content=f"Pattern {i}"))

        prompt = "Base prompt."
        result = inject_patterns(patterns, prompt, max_patterns=5)

        # Count pattern entries
        pattern_count = result.count("- Pattern")
        assert pattern_count <= 5

    def test_inject_preserves_original_prompt(self):
        """Test that injection preserves original prompt."""
        patterns = CodebasePatterns()
        patterns.add(CodebasePattern(content="Test pattern"))

        prompt = "This is the original prompt with special content."
        result = inject_patterns(patterns, prompt)

        assert result.startswith(prompt)
