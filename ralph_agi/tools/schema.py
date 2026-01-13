"""Schema parsing and inspection for MCP tools.

Provides structured access to tool input schemas with parameter
extraction, validation, and LLM-friendly formatting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any


class ToolNotFoundError(Exception):
    """Raised when a requested tool is not found.

    Provides helpful context including similar tool names and
    the server that was searched.
    """

    def __init__(
        self,
        tool_name: str,
        available_tools: list[str] | None = None,
        server: str | None = None,
        suggestions: list[str] | None = None,
    ):
        self.tool_name = tool_name
        self.server = server
        self.available_tools = available_tools or []
        self.suggestions = suggestions or self._find_similar(tool_name, self.available_tools)

        message = f"Tool not found: '{tool_name}'"
        if server:
            message += f" on server '{server}'"
        if self.suggestions:
            message += f". Did you mean: {', '.join(self.suggestions)}?"
        elif self.available_tools:
            message += f". Available tools: {', '.join(self.available_tools[:10])}"
            if len(self.available_tools) > 10:
                message += f" (and {len(self.available_tools) - 10} more)"

        super().__init__(message)

    @staticmethod
    def _find_similar(name: str, candidates: list[str], threshold: float = 0.6) -> list[str]:
        """Find similar tool names using fuzzy matching."""
        if not candidates:
            return []

        scored = []
        name_lower = name.lower()

        for candidate in candidates:
            # Calculate similarity ratio
            ratio = SequenceMatcher(None, name_lower, candidate.lower()).ratio()

            # Boost score if name is substring
            if name_lower in candidate.lower() or candidate.lower() in name_lower:
                ratio = max(ratio, 0.7)

            if ratio >= threshold:
                scored.append((candidate, ratio))

        # Sort by score descending, return top 3
        scored.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scored[:3]]


class SchemaParseError(Exception):
    """Raised when schema parsing fails."""

    def __init__(self, message: str, schema: dict | None = None):
        super().__init__(message)
        self.schema = schema


@dataclass
class Parameter:
    """A single parameter in a tool schema.

    Attributes:
        name: Parameter name
        type: JSON Schema type (string, number, boolean, object, array)
        description: Human-readable description
        required: Whether parameter is required
        default: Default value if any
        enum: Allowed values for constrained parameters
        items_type: For array types, the type of items
        properties: For object types, nested properties
    """

    name: str
    type: str
    description: str = ""
    required: bool = False
    default: Any = None
    enum: list[str] | None = None
    items_type: str | None = None
    properties: dict[str, Parameter] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
        }
        if self.default is not None:
            d["default"] = self.default
        if self.enum:
            d["enum"] = self.enum
        if self.items_type:
            d["items_type"] = self.items_type
        if self.properties:
            d["properties"] = {k: v.to_dict() for k, v in self.properties.items()}
        return d

    def format_for_llm(self) -> str:
        """Format parameter for LLM context.

        Returns a concise string like:
        - path (string, required): File path to read
        - encoding (string, optional): File encoding. Default: utf-8. Values: utf-8, ascii
        """
        parts = [f"- {self.name} ({self.type}"]
        parts.append(", required)" if self.required else ", optional)")
        parts.append(f": {self.description}" if self.description else "")

        extras = []
        if self.default is not None:
            extras.append(f"Default: {self.default}")
        if self.enum:
            extras.append(f"Values: {', '.join(str(v) for v in self.enum)}")

        if extras:
            parts.append(f". {'. '.join(extras)}")

        return "".join(parts)


@dataclass
class ToolSchema:
    """Parsed schema for an MCP tool.

    Provides structured access to tool parameters with
    methods for validation and LLM formatting.

    Attributes:
        tool_name: Name of the tool
        description: Tool description
        parameters: List of parsed parameters
        required_params: Names of required parameters
        raw_schema: Original JSON Schema dict
    """

    tool_name: str
    description: str = ""
    parameters: list[Parameter] = field(default_factory=list)
    required_params: list[str] = field(default_factory=list)
    raw_schema: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_tool_info(
        cls,
        tool_name: str,
        description: str,
        input_schema: dict[str, Any],
    ) -> ToolSchema:
        """Create ToolSchema from tool info.

        Args:
            tool_name: Name of the tool
            description: Tool description
            input_schema: JSON Schema dict

        Returns:
            Parsed ToolSchema
        """
        required = input_schema.get("required", [])
        properties = input_schema.get("properties", {})

        parameters = []
        for name, prop_schema in properties.items():
            param = cls._parse_parameter(name, prop_schema, name in required)
            parameters.append(param)

        return cls(
            tool_name=tool_name,
            description=description,
            parameters=parameters,
            required_params=required,
            raw_schema=input_schema,
        )

    @classmethod
    def _parse_parameter(
        cls,
        name: str,
        schema: dict[str, Any],
        required: bool,
    ) -> Parameter:
        """Parse a single parameter from JSON Schema."""
        # Handle type - could be string or array
        param_type = schema.get("type", "any")
        if isinstance(param_type, list):
            # Union type - take first non-null
            param_type = next((t for t in param_type if t != "null"), "any")

        param = Parameter(
            name=name,
            type=param_type,
            description=schema.get("description", ""),
            required=required,
            default=schema.get("default"),
            enum=schema.get("enum"),
        )

        # Handle array items
        if param_type == "array" and "items" in schema:
            items = schema["items"]
            param.items_type = items.get("type", "any")

        # Handle nested object
        if param_type == "object" and "properties" in schema:
            nested_required = schema.get("required", [])
            param.properties = {
                prop_name: cls._parse_parameter(prop_name, prop_schema, prop_name in nested_required)
                for prop_name, prop_schema in schema["properties"].items()
            }

        return param

    def get_parameter(self, name: str) -> Parameter | None:
        """Get a parameter by name."""
        for param in self.parameters:
            if param.name == name:
                return param
        return None

    def get_required_parameters(self) -> list[Parameter]:
        """Get all required parameters."""
        return [p for p in self.parameters if p.required]

    def get_optional_parameters(self) -> list[Parameter]:
        """Get all optional parameters."""
        return [p for p in self.parameters if not p.required]

    def validate_arguments(self, arguments: dict[str, Any]) -> list[str]:
        """Validate arguments against schema.

        Args:
            arguments: Arguments dict to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check required parameters
        for name in self.required_params:
            if name not in arguments:
                errors.append(f"Missing required parameter: {name}")

        # Check for unknown parameters
        known_params = {p.name for p in self.parameters}
        for name in arguments:
            if name not in known_params:
                errors.append(f"Unknown parameter: {name}")

        # Basic type checking
        for param in self.parameters:
            if param.name in arguments:
                value = arguments[param.name]
                type_error = self._check_type(param, value)
                if type_error:
                    errors.append(type_error)

        return errors

    def _check_type(self, param: Parameter, value: Any) -> str | None:
        """Check if value matches expected type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        expected_type = type_map.get(param.type)
        if expected_type and not isinstance(value, expected_type):
            return f"Parameter '{param.name}' expected {param.type}, got {type(value).__name__}"

        # Check enum constraint
        if param.enum and value not in param.enum:
            return f"Parameter '{param.name}' must be one of: {', '.join(str(v) for v in param.enum)}"

        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_name": self.tool_name,
            "description": self.description,
            "parameters": [p.to_dict() for p in self.parameters],
            "required_params": self.required_params,
            "raw_schema": self.raw_schema,
        }

    def format_for_llm(self) -> str:
        """Format schema for LLM context.

        Returns a human-readable format optimized for LLM understanding:

        Tool: read_file
        Description: Read contents of a file

        Parameters:
        - path (string, required): File path to read
        - encoding (string, optional): File encoding. Default: utf-8
        """
        lines = [f"Tool: {self.tool_name}"]

        if self.description:
            lines.append(f"Description: {self.description}")

        if self.parameters:
            lines.append("")
            lines.append("Parameters:")
            for param in self.parameters:
                lines.append(param.format_for_llm())
        else:
            lines.append("")
            lines.append("Parameters: None")

        return "\n".join(lines)

    def format_compact(self) -> str:
        """Format as compact single-line for tool lists.

        Returns: read_file(path: string, encoding?: string)
        """
        params = []
        for p in self.parameters:
            suffix = "?" if not p.required else ""
            params.append(f"{p.name}{suffix}: {p.type}")

        return f"{self.tool_name}({', '.join(params)})"
