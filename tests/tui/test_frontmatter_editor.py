"""Tests for frontmatter YAML editor widget."""

import pytest

from ralph_agi.tui.widgets.frontmatter_editor import (
    FrontmatterField,
    SCHEMAS,
    parse_frontmatter,
    serialize_frontmatter,
)


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_parse_with_frontmatter(self):
        """Test parsing markdown with frontmatter."""
        content = """---
title: Test Document
author: Test Author
version: "1.0"
---
# Hello World

This is the body content.
"""
        data, body = parse_frontmatter(content)

        assert data["title"] == "Test Document"
        assert data["author"] == "Test Author"
        assert data["version"] == "1.0"
        assert "# Hello World" in body
        assert "This is the body content." in body

    def test_parse_without_frontmatter(self):
        """Test parsing markdown without frontmatter."""
        content = """# Hello World

This is just markdown without frontmatter.
"""
        data, body = parse_frontmatter(content)

        assert data == {}
        assert body == content

    def test_parse_empty_frontmatter(self):
        """Test parsing empty frontmatter."""
        content = """---
---
# Body
"""
        data, body = parse_frontmatter(content)

        assert data == {}
        assert "# Body" in body

    def test_parse_complex_frontmatter(self):
        """Test parsing complex YAML frontmatter."""
        content = """---
title: Complex Example
tags:
  - python
  - testing
nested:
  key: value
  number: 42
---
Body content.
"""
        data, body = parse_frontmatter(content)

        assert data["title"] == "Complex Example"
        assert data["tags"] == ["python", "testing"]
        assert data["nested"]["key"] == "value"
        assert data["nested"]["number"] == 42
        assert body.strip() == "Body content."

    def test_parse_preserves_body_formatting(self):
        """Test that body formatting is preserved."""
        content = """---
title: Test
---
Line 1

Line 2

Line 3
"""
        data, body = parse_frontmatter(content)

        assert "Line 1" in body
        assert "Line 2" in body
        assert "Line 3" in body
        # Body should preserve newlines between lines
        assert "\n\n" in body

    def test_parse_invalid_yaml(self):
        """Test parsing invalid YAML returns empty dict."""
        content = """---
invalid: yaml: syntax: here
---
Body
"""
        data, body = parse_frontmatter(content)

        # Should return empty dict on parse error
        assert data == {}
        assert "Body" in body


class TestSerializeFrontmatter:
    """Tests for serialize_frontmatter function."""

    def test_serialize_basic(self):
        """Test basic serialization."""
        data = {"title": "Test", "author": "Me"}
        body = "# Content"

        result = serialize_frontmatter(data, body)

        assert result.startswith("---\n")
        assert "title: Test" in result
        assert "author: Me" in result
        assert result.endswith("---\n# Content")

    def test_serialize_empty_data(self):
        """Test serialization with empty data."""
        data = {}
        body = "# Just Body"

        result = serialize_frontmatter(data, body)

        assert result == "# Just Body"

    def test_serialize_filters_none(self):
        """Test that None values are filtered out."""
        data = {"title": "Test", "author": None, "date": ""}
        body = "Content"

        result = serialize_frontmatter(data, body)

        assert "title: Test" in result
        assert "author" not in result
        assert "date" not in result

    def test_serialize_preserves_body(self):
        """Test that body is preserved exactly."""
        data = {"title": "Test"}
        body = "\n\nFormatted\n\n  Indented\n"

        result = serialize_frontmatter(data, body)

        assert result.endswith(body)

    def test_roundtrip(self):
        """Test parse/serialize roundtrip preserves data."""
        original = """---
title: Test Document
author: Test Author
priority: 1
---
# Heading

Body content here.
"""
        data, body = parse_frontmatter(original)
        result = serialize_frontmatter(data, body)

        # Parse again
        data2, body2 = parse_frontmatter(result)

        assert data2["title"] == data["title"]
        assert data2["author"] == data["author"]
        assert data2["priority"] == data["priority"]
        assert body2 == body


