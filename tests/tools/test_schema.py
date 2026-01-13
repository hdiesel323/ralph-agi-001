"""Tests for schema parsing and inspection."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from ralph_agi.tools.schema import (
    Parameter,
    SchemaParseError,
    ToolNotFoundError,
    ToolSchema,
)
from ralph_agi.tools.registry import (
    ServerConfig,
    ToolInfo,
    ToolRegistry,
    ServerStatus,
)


# =============================================================================
# ToolNotFoundError Tests
# =============================================================================


class TestToolNotFoundError:
    """Tests for ToolNotFoundError exception."""

    def test_basic_error(self):
        """Test basic error message."""
        error = ToolNotFoundError("read_file")

        assert "read_file" in str(error)
        assert error.tool_name == "read_file"

    def test_error_with_server(self):
        """Test error with server context."""
        error = ToolNotFoundError("read_file", server="filesystem")

        assert "read_file" in str(error)
        assert "filesystem" in str(error)
        assert error.server == "filesystem"

    def test_error_with_suggestions(self):
        """Test error with manual suggestions."""
        error = ToolNotFoundError(
            "read_fil",
            suggestions=["read_file", "read_dir"],
        )

        assert "Did you mean" in str(error)
        assert "read_file" in str(error)

    def test_error_finds_similar_names(self):
        """Test automatic fuzzy matching."""
        available = ["read_file", "write_file", "delete_file", "list_dir"]
        error = ToolNotFoundError("read_fil", available_tools=available)

        assert "read_file" in error.suggestions
        assert error.tool_name == "read_fil"

    def test_error_no_suggestions_different_names(self):
        """Test when no similar names exist."""
        available = ["alpha", "beta", "gamma"]
        error = ToolNotFoundError("xyz123", available_tools=available)

        assert len(error.suggestions) == 0
        # Should list available tools instead
        assert "alpha" in str(error)

    def test_error_substring_matching(self):
        """Test substring boost in fuzzy matching."""
        available = ["github_create_issue", "github_list_repos", "slack_send"]
        error = ToolNotFoundError("github", available_tools=available)

        # Both github tools should be suggested
        assert len(error.suggestions) >= 2
        assert all("github" in s for s in error.suggestions)

    def test_error_limits_suggestions(self):
        """Test suggestion limit."""
        available = [f"read_file_{i}" for i in range(10)]
        error = ToolNotFoundError("read_file", available_tools=available)

        # Should limit to 3 suggestions
        assert len(error.suggestions) <= 3

    def test_error_empty_available_tools(self):
        """Test with no available tools."""
        error = ToolNotFoundError("tool", available_tools=[])

        assert error.suggestions == []


# =============================================================================
# Parameter Tests
# =============================================================================


class TestParameter:
    """Tests for Parameter dataclass."""

    def test_basic_parameter(self):
        """Test creating basic parameter."""
        param = Parameter(
            name="path",
            type="string",
            description="File path to read",
            required=True,
        )

        assert param.name == "path"
        assert param.type == "string"
        assert param.description == "File path to read"
        assert param.required is True

    def test_parameter_with_default(self):
        """Test parameter with default value."""
        param = Parameter(
            name="encoding",
            type="string",
            default="utf-8",
            required=False,
        )

        assert param.default == "utf-8"
        assert param.required is False

    def test_parameter_with_enum(self):
        """Test parameter with enum constraint."""
        param = Parameter(
            name="format",
            type="string",
            enum=["json", "yaml", "toml"],
        )

        assert param.enum == ["json", "yaml", "toml"]

    def test_parameter_to_dict(self):
        """Test to_dict serialization."""
        param = Parameter(
            name="count",
            type="integer",
            description="Number of items",
            required=True,
            default=10,
            enum=[1, 5, 10, 20],
        )

        d = param.to_dict()

        assert d["name"] == "count"
        assert d["type"] == "integer"
        assert d["description"] == "Number of items"
        assert d["required"] is True
        assert d["default"] == 10
        assert d["enum"] == [1, 5, 10, 20]

    def test_parameter_to_dict_minimal(self):
        """Test to_dict with minimal fields."""
        param = Parameter(name="x", type="string")
        d = param.to_dict()

        assert d["name"] == "x"
        assert d["type"] == "string"
        assert "default" not in d  # None values omitted
        assert "enum" not in d

    def test_format_for_llm_required(self):
        """Test LLM formatting for required param."""
        param = Parameter(
            name="path",
            type="string",
            description="File path to read",
            required=True,
        )

        formatted = param.format_for_llm()

        assert "- path (string, required)" in formatted
        assert "File path to read" in formatted

    def test_format_for_llm_optional_with_default(self):
        """Test LLM formatting with default."""
        param = Parameter(
            name="encoding",
            type="string",
            description="File encoding",
            required=False,
            default="utf-8",
        )

        formatted = param.format_for_llm()

        assert "- encoding (string, optional)" in formatted
        assert "Default: utf-8" in formatted

    def test_format_for_llm_with_enum(self):
        """Test LLM formatting with enum values."""
        param = Parameter(
            name="format",
            type="string",
            description="Output format",
            required=True,
            enum=["json", "yaml"],
        )

        formatted = param.format_for_llm()

        assert "Values: json, yaml" in formatted


# =============================================================================
# ToolSchema Basic Tests
# =============================================================================


class TestToolSchemaBasic:
    """Basic tests for ToolSchema."""

    def test_schema_creation(self):
        """Test creating ToolSchema."""
        schema = ToolSchema(
            tool_name="test_tool",
            description="A test tool",
            parameters=[
                Parameter(name="arg1", type="string", required=True),
                Parameter(name="arg2", type="number", required=False),
            ],
            required_params=["arg1"],
        )

        assert schema.tool_name == "test_tool"
        assert schema.description == "A test tool"
        assert len(schema.parameters) == 2
        assert schema.required_params == ["arg1"]

    def test_get_parameter(self):
        """Test getting parameter by name."""
        schema = ToolSchema(
            tool_name="test",
            parameters=[
                Parameter(name="a", type="string"),
                Parameter(name="b", type="number"),
            ],
        )

        param = schema.get_parameter("a")
        assert param is not None
        assert param.name == "a"

        missing = schema.get_parameter("c")
        assert missing is None

    def test_get_required_parameters(self):
        """Test getting required parameters."""
        schema = ToolSchema(
            tool_name="test",
            parameters=[
                Parameter(name="req1", type="string", required=True),
                Parameter(name="opt1", type="string", required=False),
                Parameter(name="req2", type="number", required=True),
            ],
        )

        required = schema.get_required_parameters()

        assert len(required) == 2
        assert all(p.required for p in required)

    def test_get_optional_parameters(self):
        """Test getting optional parameters."""
        schema = ToolSchema(
            tool_name="test",
            parameters=[
                Parameter(name="req", type="string", required=True),
                Parameter(name="opt1", type="string", required=False),
                Parameter(name="opt2", type="number", required=False),
            ],
        )

        optional = schema.get_optional_parameters()

        assert len(optional) == 2
        assert all(not p.required for p in optional)


# =============================================================================
# ToolSchema Parsing Tests
# =============================================================================


class TestToolSchemaParsing:
    """Tests for parsing JSON Schema to ToolSchema."""

    def test_from_tool_info_basic(self):
        """Test parsing basic schema."""
        input_schema = {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path",
                }
            },
            "required": ["path"],
        }

        schema = ToolSchema.from_tool_info(
            tool_name="read_file",
            description="Read a file",
            input_schema=input_schema,
        )

        assert schema.tool_name == "read_file"
        assert schema.description == "Read a file"
        assert len(schema.parameters) == 1

        param = schema.parameters[0]
        assert param.name == "path"
        assert param.type == "string"
        assert param.required is True

    def test_from_tool_info_multiple_params(self):
        """Test parsing schema with multiple parameters."""
        input_schema = {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "append": {"type": "boolean", "default": False},
            },
            "required": ["path", "content"],
        }

        schema = ToolSchema.from_tool_info(
            tool_name="write_file",
            description="Write to file",
            input_schema=input_schema,
        )

        assert len(schema.parameters) == 3
        assert schema.required_params == ["path", "content"]

        append_param = schema.get_parameter("append")
        assert append_param is not None
        assert append_param.required is False
        assert append_param.default is False

    def test_from_tool_info_with_enum(self):
        """Test parsing schema with enum."""
        input_schema = {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["json", "yaml", "toml"],
                }
            },
        }

        schema = ToolSchema.from_tool_info("convert", "", input_schema)

        param = schema.parameters[0]
        assert param.enum == ["json", "yaml", "toml"]

    def test_from_tool_info_array_type(self):
        """Test parsing array parameter."""
        input_schema = {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
        }

        schema = ToolSchema.from_tool_info("batch", "", input_schema)

        param = schema.parameters[0]
        assert param.type == "array"
        assert param.items_type == "string"

    def test_from_tool_info_nested_object(self):
        """Test parsing nested object parameter."""
        input_schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer"},
                    },
                    "required": ["host"],
                }
            },
        }

        schema = ToolSchema.from_tool_info("connect", "", input_schema)

        param = schema.parameters[0]
        assert param.type == "object"
        assert param.properties is not None
        assert "host" in param.properties
        assert param.properties["host"].required is True

    def test_from_tool_info_union_type(self):
        """Test parsing union type (takes first non-null)."""
        input_schema = {
            "type": "object",
            "properties": {
                "value": {
                    "type": ["null", "string", "number"],
                }
            },
        }

        schema = ToolSchema.from_tool_info("test", "", input_schema)

        param = schema.parameters[0]
        assert param.type == "string"  # First non-null

    def test_from_tool_info_empty_schema(self):
        """Test parsing empty schema."""
        schema = ToolSchema.from_tool_info("no_args", "No arguments", {})

        assert schema.tool_name == "no_args"
        assert len(schema.parameters) == 0


# =============================================================================
# ToolSchema Validation Tests
# =============================================================================


class TestToolSchemaValidation:
    """Tests for argument validation."""

    @pytest.fixture
    def test_schema(self):
        """Create test schema."""
        return ToolSchema.from_tool_info(
            tool_name="test_tool",
            description="Test",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "count": {"type": "integer"},
                    "enabled": {"type": "boolean"},
                    "format": {"type": "string", "enum": ["a", "b"]},
                },
                "required": ["name"],
            },
        )

    def test_validate_valid_arguments(self, test_schema):
        """Test validation passes with valid args."""
        errors = test_schema.validate_arguments({
            "name": "test",
            "count": 5,
        })

        assert errors == []

    def test_validate_missing_required(self, test_schema):
        """Test validation catches missing required."""
        errors = test_schema.validate_arguments({
            "count": 5,
        })

        assert len(errors) == 1
        assert "Missing required" in errors[0]
        assert "name" in errors[0]

    def test_validate_unknown_parameter(self, test_schema):
        """Test validation catches unknown params."""
        errors = test_schema.validate_arguments({
            "name": "test",
            "unknown_param": "value",
        })

        assert len(errors) == 1
        assert "Unknown parameter" in errors[0]

    def test_validate_wrong_type(self, test_schema):
        """Test validation catches wrong type."""
        errors = test_schema.validate_arguments({
            "name": "test",
            "count": "not a number",  # Should be integer
        })

        assert len(errors) == 1
        assert "expected integer" in errors[0]

    def test_validate_enum_violation(self, test_schema):
        """Test validation catches enum violation."""
        errors = test_schema.validate_arguments({
            "name": "test",
            "format": "c",  # Not in enum [a, b]
        })

        assert len(errors) == 1
        assert "must be one of" in errors[0]

    def test_validate_multiple_errors(self, test_schema):
        """Test validation returns all errors."""
        errors = test_schema.validate_arguments({
            # Missing: name
            "count": "wrong type",
            "unknown": "value",
        })

        assert len(errors) == 3


# =============================================================================
# ToolSchema Formatting Tests
# =============================================================================


class TestToolSchemaFormatting:
    """Tests for schema formatting."""

    def test_to_dict(self):
        """Test to_dict serialization."""
        schema = ToolSchema.from_tool_info(
            tool_name="test",
            description="Test tool",
            input_schema={
                "type": "object",
                "properties": {
                    "arg": {"type": "string"},
                },
                "required": ["arg"],
            },
        )

        d = schema.to_dict()

        assert d["tool_name"] == "test"
        assert d["description"] == "Test tool"
        assert len(d["parameters"]) == 1
        assert d["required_params"] == ["arg"]
        assert "raw_schema" in d

    def test_format_for_llm(self):
        """Test LLM-friendly formatting."""
        schema = ToolSchema.from_tool_info(
            tool_name="read_file",
            description="Read contents of a file",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "encoding": {
                        "type": "string",
                        "description": "Encoding",
                        "default": "utf-8",
                    },
                },
                "required": ["path"],
            },
        )

        formatted = schema.format_for_llm()

        assert "Tool: read_file" in formatted
        assert "Description: Read contents" in formatted
        assert "Parameters:" in formatted
        assert "path (string, required)" in formatted
        assert "encoding (string, optional)" in formatted
        assert "Default: utf-8" in formatted

    def test_format_for_llm_no_params(self):
        """Test LLM formatting with no parameters."""
        schema = ToolSchema.from_tool_info("noop", "Does nothing", {})

        formatted = schema.format_for_llm()

        assert "Parameters: None" in formatted

    def test_format_compact(self):
        """Test compact single-line format."""
        schema = ToolSchema.from_tool_info(
            tool_name="write_file",
            description="",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "append": {"type": "boolean"},
                },
                "required": ["path", "content"],
            },
        )

        formatted = schema.format_compact()

        assert formatted == "write_file(path: string, content: string, append?: boolean)"


# =============================================================================
# ToolRegistry get_schema Tests
# =============================================================================


class TestToolRegistryGetSchema:
    """Tests for ToolRegistry.get_schema()."""

    @pytest.fixture
    def mock_client(self):
        """Create mock MCP client."""
        client = AsyncMock()
        client.list_tools = AsyncMock(return_value=[
            {
                "name": "read_file",
                "description": "Read a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        ])
        return client

    @pytest.mark.asyncio
    async def test_get_schema_found(self, mock_client):
        """Test getting schema for existing tool."""
        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            state = registry._servers["test"]
            state.client = mock_client
            state.status = ServerStatus.CONNECTED

            schema = await registry.get_schema("read_file")

            assert schema is not None
            assert schema.tool_name == "read_file"
            assert schema.description == "Read a file"
            assert len(schema.parameters) == 1
            assert schema.parameters[0].name == "path"

    @pytest.mark.asyncio
    async def test_get_schema_not_found_raises(self, mock_client):
        """Test get_schema raises for missing tool."""
        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            state = registry._servers["test"]
            state.client = mock_client
            state.status = ServerStatus.CONNECTED

            with pytest.raises(ToolNotFoundError) as exc_info:
                await registry.get_schema("nonexistent")

            error = exc_info.value
            assert error.tool_name == "nonexistent"
            assert "read_file" in error.available_tools
            assert "write_file" in error.available_tools

    @pytest.mark.asyncio
    async def test_get_schema_not_found_returns_none(self, mock_client):
        """Test get_schema returns None when not raising."""
        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            state = registry._servers["test"]
            state.client = mock_client
            state.status = ServerStatus.CONNECTED

            schema = await registry.get_schema("nonexistent", raise_if_not_found=False)

            assert schema is None

    @pytest.mark.asyncio
    async def test_get_schema_with_suggestions(self, mock_client):
        """Test get_schema error includes suggestions."""
        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            state = registry._servers["test"]
            state.client = mock_client
            state.status = ServerStatus.CONNECTED

            with pytest.raises(ToolNotFoundError) as exc_info:
                await registry.get_schema("read_fil")  # Typo

            error = exc_info.value
            assert "read_file" in error.suggestions

    @pytest.mark.asyncio
    async def test_get_schemas_multiple(self, mock_client):
        """Test getting multiple schemas."""
        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            state = registry._servers["test"]
            state.client = mock_client
            state.status = ServerStatus.CONNECTED

            schemas = await registry.get_schemas(["read_file", "write_file", "missing"])

            assert len(schemas) == 2
            assert "read_file" in schemas
            assert "write_file" in schemas
            assert "missing" not in schemas

    @pytest.mark.asyncio
    async def test_get_schemas_empty_list(self, mock_client):
        """Test getting schemas with empty list."""
        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            schemas = await registry.get_schemas([])

            assert schemas == {}
