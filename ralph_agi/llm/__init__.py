"""LLM integration module for RALPH-AGI.

This module provides multi-LLM support for autonomous task execution,
implementing the Builder + Critic pattern from ADR-002.

Key Components:
- LLMClient: Abstract interface for LLM providers
- AnthropicClient: Claude implementation with tool_use support
- OpenAIClient: GPT implementation for Critic agent
- BuilderAgent: Task execution with tool loop
- CriticAgent: Code review and quality assurance
- LLMOrchestrator: Coordinates Builder → Critic flow
"""

from __future__ import annotations

from ralph_agi.llm.anthropic import AnthropicClient
from ralph_agi.llm.client import (
    LLMError,
    LLMResponse,
    RateLimitError,
    StopReason,
    Tool,
    ToolCall,
)
from ralph_agi.llm.openai import OpenAIClient
from ralph_agi.llm.openrouter import OpenRouterClient

__all__ = [
    # Core types
    "LLMResponse",
    "LLMError",
    "RateLimitError",
    "StopReason",
    "Tool",
    "ToolCall",
    # Clients
    "AnthropicClient",
    "OpenAIClient",
    "OpenRouterClient",
]
