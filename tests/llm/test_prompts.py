"""Tests for prompt templates and helpers."""

from __future__ import annotations

import pytest

from ralph_agi.llm.prompts import (
    BUILDER_SYSTEM_PROMPT,
    CRITIC_SYSTEM_PROMPT,
    build_review_prompt,
    build_task_prompt,
    extract_completion_signal,
    extract_critic_verdict,
)


class TestBuilderSystemPrompt:
    """Tests for Builder system prompt."""

    def test_prompt_exists(self) -> None:
        """Test that Builder prompt is defined."""
        assert BUILDER_SYSTEM_PROMPT is not None
        assert len(BUILDER_SYSTEM_PROMPT) > 100

    def test_contains_completion_signal(self) -> None:
        """Test that prompt mentions completion signal."""
        assert "<task_complete>" in BUILDER_SYSTEM_PROMPT
        assert "DONE" in BUILDER_SYSTEM_PROMPT

    def test_contains_tool_guidance(self) -> None:
        """Test that prompt mentions tools."""
        assert "tool" in BUILDER_SYSTEM_PROMPT.lower()

    def test_contains_key_guidelines(self) -> None:
        """Test that prompt contains important guidelines."""
        assert "NEVER" in BUILDER_SYSTEM_PROMPT
        assert "ALWAYS" in BUILDER_SYSTEM_PROMPT


class TestCriticSystemPrompt:
    """Tests for Critic system prompt."""

    def test_prompt_exists(self) -> None:
        """Test that Critic prompt is defined."""
        assert CRITIC_SYSTEM_PROMPT is not None
        assert len(CRITIC_SYSTEM_PROMPT) > 100

    def test_contains_verdicts(self) -> None:
        """Test that prompt mentions all verdicts."""
        assert "APPROVED" in CRITIC_SYSTEM_PROMPT
        assert "NEEDS_REVISION" in CRITIC_SYSTEM_PROMPT
        assert "BLOCKED" in CRITIC_SYSTEM_PROMPT

    def test_contains_review_criteria(self) -> None:
        """Test that prompt mentions review criteria."""
        assert "Correctness" in CRITIC_SYSTEM_PROMPT
        assert "Security" in CRITIC_SYSTEM_PROMPT
        assert "Performance" in CRITIC_SYSTEM_PROMPT


class TestBuildTaskPrompt:
    """Tests for build_task_prompt helper."""

    def test_minimal_task(self) -> None:
        """Test building prompt with minimal task."""
        task = {"title": "Fix bug"}

        result = build_task_prompt(task)

        assert "Fix bug" in result
        assert "Current Task" in result

    def test_full_task(self) -> None:
        """Test building prompt with full task."""
        task = {
            "title": "Add user authentication",
            "description": "Implement login and logout functionality.",
            "acceptance_criteria": [
                "User can log in with email/password",
                "Session is created on successful login",
            ],
            "technical_notes": "Use JWT tokens for sessions.",
            "dependencies": ["database-setup"],
        }

        result = build_task_prompt(task)

        assert "Add user authentication" in result
        assert "Implement login and logout" in result
        assert "User can log in" in result
        assert "JWT tokens" in result
        assert "database-setup" in result

    def test_with_context(self) -> None:
        """Test building prompt with context."""
        task = {"title": "Test task"}
        context = "This project uses FastAPI and PostgreSQL."

        result = build_task_prompt(task, context=context)

        assert "FastAPI" in result
        assert "Project Context" in result

    def test_with_memory_context(self) -> None:
        """Test building prompt with memory context."""
        task = {"title": "Test task"}
        memory = "Previously implemented similar feature in auth.py."

        result = build_task_prompt(task, memory_context=memory)

        assert "similar feature" in result
        assert "Relevant Memories" in result

    def test_uses_name_if_no_title(self) -> None:
        """Test that 'name' field is used if 'title' is missing."""
        task = {"name": "Task Name Here"}

        result = build_task_prompt(task)

        assert "Task Name Here" in result

    def test_acceptance_as_string(self) -> None:
        """Test handling acceptance criteria as string."""
        task = {
            "title": "Test",
            "acceptance_criteria": "Code should work",
        }

        result = build_task_prompt(task)

        assert "Code should work" in result

    def test_includes_instructions(self) -> None:
        """Test that prompt includes execution instructions."""
        task = {"title": "Test"}

        result = build_task_prompt(task)

        assert "Instructions" in result
        assert "<task_complete>DONE</task_complete>" in result


