"""Tool execution with structured results and logging.

Provides a high-level API for executing MCP tools with argument
validation, error handling, timeout support, and structured logging.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ralph_agi.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolErrorCode(Enum):
    """Categories of tool execution errors."""

    VALIDATION_ERROR = "validation_error"  # Invalid arguments
    TOOL_NOT_FOUND = "tool_not_found"  # Tool doesn't exist
    TRANSPORT_ERROR = "transport_error"  # Network/subprocess failure
    TOOL_ERROR = "tool_error"  # Tool returned error
    TIMEOUT_ERROR = "timeout_error"  # Operation timed out
    UNKNOWN_ERROR = "unknown_error"  # Unexpected failure


@dataclass
class ToolError:
    """Structured error from tool execution.

    Attributes:
        code: Error category
        message: Human-readable error message
        details: Additional error context
    """

    code: ToolErrorCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }

    def __str__(self) -> str:
        return f"[{self.code.value}] {self.message}"


@dataclass
class ToolResult:
    """Structured result from tool execution.

    Attributes:
        tool_name: Name of the executed tool
        server: MCP server that executed the tool
        arguments: Arguments passed to the tool
        success: Whether execution succeeded
        content: Result content (if successful)
        content_type: Type of content (text, image, etc.)
        error: Error details (if failed)
        duration_ms: Execution time in milliseconds
        timestamp: When execution started
    """

    tool_name: str
    server: str
    arguments: dict[str, Any]
    success: bool
    content: Any = None
    content_type: str = "text"
    error: ToolError | None = None
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.success and self.error is None

    def is_error(self) -> bool:
        """Check if execution failed."""
        return not self.success or self.error is not None

    def get_text(self) -> str:
        """Get content as text.

        Returns:
            Content as string, or empty string if no content
        """
        if self.content is None:
            return ""
        if isinstance(self.content, str):
            return self.content
        return str(self.content)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        d = {
            "tool_name": self.tool_name,
            "server": self.server,
            "arguments": self.arguments,
            "success": self.success,
            "content_type": self.content_type,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.content is not None:
            # Truncate large content for logging
            content_str = str(self.content)
            if len(content_str) > 1000:
                d["content"] = content_str[:1000] + "... (truncated)"
                d["content_length"] = len(content_str)
            else:
                d["content"] = self.content
        if self.error:
            d["error"] = self.error.to_dict()
        return d


class ToolExecutionError(Exception):
    """Exception raised during tool execution."""

    def __init__(self, result: ToolResult):
        self.result = result
        message = f"Tool '{result.tool_name}' failed"
        if result.error:
            message += f": {result.error.message}"
        super().__init__(message)


class ToolExecutor:
    """High-level executor for MCP tools.

    Provides argument validation, error handling, timeout support,
    and structured logging for tool execution.

    Usage:
        executor = ToolExecutor(registry)

        # Execute single tool
        result = await executor.execute("read_file", {"path": "/etc/hosts"})
        if result.is_success():
            print(result.content)

        # Execute with timeout
        result = await executor.execute("slow_tool", args, timeout=60)

        # Execute with validation
        result = await executor.execute("tool", args, validate=True)
    """

    # Default timeout in seconds
    DEFAULT_TIMEOUT = 30.0

    def __init__(
        self,
        registry: ToolRegistry,
        default_timeout: float = DEFAULT_TIMEOUT,
        validate_args: bool = True,
        log_calls: bool = True,
    ):
        """Initialize executor.

        Args:
            registry: ToolRegistry for tool discovery and server access
            default_timeout: Default timeout for operations
            validate_args: Whether to validate arguments against schema
            log_calls: Whether to log all tool calls
        """
        self._registry = registry
        self._default_timeout = default_timeout
        self._validate_args = validate_args
        self._log_calls = log_calls

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        timeout: float | None = None,
        validate: bool | None = None,
    ) -> ToolResult:
        """Execute a tool with arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments (empty dict if None)
            timeout: Optional timeout override
            validate: Optional validation override

        Returns:
            ToolResult with success/error status and content
        """
        arguments = arguments or {}
        timeout = timeout if timeout is not None else self._default_timeout
        validate = validate if validate is not None else self._validate_args

        start_time = time.time()
        timestamp = datetime.now(timezone.utc)

        # Log execution start
        if self._log_calls:
            self._log_start(tool_name, arguments)

        try:
            # Get tool info
            tool = await self._registry.get_tool(tool_name)
            if tool is None:
                return self._make_error_result(
                    tool_name=tool_name,
                    server="unknown",
                    arguments=arguments,
                    error=ToolError(
                        code=ToolErrorCode.TOOL_NOT_FOUND,
                        message=f"Tool not found: {tool_name}",
                    ),
                    start_time=start_time,
                    timestamp=timestamp,
                )

            server_name = tool.server

            # Validate arguments
            if validate:
                validation_errors = await self._validate_arguments(tool_name, arguments)
                if validation_errors:
                    return self._make_error_result(
                        tool_name=tool_name,
                        server=server_name,
                        arguments=arguments,
                        error=ToolError(
                            code=ToolErrorCode.VALIDATION_ERROR,
                            message="Argument validation failed",
                            details={"errors": validation_errors},
                        ),
                        start_time=start_time,
                        timestamp=timestamp,
                    )

            # Execute with timeout
            result = await self._execute_with_timeout(
                tool_name=tool_name,
                server=server_name,
                arguments=arguments,
                timeout=timeout,
                start_time=start_time,
                timestamp=timestamp,
            )

            # Log result
            if self._log_calls:
                self._log_result(result)

            return result

        except Exception as e:
            # Catch any unexpected errors
            error_result = self._make_error_result(
                tool_name=tool_name,
                server="unknown",
                arguments=arguments,
                error=ToolError(
                    code=ToolErrorCode.UNKNOWN_ERROR,
                    message=str(e),
                    details={"exception_type": type(e).__name__},
                ),
                start_time=start_time,
                timestamp=timestamp,
            )

            if self._log_calls:
                self._log_result(error_result)

            return error_result

    async def _validate_arguments(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> list[str]:
        """Validate arguments against tool schema."""
        try:
            schema = await self._registry.get_schema(tool_name, raise_if_not_found=False)
            if schema is None:
                return []  # No schema, skip validation
            return schema.validate_arguments(arguments)
        except Exception as e:
            logger.warning(f"Error validating arguments for {tool_name}: {e}")
            return []  # Don't fail on validation errors

    async def _execute_with_timeout(
        self,
        tool_name: str,
        server: str,
        arguments: dict[str, Any],
        timeout: float,
        start_time: float,
        timestamp: datetime,
    ) -> ToolResult:
        """Execute tool with timeout handling."""
        try:
            # Get server state
            state = self._registry._servers.get(server)
            if state is None or state.client is None:
                # Try to connect
                connected = await self._registry.connect_server(server)
                if not connected:
                    return self._make_error_result(
                        tool_name=tool_name,
                        server=server,
                        arguments=arguments,
                        error=ToolError(
                            code=ToolErrorCode.TRANSPORT_ERROR,
                            message=f"Cannot connect to server: {server}",
                        ),
                        start_time=start_time,
                        timestamp=timestamp,
                    )
                state = self._registry._servers.get(server)

            # Execute tool
            raw_result = await asyncio.wait_for(
                state.client.call_tool(tool_name, arguments),
                timeout=timeout,
            )

            # Parse result
            return self._parse_mcp_result(
                tool_name=tool_name,
                server=server,
                arguments=arguments,
                raw_result=raw_result,
                start_time=start_time,
                timestamp=timestamp,
            )

        except asyncio.TimeoutError:
            return self._make_error_result(
                tool_name=tool_name,
                server=server,
                arguments=arguments,
                error=ToolError(
                    code=ToolErrorCode.TIMEOUT_ERROR,
                    message=f"Tool execution timed out after {timeout}s",
                    details={"timeout_seconds": timeout},
                ),
                start_time=start_time,
                timestamp=timestamp,
            )

        except Exception as e:
            return self._make_error_result(
                tool_name=tool_name,
                server=server,
                arguments=arguments,
                error=ToolError(
                    code=ToolErrorCode.TRANSPORT_ERROR,
                    message=str(e),
                    details={"exception_type": type(e).__name__},
                ),
                start_time=start_time,
                timestamp=timestamp,
            )

    def _parse_mcp_result(
        self,
        tool_name: str,
        server: str,
        arguments: dict[str, Any],
        raw_result: dict[str, Any],
        start_time: float,
        timestamp: datetime,
    ) -> ToolResult:
        """Parse MCP tool result into ToolResult."""
        duration_ms = int((time.time() - start_time) * 1000)

        # Check for error in result
        if raw_result.get("isError"):
            error_content = raw_result.get("content", [])
            error_message = "Tool returned error"
            if error_content and len(error_content) > 0:
                first_content = error_content[0]
                if isinstance(first_content, dict):
                    error_message = first_content.get("text", error_message)

            return ToolResult(
                tool_name=tool_name,
                server=server,
                arguments=arguments,
                success=False,
                error=ToolError(
                    code=ToolErrorCode.TOOL_ERROR,
                    message=error_message,
                    details={"raw_result": raw_result},
                ),
                duration_ms=duration_ms,
                timestamp=timestamp,
            )

        # Extract content
        content = None
        content_type = "text"

        raw_content = raw_result.get("content", [])
        if raw_content:
            # Handle array of content items
            if isinstance(raw_content, list) and len(raw_content) > 0:
                first_item = raw_content[0]
                if isinstance(first_item, dict):
                    content_type = first_item.get("type", "text")
                    if content_type == "text":
                        content = first_item.get("text", "")
                    elif content_type == "image":
                        content = first_item.get("data", "")
                    else:
                        content = first_item
                else:
                    content = first_item

                # If multiple content items, combine text items
                if len(raw_content) > 1:
                    text_parts = []
                    for item in raw_content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                    if text_parts:
                        content = "\n".join(text_parts)
            else:
                content = raw_content

        return ToolResult(
            tool_name=tool_name,
            server=server,
            arguments=arguments,
            success=True,
            content=content,
            content_type=content_type,
            duration_ms=duration_ms,
            timestamp=timestamp,
        )

    def _make_error_result(
        self,
        tool_name: str,
        server: str,
        arguments: dict[str, Any],
        error: ToolError,
        start_time: float,
        timestamp: datetime,
    ) -> ToolResult:
        """Create error ToolResult."""
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolResult(
            tool_name=tool_name,
            server=server,
            arguments=arguments,
            success=False,
            error=error,
            duration_ms=duration_ms,
            timestamp=timestamp,
        )

    def _log_start(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Log tool execution start."""
        # Redact potentially sensitive arguments
        safe_args = self._redact_sensitive(arguments)
        logger.info(f"TOOL_CALL tool={tool_name} args={safe_args}")

    def _log_result(self, result: ToolResult) -> None:
        """Log tool execution result."""
        if result.is_success():
            content_preview = ""
            if result.content:
                content_str = str(result.content)
                if len(content_str) > 100:
                    content_preview = f" preview={content_str[:100]!r}..."
                else:
                    content_preview = f" content={content_str!r}"
            logger.info(
                f"TOOL_SUCCESS tool={result.tool_name} "
                f"duration={result.duration_ms}ms{content_preview}"
            )
        else:
            error_msg = str(result.error) if result.error else "Unknown error"
            logger.warning(
                f"TOOL_FAILED tool={result.tool_name} "
                f"duration={result.duration_ms}ms error={error_msg}"
            )

    def _redact_sensitive(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Redact potentially sensitive values from arguments."""
        sensitive_keys = {
            "password", "secret", "token", "api_key", "apikey",
            "auth", "credential", "private_key", "privatekey",
        }

        redacted = {}
        for key, value in arguments.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                redacted[key] = "***REDACTED***"
            elif isinstance(value, dict):
                redacted[key] = self._redact_sensitive(value)
            else:
                redacted[key] = value
        return redacted

    async def execute_batch(
        self,
        calls: list[tuple[str, dict[str, Any]]],
        timeout: float | None = None,
    ) -> list[ToolResult]:
        """Execute multiple tools in parallel.

        Args:
            calls: List of (tool_name, arguments) tuples
            timeout: Optional timeout for each call

        Returns:
            List of ToolResults in same order as calls
        """
        tasks = [
            self.execute(name, args, timeout=timeout)
            for name, args in calls
        ]
        return await asyncio.gather(*tasks)
