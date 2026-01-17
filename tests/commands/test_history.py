"""Tests for command history."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from datetime import datetime

from ralph_agi.commands.history import (
    HistoryEntry,
    CommandHistory,
    load_history,
    save_history,
    get_history_path,
)


class TestHistoryEntry:
    """Tests for HistoryEntry dataclass."""

    def test_entry_creation(self):
        """Test creating a history entry."""
        entry = HistoryEntry(command_id="test.cmd")
        assert entry.command_id == "test.cmd"
        assert entry.count == 1
        assert entry.timestamp is not None

    def test_entry_with_values(self):
        """Test creating entry with specific values."""
        entry = HistoryEntry(
            command_id="test.cmd",
            timestamp="2025-01-01T00:00:00",
            count=5,
        )
        assert entry.command_id == "test.cmd"
        assert entry.timestamp == "2025-01-01T00:00:00"
        assert entry.count == 5

    def test_to_dict(self):
        """Test converting entry to dictionary."""
        entry = HistoryEntry(
            command_id="test.cmd",
            timestamp="2025-01-01T00:00:00",
            count=3,
        )
        data = entry.to_dict()

        assert data["command_id"] == "test.cmd"
        assert data["timestamp"] == "2025-01-01T00:00:00"
        assert data["count"] == 3

    def test_from_dict(self):
        """Test creating entry from dictionary."""
        data = {
            "command_id": "test.cmd",
            "timestamp": "2025-01-01T00:00:00",
            "count": 7,
        }
        entry = HistoryEntry.from_dict(data)

        assert entry.command_id == "test.cmd"
        assert entry.timestamp == "2025-01-01T00:00:00"
        assert entry.count == 7

    def test_from_dict_defaults(self):
        """Test creating entry from minimal dictionary."""
        data = {"command_id": "test.cmd"}
        entry = HistoryEntry.from_dict(data)

        assert entry.command_id == "test.cmd"
        assert entry.count == 1


class TestCommandHistory:
    """Tests for CommandHistory class."""

    def test_history_creation(self):
        """Test creating empty history."""
        history = CommandHistory()
        assert len(history) == 0

    def test_record_new_command(self):
        """Test recording a new command."""
        history = CommandHistory()
        history.record("test.cmd")

        assert len(history) == 1
        assert history.get_count("test.cmd") == 1

    def test_record_existing_command(self):
        """Test recording same command multiple times."""
        history = CommandHistory()
        history.record("test.cmd")
        history.record("test.cmd")
        history.record("test.cmd")

        assert len(history) == 1
        assert history.get_count("test.cmd") == 3

    def test_get_recent(self):
        """Test getting recent commands."""
        history = CommandHistory()

        # Record in specific order with timestamps
        history.record("cmd1")
        history.record("cmd2")
        history.record("cmd3")

        recent = history.get_recent(limit=2)

        # Most recent should be last recorded
        assert len(recent) == 2
        assert recent[0] == "cmd3"

    def test_get_frequent(self):
        """Test getting frequent commands."""
        history = CommandHistory()

        history.record("cmd1")
        history.record("cmd2")
        history.record("cmd2")
        history.record("cmd2")
        history.record("cmd3")
        history.record("cmd3")

        frequent = history.get_frequent(limit=2)

        assert len(frequent) == 2
        assert frequent[0] == "cmd2"  # Most frequent
        assert frequent[1] == "cmd3"  # Second most frequent

    def test_get_count(self):
        """Test getting execution count."""
        history = CommandHistory()
        history.record("cmd1")
        history.record("cmd1")
        history.record("cmd2")

        assert history.get_count("cmd1") == 2
        assert history.get_count("cmd2") == 1
        assert history.get_count("cmd3") == 0  # Never executed

    def test_clear(self):
        """Test clearing history."""
        history = CommandHistory()
        history.record("cmd1")
        history.record("cmd2")

        history.clear()

        assert len(history) == 0

    def test_prune_on_overflow(self):
        """Test that old entries are pruned when limit exceeded."""
        history = CommandHistory(max_entries=3)

        history.record("cmd1")
        history.record("cmd2")
        history.record("cmd3")
        history.record("cmd4")  # Should trigger prune

        assert len(history) == 3

    def test_to_dict(self):
        """Test converting history to dictionary."""
        history = CommandHistory()
        history.record("cmd1")
        history.record("cmd2")

        data = history.to_dict()

        assert data["version"] == "1.0"
        assert len(data["entries"]) == 2

    def test_from_dict(self):
        """Test creating history from dictionary."""
        data = {
            "version": "1.0",
            "max_entries": 50,
            "entries": [
                {"command_id": "cmd1", "count": 3},
                {"command_id": "cmd2", "count": 1},
            ],
        }
        history = CommandHistory.from_dict(data)

        assert history.max_entries == 50
        assert len(history) == 2
        assert history.get_count("cmd1") == 3


class TestHistoryPersistence:
    """Tests for history load/save functions."""

    def test_get_history_path(self):
        """Test getting history path."""
        path = get_history_path()
        assert path.name == "command_history.json"
        assert ".ralph" in str(path)

    def test_load_nonexistent(self, tmp_path):
        """Test loading from nonexistent file."""
        path = tmp_path / "history.json"
        history = load_history(path)

        assert isinstance(history, CommandHistory)
        assert len(history) == 0

    def test_save_and_load(self, tmp_path):
        """Test saving and loading history."""
        path = tmp_path / "history.json"

        # Create and save
        history = CommandHistory()
        history.record("cmd1")
        history.record("cmd2")
        history.record("cmd1")
        save_history(history, path)

        # Load and verify
        loaded = load_history(path)
        assert len(loaded) == 2
        assert loaded.get_count("cmd1") == 2
        assert loaded.get_count("cmd2") == 1

    def test_save_creates_directory(self, tmp_path):
        """Test that save creates parent directory."""
        path = tmp_path / "subdir" / "history.json"
        history = CommandHistory()
        history.record("cmd1")

        save_history(history, path)

        assert path.exists()

    def test_load_invalid_json(self, tmp_path):
        """Test loading from invalid JSON file."""
        path = tmp_path / "history.json"
        path.write_text("not valid json {{{")

        # Should return empty history, not raise
        history = load_history(path)
        assert len(history) == 0

    def test_load_valid_json(self, tmp_path):
        """Test loading from valid JSON file."""
        path = tmp_path / "history.json"
        data = {
            "version": "1.0",
            "max_entries": 100,
            "entries": [
                {"command_id": "test.cmd", "timestamp": "2025-01-01T00:00:00", "count": 5}
            ],
        }
        path.write_text(json.dumps(data))

        history = load_history(path)
        assert len(history) == 1
        assert history.get_count("test.cmd") == 5
