"""Tests for Anthropic Claude client."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ralph_agi.llm.anthropic import AnthropicClient
from ralph_agi.llm.client import (
    AuthenticationError,
    ContextLengthError,
    InvalidRequestError,
    LLMError,
    ModelNotFoundError,
    RateLimitError,
    StopReason,
    Tool,
)


class TestAnthropicClientInit:
    """Tests for AnthropicClient initialization."""

    def test_default_init(self) -> None:
        """Test default initialization."""
        client = AnthropicClient()

        assert client.model == AnthropicClient.DEFAULT_MODEL
        assert client.timeout == 120.0
        assert client._client is None  # Lazy init

    def test_custom_model(self) -> None:
        """Test custom model selection."""
        client = AnthropicClient(model="claude-opus-4-20250514")

        assert client.model == "claude-opus-4-20250514"

    def test_custom_timeout(self) -> None:
        """Test custom timeout."""
        client = AnthropicClient(timeout=60.0)

        assert client.timeout == 60.0

    def test_custom_base_url(self) -> None:
        """Test custom base URL."""
        client = AnthropicClient(base_url="https://proxy.example.com")

        assert client._base_url == "https://proxy.example.com"


class TestConvertTools:
    """Tests for tool conversion."""

    def test_convert_single_tool(self) -> None:
        """Test converting a single tool."""
        client = AnthropicClient()
        tool = Tool(
            name="read_file",
            description="Read file contents",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        )

        result = client._convert_tools([tool])

        assert len(result) == 1
        assert result[0]["name"] == "read_file"
        assert result[0]["description"] == "Read file contents"
        assert result[0]["input_schema"]["type"] == "object"

    def test_convert_multiple_tools(self) -> None:
        """Test converting multiple tools."""
        client = AnthropicClient()
        tools = [
            Tool(name="tool1", description="First tool", input_schema={}),
            Tool(name="tool2", description="Second tool", input_schema={}),
            Tool(name="tool3", description="Third tool", input_schema={}),
        ]

        result = client._convert_tools(tools)

        assert len(result) == 3
        assert [t["name"] for t in result] == ["tool1", "tool2", "tool3"]

    def test_convert_empty_tools(self) -> None:
        """Test converting empty tool list."""
        client = AnthropicClient()

        result = client._convert_tools([])

        assert result == []


class TestMapStopReason:
    """Tests for stop reason mapping."""

    def test_map_end_turn(self) -> None:
        """Test mapping end_turn."""
        client = AnthropicClient()

        assert client._map_stop_reason("end_turn") == StopReason.END_TURN

    def test_map_tool_use(self) -> None:
        """Test mapping tool_use."""
        client = AnthropicClient()

        assert client._map_stop_reason("tool_use") == StopReason.TOOL_USE

    def test_map_max_tokens(self) -> None:
        """Test mapping max_tokens."""
        client = AnthropicClient()

        assert client._map_stop_reason("max_tokens") == StopReason.MAX_TOKENS

    def test_map_stop_sequence(self) -> None:
        """Test mapping stop_sequence."""
        client = AnthropicClient()

        assert client._map_stop_reason("stop_sequence") == StopReason.STOP_SEQUENCE

    def test_map_unknown(self) -> None:
        """Test mapping unknown reason."""
        client = AnthropicClient()

        assert client._map_stop_reason("unknown") == StopReason.END_TURN

    def test_map_none(self) -> None:
        """Test mapping None."""
        client = AnthropicClient()

        assert client._map_stop_reason(None) == StopReason.END_TURN


class MockTextBlock:
    """Mock for Anthropic text block."""

    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class MockToolUseBlock:
    """Mock for Anthropic tool_use block."""

    def __init__(self, id: str, name: str, input: dict):
        self.type = "tool_use"
        self.id = id
        self.name = name
        self.input = input


class MockUsage:
    """Mock for Anthropic usage."""

    def __init__(self, input_tokens: int, output_tokens: int):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class MockResponse:
    """Mock for Anthropic response."""

    def __init__(
        self,
        content: list,
        stop_reason: str,
        input_tokens: int,
        output_tokens: int,
        model: str = "claude-sonnet-4-20250514",
    ):
        self.content = content
        self.stop_reason = stop_reason
        self.usage = MockUsage(input_tokens, output_tokens)
        self.model = model


class TestParseResponse:
    """Tests for response parsing."""

    def test_parse_text_response(self) -> None:
        """Test parsing a text-only response."""
        client = AnthropicClient()

        mock_response = MockResponse(
            content=[MockTextBlock("Hello, world!")],
            stop_reason="end_turn",
            input_tokens=10,
            output_tokens=5,
        )

        result = client._parse_response(mock_response)

        assert result.content == "Hello, world!"
        assert result.stop_reason == StopReason.END_TURN
        assert result.tool_calls == []
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        assert result.model == "claude-sonnet-4-20250514"

    def test_parse_tool_use_response(self) -> None:
        """Test parsing a response with tool calls."""
        client = AnthropicClient()

        mock_response = MockResponse(
            content=[
                MockTextBlock("I need to read a file."),
                MockToolUseBlock("tc_123", "read_file", {"path": "/test.txt"}),
            ],
            stop_reason="tool_use",
            input_tokens=20,
            output_tokens=15,
        )

        result = client._parse_response(mock_response)

        assert result.content == "I need to read a file."
        assert result.stop_reason == StopReason.TOOL_USE
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "tc_123"
        assert result.tool_calls[0].name == "read_file"
        assert result.tool_calls[0].arguments == {"path": "/test.txt"}

    def test_parse_multiple_tool_calls(self) -> None:
        """Test parsing response with multiple tool calls."""
        client = AnthropicClient()

        mock_response = MockResponse(
            content=[
                MockTextBlock("Let me check both files."),
                MockToolUseBlock("tc_1", "read_file", {"path": "/a.txt"}),
                MockToolUseBlock("tc_2", "read_file", {"path": "/b.txt"}),
            ],
            stop_reason="tool_use",
            input_tokens=30,
            output_tokens=25,
        )

        result = client._parse_response(mock_response)

        assert len(result.tool_calls) == 2
        assert result.tool_calls[0].id == "tc_1"
        assert result.tool_calls[1].id == "tc_2"

    def test_parse_multiple_text_blocks(self) -> None:
        """Test parsing response with multiple text blocks."""
        client = AnthropicClient()

        mock_response = MockResponse(
            content=[
                MockTextBlock("First part."),
                MockTextBlock("Second part."),
            ],
            stop_reason="end_turn",
            input_tokens=10,
            output_tokens=10,
        )

        result = client._parse_response(mock_response)

        assert result.content == "First part.\nSecond part."


@pytest.fixture
def mock_anthropic_module():
    """Create a mock anthropic module."""
    mock_module = MagicMock()

    # Create exception classes
    mock_module.RateLimitError = type("RateLimitError", (Exception,), {})
    mock_module.AuthenticationError = type("AuthenticationError", (Exception,), {})
    mock_module.BadRequestError = type("BadRequestError", (Exception,), {})
    mock_module.NotFoundError = type("NotFoundError", (Exception,), {})
    mock_module.APIError = type("APIError", (Exception,), {"status_code": None})

    # Mock AsyncAnthropic
    mock_module.AsyncAnthropic = MagicMock()

    return mock_module


class TestHandleError:
    """Tests for error handling."""

    def test_handle_rate_limit_error(self, mock_anthropic_module) -> None:
        """Test handling rate limit error."""
        client = AnthropicClient()

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            error = mock_anthropic_module.RateLimitError("Rate limit exceeded")
            error.response = MagicMock()
            error.response.headers = {"retry-after": "30"}

            with pytest.raises(RateLimitError) as exc:
                client._handle_error(error)

            assert exc.value.retryable is True

    def test_handle_authentication_error(self, mock_anthropic_module) -> None:
        """Test handling authentication error."""
        client = AnthropicClient()

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            error = mock_anthropic_module.AuthenticationError("Invalid API key")

            with pytest.raises(AuthenticationError):
                client._handle_error(error)

    def test_handle_context_length_error(self, mock_anthropic_module) -> None:
        """Test handling context length error."""
        client = AnthropicClient()

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            error = mock_anthropic_module.BadRequestError("Context length exceeded")

            with pytest.raises(ContextLengthError):
                client._handle_error(error)

    def test_handle_bad_request_error(self, mock_anthropic_module) -> None:
        """Test handling bad request error."""
        client = AnthropicClient()

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            error = mock_anthropic_module.BadRequestError("Invalid parameter")

            with pytest.raises(InvalidRequestError):
                client._handle_error(error)

    def test_handle_not_found_error(self, mock_anthropic_module) -> None:
        """Test handling model not found error."""
        client = AnthropicClient()

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            error = mock_anthropic_module.NotFoundError("Model not found")

            with pytest.raises(ModelNotFoundError):
                client._handle_error(error)

    def test_handle_generic_api_error(self, mock_anthropic_module) -> None:
        """Test handling generic API error."""
        client = AnthropicClient()

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            error = mock_anthropic_module.APIError("Internal server error")
            error.status_code = 500

            with pytest.raises(LLMError) as exc:
                client._handle_error(error)

            assert exc.value.retryable is True

    def test_handle_unknown_error(self, mock_anthropic_module) -> None:
        """Test handling unknown error type."""
        client = AnthropicClient()

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            error = ValueError("Unknown error")

            with pytest.raises(LLMError):
                client._handle_error(error)


class TestEnsureClient:
    """Tests for client initialization."""

    def test_no_api_key_raises(self, mock_anthropic_module) -> None:
        """Test that missing API key raises error."""
        client = AnthropicClient()

        with patch.dict("os.environ", {}, clear=True):
            with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
                with pytest.raises(AuthenticationError) as exc:
                    client._ensure_client()

                assert "ANTHROPIC_API_KEY" in str(exc.value)

    def test_api_key_from_init(self, mock_anthropic_module) -> None:
        """Test using API key from init."""
        client = AnthropicClient(api_key="sk-ant-test123")

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            client._ensure_client()

            mock_anthropic_module.AsyncAnthropic.assert_called_once()
            call_kwargs = mock_anthropic_module.AsyncAnthropic.call_args[1]
            assert call_kwargs["api_key"] == "sk-ant-test123"

    def test_api_key_from_env(self, mock_anthropic_module) -> None:
        """Test using API key from environment."""
        client = AnthropicClient()

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-env123"}):
            with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
                client._ensure_client()

                call_kwargs = mock_anthropic_module.AsyncAnthropic.call_args[1]
                assert call_kwargs["api_key"] == "sk-ant-env123"

    def test_client_reused(self, mock_anthropic_module) -> None:
        """Test that client is reused on subsequent calls."""
        client = AnthropicClient(api_key="sk-ant-test")

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            mock_client = MagicMock()
            mock_anthropic_module.AsyncAnthropic.return_value = mock_client

            client._ensure_client()
            client._ensure_client()
            client._ensure_client()

            # Should only create client once
            assert mock_anthropic_module.AsyncAnthropic.call_count == 1


class TestComplete:
    """Tests for complete method."""

    @pytest.mark.asyncio
    async def test_complete_basic(self, mock_anthropic_module) -> None:
        """Test basic completion."""
        client = AnthropicClient(api_key="sk-ant-test")

        mock_response = MockResponse(
            content=[MockTextBlock("Hello!")],
            stop_reason="end_turn",
            input_tokens=5,
            output_tokens=2,
        )

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic_module.AsyncAnthropic.return_value = mock_client

            result = await client.complete(
                messages=[{"role": "user", "content": "Hi"}],
            )

            assert result.content == "Hello!"
            assert result.stop_reason == StopReason.END_TURN

    @pytest.mark.asyncio
    async def test_complete_with_system(self, mock_anthropic_module) -> None:
        """Test completion with system prompt."""
        client = AnthropicClient(api_key="sk-ant-test")

        mock_response = MockResponse(
            content=[MockTextBlock("I am helpful")],
            stop_reason="end_turn",
            input_tokens=10,
            output_tokens=5,
        )

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic_module.AsyncAnthropic.return_value = mock_client

            await client.complete(
                messages=[{"role": "user", "content": "Hello"}],
                system="You are a helpful assistant.",
            )

            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["system"] == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_complete_with_tools(self, mock_anthropic_module) -> None:
        """Test completion with tools."""
        client = AnthropicClient(api_key="sk-ant-test")

        tools = [
            Tool(name="read_file", description="Read a file", input_schema={"type": "object"}),
        ]

        mock_response = MockResponse(
            content=[MockToolUseBlock("tc_1", "read_file", {"path": "/test"})],
            stop_reason="tool_use",
            input_tokens=15,
            output_tokens=10,
        )

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic_module.AsyncAnthropic.return_value = mock_client

            result = await client.complete(
                messages=[{"role": "user", "content": "Read /test"}],
                tools=tools,
            )

            assert result.stop_reason == StopReason.TOOL_USE
            assert len(result.tool_calls) == 1

            call_kwargs = mock_client.messages.create.call_args[1]
            assert "tools" in call_kwargs

    @pytest.mark.asyncio
    async def test_complete_with_stop_sequences(self, mock_anthropic_module) -> None:
        """Test completion with stop sequences."""
        client = AnthropicClient(api_key="sk-ant-test")

        mock_response = MockResponse(
            content=[MockTextBlock("Stopped here")],
            stop_reason="stop_sequence",
            input_tokens=10,
            output_tokens=5,
        )

        with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic_module.AsyncAnthropic.return_value = mock_client

            result = await client.complete(
                messages=[{"role": "user", "content": "Test"}],
                stop_sequences=["STOP", "END"],
            )

            assert result.stop_reason == StopReason.STOP_SEQUENCE

            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["stop_sequences"] == ["STOP", "END"]
