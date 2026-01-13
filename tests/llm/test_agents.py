"""Tests for Builder and Critic agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from ralph_agi.llm.agents import (
    AgentStatus,
    BuilderAgent,
    BuilderResult,
    CriticAgent,
    CriticResult,
    CriticVerdict,
    ToolExecutionRecord,
)
from ralph_agi.llm.client import LLMResponse, StopReason, ToolCall


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock LLM client."""
    client = MagicMock()
    client.complete = AsyncMock()
    return client


@pytest.fixture
def mock_tool_executor() -> MagicMock:
    """Create a mock tool executor."""
    executor = MagicMock()
    executor.execute = AsyncMock()
    return executor


@pytest.fixture
def sample_task() -> dict[str, Any]:
    """Create a sample task."""
    return {
        "title": "Add user validation",
        "description": "Add email validation to user registration.",
        "acceptance_criteria": [
            "Email format is validated",
            "Invalid emails are rejected",
        ],
    }


# =============================================================================
# BuilderResult Tests
# =============================================================================


class TestBuilderResult:
    """Tests for BuilderResult dataclass."""

    def test_is_complete_when_completed(self) -> None:
        """Test is_complete returns True for COMPLETED status."""
        result = BuilderResult(
            status=AgentStatus.COMPLETED,
            task={"title": "Test"},
        )
        assert result.is_complete is True

    def test_is_complete_when_not_completed(self) -> None:
        """Test is_complete returns False for other statuses."""
        result = BuilderResult(
            status=AgentStatus.RUNNING,
            task={"title": "Test"},
        )
        assert result.is_complete is False

    def test_is_blocked(self) -> None:
        """Test is_blocked property."""
        result = BuilderResult(
            status=AgentStatus.BLOCKED,
            task={"title": "Test"},
            error="Missing credentials",
        )
        assert result.is_blocked is True


class TestCriticResult:
    """Tests for CriticResult dataclass."""

    def test_is_approved_when_approved(self) -> None:
        """Test is_approved returns True for APPROVED verdict."""
        result = CriticResult(
            verdict=CriticVerdict.APPROVED,
            feedback="Looks good!",
        )
        assert result.is_approved is True

    def test_is_approved_when_not_approved(self) -> None:
        """Test is_approved returns False for other verdicts."""
        result = CriticResult(
            verdict=CriticVerdict.NEEDS_REVISION,
            feedback="Issues found",
        )
        assert result.is_approved is False


# =============================================================================
# BuilderAgent Tests
# =============================================================================


class TestBuilderAgentInit:
    """Tests for BuilderAgent initialization."""

    def test_default_init(self, mock_client: MagicMock) -> None:
        """Test default initialization."""
        agent = BuilderAgent(mock_client)

        assert agent._client == mock_client
        assert agent._tool_executor is None
        assert agent._max_iterations == 10
        assert agent._max_tokens == 4096

    def test_custom_init(
        self,
        mock_client: MagicMock,
        mock_tool_executor: MagicMock,
    ) -> None:
        """Test custom initialization."""
        agent = BuilderAgent(
            mock_client,
            tool_executor=mock_tool_executor,
            max_iterations=20,
            max_tokens=8192,
        )

        assert agent._tool_executor == mock_tool_executor
        assert agent._max_iterations == 20
        assert agent._max_tokens == 8192