class TestFrontmatterField:
    """Tests for FrontmatterField dataclass."""

    def test_text_field(self):
        """Test creating a text field."""
        field = FrontmatterField(
            name="title",
            label="Title",
            field_type="text",
            required=True,
        )

        assert field.name == "title"
        assert field.label == "Title"
        assert field.field_type == "text"
        assert field.required is True
        assert field.default is None

    def test_field_with_default(self):
        """Test creating a field with default value."""
        field = FrontmatterField(
            name="status",
            label="Status",
            field_type="text",
            default="draft",
        )

        assert field.default == "draft"

    def test_checkbox_field(self):
        """Test creating a checkbox field."""
        field = FrontmatterField(
            name="published",
            label="Published",
            field_type="checkbox",
            default=False,
        )

        assert field.field_type == "checkbox"
        assert field.default is False

    def test_number_field(self):
        """Test creating a number field."""
        field = FrontmatterField(
            name="priority",
            label="Priority",
            field_type="number",
            default=2,
        )

        assert field.field_type == "number"
        assert field.default == 2

    def test_textarea_field(self):
        """Test creating a textarea field."""
        field = FrontmatterField(
            name="description",
            label="Description",
            field_type="textarea",
            help_text="Enter a detailed description",
        )

        assert field.field_type == "textarea"
        assert field.help_text == "Enter a detailed description"


class TestSchemas:
    """Tests for predefined schemas."""

    def test_story_schema_exists(self):
        """Test that story schema exists."""
        assert "story" in SCHEMAS
        story_fields = {f.name for f in SCHEMAS["story"]}
        assert "id" in story_fields
        assert "title" in story_fields
        assert "status" in story_fields

    def test_epic_schema_exists(self):
        """Test that epic schema exists."""
        assert "epic" in SCHEMAS
        epic_fields = {f.name for f in SCHEMAS["epic"]}
        assert "id" in epic_fields
        assert "title" in epic_fields

    def test_task_schema_exists(self):
        """Test that task schema exists."""
        assert "task" in SCHEMAS
        task_fields = {f.name for f in SCHEMAS["task"]}
        assert "id" in task_fields
        assert "blocked" in task_fields

    def test_generic_schema_exists(self):
        """Test that generic schema exists."""
        assert "generic" in SCHEMAS
        generic_fields = {f.name for f in SCHEMAS["generic"]}
        assert "title" in generic_fields
        assert "date" in generic_fields

    def test_schema_has_required_fields(self):
        """Test that schemas have required fields marked."""
        story_schema = SCHEMAS["story"]
        required_fields = [f for f in story_schema if f.required]

        # Story should have required id and title
        required_names = {f.name for f in required_fields}
        assert "id" in required_names
        assert "title" in required_names

    def test_schema_field_types(self):
        """Test that schema fields have valid types."""
        valid_types = {"text", "textarea", "checkbox", "number"}

        for schema_name, fields in SCHEMAS.items():
            for field in fields:
                assert field.field_type in valid_types, (
                    f"Invalid type '{field.field_type}' in {schema_name}.{field.name}"
                )


class TestFrontmatterEditorValidation:
    """Tests for FrontmatterEditor validation logic."""

    def test_validate_required_fields(self):
        """Test validation of required fields."""
        fields = [
            FrontmatterField("id", "ID", "text", required=True),
            FrontmatterField("title", "Title", "text", required=True),
            FrontmatterField("notes", "Notes", "textarea", required=False),
        ]
        data = {"id": "task-1", "notes": "Some notes"}

        errors = []
        for field in fields:
            if field.required:
                value = data.get(field.name)
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors.append(f"{field.label} is required")

        assert "Title is required" in errors
        assert len(errors) == 1

    def test_validate_all_required_present(self):
        """Test validation when all required fields are present."""
        fields = [
            FrontmatterField("id", "ID", "text", required=True),
            FrontmatterField("title", "Title", "text", required=True),
        ]
        data = {"id": "task-1", "title": "My Task"}

        errors = []
        for field in fields:
            if field.required:
                value = data.get(field.name)
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors.append(f"{field.label} is required")

        assert errors == []

    def test_validate_empty_string_is_missing(self):
        """Test that empty string counts as missing for required fields."""
        fields = [
            FrontmatterField("title", "Title", "text", required=True),
        ]
        data = {"title": "   "}  # Whitespace only

        errors = []
        for field in fields:
            if field.required:
                value = data.get(field.name)
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors.append(f"{field.label} is required")

        assert "Title is required" in errors
