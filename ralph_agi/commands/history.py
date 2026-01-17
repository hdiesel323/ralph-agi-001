"""Command history persistence for RALPH-AGI.

Tracks recently used commands for quick access in the command palette.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default history file location
DEFAULT_HISTORY_FILE = ".ralph/command_history.json"
MAX_HISTORY_ENTRIES = 100


@dataclass
class HistoryEntry:
    """A single command history entry.

    Attributes:
        command_id: ID of the executed command.
        timestamp: When the command was executed.
        count: Number of times executed.
    """

    command_id: str
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    count: int = 1

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "command_id": self.command_id,
            "timestamp": self.timestamp,
            "count": self.count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> HistoryEntry:
        """Create from dictionary."""
        return cls(
            command_id=data["command_id"],
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            count=data.get("count", 1),
        )


@dataclass
class CommandHistory:
    """Manages command execution history.

    Tracks recently and frequently used commands for the command palette.

    Example:
        >>> history = CommandHistory()
        >>> history.record("task.run")
        >>> recent = history.get_recent(5)
    """

    entries: dict[str, HistoryEntry] = field(default_factory=dict)
    max_entries: int = MAX_HISTORY_ENTRIES

    def record(self, command_id: str) -> None:
        """Record a command execution.

        Args:
            command_id: ID of executed command.
        """
        if command_id in self.entries:
            entry = self.entries[command_id]
            entry.timestamp = datetime.now().isoformat()
            entry.count += 1
        else:
            self.entries[command_id] = HistoryEntry(command_id=command_id)

        # Prune if needed
        self._prune()

    def _prune(self) -> None:
        """Remove old entries if over limit."""
        if len(self.entries) <= self.max_entries:
            return

        # Sort by timestamp and keep newest
        sorted_entries = sorted(
            self.entries.items(),
            key=lambda x: x[1].timestamp,
            reverse=True,
        )
        self.entries = dict(sorted_entries[: self.max_entries])

    def get_recent(self, limit: int = 10) -> list[str]:
        """Get recently used command IDs.

        Args:
            limit: Maximum number to return.

        Returns:
            List of command IDs, most recent first.
        """
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: e.timestamp,
            reverse=True,
        )
        return [e.command_id for e in sorted_entries[:limit]]

    def get_frequent(self, limit: int = 10) -> list[str]:
        """Get frequently used command IDs.

        Args:
            limit: Maximum number to return.

        Returns:
            List of command IDs, most frequent first.
        """
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: e.count,
            reverse=True,
        )
        return [e.command_id for e in sorted_entries[:limit]]

    def get_count(self, command_id: str) -> int:
        """Get execution count for a command.

        Args:
            command_id: Command ID.

        Returns:
            Execution count, or 0 if never executed.
        """
        entry = self.entries.get(command_id)
        return entry.count if entry else 0

    def clear(self) -> None:
        """Clear all history."""
        self.entries.clear()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": "1.0",
            "max_entries": self.max_entries,
            "entries": [e.to_dict() for e in self.entries.values()],
        }

    @classmethod
    def from_dict(cls, data: dict) -> CommandHistory:
        """Create from dictionary."""
        history = cls(max_entries=data.get("max_entries", MAX_HISTORY_ENTRIES))
        for entry_data in data.get("entries", []):
            entry = HistoryEntry.from_dict(entry_data)
            history.entries[entry.command_id] = entry
        return history

    def __len__(self) -> int:
        """Get number of history entries."""
        return len(self.entries)


def get_history_path() -> Path:
    """Get the path to command history file.

    Returns:
        Path to ~/.ralph/command_history.json
    """
    return Path.home() / DEFAULT_HISTORY_FILE


def load_history(path: Optional[Path] = None) -> CommandHistory:
    """Load command history from file.

    Args:
        path: Path to history file. Uses default if None.

    Returns:
        CommandHistory instance.
    """
    if path is None:
        path = get_history_path()

    if not path.exists():
        return CommandHistory()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CommandHistory.from_dict(data)
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in history file {path}: {e}")
    except Exception as e:
        logger.warning(f"Error loading history from {path}: {e}")

    return CommandHistory()


def save_history(
    history: CommandHistory,
    path: Optional[Path] = None,
) -> None:
    """Save command history to file.

    Args:
        history: CommandHistory to save.
        path: Path to save to. Uses default if None.
    """
    if path is None:
        path = get_history_path()

    # Create directory if needed
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        data = history.to_dict()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        logger.debug(f"Saved {len(history)} history entries to {path}")
    except Exception as e:
        logger.error(f"Failed to save history to {path}: {e}")
        raise
