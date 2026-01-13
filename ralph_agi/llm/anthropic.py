"""Anthropic Claude LLM client for RALPH-AGI.

This module provides Claude API integration with native tool_use support,
serving as the Builder LLM in the multi-agent architecture.
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
    import anthropic

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Claude API client with tool_use support.

    This client implements the LLMClient protocol and provides full support
    for Claude's native tool_use feature, making it ideal for the Builder agent.

    Attributes:
        model: Claude model to use.
        timeout: Request timeout in seconds.

    Example:
        >>> client = AnthropicClient(model="claude-sonnet-4-20250514")
        >>> response = await client.complete(
        ...     messages=[{"role": "user", "content": "Hello"}],
        ...     system="You are a helpful assistant.",
        ... )
        >>> print(response.content)
    """

    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
            model: Claude model to use. Default: claude-sonnet-4-20250514
            base_url: Optional API base URL for proxies.
            timeout: Request timeout in seconds. Default: 120.0
        """
        self.model = model
        self.timeout = timeout
        self._api_key = api_key
        self._base_url = base_url
        self._client: Optional[anthropic.AsyncAnthropic] = None

    def _ensure_client(self) -> None:
        """Lazily initialize the Anthropic client.

        Raises:
            AuthenticationError: If no API key is available.
        """
        if self._client is not None:
            return

        try:
            import anthropic
        except ImportError:
            raise LLMError(
                "anthropic package not installed. Run: pip install anthropic"
            )

        api_key = self._api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise AuthenticationError(
                "ANTHROPIC_API_KEY not set. Provide api_key or set environment variable."
            )

        self._client = anthropic.AsyncAnthropic(
            api_key=api_key,
            base_url=self._base_url,
            timeout=self.timeout,
        )

    def _convert_tools(self, tools: list[Tool]) -> list[dict[str, Any]]:
        """Convert Tool objects to Anthropic format.

        Args:
            tools: List of Tool objects.

        Returns:
            List of tool definitions in Anthropic format.
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in tools
        ]

    async def complete(
        self,
        messages: list[dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[list[Tool]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        stop_sequences: Optional[list[str]] = None,
    ) -> LLMResponse:
        """Generate a completion using Claude.

        Args:
            messages: Conversation history as list of message dicts.
            system: Optional system prompt.
            tools: Optional list of tools available to Claude.
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

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
        if stop_sequences:
            kwargs["stop_sequences"] = stop_sequences

        try:
            response = await self._client.messages.create(**kwargs)
            return self._parse_response(response)
        except Exception as e:
            self._handle_error(e)
            raise  # Never reached, but makes type checker happy

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse Anthropic response into LLMResponse.

        Args:
            response: Raw Anthropic API response.

        Returns:
            Parsed LLMResponse.
        """
        content_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                content_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        stop_reason = self._map_stop_reason(response.stop_reason)

        return LLMResponse(
            content="\n".join(content_parts),
            stop_reason=stop_reason,
            tool_calls=tool_calls,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            model=response.model,
            raw_response=response,
        )

    def _map_stop_reason(self, reason: Optional[str]) -> StopReason:
        """Map Anthropic stop reason to StopReason enum.

        Args:
            reason: Anthropic stop reason string.

        Returns:
            Mapped StopReason enum value.
        """
        mapping = {
            "end_turn": StopReason.END_TURN,
            "tool_use": StopReason.TOOL_USE,
            "max_tokens": StopReason.MAX_TOKENS,
            "stop_sequence": StopReason.STOP_SEQUENCE,
        }
        return mapping.get(reason or "", StopReason.END_TURN)

    def _handle_error(self, error: Exception) -> None:
        """Convert Anthropic errors to LLMError types.

        Args:
            error: Exception from Anthropic client.

        Raises:
            Appropriate LLMError subclass.
        """
        try:
            import anthropic
        except ImportError:
            raise LLMError(str(error))

        error_message = str(error)

        if isinstance(error, anthropic.RateLimitError):
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

        elif isinstance(error, anthropic.AuthenticationError):
            raise AuthenticationError(error_message)

        elif isinstance(error, anthropic.BadRequestError):
            # Check for context length errors
            if "context" in error_message.lower() and "length" in error_message.lower():
                raise ContextLengthError(error_message)
            raise InvalidRequestError(error_message)

        elif isinstance(error, anthropic.NotFoundError):
            raise ModelNotFoundError(error_message)

        elif isinstance(error, anthropic.APIError):
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
        """Stream a completion from Claude.

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

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        try:
            async with self._client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            self._handle_error(e)
