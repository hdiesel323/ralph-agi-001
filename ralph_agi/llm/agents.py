"""Agent implementations for RALPH-AGI.

This module provides the Builder and Critic agents that work together
in the multi-agent architecture defined in ADR-002.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable

from ralph_agi.llm.client import LLMResponse, StopReason, Tool, ToolCall
from ralph_agi.llm.prompts import (
    BUILDER_SYSTEM_PROMPT,
    CRITIC_SYSTEM_PROMPT,
    build_review_prompt,
    build_task_prompt,
    extract_completion_signal,
    extract_critic_verdict,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Types and Protocols
# =============================================================================


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM clients."""

    async def complete(
        self,
        messages: list[dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[list[Tool]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse: ...


@runtime_checkable
class ToolExecutorProtocol(Protocol):
    """Protocol for tool executors."""

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any: ...


class AgentStatus(Enum):
    """Status of an agent execution."""

    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    MAX_ITERATIONS = "max_iterations"
    ERROR = "error"


class CriticVerdict(Enum):
    """Critic review verdict."""

    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    BLOCKED = "blocked"


# =============================================================================
# Result Data Classes
# =============================================================================


@dataclass
class ToolExecutionRecord:
    """Record of a tool execution during agent work."""

    tool_name: str
    arguments: dict[str, Any]
    result: str
    success: bool
    iteration: int


@dataclass
class BuilderResult:
    """Result from Builder agent execution.

    Attributes:
        status: Final status of the execution.
        task: The task that was being executed.
        iterations: Number of LLM calls made.
        tool_calls: List of tool executions.
        final_response: Last LLM response content.
        files_changed: List of files modified (if tracked).
        total_tokens: Total tokens used.
        error: Error message if failed.
    """

    status: AgentStatus
    task: dict[str, Any]
    iterations: int = 0
    tool_calls: list[ToolExecutionRecord] = field(default_factory=list)
    final_response: str = ""
    files_changed: list[str] = field(default_factory=list)
    total_tokens: int = 0
    error: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        """Check if task was completed successfully."""
        return self.status == AgentStatus.COMPLETED

    @property
    def is_blocked(self) -> bool:
        """Check if task is blocked."""
        return self.status == AgentStatus.BLOCKED


@dataclass
class CriticResult:
    """Result from Critic agent review.

    Attributes:
        verdict: The review verdict.
        feedback: Detailed feedback from the critic.
        issues: List of specific issues found.
        suggestions: List of suggestions for improvement.
        total_tokens: Total tokens used.
    """

    verdict: CriticVerdict
    feedback: str
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    total_tokens: int = 0

    @property
    def is_approved(self) -> bool:
        """Check if the review was approved."""
        return self.verdict == CriticVerdict.APPROVED


# =============================================================================
# Builder Agent
# =============================================================================


class BuilderAgent:
    """Builder agent that executes tasks using a tool loop.

    The Builder agent is the primary worker in RALPH-AGI. It:
    1. Receives a task to complete
    2. Calls the LLM with available tools
    3. Executes any tool calls from the LLM
    4. Continues until task completion or max iterations

    Attributes:
        client: LLM client for generating responses.
        tool_executor: Executor for running tools.
        max_iterations: Maximum LLM calls per task.
        max_tokens: Maximum tokens per LLM call.

    Example:
        >>> builder = BuilderAgent(client, tool_executor)
        >>> result = await builder.execute(task, tools)
        >>> if result.is_complete:
        ...     print("Task completed!")
    """

    DEFAULT_MAX_ITERATIONS = 10
    DEFAULT_MAX_TOKENS = 4096

    def __init__(
        self,
        client: LLMClient,
        tool_executor: Optional[ToolExecutorProtocol] = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """Initialize the Builder agent.

        Args:
            client: LLM client for completions.
            tool_executor: Executor for running tools (optional).
            max_iterations: Max LLM calls per task.
            max_tokens: Max tokens per LLM call.
        """
        self._client = client
        self._tool_executor = tool_executor
        self._max_iterations = max_iterations
        self._max_tokens = max_tokens

    async def execute(
        self,
        task: dict[str, Any],
        tools: Optional[list[Tool]] = None,
        context: Optional[str] = None,
        memory_context: Optional[str] = None,
    ) -> BuilderResult:
        """Execute a task using the tool loop.

        Args:
            task: Task dictionary with title, description, etc.
            tools: List of tools available to the agent.
            context: Optional project context.
            memory_context: Optional relevant memories.

        Returns:
            BuilderResult with execution details.
        """
        tools = tools or []
        messages: list[dict[str, Any]] = []
        tool_records: list[ToolExecutionRecord] = []
        total_tokens = 0
        files_changed: list[str] = []

        # Build initial task prompt
        task_prompt = build_task_prompt(task, context, memory_context)
        messages.append({"role": "user", "content": task_prompt})

        logger.info(f"Builder starting task: {task.get('title', 'Unknown')}")

        for iteration in range(self._max_iterations):
            logger.debug(f"Builder iteration {iteration + 1}/{self._max_iterations}")

            try:
                # Call LLM
                response = await self._client.complete(
                    messages=messages,
                    system=BUILDER_SYSTEM_PROMPT,
                    tools=tools if tools else None,
                    max_tokens=self._max_tokens,
                )
                total_tokens += response.total_tokens

                # Add assistant response to conversation
                assistant_message = self._build_assistant_message(response)
                messages.append(assistant_message)

                # Check for completion signal in response
                is_complete, status_msg = extract_completion_signal(response.content)

                if is_complete:
                    logger.info(f"Builder completed task: {status_msg}")
                    return BuilderResult(
                        status=AgentStatus.COMPLETED,
                        task=task,
                        iterations=iteration + 1,
                        tool_calls=tool_records,
                        final_response=response.content,
                        files_changed=files_changed,
                        total_tokens=total_tokens,
                    )

                if status_msg.startswith("BLOCKED"):
                    logger.warning(f"Builder blocked: {status_msg}")
                    return BuilderResult(
                        status=AgentStatus.BLOCKED,
                        task=task,
                        iterations=iteration + 1,
                        tool_calls=tool_records,
                        final_response=response.content,
                        files_changed=files_changed,
                        total_tokens=total_tokens,
                        error=status_msg,
                    )

                # Handle tool calls
                if response.has_tool_calls:
                    tool_results = await self._execute_tools(
                        response.tool_calls,
                        iteration + 1,
                        tool_records,
                        files_changed,
                    )

                    # Add tool results to conversation
                    messages.append({"role": "user", "content": tool_results})
                elif response.stop_reason == StopReason.END_TURN:
                    # No tool calls and end of turn - task might be stuck
                    logger.debug("No tool calls and end_turn - continuing")

            except Exception as e:
                logger.error(f"Builder error on iteration {iteration + 1}: {e}")
                return BuilderResult(
                    status=AgentStatus.ERROR,
                    task=task,
                    iterations=iteration + 1,
                    tool_calls=tool_records,
                    total_tokens=total_tokens,
                    error=str(e),
                )

        # Max iterations reached
        logger.warning(f"Builder reached max iterations ({self._max_iterations})")
        return BuilderResult(
            status=AgentStatus.MAX_ITERATIONS,
            task=task,
            iterations=self._max_iterations,
            tool_calls=tool_records,
            final_response=messages[-1].get("content", "") if messages else "",
            files_changed=files_changed,
            total_tokens=total_tokens,
        )

    def _build_assistant_message(self, response: LLMResponse) -> dict[str, Any]:
        """Build assistant message from LLM response.

        Args:
            response: LLM response object.

        Returns:
            Message dict for conversation.
        """
        content: list[dict[str, Any]] = []

        # Add text content if present
        if response.content:
            content.append({"type": "text", "text": response.content})

        # Add tool use blocks
        for tc in response.tool_calls:
            content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.arguments,
            })

        return {"role": "assistant", "content": content}

    async def _execute_tools(
        self,
        tool_calls: list[ToolCall],
        iteration: int,
        records: list[ToolExecutionRecord],
        files_changed: list[str],
    ) -> list[dict[str, Any]]:
        """Execute tool calls and build result messages.

        Args:
            tool_calls: List of tool calls from LLM.
            iteration: Current iteration number.
            records: List to append execution records to.
            files_changed: List to track modified files.

        Returns:
            List of tool result message blocks.
        """
        results: list[dict[str, Any]] = []

        for tc in tool_calls:
            logger.debug(f"Executing tool: {tc.name}")

            try:
                if self._tool_executor:
                    result = await self._tool_executor.execute(tc.name, tc.arguments)
                    # Handle ToolResult from our executor
                    if hasattr(result, "get_text"):
                        result_text = result.get_text()
                        success = result.is_success() if hasattr(result, "is_success") else True
                    else:
                        result_text = str(result)
                        success = True
                else:
                    # No executor - return mock result
                    result_text = f"Tool '{tc.name}' executed (no executor configured)"
                    success = True

                # Track file changes
                if tc.name in ("write_file", "edit_file", "create_file"):
                    path = tc.arguments.get("path", tc.arguments.get("file_path", ""))
                    if path and path not in files_changed:
                        files_changed.append(path)

                records.append(ToolExecutionRecord(
                    tool_name=tc.name,
                    arguments=tc.arguments,
                    result=result_text[:500] if len(result_text) > 500 else result_text,
                    success=success,
                    iteration=iteration,
                ))

                results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": result_text,
                    "is_error": not success,
                })

            except Exception as e:
                error_msg = f"Tool execution error: {e}"
                logger.error(f"Tool {tc.name} failed: {e}")

                records.append(ToolExecutionRecord(
                    tool_name=tc.name,
                    arguments=tc.arguments,
                    result=error_msg,
                    success=False,
                    iteration=iteration,
                ))

                results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": error_msg,
                    "is_error": True,
                })

        return results


