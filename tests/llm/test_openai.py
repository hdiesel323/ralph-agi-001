"""Tests for OpenAI GPT client."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


# Mock classes for OpenAI response parsing
class MockFunction:
    """Mock OpenAI function call."""

    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class MockToolCall:
    """Mock OpenAI tool call."""

    def __init__(self, id: str, name: str, arguments: str):
        self.id = id
        self.function = MockFunction(name, arguments)


class MockMessage:
    """Mock OpenAI message."""

    def __init__(
        self,
        content: str | None = None,
        tool_calls: list[MockToolCall] | None = None,
    ):
        self.content = content
        self.tool_calls = tool_calls


class MockChoice:
    """Mock OpenAI choice."""

    def __init__(self, message: MockMessage, finish_reason: str):
        self.message = message
        self.finish_reason = finish_reason


class MockUsage:
    """Mock OpenAI usage."""

    def __init__(self, prompt_tokens: int, completion_tokens: int):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class MockResponse:
    """Mock OpenAI response."""

    def __init__(
        self,
        content: str | None = None,
        finish_reason: str = "stop",
        prompt_tokens: int = 100,
        completion_tokens: int = 50,
        model: str = "gpt-4o",
        tool_calls: list[MockToolCall] | None = None,
    ):
        self.choices = [
            MockChoice(MockMessage(content, tool_calls), finish_reason)
        ]
        self.usage = MockUsage(prompt_tokens, completion_tokens)
        self.model = model


@pytest.fixture
def mock_openai_module():
    """Create mock OpenAI module."""
    mock_module = MagicMock()

    # Create async client mock
    mock_async_client = MagicMock()
    mock_module.AsyncOpenAI = MagicMock(return_value=mock_async_client)

    # Create error classes
    mock_module.RateLimitError = type("RateLimitError", (Exception,), {})
    mock_module.AuthenticationError = type("AuthenticationError", (Exception,), {})
    mock_module.BadRequestError = type("BadRequestError", (Exception,), {})
    mock_module.NotFoundError = type("NotFoundError", (Exception,), {})
    mock_module.APIError = type("APIError", (Exception,), {})

    return mock_module


class TestOpenAIClientInit:
    """Tests for OpenAI client initialization."""

    def test_default_init(self) -> None:
        """Test default initialization."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()

        assert client.model == "gpt-4o"
        assert client.timeout == 120.0
        assert client._client is None

    def test_custom_model(self) -> None:
        """Test initialization with custom model."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient(model="gpt-4-turbo")

        assert client.model == "gpt-4-turbo"

    def test_custom_timeout(self) -> None:
        """Test initialization with custom timeout."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient(timeout=60.0)

        assert client.timeout == 60.0

    def test_custom_base_url(self) -> None:
        """Test initialization with custom base URL."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient(base_url="https://api.custom.com")

        assert client._base_url == "https://api.custom.com"


class TestConvertTools:
    """Tests for tool conversion to OpenAI format."""

    def test_convert_single_tool(self) -> None:
        """Test converting a single tool."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()
        tools = [
            Tool(
                name="read_file",
                description="Read a file",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            )
        ]

        result = client._convert_tools(tools)

        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "read_file"
        assert result[0]["function"]["description"] == "Read a file"
        assert result[0]["function"]["parameters"]["type"] == "object"

    def test_convert_multiple_tools(self) -> None:
        """Test converting multiple tools."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()
        tools = [
            Tool(name="tool1", description="First", input_schema={}),
            Tool(name="tool2", description="Second", input_schema={}),
        ]

        result = client._convert_tools(tools)

        assert len(result) == 2
        assert result[0]["function"]["name"] == "tool1"
        assert result[1]["function"]["name"] == "tool2"

    def test_convert_empty_tools(self) -> None:
        """Test converting empty tools list."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()

        result = client._convert_tools([])

        assert result == []


class TestBuildMessages:
    """Tests for message building with system prompt."""

    def test_build_messages_with_system(self) -> None:
        """Test building messages with system prompt."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()
        messages = [{"role": "user", "content": "Hello"}]

        result = client._build_messages(messages, system="You are helpful.")

        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are helpful."
        assert result[1]["role"] == "user"

    def test_build_messages_without_system(self) -> None:
        """Test building messages without system prompt."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()
        messages = [{"role": "user", "content": "Hello"}]

        result = client._build_messages(messages, system=None)

        assert len(result) == 1
        assert result[0]["role"] == "user"


