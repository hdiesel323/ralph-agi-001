"""Tests for tool execution with structured results."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ralph_agi.tools.executor import (
    ToolError,
    ToolErrorCode,
    ToolExecutionError,
    ToolExecutor,
    ToolResult,
)
from ralph_agi.tools.registry import ServerConfig, ToolInfo, ToolRegistry


# =============================================================================
# ToolErrorCode Tests
# =============================================================================


class TestToolErrorCode:
    """Tests for ToolErrorCode enum."""

    def test_all_error_codes_exist(self):
        """All expected error codes are defined."""
        assert ToolErrorCode.VALIDATION_ERROR.value == "validation_error"
        assert ToolErrorCode.TOOL_NOT_FOUND.value == "tool_not_found"
        assert ToolErrorCode.TRANSPORT_ERROR.value == "transport_error"
        assert ToolErrorCode.TOOL_ERROR.value == "tool_error"
        assert ToolErrorCode.TIMEOUT_ERROR.value == "timeout_error"
        assert ToolErrorCode.UNKNOWN_ERROR.value == "unknown_error"

    def test_error_codes_are_unique(self):
        """All error code values are unique."""
        values = [code.value for code in ToolErrorCode]
        assert len(values) == len(set(values))


# =============================================================================
# ToolError Tests
# =============================================================================


class TestToolError:
    """Tests for ToolError dataclass."""

    def test_create_simple_error(self):
        """Create error with code and message."""
        error = ToolError(
            code=ToolErrorCode.TOOL_NOT_FOUND,
            message="Tool 'foo' not found",
        )
        assert error.code == ToolErrorCode.TOOL_NOT_FOUND
        assert error.message == "Tool 'foo' not found"
        assert error.details == {}

    def test_create_error_with_details(self):
        """Create error with additional details."""
        error = ToolError(
            code=ToolErrorCode.VALIDATION_ERROR,
            message="Invalid arguments",
            details={"errors": ["missing 'path'", "invalid 'mode'"]},
        )
        assert error.details["errors"] == ["missing 'path'", "invalid 'mode'"]

    def test_to_dict(self):
        """Convert error to dictionary."""
        error = ToolError(
            code=ToolErrorCode.TIMEOUT_ERROR,
            message="Timed out after 30s",
            details={"timeout_seconds": 30},
        )
        d = error.to_dict()
        assert d["code"] == "timeout_error"
        assert d["message"] == "Timed out after 30s"
        assert d["details"]["timeout_seconds"] == 30

    def test_str_representation(self):
        """String representation includes code and message."""
        error = ToolError(
            code=ToolErrorCode.TRANSPORT_ERROR,
            message="Connection refused",
        )
        assert str(error) == "[transport_error] Connection refused"


# =============================================================================
# ToolResult Tests
# =============================================================================


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_create_success_result(self):
        """Create successful result."""
        result = ToolResult(
            tool_name="read_file",
            server="filesystem",
            arguments={"path": "/etc/hosts"},
            success=True,
            content="127.0.0.1 localhost",
            content_type="text",
            duration_ms=50,
        )
        assert result.is_success()
        assert not result.is_error()
        assert result.get_text() == "127.0.0.1 localhost"

    def test_create_error_result(self):
        """Create error result."""
        error = ToolError(
            code=ToolErrorCode.TOOL_ERROR,
            message="File not found",
        )
        result = ToolResult(
            tool_name="read_file",
            server="filesystem",
            arguments={"path": "/nonexistent"},
            success=False,
            error=error,
            duration_ms=10,
        )
        assert result.is_error()
        assert not result.is_success()
        assert result.error == error

    def test_get_text_with_none_content(self):
        """get_text returns empty string for None content."""
        result = ToolResult(
            tool_name="test",
            server="test",
            arguments={},
            success=True,
            content=None,
        )
        assert result.get_text() == ""

    def test_get_text_with_non_string(self):
        """get_text converts non-string content."""
        result = ToolResult(
            tool_name="test",
            server="test",
            arguments={},
            success=True,
            content={"key": "value"},
        )
        assert "key" in result.get_text()
        assert "value" in result.get_text()

    def test_to_dict_success(self):
        """Convert successful result to dict."""
        result = ToolResult(
            tool_name="test",
            server="srv",
            arguments={"a": 1},
            success=True,
            content="hello",
            content_type="text",
            duration_ms=100,
        )
        d = result.to_dict()
        assert d["tool_name"] == "test"
        assert d["server"] == "srv"
        assert d["arguments"] == {"a": 1}
        assert d["success"] is True
        assert d["content"] == "hello"
        assert d["content_type"] == "text"
        assert d["duration_ms"] == 100
        assert "timestamp" in d
        assert "error" not in d

    def test_to_dict_with_error(self):
        """Convert error result to dict includes error."""
        error = ToolError(code=ToolErrorCode.TOOL_ERROR, message="failed")
        result = ToolResult(
            tool_name="test",
            server="srv",
            arguments={},
            success=False,
            error=error,
        )
        d = result.to_dict()
        assert d["success"] is False
        assert "error" in d
        assert d["error"]["code"] == "tool_error"

    def test_to_dict_truncates_large_content(self):
        """Large content is truncated in dict."""
        large_content = "x" * 5000
        result = ToolResult(
            tool_name="test",
            server="srv",
            arguments={},
            success=True,
            content=large_content,
        )
        d = result.to_dict()
        assert len(d["content"]) < len(large_content)
        assert "truncated" in d["content"]
        assert d["content_length"] == 5000

    def test_timestamp_default(self):
        """Timestamp defaults to now in UTC."""
        before = datetime.now(timezone.utc)
        result = ToolResult(
            tool_name="test",
            server="srv",
            arguments={},
            success=True,
        )
        after = datetime.now(timezone.utc)
        assert before <= result.timestamp <= after


# =============================================================================
# ToolExecutionError Tests
# =============================================================================


class TestToolExecutionError:
    """Tests for ToolExecutionError exception."""

    def test_exception_with_error(self):
        """Exception message includes error details."""
        error = ToolError(code=ToolErrorCode.TOOL_ERROR, message="Not found")
        result = ToolResult(
            tool_name="my_tool",
            server="srv",
            arguments={},
            success=False,
            error=error,
        )
        exc = ToolExecutionError(result)
        assert "my_tool" in str(exc)
        assert "Not found" in str(exc)
        assert exc.result == result

    def test_exception_without_error(self):
        """Exception message works without error details."""
        result = ToolResult(
            tool_name="my_tool",
            server="srv",
            arguments={},
            success=False,
        )
        exc = ToolExecutionError(result)
        assert "my_tool" in str(exc)
        assert "failed" in str(exc)


# =============================================================================
# ToolExecutor Tests
# =============================================================================


@pytest.fixture
def mock_registry():
    """Create a mock ToolRegistry."""
    registry = MagicMock(spec=ToolRegistry)
    registry._servers = {}
    return registry


@pytest.fixture
def executor(mock_registry):
    """Create executor with mock registry."""
    return ToolExecutor(registry=mock_registry)


class TestToolExecutorInit:
    """Tests for ToolExecutor initialization."""

    def test_default_settings(self, mock_registry):
        """Default settings are applied."""
        executor = ToolExecutor(registry=mock_registry)
        assert executor._default_timeout == ToolExecutor.DEFAULT_TIMEOUT
        assert executor._validate_args is True
        assert executor._log_calls is True

    def test_custom_settings(self, mock_registry):
        """Custom settings override defaults."""
        executor = ToolExecutor(
            registry=mock_registry,
            default_timeout=60.0,
            validate_args=False,
            log_calls=False,
        )
        assert executor._default_timeout == 60.0
        assert executor._validate_args is False
        assert executor._log_calls is False


class TestToolExecutorExecute:
    """Tests for ToolExecutor.execute()."""

    @pytest.mark.asyncio
    async def test_tool_not_found(self, executor, mock_registry):
        """Returns error when tool not found."""
        mock_registry.get_tool = AsyncMock(return_value=None)

        result = await executor.execute("nonexistent", {"arg": "val"})

        assert result.is_error()
        assert result.error.code == ToolErrorCode.TOOL_NOT_FOUND
        assert "nonexistent" in result.error.message

    @pytest.mark.asyncio
    async def test_validation_error(self, executor, mock_registry):
        """Returns error when validation fails."""
        tool_info = ToolInfo(
            name="test_tool",
            description="Test",
            server="srv",
            input_schema={"type": "object", "required": ["path"]},
        )
        mock_registry.get_tool = AsyncMock(return_value=tool_info)
        mock_registry.get_schema = AsyncMock()
        mock_registry.get_schema.return_value = MagicMock()
        mock_registry.get_schema.return_value.validate_arguments = MagicMock(
            return_value=["Missing required: path"]
        )

        result = await executor.execute("test_tool", {})

        assert result.is_error()
        assert result.error.code == ToolErrorCode.VALIDATION_ERROR
        assert "Missing required: path" in result.error.details["errors"]

    @pytest.mark.asyncio
    async def test_validation_skipped(self, mock_registry):
        """Validation can be skipped."""
        executor = ToolExecutor(registry=mock_registry, validate_args=False)
        tool_info = ToolInfo(name="test", description="Test", server="srv")
        mock_registry.get_tool = AsyncMock(return_value=tool_info)

        # Mock server state
        mock_state = MagicMock()
        mock_state.client = MagicMock()
        mock_state.client.call_tool = AsyncMock(
            return_value={"content": [{"type": "text", "text": "ok"}]}
        )
        mock_registry._servers = {"srv": mock_state}

        result = await executor.execute("test", {}, validate=False)

        # Validation not called
        mock_registry.get_schema.assert_not_called() if hasattr(mock_registry, 'get_schema') else None
        assert result.is_success()

    @pytest.mark.asyncio
    async def test_successful_execution(self, executor, mock_registry):
        """Successful tool execution returns content."""
        tool_info = ToolInfo(name="echo", description="Echo", server="test-srv")
        mock_registry.get_tool = AsyncMock(return_value=tool_info)
        mock_registry.get_schema = AsyncMock(return_value=None)

        # Mock server state with client
        mock_state = MagicMock()
        mock_state.client = MagicMock()
        mock_state.client.call_tool = AsyncMock(
            return_value={"content": [{"type": "text", "text": "Hello World"}]}
        )
        mock_registry._servers = {"test-srv": mock_state}

        result = await executor.execute("echo", {"message": "Hello World"})

        assert result.is_success()
        assert result.content == "Hello World"
        assert result.tool_name == "echo"
        assert result.server == "test-srv"
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_server_not_connected_reconnects(self, executor, mock_registry):
        """Reconnects to server if not connected."""
        tool_info = ToolInfo(name="test", description="Test", server="srv")
        mock_registry.get_tool = AsyncMock(return_value=tool_info)
        mock_registry.get_schema = AsyncMock(return_value=None)
        mock_registry._servers = {}  # No server connected

        # Mock connect_server to add server state
        async def mock_connect(name):
            mock_state = MagicMock()
            mock_state.client = MagicMock()
            mock_state.client.call_tool = AsyncMock(
                return_value={"content": [{"type": "text", "text": "connected"}]}
            )
            mock_registry._servers[name] = mock_state
            return True

        mock_registry.connect_server = AsyncMock(side_effect=mock_connect)

        result = await executor.execute("test", {})

        mock_registry.connect_server.assert_called_once_with("srv")
        assert result.is_success()

    @pytest.mark.asyncio
    async def test_server_connection_fails(self, mock_registry):
        """Returns transport error if connection fails."""
        executor = ToolExecutor(registry=mock_registry, validate_args=False)
        tool_info = ToolInfo(name="test", description="Test", server="srv")
        mock_registry.get_tool = AsyncMock(return_value=tool_info)
        mock_registry._servers = {}
        mock_registry.connect_server = AsyncMock(return_value=False)

        result = await executor.execute("test", {})

        assert result.is_error()
        assert result.error.code == ToolErrorCode.TRANSPORT_ERROR
        assert "Cannot connect" in result.error.message

    @pytest.mark.asyncio
    async def test_timeout_error(self, executor, mock_registry):
        """Returns timeout error when execution times out."""
        tool_info = ToolInfo(name="slow", description="Slow", server="srv")
        mock_registry.get_tool = AsyncMock(return_value=tool_info)
        mock_registry.get_schema = AsyncMock(return_value=None)

        # Mock slow execution
        async def slow_call(*args, **kwargs):
            await asyncio.sleep(10)  # Very slow
            return {}

        mock_state = MagicMock()
        mock_state.client = MagicMock()
        mock_state.client.call_tool = slow_call
        mock_registry._servers = {"srv": mock_state}

        result = await executor.execute("slow", {}, timeout=0.01)

        assert result.is_error()
        assert result.error.code == ToolErrorCode.TIMEOUT_ERROR
        assert "0.01" in result.error.message

    @pytest.mark.asyncio
    async def test_tool_returns_error(self, executor, mock_registry):
        """Handles tool returning isError=True."""
        tool_info = ToolInfo(name="fail", description="Fails", server="srv")
        mock_registry.get_tool = AsyncMock(return_value=tool_info)
        mock_registry.get_schema = AsyncMock(return_value=None)

        mock_state = MagicMock()
        mock_state.client = MagicMock()
        mock_state.client.call_tool = AsyncMock(
            return_value={
                "isError": True,
                "content": [{"type": "text", "text": "Access denied"}],
            }
        )
        mock_registry._servers = {"srv": mock_state}

        result = await executor.execute("fail", {})

        assert result.is_error()
        assert result.error.code == ToolErrorCode.TOOL_ERROR
        assert "Access denied" in result.error.message

    @pytest.mark.asyncio
    async def test_transport_exception(self, executor, mock_registry):
        """Transport errors are caught and returned."""
        tool_info = ToolInfo(name="test", description="Test", server="srv")
        mock_registry.get_tool = AsyncMock(return_value=tool_info)
        mock_registry.get_schema = AsyncMock(return_value=None)

        mock_state = MagicMock()
        mock_state.client = MagicMock()
        mock_state.client.call_tool = AsyncMock(
            side_effect=ConnectionError("Pipe broken")
        )
        mock_registry._servers = {"srv": mock_state}

        result = await executor.execute("test", {})

        assert result.is_error()
        assert result.error.code == ToolErrorCode.TRANSPORT_ERROR
        assert "Pipe broken" in result.error.message

    @pytest.mark.asyncio
    async def test_unexpected_exception(self, executor, mock_registry):
        """Unexpected exceptions are caught."""
        mock_registry.get_tool = AsyncMock(side_effect=RuntimeError("Unexpected"))

        result = await executor.execute("test", {})

        assert result.is_error()
        assert result.error.code == ToolErrorCode.UNKNOWN_ERROR
        assert "Unexpected" in result.error.message

    @pytest.mark.asyncio
    async def test_arguments_default_to_empty_dict(self, executor, mock_registry):
        """Arguments default to empty dict if None."""
        tool_info = ToolInfo(name="test", description="Test", server="srv")
        mock_registry.get_tool = AsyncMock(return_value=tool_info)
        mock_registry.get_schema = AsyncMock(return_value=None)

        mock_state = MagicMock()
        mock_state.client = MagicMock()
        mock_state.client.call_tool = AsyncMock(
            return_value={"content": [{"type": "text", "text": "ok"}]}
        )
        mock_registry._servers = {"srv": mock_state}

        result = await executor.execute("test")

        assert result.arguments == {}
        mock_state.client.call_tool.assert_called_once_with("test", {})


class TestToolExecutorBatch:
    """Tests for ToolExecutor.execute_batch()."""

    @pytest.mark.asyncio
    async def test_batch_execution(self, mock_registry):
        """Execute multiple tools in parallel."""
        executor = ToolExecutor(registry=mock_registry, log_calls=False)

        # Setup tools
        tool_a = ToolInfo(name="tool_a", description="A", server="srv")
        tool_b = ToolInfo(name="tool_b", description="B", server="srv")

        async def get_tool(name):
            return {"tool_a": tool_a, "tool_b": tool_b}.get(name)

        mock_registry.get_tool = AsyncMock(side_effect=get_tool)
        mock_registry.get_schema = AsyncMock(return_value=None)

        # Mock server
        call_count = 0

        async def mock_call(name, args):
            nonlocal call_count
            call_count += 1
            return {"content": [{"type": "text", "text": f"result_{name}"}]}

        mock_state = MagicMock()
        mock_state.client = MagicMock()
        mock_state.client.call_tool = mock_call
        mock_registry._servers = {"srv": mock_state}

        # Execute batch
        calls = [
            ("tool_a", {"x": 1}),
            ("tool_b", {"y": 2}),
        ]
        results = await executor.execute_batch(calls)

        assert len(results) == 2
        assert results[0].tool_name == "tool_a"
        assert results[1].tool_name == "tool_b"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_batch_preserves_order(self, mock_registry):
        """Results maintain order of calls."""
        executor = ToolExecutor(registry=mock_registry, log_calls=False)

        tools = {f"tool_{i}": ToolInfo(name=f"tool_{i}", description=f"Tool {i}", server="srv") for i in range(5)}
        mock_registry.get_tool = AsyncMock(side_effect=lambda n: tools.get(n))
        mock_registry.get_schema = AsyncMock(return_value=None)

        async def mock_call(name, args):
            # Add varying delays
            await asyncio.sleep(0.01 * (5 - int(name[-1])))  # Later tools finish first
            return {"content": [{"type": "text", "text": name}]}

        mock_state = MagicMock()
        mock_state.client = MagicMock()
        mock_state.client.call_tool = mock_call
        mock_registry._servers = {"srv": mock_state}

        calls = [(f"tool_{i}", {}) for i in range(5)]
        results = await executor.execute_batch(calls)

        # Order preserved despite different completion times
        for i, result in enumerate(results):
            assert result.tool_name == f"tool_{i}"

    @pytest.mark.asyncio
    async def test_batch_with_failures(self, mock_registry):
        """Batch handles individual failures."""
        executor = ToolExecutor(registry=mock_registry, log_calls=False)

        tool_good = ToolInfo(name="good", description="Good", server="srv")
        mock_registry.get_tool = AsyncMock(
            side_effect=lambda n: tool_good if n == "good" else None
        )
        mock_registry.get_schema = AsyncMock(return_value=None)

        mock_state = MagicMock()
        mock_state.client = MagicMock()
        mock_state.client.call_tool = AsyncMock(
            return_value={"content": [{"type": "text", "text": "ok"}]}
        )
        mock_registry._servers = {"srv": mock_state}

        calls = [
            ("good", {}),
            ("bad", {}),  # Not found
            ("good", {}),
        ]
        results = await executor.execute_batch(calls)

        assert len(results) == 3
        assert results[0].is_success()
        assert results[1].is_error()
        assert results[1].error.code == ToolErrorCode.TOOL_NOT_FOUND
        assert results[2].is_success()


class TestToolExecutorParsing:
    """Tests for MCP result parsing."""

    @pytest.fixture
    def executor_with_mock(self, mock_registry):
        """Executor with server mock ready."""
        executor = ToolExecutor(registry=mock_registry, log_calls=False)
        tool_info = ToolInfo(name="test", description="Test", server="srv")
        mock_registry.get_tool = AsyncMock(return_value=tool_info)
        mock_registry.get_schema = AsyncMock(return_value=None)

        mock_state = MagicMock()
        mock_state.client = MagicMock()
        mock_registry._servers = {"srv": mock_state}

        return executor, mock_state

    @pytest.mark.asyncio
    async def test_parse_text_content(self, executor_with_mock):
        """Parse single text content item."""
        executor, mock_state = executor_with_mock
        mock_state.client.call_tool = AsyncMock(
            return_value={"content": [{"type": "text", "text": "Hello"}]}
        )

        result = await executor.execute("test", {})

        assert result.content == "Hello"
        assert result.content_type == "text"

    @pytest.mark.asyncio
    async def test_parse_image_content(self, executor_with_mock):
        """Parse image content item."""
        executor, mock_state = executor_with_mock
        mock_state.client.call_tool = AsyncMock(
            return_value={"content": [{"type": "image", "data": "base64data..."}]}
        )

        result = await executor.execute("test", {})

        assert result.content == "base64data..."
        assert result.content_type == "image"

    @pytest.mark.asyncio
    async def test_parse_multiple_text_items(self, executor_with_mock):
        """Multiple text items are joined."""
        executor, mock_state = executor_with_mock
        mock_state.client.call_tool = AsyncMock(
            return_value={
                "content": [
                    {"type": "text", "text": "Line 1"},
                    {"type": "text", "text": "Line 2"},
                    {"type": "text", "text": "Line 3"},
                ]
            }
        )

        result = await executor.execute("test", {})

        assert "Line 1" in result.content
        assert "Line 2" in result.content
        assert "Line 3" in result.content

    @pytest.mark.asyncio
    async def test_parse_empty_content(self, executor_with_mock):
        """Empty content array returns None."""
        executor, mock_state = executor_with_mock
        mock_state.client.call_tool = AsyncMock(return_value={"content": []})

        result = await executor.execute("test", {})

        assert result.content is None
        assert result.is_success()

    @pytest.mark.asyncio
    async def test_parse_unknown_content_type(self, executor_with_mock):
        """Unknown content type returns full item."""
        executor, mock_state = executor_with_mock
        mock_state.client.call_tool = AsyncMock(
            return_value={"content": [{"type": "custom", "data": {"key": "val"}}]}
        )

        result = await executor.execute("test", {})

        assert result.content["type"] == "custom"
        assert result.content["data"]["key"] == "val"


class TestToolExecutorLogging:
    """Tests for tool call logging."""

    @pytest.mark.asyncio
    async def test_logging_enabled(self, mock_registry, caplog):
        """Logs tool calls when enabled."""
        import logging

        executor = ToolExecutor(registry=mock_registry, log_calls=True)
        mock_registry.get_tool = AsyncMock(return_value=None)

        with caplog.at_level(logging.INFO, logger="ralph_agi.tools.executor"):
            await executor.execute("test_tool", {"arg": "val"})

        assert "TOOL_CALL" in caplog.text
        assert "test_tool" in caplog.text

    @pytest.mark.asyncio
    async def test_logging_disabled(self, mock_registry, caplog):
        """No logs when disabled."""
        import logging

        executor = ToolExecutor(registry=mock_registry, log_calls=False)
        mock_registry.get_tool = AsyncMock(return_value=None)

        with caplog.at_level(logging.INFO, logger="ralph_agi.tools.executor"):
            await executor.execute("test_tool", {"arg": "val"})

        assert "TOOL_CALL" not in caplog.text

    @pytest.mark.asyncio
    async def test_sensitive_args_redacted(self, mock_registry, caplog):
        """Sensitive arguments are redacted in logs."""
        import logging

        executor = ToolExecutor(registry=mock_registry, log_calls=True)
        mock_registry.get_tool = AsyncMock(return_value=None)

        with caplog.at_level(logging.INFO, logger="ralph_agi.tools.executor"):
            await executor.execute(
                "test_tool",
                {
                    "path": "/etc/hosts",
                    "password": "secret123",
                    "api_key": "key-xyz",
                    "normal": "visible",
                },
            )

        assert "secret123" not in caplog.text
        assert "key-xyz" not in caplog.text
        assert "REDACTED" in caplog.text
        assert "visible" in caplog.text


class TestToolExecutorRedaction:
    """Tests for sensitive argument redaction."""

    def test_redact_sensitive_keys(self, executor):
        """Sensitive keys are redacted."""
        args = {
            "password": "secret",
            "api_key": "key123",
            "token": "tok456",
            "auth": "auth789",
            "secret_value": "hidden",
            "privatekey": "pk",
            "credential": "cred",
        }
        redacted = executor._redact_sensitive(args)

        for key in args:
            assert redacted[key] == "***REDACTED***"

    def test_keep_non_sensitive_keys(self, executor):
        """Non-sensitive keys are preserved."""
        args = {
            "path": "/etc/hosts",
            "mode": "read",
            "count": 10,
        }
        redacted = executor._redact_sensitive(args)

        assert redacted == args

    def test_redact_nested_sensitive(self, executor):
        """Nested sensitive values are redacted."""
        args = {
            "config": {
                "api_key": "nested_key",
                "url": "https://example.com",
            },
            "name": "test",
        }
        redacted = executor._redact_sensitive(args)

        assert redacted["config"]["api_key"] == "***REDACTED***"
        assert redacted["config"]["url"] == "https://example.com"
        assert redacted["name"] == "test"

    def test_case_insensitive_redaction(self, executor):
        """Redaction is case-insensitive."""
        args = {
            "PASSWORD": "secret1",
            "Api_Key": "secret2",
            "TOKEN": "secret3",
        }
        redacted = executor._redact_sensitive(args)

        for key in args:
            assert redacted[key] == "***REDACTED***"
