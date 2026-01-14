"""Tests for OpenRouter client."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ralph_agi.llm.client import AuthenticationError, LLMError
from ralph_agi.llm.openrouter import MODELS, OpenRouterClient


# Mock response classes (reused from test_openai)
class MockFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class MockToolCall:
    def __init__(self, id: str, name: str, arguments: str):
        self.id = id
        self.function = MockFunction(name, arguments)


class MockMessage:
    def __init__(
        self,
        content: str | None = None,
        tool_calls: list[MockToolCall] | None = None,
    ):
        self.content = content
        self.tool_calls = tool_calls


class MockChoice:
    def __init__(self, message: MockMessage, finish_reason: str):
        self.message = message
        self.finish_reason = finish_reason


class MockUsage:
    def __init__(self, prompt_tokens: int, completion_tokens: int):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class MockResponse:
    def __init__(
        self,
        content: str | None = None,
        finish_reason: str = "stop",
        prompt_tokens: int = 100,
        completion_tokens: int = 50,
        model: str = "anthropic/claude-sonnet-4-20250514",
    ):
        self.choices = [MockChoice(MockMessage(content), finish_reason)]
        self.usage = MockUsage(prompt_tokens, completion_tokens)
        self.model = model


@pytest.fixture
def mock_openai_module():
    """Create mock OpenAI module for OpenRouter."""
    mock_module = MagicMock()
    mock_async_client = MagicMock()
    mock_module.AsyncOpenAI = MagicMock(return_value=mock_async_client)
    mock_module.RateLimitError = type("RateLimitError", (Exception,), {})
    mock_module.AuthenticationError = type("AuthenticationError", (Exception,), {})
    mock_module.BadRequestError = type("BadRequestError", (Exception,), {})
    mock_module.NotFoundError = type("NotFoundError", (Exception,), {})
    mock_module.APIError = type("APIError", (Exception,), {})
    return mock_module


class TestOpenRouterClientInit:
    """Tests for OpenRouter client initialization."""

    def test_default_init(self) -> None:
        """Test default initialization."""
        client = OpenRouterClient()

        assert client.model == "anthropic/claude-sonnet-4.5"
        assert client._base_url == "https://openrouter.ai/api/v1"
        assert client.app_name == "RALPH-AGI"
        assert client._client is None

    def test_model_alias_resolution(self) -> None:
        """Test that model aliases are resolved."""
        client = OpenRouterClient(model="claude-sonnet")

        assert client.model == "anthropic/claude-sonnet-4.5"

    def test_full_model_path(self) -> None:
        """Test using full model path."""
        client = OpenRouterClient(model="meta-llama/llama-3.1-70b-instruct")

        assert client.model == "meta-llama/llama-3.1-70b-instruct"

    def test_custom_site_url(self) -> None:
        """Test custom site URL."""
        client = OpenRouterClient(site_url="https://mysite.com")

        assert client.site_url == "https://mysite.com"

    def test_custom_app_name(self) -> None:
        """Test custom app name."""
        client = OpenRouterClient(app_name="My Custom App")

        assert client.app_name == "My Custom App"


class TestModelAliases:
    """Tests for model alias functionality."""

    def test_list_models(self) -> None:
        """Test listing available models."""
        models = OpenRouterClient.list_models()

        assert "claude-sonnet" in models
        assert "gpt-4o" in models
        assert "llama-3.1-70b" in models
        assert "mistral-large" in models

    def test_resolve_alias(self) -> None:
        """Test resolving model alias."""
        resolved = OpenRouterClient.resolve_model("claude-haiku")

        assert resolved == "anthropic/claude-3.5-haiku"

    def test_resolve_full_path(self) -> None:
        """Test resolving full model path (no change)."""
        resolved = OpenRouterClient.resolve_model("openai/gpt-4o")

        assert resolved == "openai/gpt-4o"

    def test_all_aliases_defined(self) -> None:
        """Test that all aliases have valid values."""
        for alias, path in MODELS.items():
            assert "/" in path, f"Model {alias} should have provider prefix"


class TestGetExtraHeaders:
    """Tests for OpenRouter-specific headers."""

    def test_headers_with_site_and_app(self) -> None:
        """Test headers with both site URL and app name."""
        client = OpenRouterClient(
            site_url="https://mysite.com",
            app_name="TestApp",
        )

        headers = client._get_extra_headers()

        assert headers["HTTP-Referer"] == "https://mysite.com"
        assert headers["X-Title"] == "TestApp"

    def test_headers_with_site_only(self) -> None:
        """Test headers with only site URL."""
        client = OpenRouterClient(site_url="https://mysite.com")

        headers = client._get_extra_headers()

        assert headers["HTTP-Referer"] == "https://mysite.com"
        assert headers["X-Title"] == "RALPH-AGI"

    def test_headers_default(self) -> None:
        """Test default headers (app name only)."""
        client = OpenRouterClient()

        headers = client._get_extra_headers()

        assert "HTTP-Referer" not in headers
        assert headers["X-Title"] == "RALPH-AGI"


class TestEnsureClient:
    """Tests for lazy client initialization."""

    def test_no_api_key_raises(self, mock_openai_module: Any) -> None:
        """Test that missing API key raises error."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            with patch.dict("os.environ", {}, clear=True):
                client = OpenRouterClient()

                with pytest.raises(AuthenticationError) as exc_info:
                    client._ensure_client()

                assert "OPENROUTER_API_KEY" in str(exc_info.value)

    def test_api_key_from_init(self, mock_openai_module: Any) -> None:
        """Test using API key from init."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            client = OpenRouterClient(api_key="sk-or-test-key")
            client._ensure_client()

            call_kwargs = mock_openai_module.AsyncOpenAI.call_args[1]
            assert call_kwargs["api_key"] == "sk-or-test-key"
            assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"

    def test_api_key_from_env(self, mock_openai_module: Any) -> None:
        """Test using API key from environment."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-env-key"}):
                client = OpenRouterClient()
                client._ensure_client()

                call_kwargs = mock_openai_module.AsyncOpenAI.call_args[1]
                assert call_kwargs["api_key"] == "sk-or-env-key"

    def test_extra_headers_passed(self, mock_openai_module: Any) -> None:
        """Test that extra headers are passed to client."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            client = OpenRouterClient(
                api_key="sk-test",
                site_url="https://example.com",
                app_name="TestApp",
            )
            client._ensure_client()

            call_kwargs = mock_openai_module.AsyncOpenAI.call_args[1]
            assert call_kwargs["default_headers"]["HTTP-Referer"] == "https://example.com"
            assert call_kwargs["default_headers"]["X-Title"] == "TestApp"


class TestComplete:
    """Tests for complete method."""

    @pytest.mark.asyncio
    async def test_complete_basic(self, mock_openai_module: Any) -> None:
        """Test basic completion through OpenRouter."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            client = OpenRouterClient(api_key="sk-test")

            mock_response = MockResponse(content="Hello from Claude via OpenRouter!")
            mock_create = AsyncMock(return_value=mock_response)
            mock_openai_module.AsyncOpenAI.return_value.chat.completions.create = mock_create

            response = await client.complete(
                messages=[{"role": "user", "content": "Hi"}]
            )

            assert response.content == "Hello from Claude via OpenRouter!"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_with_system(self, mock_openai_module: Any) -> None:
        """Test completion with system prompt."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            client = OpenRouterClient(api_key="sk-test")

            mock_response = MockResponse(content="I'll help!")
            mock_create = AsyncMock(return_value=mock_response)
            mock_openai_module.AsyncOpenAI.return_value.chat.completions.create = mock_create

            await client.complete(
                messages=[{"role": "user", "content": "Hi"}],
                system="You are a code reviewer.",
            )

            call_args = mock_create.call_args[1]
            assert call_args["messages"][0]["role"] == "system"
            assert call_args["messages"][0]["content"] == "You are a code reviewer."

    @pytest.mark.asyncio
    async def test_complete_uses_resolved_model(self, mock_openai_module: Any) -> None:
        """Test that resolved model name is used."""
        with patch.dict(sys.modules, {"openai": mock_openai_module}):
            client = OpenRouterClient(api_key="sk-test", model="llama-3.1-70b")

            mock_response = MockResponse(content="Response")
            mock_create = AsyncMock(return_value=mock_response)
            mock_openai_module.AsyncOpenAI.return_value.chat.completions.create = mock_create

            await client.complete(messages=[{"role": "user", "content": "Hi"}])

            call_args = mock_create.call_args[1]
            assert call_args["model"] == "meta-llama/llama-3.1-70b-instruct"


class TestInheritance:
    """Tests for proper inheritance from OpenAIClient."""

    def test_inherits_from_openai_client(self) -> None:
        """Test that OpenRouterClient inherits from OpenAIClient."""
        from ralph_agi.llm.openai import OpenAIClient

        client = OpenRouterClient()

        assert isinstance(client, OpenAIClient)

    def test_has_convert_tools_method(self) -> None:
        """Test that client has _convert_tools from parent."""
        from ralph_agi.llm.client import Tool

        client = OpenRouterClient()
        tools = [Tool(name="test", description="Test", input_schema={})]

        result = client._convert_tools(tools)

        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "test"

    def test_has_build_messages_method(self) -> None:
        """Test that client has _build_messages from parent."""
        client = OpenRouterClient()
        messages = [{"role": "user", "content": "Hi"}]

        result = client._build_messages(messages, system="System prompt")

        assert len(result) == 2
        assert result[0]["role"] == "system"
