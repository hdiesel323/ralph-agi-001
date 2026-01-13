"""OpenRouter LLM client for RALPH-AGI.

This module provides OpenRouter API integration, enabling access to 100+ models
through a unified OpenAI-compatible interface. Useful for:
- Cost optimization (choosing cheaper models when appropriate)
- Redundancy (fallback if primary provider is down)
- Model experimentation (testing different models without code changes)
- Access to open-source models (Llama, Mistral, Mixtral, etc.)
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, Optional

from ralph_agi.llm.client import (
    AuthenticationError,
    LLMError,
    LLMResponse,
    Tool,
)
from ralph_agi.llm.openai import OpenAIClient

if TYPE_CHECKING:
    import openai

logger = logging.getLogger(__name__)


# Popular model aliases for convenience
MODELS = {
    # Anthropic Claude models via OpenRouter (2025)
    "claude-opus": "anthropic/claude-opus-4.5",
    "claude-sonnet": "anthropic/claude-sonnet-4.5",
    "claude-haiku": "anthropic/claude-3.5-haiku",
    "claude-3.7-sonnet": "anthropic/claude-3.7-sonnet",
    # OpenAI models via OpenRouter
    "gpt-4o": "openai/gpt-4o",
    "gpt-4-turbo": "openai/gpt-4-turbo",
    "gpt-4": "openai/gpt-4",
    "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
    # Google models
    "gemini-pro": "google/gemini-pro-1.5",
    "gemini-flash": "google/gemini-flash-1.5",
    # Meta Llama models
    "llama-3.1-405b": "meta-llama/llama-3.1-405b-instruct",
    "llama-3.1-70b": "meta-llama/llama-3.1-70b-instruct",
    "llama-3.1-8b": "meta-llama/llama-3.1-8b-instruct",
    # Mistral models
    "mistral-large": "mistralai/mistral-large",
    "mixtral-8x22b": "mistralai/mixtral-8x22b-instruct",
    "mixtral-8x7b": "mistralai/mixtral-8x7b-instruct",
    # DeepSeek
    "deepseek-v3": "deepseek/deepseek-chat",
    "deepseek-coder": "deepseek/deepseek-coder",
    # Qwen
    "qwen-72b": "qwen/qwen-2.5-72b-instruct",
}


class OpenRouterClient(OpenAIClient):
    """OpenRouter API client providing access to 100+ models.

    OpenRouter is OpenAI-compatible, so this extends OpenAIClient with:
    - Custom base URL for OpenRouter API
    - Model aliasing for convenience
    - Additional headers for OpenRouter features
    - Site/app identification for analytics

    Attributes:
        model: Model to use (can be alias or full model path).
        site_url: Optional URL of your site for OpenRouter analytics.
        app_name: Optional app name for OpenRouter analytics.

    Example:
        >>> client = OpenRouterClient(model="claude-sonnet")
        >>> response = await client.complete(
        ...     messages=[{"role": "user", "content": "Hello"}],
        ...     system="You are helpful.",
        ... )
        >>> print(response.content)
    """

    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "anthropic/claude-sonnet-4.5"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout: float = 120.0,
        site_url: Optional[str] = None,
        app_name: Optional[str] = None,
    ):
        """Initialize the OpenRouter client.

        Args:
            api_key: OpenRouter API key. If not provided, uses OPENROUTER_API_KEY env var.
            model: Model to use. Can be an alias (e.g., "claude-sonnet") or
                   full model path (e.g., "anthropic/claude-sonnet-4-20250514").
            timeout: Request timeout in seconds. Default: 120.0
            site_url: Optional URL for your site (for OpenRouter analytics).
            app_name: Optional app name (for OpenRouter analytics).
        """
        # Resolve model alias if provided
        resolved_model = MODELS.get(model, model)

        # Initialize parent with OpenRouter base URL
        super().__init__(
            api_key=api_key,
            model=resolved_model,
            base_url=self.OPENROUTER_BASE_URL,
            timeout=timeout,
        )

        self.site_url = site_url
        self.app_name = app_name or "RALPH-AGI"

    def _ensure_client(self) -> None:
        """Lazily initialize the OpenRouter client.

        Uses OPENROUTER_API_KEY instead of OPENAI_API_KEY.

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

        api_key = self._api_key or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise AuthenticationError(
                "OPENROUTER_API_KEY not set. Provide api_key or set environment variable."
            )

        # Create client with OpenRouter base URL
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=self._base_url,
            timeout=self.timeout,
            default_headers=self._get_extra_headers(),
        )

    def _get_extra_headers(self) -> dict[str, str]:
        """Get OpenRouter-specific headers.

        Returns:
            Headers dict with site URL and app name if provided.
        """
        headers = {}
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.app_name:
            headers["X-Title"] = self.app_name
        return headers

    async def complete(
        self,
        messages: list[dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[list[Tool]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        stop_sequences: Optional[list[str]] = None,
    ) -> LLMResponse:
        """Generate a completion using OpenRouter.

        Supports the same interface as OpenAIClient but routes through OpenRouter.

        Args:
            messages: Conversation history as list of message dicts.
            system: Optional system prompt (prepended to messages).
            tools: Optional list of tools available to the model.
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
        return await super().complete(
            messages=messages,
            system=system,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            stop_sequences=stop_sequences,
        )

    @classmethod
    def list_models(cls) -> dict[str, str]:
        """List available model aliases.

        Returns:
            Dict mapping alias names to full model paths.
        """
        return MODELS.copy()

    @classmethod
    def resolve_model(cls, model: str) -> str:
        """Resolve a model alias to full path.

        Args:
            model: Model alias or full path.

        Returns:
            Full model path.
        """
        return MODELS.get(model, model)
