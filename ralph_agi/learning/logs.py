"""Conversation log parsing for contextual learning.

Layer 4 of the Contextual Learning System - provides parsing and
analysis of Claude conversation logs stored in JSONL format.

Conversation logs provide:
- Complete interaction history
- Error pattern extraction
- Reasoning chain analysis
- Solution approaches for debugging
"""

from __future__ import annotations

import gzip
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """Role in a conversation message."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ToolCall:
    """A tool call from an assistant message.

    Attributes:
        id: Tool call identifier.
        name: Tool name.
        arguments: Tool arguments.
        result: Tool result (if available).
    """

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCall:
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            arguments=data.get("arguments", {}),
            result=data.get("result"),
        )


@dataclass
class ConversationMessage:
    """A single message in a conversation.

    Attributes:
        role: Message role (user/assistant/system/tool).
        content: Message content.
        timestamp: When the message was sent.
        session_id: Session identifier.
        iteration: Iteration number.
        tool_calls: Tool calls made in this message.
        metadata: Additional metadata.
    """

    role: MessageRole
    content: str
    timestamp: Optional[str] = None
    session_id: Optional[str] = None
    iteration: Optional[int] = None
    tool_calls: tuple[ToolCall, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    @property
    def has_tool_calls(self) -> bool:
        """Check if message has tool calls."""
        return len(self.tool_calls) > 0

    @property
    def word_count(self) -> int:
        """Get word count of content."""
        return len(self.content.split())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "session": self.session_id,
            "iteration": self.iteration,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "metadata": self.metadata,
        }

    def to_jsonl(self) -> str:
        """Convert to JSONL line."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversationMessage:
        """Create from dictionary."""
        role = data.get("role", "user")
        if isinstance(role, str):
            try:
                role = MessageRole(role)
            except ValueError:
                role = MessageRole.USER

        tool_calls = tuple(
            ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])
        )

        return cls(
            role=role,
            content=data.get("content", ""),
            timestamp=data.get("timestamp"),
            session_id=data.get("session"),
            iteration=data.get("iteration"),
            tool_calls=tool_calls,
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_jsonl(cls, line: str) -> ConversationMessage:
        """Parse from JSONL line."""
        data = json.loads(line)
        return cls.from_dict(data)


@dataclass
class ConversationLog:
    """A collection of conversation messages.

    Attributes:
        messages: List of messages.
        session_id: Session identifier.
        metadata: Log metadata.
    """

    messages: list[ConversationMessage] = field(default_factory=list)
    session_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, message: ConversationMessage) -> None:
        """Add a message to the log."""
        if self.session_id is None:
            self.session_id = message.session_id
        self.messages.append(message)

    def get_by_role(self, role: MessageRole) -> list[ConversationMessage]:
        """Get messages by role."""
        return [m for m in self.messages if m.role == role]

    def get_by_session(self, session_id: str) -> list[ConversationMessage]:
        """Get messages for a specific session."""
        return [m for m in self.messages if m.session_id == session_id]

    def get_by_iteration(self, iteration: int) -> list[ConversationMessage]:
        """Get messages for a specific iteration."""
        return [m for m in self.messages if m.iteration == iteration]

    def search(self, query: str) -> list[ConversationMessage]:
        """Search messages by content.

        Args:
            query: Search query (case-insensitive).

        Returns:
            Matching messages.
        """
        query_lower = query.lower()
        return [m for m in self.messages if query_lower in m.content.lower()]

    def get_tool_calls(self) -> list[ToolCall]:
        """Get all tool calls from the log."""
        calls = []
        for message in self.messages:
            calls.extend(message.tool_calls)
        return calls

    def get_errors(self) -> list[ConversationMessage]:
        """Get messages that contain error patterns.

        Looks for common error indicators in content.
        """
        error_patterns = [
            r"error:",
            r"exception:",
            r"failed",
            r"traceback",
            r"TypeError",
            r"ValueError",
            r"AttributeError",
            r"KeyError",
            r"ImportError",
            r"cannot\s+\w+",
        ]
        pattern = re.compile("|".join(error_patterns), re.IGNORECASE)

        return [m for m in self.messages if pattern.search(m.content)]

    def get_recent(self, limit: int = 10) -> list[ConversationMessage]:
        """Get most recent messages."""
        return self.messages[-limit:]

    def summarize(self) -> dict[str, Any]:
        """Get summary statistics."""
        user_msgs = len(self.get_by_role(MessageRole.USER))
        assistant_msgs = len(self.get_by_role(MessageRole.ASSISTANT))
        tool_calls = len(self.get_tool_calls())
        errors = len(self.get_errors())

        total_words = sum(m.word_count for m in self.messages)

        return {
            "total_messages": len(self.messages),
            "user_messages": user_msgs,
            "assistant_messages": assistant_msgs,
            "tool_calls": tool_calls,
            "errors_detected": errors,
            "total_words": total_words,
        }

    def __len__(self) -> int:
        """Get number of messages."""
        return len(self.messages)


def get_logs_path(project_root: Optional[Path] = None) -> Path:
    """Get the path to conversation logs directory.

    Args:
        project_root: Project root directory. Uses CWD if None.

    Returns:
        Path to .ralph/logs/conversations/
    """
    if project_root is None:
        project_root = Path.cwd()
    return project_root / ".ralph" / "logs" / "conversations"