class TestBuilderAgentExecute:
    """Tests for BuilderAgent.execute method."""

    @pytest.mark.asyncio
    async def test_completes_on_done_signal(
        self,
        mock_client: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test that agent completes when DONE signal is found."""
        # Mock response with completion signal
        mock_client.complete.return_value = LLMResponse(
            content="Done!\n<task_complete>DONE</task_complete>",
            stop_reason=StopReason.END_TURN,
            usage={"input_tokens": 100, "output_tokens": 50},
        )

        agent = BuilderAgent(mock_client)
        result = await agent.execute(sample_task)

        assert result.status == AgentStatus.COMPLETED
        assert result.iterations == 1
        assert result.total_tokens == 150

    @pytest.mark.asyncio
    async def test_blocked_on_blocked_signal(
        self,
        mock_client: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test that agent returns BLOCKED when blocked signal is found."""
        mock_client.complete.return_value = LLMResponse(
            content="<task_complete>BLOCKED: Missing API key</task_complete>",
            stop_reason=StopReason.END_TURN,
        )

        agent = BuilderAgent(mock_client)
        result = await agent.execute(sample_task)

        assert result.status == AgentStatus.BLOCKED
        assert "BLOCKED" in result.error

    @pytest.mark.asyncio
    async def test_max_iterations_reached(
        self,
        mock_client: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test that agent stops at max iterations."""
        # Response without completion signal
        mock_client.complete.return_value = LLMResponse(
            content="Still working...",
            stop_reason=StopReason.END_TURN,
        )

        agent = BuilderAgent(mock_client, max_iterations=3)
        result = await agent.execute(sample_task)

        assert result.status == AgentStatus.MAX_ITERATIONS
        assert result.iterations == 3
        assert mock_client.complete.call_count == 3

    @pytest.mark.asyncio
    async def test_executes_tool_calls(
        self,
        mock_client: MagicMock,
        mock_tool_executor: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test that tool calls are executed."""
        # First response with tool call
        tool_call = ToolCall(
            id="tc_1",
            name="read_file",
            arguments={"path": "/test.txt"},
        )
        first_response = LLMResponse(
            content="Let me read the file.",
            stop_reason=StopReason.TOOL_USE,
            tool_calls=[tool_call],
        )

        # Second response with completion
        second_response = LLMResponse(
            content="Done!\n<task_complete>DONE</task_complete>",
            stop_reason=StopReason.END_TURN,
        )

        mock_client.complete.side_effect = [first_response, second_response]

        # Mock tool execution result
        mock_result = MagicMock()
        mock_result.get_text.return_value = "file contents"
        mock_result.is_success.return_value = True
        mock_tool_executor.execute.return_value = mock_result

        agent = BuilderAgent(mock_client, tool_executor=mock_tool_executor)
        result = await agent.execute(sample_task)

        assert result.status == AgentStatus.COMPLETED
        assert result.iterations == 2
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "read_file"

    @pytest.mark.asyncio
    async def test_tracks_file_changes(
        self,
        mock_client: MagicMock,
        mock_tool_executor: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test that file changes are tracked."""
        # Response with write_file tool call
        tool_call = ToolCall(
            id="tc_1",
            name="write_file",
            arguments={"path": "/src/validation.py", "content": "code"},
        )
        first_response = LLMResponse(
            content="Writing file.",
            stop_reason=StopReason.TOOL_USE,
            tool_calls=[tool_call],
        )
        second_response = LLMResponse(
            content="<task_complete>DONE</task_complete>",
            stop_reason=StopReason.END_TURN,
        )

        mock_client.complete.side_effect = [first_response, second_response]

        mock_result = MagicMock()
        mock_result.get_text.return_value = "written"
        mock_result.is_success.return_value = True
        mock_tool_executor.execute.return_value = mock_result

        agent = BuilderAgent(mock_client, tool_executor=mock_tool_executor)
        result = await agent.execute(sample_task)

        assert "/src/validation.py" in result.files_changed

    @pytest.mark.asyncio
    async def test_handles_tool_execution_error(
        self,
        mock_client: MagicMock,
        mock_tool_executor: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test that tool execution errors are handled."""
        tool_call = ToolCall(
            id="tc_1",
            name="read_file",
            arguments={"path": "/nonexistent.txt"},
        )
        first_response = LLMResponse(
            content="Reading file.",
            stop_reason=StopReason.TOOL_USE,
            tool_calls=[tool_call],
        )
        second_response = LLMResponse(
            content="<task_complete>DONE</task_complete>",
            stop_reason=StopReason.END_TURN,
        )

        mock_client.complete.side_effect = [first_response, second_response]
        mock_tool_executor.execute.side_effect = Exception("File not found")

        agent = BuilderAgent(mock_client, tool_executor=mock_tool_executor)
        result = await agent.execute(sample_task)

        assert result.status == AgentStatus.COMPLETED
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].success is False

    @pytest.mark.asyncio
    async def test_passes_context_and_memory(
        self,
        mock_client: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test that context and memory are passed to LLM."""
        mock_client.complete.return_value = LLMResponse(
            content="<task_complete>DONE</task_complete>",
            stop_reason=StopReason.END_TURN,
        )

        agent = BuilderAgent(mock_client)
        await agent.execute(
            sample_task,
            context="Using FastAPI framework.",
            memory_context="Previously added similar validation.",
        )

        # Check that prompt includes context
        call_args = mock_client.complete.call_args
        messages = call_args.kwargs["messages"]
        user_content = messages[0]["content"]

        assert "FastAPI" in user_content
        assert "Previously added" in user_content

    @pytest.mark.asyncio
    async def test_error_status_on_exception(
        self,
        mock_client: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test that ERROR status is returned on exception."""
        mock_client.complete.side_effect = Exception("API error")

        agent = BuilderAgent(mock_client)
        result = await agent.execute(sample_task)

        assert result.status == AgentStatus.ERROR
        assert "API error" in result.error


class TestBuilderAgentBuildAssistantMessage:
    """Tests for _build_assistant_message method."""

    def test_text_only_response(self, mock_client: MagicMock) -> None:
        """Test building message with text only."""
        agent = BuilderAgent(mock_client)
        response = LLMResponse(
            content="Hello!",
            stop_reason=StopReason.END_TURN,
        )

        message = agent._build_assistant_message(response)

        assert message["role"] == "assistant"
        assert len(message["content"]) == 1
        assert message["content"][0]["type"] == "text"
        assert message["content"][0]["text"] == "Hello!"

    def test_response_with_tool_calls(self, mock_client: MagicMock) -> None:
        """Test building message with tool calls."""
        agent = BuilderAgent(mock_client)
        response = LLMResponse(
            content="Using tool.",
            stop_reason=StopReason.TOOL_USE,
            tool_calls=[
                ToolCall(id="tc_1", name="read_file", arguments={"path": "/test"}),
            ],
        )

        message = agent._build_assistant_message(response)

        assert len(message["content"]) == 2
        assert message["content"][0]["type"] == "text"
        assert message["content"][1]["type"] == "tool_use"
        assert message["content"][1]["id"] == "tc_1"
        assert message["content"][1]["name"] == "read_file"


# =============================================================================
# CriticAgent Tests
# =============================================================================


class TestCriticAgentInit:
    """Tests for CriticAgent initialization."""

    def test_default_init(self, mock_client: MagicMock) -> None:
        """Test default initialization."""
        agent = CriticAgent(mock_client)

        assert agent._client == mock_client
        assert agent._max_tokens == 4096

    def test_custom_init(self, mock_client: MagicMock) -> None:
        """Test custom initialization."""
        agent = CriticAgent(mock_client, max_tokens=8192)

        assert agent._max_tokens == 8192


class TestCriticAgentReview:
    """Tests for CriticAgent.review method."""

    @pytest.mark.asyncio
    async def test_approved_verdict(
        self,
        mock_client: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test that APPROVED verdict is correctly parsed."""
        mock_client.complete.return_value = LLMResponse(
            content="VERDICT: APPROVED\n\nThe code looks good.",
            stop_reason=StopReason.END_TURN,
            usage={"input_tokens": 100, "output_tokens": 50},
        )

        builder_result = BuilderResult(
            status=AgentStatus.COMPLETED,
            task=sample_task,
            final_response="Added validation.",
        )

        agent = CriticAgent(mock_client)
        result = await agent.review(sample_task, builder_result)

        assert result.verdict == CriticVerdict.APPROVED
        assert result.is_approved is True
        assert result.total_tokens == 150

    @pytest.mark.asyncio
    async def test_needs_revision_verdict(
        self,
        mock_client: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test that NEEDS_REVISION verdict is correctly parsed."""
        mock_client.complete.return_value = LLMResponse(
            content="""VERDICT: NEEDS_REVISION

Issues found:
1. Missing error handling
2. No input sanitization

Suggestions:
- Add try/catch blocks
- Validate input before processing""",
            stop_reason=StopReason.END_TURN,
        )

        builder_result = BuilderResult(
            status=AgentStatus.COMPLETED,
            task=sample_task,
        )

        agent = CriticAgent(mock_client)
        result = await agent.review(sample_task, builder_result)

        assert result.verdict == CriticVerdict.NEEDS_REVISION
        assert result.is_approved is False
        assert len(result.issues) >= 1
        assert len(result.suggestions) >= 1

    @pytest.mark.asyncio
    async def test_blocked_verdict(
        self,
        mock_client: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test that BLOCKED verdict is correctly parsed."""
        mock_client.complete.return_value = LLMResponse(
            content="VERDICT: BLOCKED\n\nCannot review without test files.",
            stop_reason=StopReason.END_TURN,
        )

        builder_result = BuilderResult(
            status=AgentStatus.COMPLETED,
            task=sample_task,
        )

        agent = CriticAgent(mock_client)
        result = await agent.review(sample_task, builder_result)

        assert result.verdict == CriticVerdict.BLOCKED

    @pytest.mark.asyncio
    async def test_includes_files_changed(
        self,
        mock_client: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test that files_changed are included in review."""
        mock_client.complete.return_value = LLMResponse(
            content="VERDICT: APPROVED",
            stop_reason=StopReason.END_TURN,
        )

        builder_result = BuilderResult(
            status=AgentStatus.COMPLETED,
            task=sample_task,
            files_changed=["/src/auth.py", "/tests/test_auth.py"],
        )

        agent = CriticAgent(mock_client)
        await agent.review(sample_task, builder_result)

        # Check that files were included in prompt
        call_args = mock_client.complete.call_args
        messages = call_args.kwargs["messages"]
        user_content = messages[0]["content"]

        assert "/src/auth.py" in user_content
        assert "/tests/test_auth.py" in user_content

    @pytest.mark.asyncio
    async def test_handles_error(
        self,
        mock_client: MagicMock,
        sample_task: dict[str, Any],
    ) -> None:
        """Test that errors are handled gracefully."""
        mock_client.complete.side_effect = Exception("API error")

        builder_result = BuilderResult(
            status=AgentStatus.COMPLETED,
            task=sample_task,
        )

        agent = CriticAgent(mock_client)
        result = await agent.review(sample_task, builder_result)

        assert result.verdict == CriticVerdict.BLOCKED
        assert "failed" in result.feedback.lower()


class TestCriticAgentBuildChangesSummary:
    """Tests for _build_changes_summary method."""

    def test_includes_final_response(self, mock_client: MagicMock) -> None:
        """Test that final response is included."""
        agent = CriticAgent(mock_client)
        builder_result = BuilderResult(
            status=AgentStatus.COMPLETED,
            task={"title": "Test"},
            final_response="I added the validation logic.",
        )

        summary = agent._build_changes_summary(builder_result)

        assert "validation logic" in summary
        assert "Builder's Summary" in summary

    def test_includes_tool_calls(self, mock_client: MagicMock) -> None:
        """Test that tool calls are included."""
        agent = CriticAgent(mock_client)
        builder_result = BuilderResult(
            status=AgentStatus.COMPLETED,
            task={"title": "Test"},
            tool_calls=[
                ToolExecutionRecord(
                    tool_name="write_file",
                    arguments={"path": "/test.py"},
                    result="success",
                    success=True,
                    iteration=1,
                ),
            ],
        )

        summary = agent._build_changes_summary(builder_result)

        assert "write_file" in summary
        assert "Tool Executions" in summary

    def test_includes_files_changed(self, mock_client: MagicMock) -> None:
        """Test that files changed are included."""
        agent = CriticAgent(mock_client)
        builder_result = BuilderResult(
            status=AgentStatus.COMPLETED,
            task={"title": "Test"},
            files_changed=["/src/auth.py"],
        )

        summary = agent._build_changes_summary(builder_result)

        assert "/src/auth.py" in summary
        assert "Files Modified" in summary


class TestCriticAgentParseFeedback:
    """Tests for _parse_feedback method."""

    def test_parses_numbered_issues(self, mock_client: MagicMock) -> None:
        """Test parsing numbered issues."""
        agent = CriticAgent(mock_client)
        feedback = """Issues found:
1. Missing error handling
2. No input validation
3. SQL injection risk"""

        issues, suggestions = agent._parse_feedback(feedback)

        assert len(issues) >= 2

    def test_parses_suggestions(self, mock_client: MagicMock) -> None:
        """Test parsing suggestions."""
        agent = CriticAgent(mock_client)
        feedback = """Suggestions:
- Add try/catch blocks
- Use parameterized queries
- Add input sanitization"""

        issues, suggestions = agent._parse_feedback(feedback)

        assert len(suggestions) >= 2

    def test_handles_empty_feedback(self, mock_client: MagicMock) -> None:
        """Test handling empty feedback."""
        agent = CriticAgent(mock_client)

        issues, suggestions = agent._parse_feedback("")

        assert issues == []
        assert suggestions == []
