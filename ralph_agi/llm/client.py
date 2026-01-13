"""Abstract LLM client interface for RALPH-AGI.

This module defines the common interface and data structures for LLM providers,
enabling the Builder + Critic multi-agent pattern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable


class StopReason(Enum):
    """Reason the LLM stopped generating.

    Maps to provider-specific stop reasons:
    - Anthropic: end_turn, tool_use, max_tokens, stop_sequence
    - OpenAI: stop, length, tool_calls, content_filter
    """

    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    CONTENT_FILTER = "content_filter"


@dataclass(frozen=True)
class ToolCall:
    """A tool call requested by the LLM.

    Attributes:
        id: Unique identifier for this tool call (for result mapping).
        name: Name of the tool to call.
        arguments: Arguments to pass to the tool.
    """

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Response from an LLM completion.

    Attributes:
        content: Text content of the response.
        stop_reason: Why the LLM stopped generating.
        tool_calls: List of tool calls requested (if any).
        usage: Token usage statistics.
        model: Model identifier that generated this response.
        raw_response: Original provider response (for debugging).
    """

    content: str
    stop_reason: StopReason
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    model: str = ""
    raw_response: Any = None

    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return len(self.tool_calls) > 0

    @property
    def input_tokens(self) -> int:
        """Get input token count."""
        return self.usage.get("input_tokens", 0)

    @property
    def output_tokens(self) -> int:
        """Get output token count."""
        return self.usage.get("output_tokens", 0)

    @property
    def total_tokens(self) -> int:
        """Get total token count."""
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class Tool:
    """Tool definition for LLM.

    Attributes:
        name: Unique tool name.
        description: What the tool does (for LLM context).
        input_schema: JSON Schema for tool arguments.
    """

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class Message:
    """A message in the conversation.

    Attributes:
        role: Message role (user, assistant, system).
        content: Message content (text or structured).
    """

    role: str
    content: Any  # str or list of content blocks


class LLMError(Exception):
    """Base exception for LLM errors.

    Attributes:
        message: Error description.
        retryable: Whether this error can be retried.
        status_code: HTTP status code if applicable.
    """

    def __init__(
        self,
        message: str,
        retryable: bool = False,
        status_code: Optional[int] = None,
    ):
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code


class RateLimitError(LLMError):
    """Rate limit exceeded error.

    Attributes:
        retry_after: Seconds to wait before retrying.
    """

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message, retryable=True, status_code=429)
        self.retry_after = retry_after


class AuthenticationError(LLMError):
    """Authentication/authorization error."""

    def __init__(self, message: str):
        super().__init__(message, retryable=False, status_code=401)


class InvalidRequestError(LLMError):
    """Invalid request error (bad parameters, schema, etc.)."""

    def __init__(self, message: str):
        super().__init__(message, retryable=False, status_code=400)


class ModelNotFoundError(LLMError):
    """Model not found or not available."""

    def __init__(self, message: str):
        super().__init__(message, retryable=False, status_code=404)


class ContextLengthError(LLMError):
    """Context length exceeded."""

    def __init__(self, message: str):
        super().__init__(message, retryable=False, status_code=400)


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM clients.

    All LLM providers must implement this interface to work with RALPH-AGI.
    The interface is async-first for better performance with I/O-bound LLM calls.
    """

    async def complete(
        self,
        messages: list[dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[list[Tool]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        stop_sequences: Optional[list[str]] = None,
    ) -> LLMResponse:
        """Generate a completion.

        Args:
            messages: Conversation history as list of message dicts.
            system: Optional system prompt.
            tools: Optional list of tools available to the LLM.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature (0.0 = deterministic).
            stop_sequences: Optional stop sequences.

        Returns:
            LLMResponse with completion result.

        Raises:
            LLMError: On API errors.
        """
        ...


def create_tool_result_message(tool_call_id: str, result: str, is_error: bool = False) -> dict[str, Any]:
    """Create a tool result message for continuing the conversation.

    Args:
        tool_call_id: ID of the tool call this result is for.
        result: Tool execution result (or error message).
        is_error: Whether this is an error result.

    Returns:
        Message dict formatted for the LLM.
    """
    return {
        "type": "tool_result",
        "tool_use_id": tool_call_id,
        "content": result,
        "is_error": is_error,
    }