def save_message(
    message: ConversationMessage,
    log_path: Optional[Path] = None,
) -> None:
    """Append a message to the log file.

    Args:
        message: Message to save.
        log_path: Path to log file. Uses date-based name if None.
    """
    if log_path is None:
        logs_dir = get_logs_path()
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_path = logs_dir / f"{date_str}.jsonl"

    # Ensure directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Append to file
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(message.to_jsonl() + "\n")


def load_log(path: Path) -> ConversationLog:
    """Load a conversation log from file.

    Args:
        path: Path to JSONL file (can be .gz compressed).

    Returns:
        ConversationLog instance.
    """
    log = ConversationLog()

    if not path.exists():
        return log

    try:
        # Handle gzipped files
        if path.suffix == ".gz":
            opener = gzip.open
        else:
            opener = open

        with opener(path, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        message = ConversationMessage.from_jsonl(line)
                        log.add(message)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON line in {path}")
                        continue

    except Exception as e:
        logger.warning(f"Failed to load log {path}: {e}")

    return log


def load_recent_logs(
    limit: int = 7,
    logs_dir: Optional[Path] = None,
) -> ConversationLog:
    """Load recent conversation logs.

    Args:
        limit: Number of days to load.
        logs_dir: Directory containing logs.

    Returns:
        Combined ConversationLog.
    """
    if logs_dir is None:
        logs_dir = get_logs_path()

    if not logs_dir.exists():
        return ConversationLog()

    combined = ConversationLog()

    # Get all log files sorted by name (date-based)
    log_files = sorted(logs_dir.glob("*.jsonl*"), reverse=True)[:limit]

    for log_file in log_files:
        log = load_log(log_file)
        for message in log.messages:
            combined.add(message)

    return combined


def compress_old_logs(
    days_old: int = 7,
    logs_dir: Optional[Path] = None,
) -> int:
    """Compress logs older than specified days.

    Args:
        days_old: Compress logs older than this many days.
        logs_dir: Directory containing logs.

    Returns:
        Number of files compressed.
    """
    if logs_dir is None:
        logs_dir = get_logs_path()

    if not logs_dir.exists():
        return 0

    compressed = 0
    cutoff = datetime.now().timestamp() - (days_old * 86400)

    for log_file in logs_dir.glob("*.jsonl"):
        if log_file.stat().st_mtime < cutoff:
            # Compress the file
            gz_path = log_file.with_suffix(".jsonl.gz")
            with open(log_file, "rb") as f_in:
                with gzip.open(gz_path, "wb") as f_out:
                    f_out.writelines(f_in)
            log_file.unlink()
            compressed += 1
            logger.debug(f"Compressed {log_file}")

    return compressed


def extract_patterns(log: ConversationLog) -> dict[str, list[str]]:
    """Extract patterns from conversation log.

    Identifies:
    - Error patterns and their solutions
    - Successful tool call patterns
    - Common issues and fixes

    Args:
        log: Conversation log to analyze.

    Returns:
        Dictionary of pattern categories to examples.
    """
    patterns = {
        "errors": [],
        "solutions": [],
        "tool_patterns": [],
    }

    # Find error-solution pairs
    error_msgs = log.get_errors()
    for i, error_msg in enumerate(error_msgs):
        patterns["errors"].append(error_msg.content[:200])

        # Look for solution in next few messages
        error_idx = log.messages.index(error_msg)
        for j in range(error_idx + 1, min(error_idx + 5, len(log.messages))):
            next_msg = log.messages[j]
            if next_msg.role == MessageRole.ASSISTANT:
                # Check for fix indicators
                fix_patterns = ["fixed", "solved", "resolved", "working now"]
                if any(fp in next_msg.content.lower() for fp in fix_patterns):
                    patterns["solutions"].append(next_msg.content[:200])
                    break

    # Extract tool usage patterns
    for call in log.get_tool_calls():
        patterns["tool_patterns"].append(f"{call.name}: {json.dumps(call.arguments)[:100]}")

    return patterns


def inject_conversation_context(
    log: ConversationLog,
    prompt: str,
    max_messages: int = 10,
    include_errors: bool = True,
) -> str:
    """Inject conversation context into a system prompt.

    Args:
        log: Conversation log.
        prompt: Base system prompt.
        max_messages: Maximum messages to include.
        include_errors: Include error analysis.

    Returns:
        Prompt with context injected.
    """
    if len(log) == 0:
        return prompt

    lines = ["\n\n## Conversation Context\n"]
    lines.append("Recent conversation history:\n")

    # Get recent messages
    recent = log.get_recent(max_messages)

    for msg in recent[-5:]:  # Just last 5 for context
        role = msg.role.value.title()
        content = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
        lines.append(f"- **{role}**: {content}")

    # Add error context if any
    if include_errors:
        errors = log.get_errors()
        if errors:
            lines.append("\n### Recent Issues")
            for error in errors[-3:]:
                lines.append(f"- {error.content[:100]}...")

    # Add summary
    summary = log.summarize()
    lines.append("\n### Session Summary")
    lines.append(f"- Messages: {summary['total_messages']}")
    lines.append(f"- Tool calls: {summary['tool_calls']}")
    lines.append(f"- Errors detected: {summary['errors_detected']}")

    context_section = "\n".join(lines)
    return prompt + context_section