class TestMapStopReason:
    """Tests for OpenAI finish reason mapping."""

    def test_map_stop(self) -> None:
        """Test mapping 'stop' reason."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()
        assert client._map_stop_reason("stop") == StopReason.END_TURN

    def test_map_tool_calls(self) -> None:
        """Test mapping 'tool_calls' reason."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()
        assert client._map_stop_reason("tool_calls") == StopReason.TOOL_USE

    def test_map_length(self) -> None:
        """Test mapping 'length' reason."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()
        assert client._map_stop_reason("length") == StopReason.MAX_TOKENS

    def test_map_content_filter(self) -> None:
        """Test mapping 'content_filter' reason."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()
        assert client._map_stop_reason("content_filter") == StopReason.CONTENT_FILTER

    def test_map_unknown(self) -> None:
        """Test mapping unknown reason."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()
        assert client._map_stop_reason("unknown") == StopReason.END_TURN

    def test_map_none(self) -> None:
        """Test mapping None reason."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()
        assert client._map_stop_reason(None) == StopReason.END_TURN


class TestParseResponse:
    """Tests for OpenAI response parsing."""

    def test_parse_text_response(self) -> None:
        """Test parsing a simple text response."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()
        response = MockResponse(content="Hello, world!")

        result = client._parse_response(response)

        assert result.content == "Hello, world!"
        assert result.stop_reason == StopReason.END_TURN
        assert result.tool_calls == []
        assert result.usage["input_tokens"] == 100
        assert result.usage["output_tokens"] == 50
        assert result.model == "gpt-4o"

    def test_parse_tool_call_response(self) -> None:
        """Test parsing a response with tool call."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()
        tool_calls = [
            MockToolCall("call_123", "read_file", '{"path": "/test.txt"}')
        ]
        response = MockResponse(
            content=None,
            finish_reason="tool_calls",
            tool_calls=tool_calls,
        )

        result = client._parse_response(response)

        assert result.content == ""
        assert result.stop_reason == StopReason.TOOL_USE
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "call_123"
        assert result.tool_calls[0].name == "read_file"
        assert result.tool_calls[0].arguments == {"path": "/test.txt"}

    def test_parse_multiple_tool_calls(self) -> None:
        """Test parsing response with multiple tool calls."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()
        tool_calls = [
            MockToolCall("call_1", "tool1", '{"arg": "value1"}'),
            MockToolCall("call_2", "tool2", '{"arg": "value2"}'),
        ]
        response = MockResponse(
            content="I'll use two tools.",
            finish_reason="tool_calls",
            tool_calls=tool_calls,
        )

        result = client._parse_response(response)

        assert len(result.tool_calls) == 2
        assert result.tool_calls[0].name == "tool1"
        assert result.tool_calls[1].name == "tool2"

    def test_parse_invalid_json_arguments(self) -> None:
        """Test parsing tool call with invalid JSON arguments."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenAIClient()
        tool_calls = [
            MockToolCall("call_123", "tool", "not valid json")
        ]
        response = MockResponse(
            content=None,
            finish_reason="tool_calls",
            tool_calls=tool_calls,
        )

        result = client._parse_response(response)

        assert result.tool_calls[0].arguments == {}