class TestBuildReviewPrompt:
    """Tests for build_review_prompt helper."""

    def test_basic_review(self) -> None:
        """Test building basic review prompt."""
        task = {"title": "Fix bug"}
        changes = "Fixed null pointer exception in user lookup."

        result = build_review_prompt(task, changes)

        assert "Fix bug" in result
        assert "null pointer" in result
        assert "Review" in result

    def test_with_files_changed(self) -> None:
        """Test building review prompt with files list."""
        task = {"title": "Test"}
        changes = "Added tests"
        files = ["tests/test_auth.py", "src/auth.py"]

        result = build_review_prompt(task, changes, files_changed=files)

        assert "test_auth.py" in result
        assert "src/auth.py" in result
        assert "Files Modified" in result

    def test_with_acceptance_criteria(self) -> None:
        """Test that acceptance criteria is included for verification."""
        task = {
            "title": "Feature",
            "acceptance_criteria": ["Must handle errors", "Must log events"],
        }
        changes = "Implemented feature"

        result = build_review_prompt(task, changes)

        assert "Must handle errors" in result
        assert "Acceptance Criteria to Verify" in result

    def test_includes_verdict_instructions(self) -> None:
        """Test that review instructions are included."""
        task = {"title": "Test"}
        changes = "Changes"

        result = build_review_prompt(task, changes)

        assert "APPROVED" in result
        assert "NEEDS_REVISION" in result
        assert "BLOCKED" in result


class TestExtractCompletionSignal:
    """Tests for extract_completion_signal helper."""

    def test_done_signal(self) -> None:
        """Test extracting DONE signal."""
        response = "I've finished the work.\n\n<task_complete>DONE</task_complete>"

        is_complete, status = extract_completion_signal(response)

        assert is_complete is True
        assert status == "DONE"

    def test_done_with_message(self) -> None:
        """Test extracting DONE with additional message."""
        response = "<task_complete>DONE - All tests pass</task_complete>"

        is_complete, status = extract_completion_signal(response)

        assert is_complete is True
        assert "DONE" in status

    def test_blocked_signal(self) -> None:
        """Test extracting BLOCKED signal."""
        response = "<task_complete>BLOCKED: Missing API credentials</task_complete>"

        is_complete, status = extract_completion_signal(response)

        assert is_complete is False
        assert "BLOCKED" in status
        assert "credentials" in status

    def test_no_signal(self) -> None:
        """Test response without completion signal."""
        response = "Still working on it..."

        is_complete, status = extract_completion_signal(response)

        assert is_complete is False
        assert status == "IN_PROGRESS"

    def test_case_insensitive(self) -> None:
        """Test that signal extraction is case insensitive."""
        response = "<TASK_COMPLETE>done</TASK_COMPLETE>"

        is_complete, status = extract_completion_signal(response)

        assert is_complete is True

    def test_multiline_signal(self) -> None:
        """Test signal extraction with multiline content."""
        response = """<task_complete>
DONE
All work completed successfully.
</task_complete>"""

        is_complete, status = extract_completion_signal(response)

        assert is_complete is True


class TestExtractCriticVerdict:
    """Tests for extract_critic_verdict helper."""

    def test_approved_verdict(self) -> None:
        """Test extracting APPROVED verdict."""
        response = """VERDICT: APPROVED

The implementation is correct and follows best practices."""

        verdict, details = extract_critic_verdict(response)

        assert verdict == "APPROVED"

    def test_needs_revision_verdict(self) -> None:
        """Test extracting NEEDS_REVISION verdict."""
        response = """VERDICT: NEEDS_REVISION

Issues found:
1. Missing error handling"""

        verdict, details = extract_critic_verdict(response)

        assert verdict == "NEEDS_REVISION"

    def test_blocked_verdict(self) -> None:
        """Test extracting BLOCKED verdict."""
        response = """VERDICT: BLOCKED

Cannot review without seeing test files."""

        verdict, details = extract_critic_verdict(response)

        assert verdict == "BLOCKED"

    def test_no_colon_format(self) -> None:
        """Test verdict without colon format."""
        response = "VERDICT:APPROVED\n\nGood work!"

        verdict, details = extract_critic_verdict(response)

        assert verdict == "APPROVED"

    def test_fallback_keyword_approved(self) -> None:
        """Test fallback keyword detection for APPROVED."""
        response = """APPROVED

The code looks good."""

        verdict, details = extract_critic_verdict(response)

        assert verdict == "APPROVED"

    def test_fallback_keyword_needs_revision(self) -> None:
        """Test fallback keyword detection for NEEDS_REVISION."""
        response = """NEEDS_REVISION

There are issues to fix."""

        verdict, details = extract_critic_verdict(response)

        assert verdict == "NEEDS_REVISION"

    def test_default_to_needs_revision(self) -> None:
        """Test that unclear response defaults to NEEDS_REVISION."""
        response = "I'm not sure about this code."

        verdict, details = extract_critic_verdict(response)

        assert verdict == "NEEDS_REVISION"

    def test_returns_full_response_as_details(self) -> None:
        """Test that full response is returned as details."""
        response = """VERDICT: APPROVED

The implementation is solid.
Good use of error handling.
Tests are comprehensive."""

        verdict, details = extract_critic_verdict(response)

        assert details == response
        assert "comprehensive" in details
