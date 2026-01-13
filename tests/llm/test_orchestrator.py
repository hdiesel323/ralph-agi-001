"""Tests for LLM Orchestrator."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ralph_agi.llm.agents import (
    AgentStatus,
    BuilderResult,
    CriticResult,
    CriticVerdict,
)
from ralph_agi.llm.client import RateLimitError
from ralph_agi.llm.orchestrator import (
    LLMOrchestrator,
    OrchestratorResult,
    OrchestratorStatus,
    TokenUsage,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_builder() -> MagicMock:
    """Create a mock Builder agent."""
    builder = MagicMock()
    builder.execute = AsyncMock()
    return builder


@pytest.fixture
def mock_critic() -> MagicMock:
    """Create a mock Critic agent."""
    critic = MagicMock()
    critic.review = AsyncMock()
    return critic


@pytest.fixture
def sample_task() -> dict[str, Any]:
    """Create a sample task."""
    return {
        "title": "Add validation",
        "description": "Add input validation to the form.",
    }


@pytest.fixture
def completed_builder_result(sample_task: dict[str, Any]) -> BuilderResult:
    """Create a completed Builder result."""
    return BuilderResult(
        status=AgentStatus.COMPLETED,
        task=sample_task,
        iterations=3,
        total_tokens=500,
        files_changed=["/src/form.py"],
    )


@pytest.fixture
def approved_critic_result() -> CriticResult:
    """Create an approved Critic result."""
    return CriticResult(
        verdict=CriticVerdict.APPROVED,
        feedback="Code looks good!",
        total_tokens=200,
    )


# =============================================================================
# TokenUsage Tests
# =============================================================================


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""

    def test_initial_values(self) -> None:
        """Test initial values are zero."""
        usage = TokenUsage()

        assert usage.builder_input == 0
        assert usage.builder_output == 0
        assert usage.critic_input == 0
        assert usage.critic_output == 0
        assert usage.total == 0

    def test_total_input(self) -> None:
        """Test total_input calculation."""
        usage = TokenUsage(builder_input=100, critic_input=50)

        assert usage.total_input == 150

    def test_total_output(self) -> None:
        """Test total_output calculation."""
        usage = TokenUsage(builder_output=100, critic_output=50)

        assert usage.total_output == 150

    def test_total(self) -> None:
        """Test total calculation."""
        usage = TokenUsage(
            builder_input=100,
            builder_output=50,
            critic_input=80,
            critic_output=20,
        )

        assert usage.total == 250

    def test_add_builder_usage(self) -> None:
        """Test adding Builder token usage."""
        usage = TokenUsage()
        usage.add_builder_usage(1000)

        assert usage.builder_input == 700  # 70%
        assert usage.builder_output == 300  # 30%

    def test_add_critic_usage(self) -> None:
        """Test adding Critic token usage."""
        usage = TokenUsage()
        usage.add_critic_usage(1000)

        assert usage.critic_input == 800  # 80%
        assert usage.critic_output == 200  # 20%


# =============================================================================
# OrchestratorResult Tests
# =============================================================================


class TestOrchestratorResult:
    """Tests for OrchestratorResult dataclass."""

    def test_is_success_for_success(self) -> None:
        """Test is_success for SUCCESS status."""
        result = OrchestratorResult(
            status=OrchestratorStatus.SUCCESS,
            task={"title": "Test"},
        )

        assert result.is_success is True

    def test_is_success_for_completed_no_review(self) -> None:
        """Test is_success for COMPLETED_NO_REVIEW status."""
        result = OrchestratorResult(
            status=OrchestratorStatus.COMPLETED_NO_REVIEW,
            task={"title": "Test"},
        )

        assert result.is_success is True

    def test_is_success_for_error(self) -> None:
        """Test is_success for ERROR status."""
        result = OrchestratorResult(
            status=OrchestratorStatus.ERROR,
            task={"title": "Test"},
        )

        assert result.is_success is False

    def test_files_changed_from_builder(
        self,
        completed_builder_result: BuilderResult,
    ) -> None:
        """Test files_changed comes from builder_result."""
        result = OrchestratorResult(
            status=OrchestratorStatus.SUCCESS,
            task={"title": "Test"},
            builder_result=completed_builder_result,
        )

        assert result.files_changed == ["/src/form.py"]

    def test_files_changed_empty_without_builder(self) -> None:
        """Test files_changed is empty without builder_result."""
        result = OrchestratorResult(
            status=OrchestratorStatus.ERROR,
            task={"title": "Test"},
        )

        assert result.files_changed == []


# =============================================================================
# LLMOrchestrator Initialization Tests
# =============================================================================


class TestOrchestratorInit:
    """Tests for LLMOrchestrator initialization."""

    def test_default_init(self, mock_builder: MagicMock) -> None:
        """Test default initialization."""
        orchestrator = LLMOrchestrator(mock_builder)

        assert orchestrator._builder == mock_builder
        assert orchestrator._critic is None
        assert orchestrator._critic_enabled is False
        assert orchestrator._max_rate_limit_retries == 3
        assert orchestrator._base_retry_delay == 2.0

    def test_with_critic(
        self,
        mock_builder: MagicMock,
        mock_critic: MagicMock,
    ) -> None:
        """Test initialization with Critic."""
        orchestrator = LLMOrchestrator(mock_builder, critic=mock_critic)

        assert orchestrator._critic == mock_critic
        assert orchestrator._critic_enabled is True

    def test_critic_disabled_explicitly(
        self,
        mock_builder: MagicMock,
        mock_critic: MagicMock,
    ) -> None:
        """Test explicitly disabling Critic."""
        orchestrator = LLMOrchestrator(
            mock_builder,
            critic=mock_critic,
            critic_enabled=False,
        )

        assert orchestrator._critic_enabled is False

    def test_custom_retry_settings(self, mock_builder: MagicMock) -> None:
        """Test custom retry settings."""
        orchestrator = LLMOrchestrator(
            mock_builder,
            max_rate_limit_retries=5,
            base_retry_delay=1.0,
        )

        assert orchestrator._max_rate_limit_retries == 5
        assert orchestrator._base_retry_delay == 1.0


# =============================================================================
# LLMOrchestrator.execute_task Tests
# =============================================================================


class TestOrchestratorExecuteTask:
    """Tests for execute_task method."""

    @pytest.mark.asyncio
    async def test_success_with_critic_approval(
        self,
        mock_builder: MagicMock,
        mock_critic: MagicMock,
        sample_task: dict[str, Any],
        completed_builder_result: BuilderResult,
        approved_critic_result: CriticResult,
    ) -> None:
        """Test successful execution with Critic approval."""
        mock_builder.execute.return_value = completed_builder_result
        mock_critic.review.return_value = approved_critic_result

        orchestrator = LLMOrchestrator(mock_builder, critic=mock_critic)
        result = await orchestrator.execute_task(sample_task)

        assert result.status == OrchestratorStatus.SUCCESS
        assert result.is_success is True
        assert result.builder_result == completed_builder_result
        assert result.critic_result == approved_critic_result

    @pytest.mark.asyncio
    async def test_completed_without_critic(
        self,
        mock_builder: MagicMock,
        sample_task: dict[str, Any],
        completed_builder_result: BuilderResult,
    ) -> None:
        """Test completion without Critic."""
        mock_builder.execute.return_value = completed_builder_result

        orchestrator = LLMOrchestrator(mock_builder)
        result = await orchestrator.execute_task(sample_task)

        assert result.status == OrchestratorStatus.COMPLETED_NO_REVIEW
        assert result.is_success is True
        assert result.critic_result is None

    @pytest.mark.asyncio
    async def test_needs_revision_verdict(
        self,
        mock_builder: MagicMock,
        mock_critic: MagicMock,
        sample_task: dict[str, Any],
        completed_builder_result: BuilderResult,
    ) -> None:
        """Test NEEDS_REVISION verdict from Critic."""
        mock_builder.execute.return_value = completed_builder_result
        mock_critic.review.return_value = CriticResult(
            verdict=CriticVerdict.NEEDS_REVISION,
            feedback="Missing error handling",
            issues=["No try/catch blocks"],
        )

        orchestrator = LLMOrchestrator(mock_builder, critic=mock_critic)
        result = await orchestrator.execute_task(sample_task)

        assert result.status == OrchestratorStatus.NEEDS_REVISION

    @pytest.mark.asyncio
    async def test_builder_blocked(
        self,
        mock_builder: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test when Builder is blocked."""
        mock_builder.execute.return_value = BuilderResult(
            status=AgentStatus.BLOCKED,
            task=sample_task,
            error="Missing API credentials",
        )

        orchestrator = LLMOrchestrator(mock_builder)
        result = await orchestrator.execute_task(sample_task)

        assert result.status == OrchestratorStatus.BLOCKED
        assert "credentials" in result.error

    @pytest.mark.asyncio
    async def test_builder_error(
        self,
        mock_builder: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test when Builder encounters error."""
        mock_builder.execute.return_value = BuilderResult(
            status=AgentStatus.ERROR,
            task=sample_task,
            error="API failure",
        )

        orchestrator = LLMOrchestrator(mock_builder)
        result = await orchestrator.execute_task(sample_task)

        assert result.status == OrchestratorStatus.ERROR

    @pytest.mark.asyncio
    async def test_rate_limit_retry(
        self,
        mock_builder: MagicMock,
        sample_task: dict[str, Any],
        completed_builder_result: BuilderResult,
    ) -> None:
        """Test rate limit retry with eventual success."""
        # First call fails, second succeeds
        mock_builder.execute.side_effect = [
            RateLimitError("Rate limited", retry_after=0.01),
            completed_builder_result,
        ]

        orchestrator = LLMOrchestrator(
            mock_builder,
            base_retry_delay=0.01,  # Fast for testing
        )
        result = await orchestrator.execute_task(sample_task)

        assert result.status == OrchestratorStatus.COMPLETED_NO_REVIEW
        assert result.rate_limit_retries == 1
        assert mock_builder.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_exhausted(
        self,
        mock_builder: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test rate limit retries exhausted."""
        mock_builder.execute.side_effect = RateLimitError("Rate limited")

        orchestrator = LLMOrchestrator(
            mock_builder,
            max_rate_limit_retries=2,
            base_retry_delay=0.01,
        )
        result = await orchestrator.execute_task(sample_task)

        assert result.status == OrchestratorStatus.MAX_RETRIES
        assert mock_builder.execute.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_token_usage_tracking(
        self,
        mock_builder: MagicMock,
        mock_critic: MagicMock,
        sample_task: dict[str, Any],
        completed_builder_result: BuilderResult,
        approved_critic_result: CriticResult,
    ) -> None:
        """Test token usage is tracked correctly."""
        mock_builder.execute.return_value = completed_builder_result
        mock_critic.review.return_value = approved_critic_result

        orchestrator = LLMOrchestrator(mock_builder, critic=mock_critic)
        result = await orchestrator.execute_task(sample_task)

        assert result.token_usage.total > 0
        # Builder: 500 tokens (70% input, 30% output)
        assert result.token_usage.builder_input == 350
        assert result.token_usage.builder_output == 150
        # Critic: 200 tokens (80% input, 20% output)
        assert result.token_usage.critic_input == 160
        assert result.token_usage.critic_output == 40


# =============================================================================
# LLMOrchestrator.execute_iteration Tests
# =============================================================================


class TestOrchestratorExecuteIteration:
    """Tests for execute_iteration method with revision loop."""

    @pytest.mark.asyncio
    async def test_first_attempt_success(
        self,
        mock_builder: MagicMock,
        mock_critic: MagicMock,
        sample_task: dict[str, Any],
        completed_builder_result: BuilderResult,
        approved_critic_result: CriticResult,
    ) -> None:
        """Test success on first attempt."""
        mock_builder.execute.return_value = completed_builder_result
        mock_critic.review.return_value = approved_critic_result

        orchestrator = LLMOrchestrator(mock_builder, critic=mock_critic)
        result = await orchestrator.execute_iteration(sample_task)

        assert result.status == OrchestratorStatus.SUCCESS
        assert mock_builder.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_revision_then_approval(
        self,
        mock_builder: MagicMock,
        mock_critic: MagicMock,
        sample_task: dict[str, Any],
        completed_builder_result: BuilderResult,
    ) -> None:
        """Test revision loop with eventual approval."""
        mock_builder.execute.return_value = completed_builder_result

        # First review: needs revision, second: approved
        mock_critic.review.side_effect = [
            CriticResult(
                verdict=CriticVerdict.NEEDS_REVISION,
                feedback="Add error handling",
            ),
            CriticResult(
                verdict=CriticVerdict.APPROVED,
                feedback="Looks good now!",
            ),
        ]

        orchestrator = LLMOrchestrator(mock_builder, critic=mock_critic)
        result = await orchestrator.execute_iteration(sample_task)

        assert result.status == OrchestratorStatus.SUCCESS
        assert mock_builder.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_max_revisions_reached(
        self,
        mock_builder: MagicMock,
        mock_critic: MagicMock,
        sample_task: dict[str, Any],
        completed_builder_result: BuilderResult,
    ) -> None:
        """Test max revision attempts reached."""
        mock_builder.execute.return_value = completed_builder_result
        mock_critic.review.return_value = CriticResult(
            verdict=CriticVerdict.NEEDS_REVISION,
            feedback="Still has issues",
        )

        orchestrator = LLMOrchestrator(mock_builder, critic=mock_critic)
        result = await orchestrator.execute_iteration(
            sample_task,
            max_revision_attempts=2,
        )

        assert result.status == OrchestratorStatus.NEEDS_REVISION
        assert mock_builder.execute.call_count == 2


# =============================================================================
# Retry Delay Tests
# =============================================================================


class TestCalculateRetryDelay:
    """Tests for _calculate_retry_delay method."""

    def test_uses_retry_after_if_provided(self, mock_builder: MagicMock) -> None:
        """Test that retry_after is used when provided."""
        orchestrator = LLMOrchestrator(mock_builder)

        delay = orchestrator._calculate_retry_delay(0, retry_after=30.0)

        assert delay == 30.0

    def test_exponential_backoff(self, mock_builder: MagicMock) -> None:
        """Test exponential backoff calculation."""
        orchestrator = LLMOrchestrator(mock_builder, base_retry_delay=2.0)

        assert orchestrator._calculate_retry_delay(0) == 2.0  # 2 * 2^0
        assert orchestrator._calculate_retry_delay(1) == 4.0  # 2 * 2^1
        assert orchestrator._calculate_retry_delay(2) == 8.0  # 2 * 2^2
        assert orchestrator._calculate_retry_delay(3) == 16.0  # 2 * 2^3
