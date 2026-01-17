"""Tests for conversation log parsing module."""

from __future__ import annotations

import gzip
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ralph_agi.learning.logs import (
    MessageRole,
    ToolCall,
    ConversationMessage,
    ConversationLog,
    get_logs_path,
    save_message,
    load_log,
    load_recent_logs,
    compress_old_logs,
    extract_patterns,
    inject_conversation_context,
)


class TestMessageRole:
    """Tests for MessageRole enum."""

    def test_all_roles_exist(self):
        """Test all expected roles exist."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.TOOL.value == "tool"


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_tool_call_creation(self):
        """Test creating tool call."""
        call = ToolCall(
            id="call_123",
            name="read_file",
            arguments={"path": "/tmp/test.txt"},
        )
        assert call.id == "call_123"
        assert call.name == "read_file"
        assert call.arguments["path"] == "/tmp/test.txt"

    def test_to_dict(self):
        """Test converting to dictionary."""
        call = ToolCall(
            id="call_456",
            name="write_file",
            arguments={"content": "hello"},
            result="success",
        )
        data = call.to_dict()

        assert data["id"] == "call_456"
        assert data["name"] == "write_file"
        assert data["result"] == "success"

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "id": "call_789",
            "name": "search",
            "arguments": {"query": "test"},
            "result": "found 3 results",
        }
        call = ToolCall.from_dict(data)

        assert call.id == "call_789"
        assert call.name == "search"
        assert call.result == "found 3 results"


class TestConversationMessage:
    """Tests for ConversationMessage dataclass."""

    def test_message_creation_minimal(self):
        """Test creating message with minimal fields."""
        msg = ConversationMessage(
            role=MessageRole.USER,
            content="Hello",
        )
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.timestamp is not None

    def test_message_creation_full(self):
        """Test creating message with all fields."""
        tool_call = ToolCall(id="tc1", name="read", arguments={})
        msg = ConversationMessage(
            role=MessageRole.ASSISTANT,
            content="I'll help you with that.",
            timestamp="2025-01-16T12:00:00",
            session_id="ralph-001",
            iteration=5,
            tool_calls=(tool_call,),
            metadata={"tokens": 100},
        )
        assert msg.role == MessageRole.ASSISTANT
        assert msg.session_id == "ralph-001"
        assert msg.iteration == 5
        assert len(msg.tool_calls) == 1

    def test_has_tool_calls(self):
        """Test has_tool_calls property."""
        with_calls = ConversationMessage(
            role=MessageRole.ASSISTANT,
            content="Using a tool",
            tool_calls=(ToolCall(id="1", name="test", arguments={}),),
        )
        without_calls = ConversationMessage(
            role=MessageRole.USER,
            content="No tools",
        )

        assert with_calls.has_tool_calls is True
        assert without_calls.has_tool_calls is False

    def test_word_count(self):
        """Test word count property."""
        msg = ConversationMessage(
            role=MessageRole.USER,
            content="This is a test message with seven words.",
        )
        assert msg.word_count == 8

    def test_to_dict(self):
        """Test converting to dictionary."""
        msg = ConversationMessage(
            role=MessageRole.USER,
            content="Test message",
            session_id="session-1",
        )
        data = msg.to_dict()

        assert data["role"] == "user"
        assert data["content"] == "Test message"
        assert data["session"] == "session-1"

    def test_to_jsonl(self):
        """Test converting to JSONL."""
        msg = ConversationMessage(
            role=MessageRole.USER,
            content="Test",
            timestamp="2025-01-16T00:00:00",
        )
        jsonl = msg.to_jsonl()
        data = json.loads(jsonl)

        assert data["role"] == "user"
        assert data["content"] == "Test"

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "role": "assistant",
            "content": "Hello!",
            "session": "s1",
            "iteration": 3,
        }
        msg = ConversationMessage.from_dict(data)

        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Hello!"
        assert msg.iteration == 3

    def test_from_jsonl(self):
        """Test creating from JSONL."""
        jsonl = '{"role": "user", "content": "Help me"}'
        msg = ConversationMessage.from_jsonl(jsonl)

        assert msg.role == MessageRole.USER
        assert msg.content == "Help me"

    def test_from_dict_invalid_role(self):
        """Test handling invalid role."""
        data = {"role": "invalid", "content": "Test"}
        msg = ConversationMessage.from_dict(data)
        assert msg.role == MessageRole.USER  # Defaults to USER


class TestConversationLog:
    """Tests for ConversationLog collection."""

    def test_log_creation(self):
        """Test creating empty log."""
        log = ConversationLog()
        assert len(log) == 0

    def test_add_message(self):
        """Test adding a message."""
        log = ConversationLog()
        msg = ConversationMessage(role=MessageRole.USER, content="Hi")
        log.add(msg)

        assert len(log) == 1

    def test_get_by_role(self):
        """Test getting messages by role."""
        log = ConversationLog()
        log.add(ConversationMessage(role=MessageRole.USER, content="Q1"))
        log.add(ConversationMessage(role=MessageRole.ASSISTANT, content="A1"))
        log.add(ConversationMessage(role=MessageRole.USER, content="Q2"))

        user_msgs = log.get_by_role(MessageRole.USER)
        assert len(user_msgs) == 2

        assistant_msgs = log.get_by_role(MessageRole.ASSISTANT)
        assert len(assistant_msgs) == 1

    def test_get_by_session(self):
        """Test getting messages by session."""
        log = ConversationLog()
        log.add(ConversationMessage(role=MessageRole.USER, content="S1", session_id="s1"))
        log.add(ConversationMessage(role=MessageRole.USER, content="S2", session_id="s2"))
        log.add(ConversationMessage(role=MessageRole.USER, content="S1-2", session_id="s1"))

        s1_msgs = log.get_by_session("s1")
        assert len(s1_msgs) == 2

    def test_get_by_iteration(self):
        """Test getting messages by iteration."""
        log = ConversationLog()
        log.add(ConversationMessage(role=MessageRole.USER, content="I1", iteration=1))
        log.add(ConversationMessage(role=MessageRole.USER, content="I2", iteration=2))
        log.add(ConversationMessage(role=MessageRole.USER, content="I1-2", iteration=1))

        i1_msgs = log.get_by_iteration(1)
        assert len(i1_msgs) == 2

    def test_search(self):
        """Test searching messages."""
        log = ConversationLog()
        log.add(ConversationMessage(role=MessageRole.USER, content="Fix the database error"))
        log.add(ConversationMessage(role=MessageRole.USER, content="Update the API"))
        log.add(ConversationMessage(role=MessageRole.ASSISTANT, content="Database is fixed"))

        results = log.search("database")
        assert len(results) == 2

        results = log.search("api")
        assert len(results) == 1

    def test_get_tool_calls(self):
        """Test getting all tool calls."""
        log = ConversationLog()
        log.add(ConversationMessage(
            role=MessageRole.ASSISTANT,
            content="Using tools",
            tool_calls=(
                ToolCall(id="1", name="read", arguments={}),
                ToolCall(id="2", name="write", arguments={}),
            ),
        ))
        log.add(ConversationMessage(
            role=MessageRole.ASSISTANT,
            content="More tools",
            tool_calls=(ToolCall(id="3", name="search", arguments={}),),
        ))

        calls = log.get_tool_calls()
        assert len(calls) == 3

    def test_get_errors(self):
        """Test getting error messages."""
        log = ConversationLog()
        log.add(ConversationMessage(role=MessageRole.USER, content="Normal message"))
        log.add(ConversationMessage(role=MessageRole.ASSISTANT, content="Error: File not found"))
        log.add(ConversationMessage(role=MessageRole.ASSISTANT, content="TypeError occurred"))
        log.add(ConversationMessage(role=MessageRole.USER, content="Another normal message"))

        errors = log.get_errors()
        assert len(errors) == 2

    def test_get_recent(self):
        """Test getting recent messages."""
        log = ConversationLog()
        for i in range(10):
            log.add(ConversationMessage(role=MessageRole.USER, content=f"Msg {i}"))

        recent = log.get_recent(3)
        assert len(recent) == 3
        assert "Msg 9" in recent[-1].content

    def test_summarize(self):
        """Test summary statistics."""
        log = ConversationLog()
        log.add(ConversationMessage(role=MessageRole.USER, content="Question"))
        log.add(ConversationMessage(
            role=MessageRole.ASSISTANT,
            content="Answer with error: something failed",
            tool_calls=(ToolCall(id="1", name="test", arguments={}),),
        ))

        summary = log.summarize()

        assert summary["total_messages"] == 2
        assert summary["user_messages"] == 1
        assert summary["assistant_messages"] == 1
        assert summary["tool_calls"] == 1
        assert summary["errors_detected"] == 1


class TestPersistence:
    """Tests for log persistence functions."""

    def test_get_logs_path(self, tmp_path):
        """Test getting logs path."""
        path = get_logs_path(tmp_path)
        assert "logs" in str(path)
        assert "conversations" in str(path)

    def test_save_message(self, tmp_path):
        """Test saving a message."""
        log_path = tmp_path / "test.jsonl"
        msg = ConversationMessage(role=MessageRole.USER, content="Test")

        save_message(msg, log_path)

        assert log_path.exists()
        content = log_path.read_text()
        assert "Test" in content

    def test_save_multiple_messages(self, tmp_path):
        """Test saving multiple messages."""
        log_path = tmp_path / "test.jsonl"

        save_message(ConversationMessage(role=MessageRole.USER, content="M1"), log_path)
        save_message(ConversationMessage(role=MessageRole.ASSISTANT, content="M2"), log_path)

        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_load_log(self, tmp_path):
        """Test loading a log file."""
        log_path = tmp_path / "test.jsonl"
        log_path.write_text(
            '{"role": "user", "content": "Hello"}\n'
            '{"role": "assistant", "content": "Hi!"}\n'
        )

        log = load_log(log_path)

        assert len(log) == 2
        assert log.messages[0].content == "Hello"
        assert log.messages[1].content == "Hi!"

    def test_load_nonexistent(self, tmp_path):
        """Test loading nonexistent file."""
        log = load_log(tmp_path / "nonexistent.jsonl")
        assert len(log) == 0

    def test_load_gzipped(self, tmp_path):
        """Test loading gzipped log file."""
        log_path = tmp_path / "test.jsonl.gz"
        content = '{"role": "user", "content": "Compressed"}\n'
        with gzip.open(log_path, "wt") as f:
            f.write(content)

        log = load_log(log_path)
        assert len(log) == 1
        assert log.messages[0].content == "Compressed"

    def test_load_recent_logs(self, tmp_path):
        """Test loading recent logs."""
        logs_dir = tmp_path / ".ralph" / "logs" / "conversations"
        logs_dir.mkdir(parents=True)

        (logs_dir / "2025-01-15.jsonl").write_text('{"role": "user", "content": "Day 1"}\n')
        (logs_dir / "2025-01-16.jsonl").write_text('{"role": "user", "content": "Day 2"}\n')

        log = load_recent_logs(limit=2, logs_dir=logs_dir)

        assert len(log) == 2

    def test_compress_old_logs(self, tmp_path):
        """Test compressing old logs."""
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        # Create an old file
        old_file = logs_dir / "old.jsonl"
        old_file.write_text('{"role": "user", "content": "Old"}\n')
        # Make it appear old by backdating mtime
        import os
        old_time = 1000000000  # Year 2001
        os.utime(old_file, (old_time, old_time))

        compressed = compress_old_logs(days_old=1, logs_dir=logs_dir)

        assert compressed == 1
        assert (logs_dir / "old.jsonl.gz").exists()
        assert not (logs_dir / "old.jsonl").exists()


class TestPatternExtraction:
    """Tests for pattern extraction."""

    def test_extract_patterns(self):
        """Test extracting patterns from log."""
        log = ConversationLog()
        log.add(ConversationMessage(
            role=MessageRole.ASSISTANT,
            content="Error: File not found",
        ))
        log.add(ConversationMessage(
            role=MessageRole.ASSISTANT,
            content="Fixed by creating the directory. The issue is now resolved.",
        ))
        log.add(ConversationMessage(
            role=MessageRole.ASSISTANT,
            content="Using read tool",
            tool_calls=(ToolCall(id="1", name="read_file", arguments={"path": "/test"}),),
        ))

        patterns = extract_patterns(log)

        assert len(patterns["errors"]) >= 1
        assert len(patterns["tool_patterns"]) == 1

    def test_extract_empty_log(self):
        """Test extracting from empty log."""
        log = ConversationLog()
        patterns = extract_patterns(log)

        assert patterns["errors"] == []
        assert patterns["solutions"] == []
        assert patterns["tool_patterns"] == []


class TestInjectContext:
    """Tests for context injection."""

    def test_inject_empty_log(self):
        """Test injecting empty log."""
        log = ConversationLog()
        prompt = "Base prompt."
        result = inject_conversation_context(log, prompt)
        assert result == prompt

    def test_inject_with_messages(self):
        """Test injecting messages."""
        log = ConversationLog()
        log.add(ConversationMessage(role=MessageRole.USER, content="Help me"))
        log.add(ConversationMessage(role=MessageRole.ASSISTANT, content="Sure!"))

        prompt = "Base prompt."
        result = inject_conversation_context(log, prompt)

        assert "Base prompt." in result
        assert "## Conversation Context" in result
        assert "Help me" in result
        assert "Sure!" in result

    def test_inject_with_errors(self):
        """Test injecting with error context."""
        log = ConversationLog()
        log.add(ConversationMessage(role=MessageRole.ASSISTANT, content="Error: Something went wrong"))

        prompt = "Base."
        result = inject_conversation_context(log, prompt, include_errors=True)

        assert "Recent Issues" in result

    def test_inject_summary(self):
        """Test that summary is included."""
        log = ConversationLog()
        log.add(ConversationMessage(role=MessageRole.USER, content="Q"))
        log.add(ConversationMessage(role=MessageRole.ASSISTANT, content="A"))

        prompt = "Base."
        result = inject_conversation_context(log, prompt)

        assert "Session Summary" in result
        assert "Messages: 2" in result
