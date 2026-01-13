"""OpenAI GPT LLM client for RALPH-AGI.

This module provides GPT API integration for the Critic agent
in the multi-agent architecture.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, AsyncIterator, Optional

from ralph_agi.llm.client import (
    AuthenticationError,
    ContextLengthError,
    InvalidRequestError,
    LLMError,
    LLMResponse,
    ModelNotFoundError,
    RateLimitError,
    StopReason,
    Tool,
    ToolCall,
)

if TYPE_CHECKING:
    import openai

logger = logging.getLogger(__name__)


class OpenAIClient:
    """OpenAI GPT client for Critic agent.

    This client implements the LLMClient protocol and provides support
    for GPT models, primarily used for code review and critique.

    Attributes:
        model: GPT model to use.
        timeout: Request timeout in seconds.

    Example:
        >>> client = OpenAIClient(model="gpt-4o")
        >>> response = await client.complete(
        ...     messages=[{"role": "user", "content": "Review this code"}],
        ...     system="You are a code reviewer.",
        ... )
        >>> print(response.content)
    """

    DEFAULT_MODEL = "gpt-4o"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            model: GPT model to use. Default: gpt-4o
            base_url: Optional API base URL for proxies.
            timeout: Request timeout in seconds. Default: 120.0
        """
        self.model = model
        self.timeout = timeout
        self._api_key = api_key
        self._base_url = base_url
        self._client: Optional[openai.AsyncOpenAI] = None

    def _ensure_client(self) -> None:
        """Lazily initialize the OpenAI client.

        Raises:
            AuthenticationError: If no API key is available.
        """
        if self._client is not None:
            return

        try:
            import openai
        except ImportError:
            raise LLMError(
                "openai package not installed. Run: pip install openai"
            )

        api_key = self._api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise AuthenticationError(
                "OPENAI_API_KEY not set. Provide api_key or set environment variable."
            )

        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=self._base_url,
            timeout=self.timeout,
        )

    def _convert_tools(self, tools: list[Tool]) -> list[dict[str, Any]]:
        """Convert Tool objects to OpenAI format.

        Args:
            tools: List of Tool objects.

        Returns:
            List of tool definitions in OpenAI format.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
            for tool in tools
        ]

    def _build_messages(
        self,
        messages: list[dict[str, Any]],
        system: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Build message list with system prompt prepended.

        OpenAI uses a system message in the messages array rather than
        a separate parameter like Anthropic.

        Args:
            messages: Conversation history.
            system: Optional system prompt.

        Returns:
            Message list with system prompt prepended if provided.
        """
        result = []
        if system:
            result.append({"role": "system", "content": system})
        result.extend(messages)
        return result

    async def complete(
        self,
        messages: list[dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[list[Tool]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        stop_sequences: Optional[list[str]] = None,
    ) -> LLMResponse:
        """Generate a completion using GPT.

        Args:
            messages: Conversation history as list of message dicts.
            system: Optional system prompt (prepended to messages).
            tools: Optional list of tools available to GPT.
            max_tokens: Maximum tokens to generate. Default: 4096
            temperature: Sampling temperature. Default: 0.0 (deterministic)
            stop_sequences: Optional stop sequences.

        Returns:
            LLMResponse with completion result.

        Raises:
            AuthenticationError: If API key is invalid.
            RateLimitError: If rate limit is exceeded.
            InvalidRequestError: If request is malformed.
            ContextLengthError: If context is too long.
            LLMError: On other API errors.
        """
        self._ensure_client()
        assert self._client is not None

        built_messages = self._build_messages(messages, system)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": built_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if tools:
            kwargs["tools"] = self._convert_tools(tools)
        if stop_sequences:
            kwargs["stop"] = stop_sequences

        try:
            response = await self._client.chat.completions.create(**kwargs)
            return self._parse_response(response)
        except Exception as e:
            self._handle_error(e)
            raise  # Never reached, but makes type checker happy

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse OpenAI response into LLMResponse.

        Args:
            response: Raw OpenAI API response.

        Returns:
            Parsed LLMResponse.
        """
        choice = response.choices[0]
        message = choice.message

        content = message.content or ""
        tool_calls: list[ToolCall] = []

        if message.tool_calls:
            import json

            for tc in message.tool_calls:
                # Parse arguments from JSON string
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=arguments,
                    )
                )

        stop_reason = self._map_stop_reason(choice.finish_reason)

        return LLMResponse(
            content=content,
            stop_reason=stop_reason,
            tool_calls=tool_calls,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
            model=response.model,
            raw_response=response,
        )

    def _map_stop_reason(self, reason: Optional[str]) -> StopReason:
        """Map OpenAI finish reason to StopReason enum.

        Args:
            reason: OpenAI finish reason string.

        Returns:
            Mapped StopReason enum value.
        """
        mapping = {
            "stop": StopReason.END_TURN,
            "tool_calls": StopReason.TOOL_USE,
            "length": StopReason.MAX_TOKENS,
            "content_filter": StopReason.CONTENT_FILTER,
        }
        return mapping.get(reason or "", StopReason.END_TURN)

    def _handle_error(self, error: Exception) -> None:
        """Convert OpenAI errors to LLMError types.

        Args:
            error: Exception from OpenAI client.

        Raises:
            Appropriate LLMError subclass.
        """
        try:
            import openai
        except ImportError:
            raise LLMError(str(error))

        error_message = str(error)

        if isinstance(error, openai.RateLimitError):
            # Try to extract retry-after from headers
            retry_after = None
            if hasattr(error, "response") and error.response:
                retry_after_str = error.response.headers.get("retry-after")
                if retry_after_str:
                    try:
                        retry_after = float(retry_after_str)
                    except ValueError:
                        pass
            raise RateLimitError(error_message, retry_after=retry_after)

        elif isinstance(error, openai.AuthenticationError):
            raise AuthenticationError(error_message)

        elif isinstance(error, openai.BadRequestError):
            # Check for context length errors
            if "context" in error_message.lower() or "tokens" in error_message.lower():
                if "maximum" in error_message.lower() or "limit" in error_message.lower():
                    raise ContextLengthError(error_message)
            raise InvalidRequestError(error_message)

        elif isinstance(error, openai.NotFoundError):
            raise ModelNotFoundError(error_message)

        elif isinstance(error, openai.APIError):
            # Generic API error - check if retryable based on status
            status_code = getattr(error, "status_code", None)
            retryable = status_code is not None and status_code >= 500
            raise LLMError(error_message, retryable=retryable, status_code=status_code)

        else:
            # Unknown error type
            raise LLMError(error_message)

    async def complete_stream(
        self,
        messages: list[dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[list[Tool]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> AsyncIterator[str]:
        """Stream a completion from GPT.

        Yields text chunks as they are generated. Tool calls are not
        supported in streaming mode.

        Args:
            messages: Conversation history.
            system: Optional system prompt.
            tools: Optional tools (for context, but responses won't stream tool calls).
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Yields:
            Text chunks as they are generated.

        Raises:
            LLMError: On API errors.
        """
        self._ensure_client()
        assert self._client is not None

        built_messages = self._build_messages(messages, system)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": built_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        try:
            stream = await self._client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            self._handle_error(e)
