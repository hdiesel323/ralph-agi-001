"""LLM Orchestrator for RALPH-AGI.

Coordinates the Builder → Critic flow in the multi-agent architecture,
handling retries, token tracking, and flow control.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from ralph_agi.llm.agents import (
    AgentStatus,
    BuilderAgent,
    BuilderResult,
    CriticAgent,
    CriticResult,
    CriticVerdict,
)
from ralph_agi.llm.client import LLMError, RateLimitError, Tool

logger = logging.getLogger(__name__)


class OrchestratorStatus(Enum):
    """Status of an orchestrated execution."""

    SUCCESS = "success"  # Task completed and approved
    COMPLETED_NO_REVIEW = "completed_no_review"  # Task done, critic disabled
    NEEDS_REVISION = "needs_revision"  # Critic requested changes
    BLOCKED = "blocked"  # Cannot proceed
    MAX_RETRIES = "max_retries"  # Rate limit retries exhausted
    ERROR = "error"  # Unexpected error


@dataclass
class TokenUsage:
    """Track token usage across agents.

    Attributes:
        builder_input: Input tokens used by Builder.
        builder_output: Output tokens used by Builder.
        critic_input: Input tokens used by Critic.
        critic_output: Output tokens used by Critic.
    """

    builder_input: int = 0
    builder_output: int = 0
    critic_input: int = 0
    critic_output: int = 0

    @property
    def total_input(self) -> int:
        """Total input tokens across all agents."""
        return self.builder_input + self.critic_input

    @property
    def total_output(self) -> int:
        """Total output tokens across all agents."""
        return self.builder_output + self.critic_output

    @property
    def total(self) -> int:
        """Total tokens used."""
        return self.total_input + self.total_output

    def add_builder_usage(self, tokens: int) -> None:
        """Add tokens from Builder execution."""
        # Estimate 70/30 split for input/output
        self.builder_input += int(tokens * 0.7)
        self.builder_output += int(tokens * 0.3)

    def add_critic_usage(self, tokens: int) -> None:
        """Add tokens from Critic execution."""
        # Estimate 80/20 split for input/output (more input for review)
        self.critic_input += int(tokens * 0.8)
        self.critic_output += int(tokens * 0.2)


@dataclass
class OrchestratorResult:
    """Result from orchestrated task execution.

    Attributes:
        status: Final status of the orchestration.
        task: The task that was executed.
        builder_result: Result from Builder agent (if executed).
        critic_result: Result from Critic agent (if executed).
        token_usage: Token usage breakdown.
        iterations: Number of Builder iterations.
        rate_limit_retries: Number of rate limit retries performed.
        error: Error message if failed.
    """

    status: OrchestratorStatus
    task: dict[str, Any]
    builder_result: Optional[BuilderResult] = None
    critic_result: Optional[CriticResult] = None
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    iterations: int = 0
    rate_limit_retries: int = 0
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status in (
            OrchestratorStatus.SUCCESS,
            OrchestratorStatus.COMPLETED_NO_REVIEW,
        )

    @property
    def files_changed(self) -> list[str]:
        """Get list of files changed during execution."""
        if self.builder_result:
            return self.builder_result.files_changed
        return []


class LLMOrchestrator:
    """Orchestrates the Builder → Critic execution flow.

    The orchestrator:
    1. Executes the Builder agent on a task
    2. Optionally passes results to Critic for review
    3. Handles rate limits with exponential backoff
    4. Tracks token usage across agents

    Attributes:
        builder: Builder agent instance.
        critic: Critic agent instance (optional).
        critic_enabled: Whether to run Critic reviews.
        max_rate_limit_retries: Max retries on rate limit.
        base_retry_delay: Initial delay for exponential backoff.

    Example:
        >>> orchestrator = LLMOrchestrator(builder, critic)
        >>> result = await orchestrator.execute_task(task, tools)
        >>> if result.is_success:
        ...     print(f"Task completed! Used {result.token_usage.total} tokens")
    """

    DEFAULT_MAX_RATE_LIMIT_RETRIES = 3
    DEFAULT_BASE_RETRY_DELAY = 2.0

    def __init__(
        self,
        builder: BuilderAgent,
        critic: Optional[CriticAgent] = None,
        critic_enabled: bool = True,
        max_rate_limit_retries: int = DEFAULT_MAX_RATE_LIMIT_RETRIES,
        base_retry_delay: float = DEFAULT_BASE_RETRY_DELAY,
    ):
        """Initialize the orchestrator.

        Args:
            builder: Builder agent for task execution.
            critic: Critic agent for review (optional).
            critic_enabled: Whether to run Critic reviews.
            max_rate_limit_retries: Max retries on rate limit errors.
            base_retry_delay: Initial delay in seconds for retry backoff.
        """
        self._builder = builder
        self._critic = critic
        self._critic_enabled = critic_enabled and critic is not None
        self._max_rate_limit_retries = max_rate_limit_retries
        self._base_retry_delay = base_retry_delay

    async def execute_task(
        self,
        task: dict[str, Any],
        tools: Optional[list[Tool]] = None,
        context: Optional[str] = None,
        memory_context: Optional[str] = None,
    ) -> OrchestratorResult:
        """Execute a task through the Builder → Critic pipeline.

        Args:
            task: Task dictionary with title, description, etc.
            tools: List of tools available to the Builder.
            context: Optional project context.
            memory_context: Optional relevant memories.

        Returns:
            OrchestratorResult with execution details.
        """
        token_usage = TokenUsage()
        rate_limit_retries = 0

        logger.info(f"Orchestrator starting task: {task.get('title', 'Unknown')}")

        # Execute Builder with rate limit retry
        builder_result: Optional[BuilderResult] = None

        for attempt in range(self._max_rate_limit_retries + 1):
            try:
                builder_result = await self._builder.execute(
                    task=task,
                    tools=tools,
                    context=context,
                    memory_context=memory_context,
                )
                token_usage.add_builder_usage(builder_result.total_tokens)
                break

            except RateLimitError as e:
                rate_limit_retries += 1
                if attempt >= self._max_rate_limit_retries:
                    logger.error(f"Rate limit retries exhausted: {e}")
                    return OrchestratorResult(
                        status=OrchestratorStatus.MAX_RETRIES,
                        task=task,
                        token_usage=token_usage,
                        rate_limit_retries=rate_limit_retries,
                        error=str(e),
                    )

                # Exponential backoff
                delay = self._calculate_retry_delay(attempt, e.retry_after)
                logger.warning(f"Rate limited, retrying in {delay:.1f}s (attempt {attempt + 1})")
                await asyncio.sleep(delay)

            except LLMError as e:
                logger.error(f"Builder LLM error: {e}")
                return OrchestratorResult(
                    status=OrchestratorStatus.ERROR,
                    task=task,
                    token_usage=token_usage,
                    error=str(e),
                )

        if builder_result is None:
            return OrchestratorResult(
                status=OrchestratorStatus.ERROR,
                task=task,
                token_usage=token_usage,
                error="Builder did not produce a result",
            )

        # Check Builder result
        if builder_result.status == AgentStatus.BLOCKED:
            logger.warning(f"Builder blocked: {builder_result.error}")
            return OrchestratorResult(
                status=OrchestratorStatus.BLOCKED,
                task=task,
                builder_result=builder_result,
                token_usage=token_usage,
                iterations=builder_result.iterations,
                error=builder_result.error,
            )

        if builder_result.status == AgentStatus.ERROR:
            return OrchestratorResult(
                status=OrchestratorStatus.ERROR,
                task=task,
                builder_result=builder_result,
                token_usage=token_usage,
                iterations=builder_result.iterations,
                error=builder_result.error,
            )

        if builder_result.status == AgentStatus.MAX_ITERATIONS:
            logger.warning("Builder hit max iterations")
            # Continue to critic review even if max iterations

        # Run Critic review if enabled
        if not self._critic_enabled or self._critic is None:
            logger.info("Critic disabled, task completed without review")
            return OrchestratorResult(
                status=OrchestratorStatus.COMPLETED_NO_REVIEW,
                task=task,
                builder_result=builder_result,
                token_usage=token_usage,
                iterations=builder_result.iterations,
                rate_limit_retries=rate_limit_retries,
            )

        # Execute Critic with rate limit retry
        critic_result: Optional[CriticResult] = None

        for attempt in range(self._max_rate_limit_retries + 1):
            try:
                critic_result = await self._critic.review(task, builder_result)
                token_usage.add_critic_usage(critic_result.total_tokens)
                break

            except RateLimitError as e:
                rate_limit_retries += 1
                if attempt >= self._max_rate_limit_retries:
                    logger.error(f"Critic rate limit retries exhausted: {e}")
                    # Return success without review if critic rate limited
                    return OrchestratorResult(
                        status=OrchestratorStatus.COMPLETED_NO_REVIEW,
                        task=task,
                        builder_result=builder_result,
                        token_usage=token_usage,
                        iterations=builder_result.iterations,
                        rate_limit_retries=rate_limit_retries,
                    )

                delay = self._calculate_retry_delay(attempt, e.retry_after)
                logger.warning(f"Critic rate limited, retrying in {delay:.1f}s")
                await asyncio.sleep(delay)

            except LLMError as e:
                logger.error(f"Critic LLM error: {e}")
                # Return success without review if critic fails
                return OrchestratorResult(
                    status=OrchestratorStatus.COMPLETED_NO_REVIEW,
                    task=task,
                    builder_result=builder_result,
                    token_usage=token_usage,
                    iterations=builder_result.iterations,
                )

        # Process Critic verdict
        if critic_result is None:
            return OrchestratorResult(
                status=OrchestratorStatus.COMPLETED_NO_REVIEW,
                task=task,
                builder_result=builder_result,
                token_usage=token_usage,
                iterations=builder_result.iterations,
            )

        if critic_result.verdict == CriticVerdict.APPROVED:
            logger.info("Task approved by Critic")
            return OrchestratorResult(
                status=OrchestratorStatus.SUCCESS,
                task=task,
                builder_result=builder_result,
                critic_result=critic_result,
                token_usage=token_usage,
                iterations=builder_result.iterations,
                rate_limit_retries=rate_limit_retries,
            )

        elif critic_result.verdict == CriticVerdict.NEEDS_REVISION:
            logger.info("Critic requested revisions")
            return OrchestratorResult(
                status=OrchestratorStatus.NEEDS_REVISION,
                task=task,
                builder_result=builder_result,
                critic_result=critic_result,
                token_usage=token_usage,
                iterations=builder_result.iterations,
                rate_limit_retries=rate_limit_retries,
            )

        else:  # BLOCKED
            logger.warning("Critic review blocked")
            return OrchestratorResult(
                status=OrchestratorStatus.BLOCKED,
                task=task,
                builder_result=builder_result,
                critic_result=critic_result,
                token_usage=token_usage,
                iterations=builder_result.iterations,
                rate_limit_retries=rate_limit_retries,
                error=critic_result.feedback,
            )

    def _calculate_retry_delay(
        self,
        attempt: int,
        retry_after: Optional[float] = None,
    ) -> float:
        """Calculate delay for exponential backoff.

        Args:
            attempt: Current attempt number (0-indexed).
            retry_after: Optional server-specified delay.

        Returns:
            Delay in seconds.
        """
        if retry_after is not None:
            return retry_after

        # Exponential backoff: 2, 4, 8, 16, ...
        return self._base_retry_delay * (2 ** attempt)

    async def execute_iteration(
        self,
        task: dict[str, Any],
        tools: Optional[list[Tool]] = None,
        context: Optional[str] = None,
        memory_context: Optional[str] = None,
        max_revision_attempts: int = 2,
    ) -> OrchestratorResult:
        """Execute a complete iteration with revision loop.

        This method runs the Builder → Critic cycle and can retry
        on NEEDS_REVISION up to max_revision_attempts times.

        Args:
            task: Task dictionary.
            tools: Available tools.
            context: Project context.
            memory_context: Relevant memories.
            max_revision_attempts: Max times to retry on NEEDS_REVISION.

        Returns:
            Final OrchestratorResult.
        """
        last_result: Optional[OrchestratorResult] = None

        for revision_attempt in range(max_revision_attempts):
            logger.debug(f"Revision attempt {revision_attempt + 1}/{max_revision_attempts}")

            # Add revision context if this is a retry
            revision_context = context
            if last_result and last_result.critic_result:
                feedback = last_result.critic_result.feedback
                revision_context = f"{context or ''}\n\n## Previous Review Feedback\n{feedback}"

            result = await self.execute_task(
                task=task,
                tools=tools,
                context=revision_context,
                memory_context=memory_context,
            )

            last_result = result

            # Stop if we get a final status
            if result.status != OrchestratorStatus.NEEDS_REVISION:
                return result

            logger.info(f"Critic requested revision (attempt {revision_attempt + 1})")

        # Max revisions reached, return last result
        return last_result or OrchestratorResult(
            status=OrchestratorStatus.ERROR,
            task=task,
            error="No result produced",
        )