# =============================================================================
# Critic Agent
# =============================================================================


class CriticAgent:
    """Critic agent that reviews Builder output.

    The Critic agent is the quality assurance component. It:
    1. Reviews code changes made by the Builder
    2. Checks against acceptance criteria
    3. Returns APPROVED, NEEDS_REVISION, or BLOCKED

    Attributes:
        client: LLM client for generating reviews.
        max_tokens: Maximum tokens per LLM call.

    Example:
        >>> critic = CriticAgent(client)
        >>> result = await critic.review(task, builder_result)
        >>> if result.is_approved:
        ...     print("Changes approved!")
    """

    DEFAULT_MAX_TOKENS = 4096

    def __init__(
        self,
        client: LLMClient,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """Initialize the Critic agent.

        Args:
            client: LLM client for completions.
            max_tokens: Max tokens per LLM call.
        """
        self._client = client
        self._max_tokens = max_tokens

    async def review(
        self,
        task: dict[str, Any],
        builder_result: BuilderResult,
    ) -> CriticResult:
        """Review changes made by the Builder.

        Args:
            task: Original task that was executed.
            builder_result: Result from Builder execution.

        Returns:
            CriticResult with verdict and feedback.
        """
        logger.info(f"Critic reviewing task: {task.get('title', 'Unknown')}")

        # Build changes summary from builder result
        changes_summary = self._build_changes_summary(builder_result)

        # Build review prompt
        review_prompt = build_review_prompt(
            task=task,
            changes_summary=changes_summary,
            files_changed=builder_result.files_changed,
        )

        try:
            # Call LLM for review
            response = await self._client.complete(
                messages=[{"role": "user", "content": review_prompt}],
                system=CRITIC_SYSTEM_PROMPT,
                max_tokens=self._max_tokens,
            )

            # Extract verdict
            verdict_str, feedback = extract_critic_verdict(response.content)

            verdict = {
                "APPROVED": CriticVerdict.APPROVED,
                "NEEDS_REVISION": CriticVerdict.NEEDS_REVISION,
                "BLOCKED": CriticVerdict.BLOCKED,
            }.get(verdict_str, CriticVerdict.NEEDS_REVISION)

            # Parse issues and suggestions from feedback
            issues, suggestions = self._parse_feedback(feedback)

            logger.info(f"Critic verdict: {verdict.value}")

            return CriticResult(
                verdict=verdict,
                feedback=feedback,
                issues=issues,
                suggestions=suggestions,
                total_tokens=response.total_tokens,
            )

        except Exception as e:
            logger.error(f"Critic error: {e}")
            return CriticResult(
                verdict=CriticVerdict.BLOCKED,
                feedback=f"Review failed: {e}",
                total_tokens=0,
            )

    def _build_changes_summary(self, builder_result: BuilderResult) -> str:
        """Build a summary of changes from Builder result.

        Args:
            builder_result: Result from Builder execution.

        Returns:
            Summary string describing the changes.
        """
        parts = []

        # Add final response
        if builder_result.final_response:
            parts.append("## Builder's Summary")
            parts.append(builder_result.final_response)
            parts.append("")

        # Add tool calls summary
        if builder_result.tool_calls:
            parts.append("## Tool Executions")
            for record in builder_result.tool_calls:
                status = "✓" if record.success else "✗"
                parts.append(f"- {status} `{record.tool_name}({record.arguments})`")
                if not record.success:
                    parts.append(f"  Error: {record.result[:100]}")
            parts.append("")

        # Add files changed
        if builder_result.files_changed:
            parts.append("## Files Modified")
            for f in builder_result.files_changed:
                parts.append(f"- {f}")
            parts.append("")

        if not parts:
            parts.append("No detailed changes available.")

        return "\n".join(parts)

    def _parse_feedback(self, feedback: str) -> tuple[list[str], list[str]]:
        """Parse issues and suggestions from feedback.

        Args:
            feedback: Full feedback text from critic.

        Returns:
            Tuple of (issues, suggestions) lists.
        """
        issues = []
        suggestions = []

        lines = feedback.split("\n")
        current_section = None

        for line in lines:
            line_stripped = line.strip()
            lower = line_stripped.lower()

            # Detect sections
            if "issue" in lower and ("found" in lower or ":" in lower):
                current_section = "issues"
                continue
            elif "suggestion" in lower and ":" in lower:
                current_section = "suggestions"
                continue

            # Parse numbered items
            if line_stripped.startswith(("1.", "2.", "3.", "4.", "5.", "-", "*")):
                item = line_stripped.lstrip("0123456789.-* ")
                if current_section == "issues" and item:
                    issues.append(item)
                elif current_section == "suggestions" and item:
                    suggestions.append(item)

        return issues, suggestions
