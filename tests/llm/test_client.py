"""Tests for LLM client interface and data structures."""

from __future__ import annotations

import pytest

from ralph_agi.llm.client import (
    AuthenticationError,
    ContextLengthError,
    InvalidRequestError,
    LLMError,
    LLMResponse,
    Message,
    ModelNotFoundError,
    RateLimitError,
    StopReason,
    Tool,
    ToolCall,
    create_tool_result_message,
)


class TestStopReason:
    """Tests for StopReason enum."""

    def test_stop_reason_values(self) -> None:
        """Test all stop reason values exist."""
        assert StopReason.END_TURN.value == "end_turn"
        assert StopReason.TOOL_USE.value == "tool_use"
        assert StopReason.MAX_TOKENS.value == "max_tokens"
        assert StopReason.STOP_SEQUENCE.value == "stop_sequence"
        assert StopReason.CONTENT_FILTER.value == "content_filter"

    def test_stop_reason_from_string(self) -> None:
        """Test creating stop reason from string."""
        assert StopReason("end_turn") == StopReason.END_TURN
        assert StopReason("tool_use") == StopReason.TOOL_USE


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_tool_call_creation(self) -> None:
        """Test creating a tool call."""
        tool_call = ToolCall(
            id="tc_123",
            name="read_file",
            arguments={"path": "/test.txt"},
        )

        assert tool_call.id == "tc_123"
        assert tool_call.name == "read_file"
        assert tool_call.arguments == {"path": "/test.txt"}

    def test_tool_call_immutable(self) -> None:
        """Test that tool call is frozen."""
        tool_call = ToolCall(id="tc_1", name="test", arguments={})

        with pytest.raises(AttributeError):
            tool_call.id = "tc_2"  # type: ignore

    def test_tool_call_with_complex_arguments(self) -> None:
        """Test tool call with nested arguments."""
        tool_call = ToolCall(
            id="tc_456",
            name="write_file",
            arguments={
                "path": "/output.json",
                "content": {"key": "value", "list": [1, 2, 3]},
                "options": {"atomic": True},
            },
        )

        assert tool_call.arguments["content"]["key"] == "value"
        assert tool_call.arguments["options"]["atomic"] is True


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_basic_response(self) -> None:
        """Test creating a basic response."""
        response = LLMResponse(
            content="Hello, world!",
            stop_reason=StopReason.END_TURN,
        )

        assert response.content == "Hello, world!"
        assert response.stop_reason == StopReason.END_TURN
        assert response.tool_calls == []
        assert response.has_tool_calls is False

    def test_response_with_tool_calls(self) -> None:
        """Test response with tool calls."""
        tool_call = ToolCall(id="tc_1", name="test", arguments={})
        response = LLMResponse(
            content="I need to use a tool.",
            stop_reason=StopReason.TOOL_USE,
            tool_calls=[tool_call],
        )

        assert response.has_tool_calls is True
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "test"

    def test_response_token_counts(self) -> None:
        """Test token count properties."""
        response = LLMResponse(
            content="Test",
            stop_reason=StopReason.END_TURN,
            usage={"input_tokens": 100, "output_tokens": 50},
        )

        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.total_tokens == 150

    def test_response_empty_usage(self) -> None:
        """Test token counts with empty usage."""
        response = LLMResponse(
            content="Test",
            stop_reason=StopReason.END_TURN,
        )

        assert response.input_tokens == 0
        assert response.output_tokens == 0
        assert response.total_tokens == 0

    def test_response_with_model(self) -> None:
        """Test response with model info."""
        response = LLMResponse(
            content="Test",
            stop_reason=StopReason.END_TURN,
            model="claude-sonnet-4-20250514",
        )

        assert response.model == "claude-sonnet-4-20250514"

    def test_response_with_raw_response(self) -> None:
        """Test response preserves raw response."""
        raw = {"id": "msg_123", "type": "message"}
        response = LLMResponse(
            content="Test",
            stop_reason=StopReason.END_TURN,
            raw_response=raw,
        )

        assert response.raw_response == raw


class TestTool:
    """Tests for Tool dataclass."""

    def test_tool_creation(self) -> None:
        """Test creating a tool definition."""
        tool = Tool(
            name="read_file",
            description="Read contents of a file",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
        )

        assert tool.name == "read_file"
        assert tool.description == "Read contents of a file"
        assert tool.input_schema["type"] == "object"

    def test_tool_immutable(self) -> None:
        """Test that tool is frozen."""
        tool = Tool(name="test", description="test", input_schema={})

        with pytest.raises(AttributeError):
            tool.name = "other"  # type: ignore


class TestMessage:
    """Tests for Message dataclass."""

    def test_user_message(self) -> None:
        """Test creating a user message."""
        msg = Message(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_assistant_message(self) -> None:
        """Test creating an assistant message."""
        msg = Message(role="assistant", content="Hi there!")

        assert msg.role == "assistant"
        assert msg.content == "Hi there!"

    def test_message_with_structured_content(self) -> None:
        """Test message with structured content."""
        content = [
            {"type": "text", "text": "Hello"},
            {"type": "tool_use", "id": "tc_1", "name": "test"},
        ]
        msg = Message(role="assistant", content=content)

        assert msg.content == content
        assert len(msg.content) == 2


class TestLLMErrors:
    """Tests for LLM error classes."""

    def test_base_error(self) -> None:
        """Test base LLM error."""
        error = LLMError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.retryable is False
        assert error.status_code is None

    def test_base_error_with_options(self) -> None:
        """Test base error with all options."""
        error = LLMError("Server error", retryable=True, status_code=500)

        assert error.retryable is True
        assert error.status_code == 500

    def test_rate_limit_error(self) -> None:
        """Test rate limit error."""
        error = RateLimitError("Too many requests", retry_after=30.0)

        assert error.retryable is True
        assert error.status_code == 429
        assert error.retry_after == 30.0

    def test_rate_limit_error_no_retry_after(self) -> None:
        """Test rate limit error without retry_after."""
        error = RateLimitError("Too many requests")

        assert error.retry_after is None

    def test_authentication_error(self) -> None:
        """Test authentication error."""
        error = AuthenticationError("Invalid API key")

        assert error.retryable is False
        assert error.status_code == 401

    def test_invalid_request_error(self) -> None:
        """Test invalid request error."""
        error = InvalidRequestError("Bad parameter")

        assert error.retryable is False
        assert error.status_code == 400

    def test_model_not_found_error(self) -> None:
        """Test model not found error."""
        error = ModelNotFoundError("Model does not exist")

        assert error.retryable is False
        assert error.status_code == 404

    def test_context_length_error(self) -> None:
        """Test context length error."""
        error = ContextLengthError("Context too long")

        assert error.retryable is False
        assert error.status_code == 400


class TestCreateToolResultMessage:
    """Tests for create_tool_result_message helper."""

    def test_success_result(self) -> None:
        """Test creating a success result message."""
        msg = create_tool_result_message(
            tool_call_id="tc_123",
            result="File contents here",
        )

        assert msg["type"] == "tool_result"
        assert msg["tool_use_id"] == "tc_123"
        assert msg["content"] == "File contents here"
        assert msg["is_error"] is False

    def test_error_result(self) -> None:
        """Test creating an error result message."""
        msg = create_tool_result_message(
            tool_call_id="tc_456",
            result="File not found",
            is_error=True,
        )

        assert msg["is_error"] is True
        assert msg["content"] == "File not found"
