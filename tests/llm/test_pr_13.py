
import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import Any
from ralph_agi.llm.agents import BuilderAgent, AgentStatus
from ralph_agi.llm.client import LLMResponse, StopReason, ToolCall

@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client.complete = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_max_iterations_extracts_text_from_list_content(mock_client: MagicMock):
    """
    Test that when max iterations is reached, the final_response is correctly
    extracted as a string even if the internal message content is a list of blocks.
    """
    # Setup response that will trigger max iterations (no completion signal)
    # Use standard text content in response, but the Agent *converts* it to list internally
    # in _build_assistant_message regardless of input format.
    # To be extra sure we test list handling, we can also verify that _extract_text_content works
    # on the structure _build_assistant_message creates.
    
    response = LLMResponse(
        content="I am working on it.",
        stop_reason=StopReason.END_TURN,
        # No tool calls, so no execution, so last message is this assistant message
    )
    
    mock_client.complete.return_value = response
    
    # We want max_iterations=1. The loop runs once.
    # It sees END_TURN but no completion signal.
    # It loops back.
    # range(1) is exhausted.
    # It breaks and goes to max iterations return.
    agent = BuilderAgent(mock_client, max_iterations=1)
    
    task = {"title": "Test Task", "description": "desc"}
    
    # Act
    result = await agent.execute(task)
    
    # Assert
    assert result.status == AgentStatus.MAX_ITERATIONS
    assert result.iterations == 1
    
    # Verify the extraction worked
    assert isinstance(result.final_response, str)
    assert "I am working on it." in result.final_response
    assert "[" not in result.final_response
@pytest.mark.asyncio
async def test_extract_text_content_helper():
    """Directly test the helper function added in PR #13."""
    from ralph_agi.llm.agents import _extract_text_content
    
    # Case 1: None
    assert _extract_text_content(None) == ""
    
    # Case 2: String
    assert _extract_text_content("hello") == "hello"
    
    # Case 3: List of text blocks
    content_list = [
        {"type": "text", "text": "Part 1"},
        {"type": "tool_use", "id": "1", "name": "t", "input": {}},
        {"type": "text", "text": "Part 2"}
    ]
    extracted = _extract_text_content(content_list)
    assert "Part 1" in extracted
    assert "Part 2" in extracted
    assert "\n" in extracted # It joins with newlines
    
    # Case 4: List of strings (fallback/edge case)
    assert _extract_text_content(["a", "b"]) == "a\nb"