class TestHandleError:
    """Tests for OpenAI error handling."""

    def test_handle_rate_limit_error(self, mock_openai_module: Any) -> None:
        """Test handling rate limit error."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            from ralph_agi.llm.openai import OpenAIClient

            client = OpenAIClient()
            error = mock_openai_module.RateLimitError("Rate limited")

            with pytest.raises(RateLimitError) as exc_info:
                client._handle_error(error)

            assert "Rate limited" in str(exc_info.value)
            assert exc_info.value.retryable is True

    def test_handle_authentication_error(self, mock_openai_module: Any) -> None:
        """Test handling authentication error."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            from ralph_agi.llm.openai import OpenAIClient

            client = OpenAIClient()
            error = mock_openai_module.AuthenticationError("Invalid key")

            with pytest.raises(AuthenticationError) as exc_info:
                client._handle_error(error)

            assert "Invalid key" in str(exc_info.value)

    def test_handle_context_length_error(self, mock_openai_module: Any) -> None:
        """Test handling context length error."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            from ralph_agi.llm.openai import OpenAIClient

            client = OpenAIClient()
            error = mock_openai_module.BadRequestError(
                "maximum context tokens exceeded limit"
            )

            with pytest.raises(ContextLengthError):
                client._handle_error(error)

    def test_handle_bad_request_error(self, mock_openai_module: Any) -> None:
        """Test handling bad request error."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            from ralph_agi.llm.openai import OpenAIClient

            client = OpenAIClient()
            error = mock_openai_module.BadRequestError("Invalid parameter")

            with pytest.raises(InvalidRequestError):
                client._handle_error(error)

    def test_handle_not_found_error(self, mock_openai_module: Any) -> None:
        """Test handling not found error."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            from ralph_agi.llm.openai import OpenAIClient

            client = OpenAIClient()
            error = mock_openai_module.NotFoundError("Model not found")

            with pytest.raises(ModelNotFoundError):
                client._handle_error(error)

    def test_handle_generic_api_error(self, mock_openai_module: Any) -> None:
        """Test handling generic API error."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            from ralph_agi.llm.openai import OpenAIClient

            client = OpenAIClient()
            error = mock_openai_module.APIError("Server error")
            error.status_code = 500

            with pytest.raises(LLMError) as exc_info:
                client._handle_error(error)

            assert exc_info.value.retryable is True

    def test_handle_unknown_error(self, mock_openai_module: Any) -> None:
        """Test handling unknown error."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            from ralph_agi.llm.openai import OpenAIClient

            client = OpenAIClient()
            error = ValueError("Unknown error")

            with pytest.raises(LLMError):
                client._handle_error(error)


class TestEnsureClient:
    """Tests for lazy client initialization."""

    def test_no_api_key_raises(self, mock_openai_module: Any) -> None:
        """Test that missing API key raises error."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            with patch.dict("os.environ", {}, clear=True):
                from ralph_agi.llm.openai import OpenAIClient

                client = OpenAIClient()

                with pytest.raises(AuthenticationError) as exc_info:
                    client._ensure_client()

                assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_api_key_from_init(self, mock_openai_module: Any) -> None:
        """Test using API key from init."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            from ralph_agi.llm.openai import OpenAIClient

            client = OpenAIClient(api_key="sk-test-key")
            client._ensure_client()

            mock_openai_module.AsyncOpenAI.assert_called_once_with(
                api_key="sk-test-key",
                base_url=None,
                timeout=120.0,
            )

    def test_api_key_from_env(self, mock_openai_module: Any) -> None:
        """Test using API key from environment."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-env-key"}):
                from ralph_agi.llm.openai import OpenAIClient

                client = OpenAIClient()
                client._ensure_client()

                mock_openai_module.AsyncOpenAI.assert_called_once_with(
                    api_key="sk-env-key",
                    base_url=None,
                    timeout=120.0,
                )

    def test_client_reused(self, mock_openai_module: Any) -> None:
        """Test that client is reused on subsequent calls."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            from ralph_agi.llm.openai import OpenAIClient

            client = OpenAIClient(api_key="sk-test")
            client._ensure_client()
            client._ensure_client()

            assert mock_openai_module.AsyncOpenAI.call_count == 1


class TestComplete:
    """Tests for complete method."""

    @pytest.mark.asyncio
    async def test_complete_basic(self, mock_openai_module: Any) -> None:
        """Test basic completion."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            from ralph_agi.llm.openai import OpenAIClient

            client = OpenAIClient(api_key="sk-test")

            mock_response = MockResponse(content="Hello!")
            mock_create = AsyncMock(return_value=mock_response)
            mock_openai_module.AsyncOpenAI.return_value.chat.completions.create = mock_create

            response = await client.complete(
                messages=[{"role": "user", "content": "Hi"}]
            )

            assert response.content == "Hello!"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_with_system(self, mock_openai_module: Any) -> None:
        """Test completion with system prompt."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            from ralph_agi.llm.openai import OpenAIClient

            client = OpenAIClient(api_key="sk-test")

            mock_response = MockResponse(content="I'll help!")
            mock_create = AsyncMock(return_value=mock_response)
            mock_openai_module.AsyncOpenAI.return_value.chat.completions.create = mock_create

            await client.complete(
                messages=[{"role": "user", "content": "Hi"}],
                system="You are helpful.",
            )

            call_args = mock_create.call_args[1]
            assert call_args["messages"][0]["role"] == "system"
            assert call_args["messages"][0]["content"] == "You are helpful."

    @pytest.mark.asyncio
    async def test_complete_with_tools(self, mock_openai_module: Any) -> None:
        """Test completion with tools."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            from ralph_agi.llm.openai import OpenAIClient

            client = OpenAIClient(api_key="sk-test")

            mock_response = MockResponse(content="Using tool")
            mock_create = AsyncMock(return_value=mock_response)
            mock_openai_module.AsyncOpenAI.return_value.chat.completions.create = mock_create

            tools = [
                Tool(name="test", description="Test tool", input_schema={})
            ]

            await client.complete(
                messages=[{"role": "user", "content": "Hi"}],
                tools=tools,
            )

            call_args = mock_create.call_args[1]
            assert "tools" in call_args
            assert call_args["tools"][0]["type"] == "function"

    @pytest.mark.asyncio
    async def test_complete_with_stop_sequences(self, mock_openai_module: Any) -> None:
        """Test completion with stop sequences."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            from ralph_agi.llm.openai import OpenAIClient

            client = OpenAIClient(api_key="sk-test")

            mock_response = MockResponse(content="Response")
            mock_create = AsyncMock(return_value=mock_response)
            mock_openai_module.AsyncOpenAI.return_value.chat.completions.create = mock_create

            await client.complete(
                messages=[{"role": "user", "content": "Hi"}],
                stop_sequences=["END", "STOP"],
            )

            call_args = mock_create.call_args[1]
            assert call_args["stop"] == ["END", "STOP"]
