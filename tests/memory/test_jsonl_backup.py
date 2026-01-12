"""Tests for JSONL backup store.

Tests cover:
- JSONLBackupStore initialization and basic operations
- File creation and append operations
- Search functionality with various filters
- get_recent() with edge cases
- Corrupt line handling
- dict_to_frame and frame_to_dict conversions
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ralph_agi.memory.jsonl_backup import (
    JSONLBackupStore,
    dict_to_frame,
    frame_to_dict,
)
from ralph_agi.memory.store import MemoryFrame


class TestJSONLBackupStoreInit:
    """Tests for JSONLBackupStore initialization."""

    def test_init_with_string_path(self):
        """Initialize with string path."""
        store = JSONLBackupStore("test.jsonl")
        assert store.backup_path == Path("test.jsonl")

    def test_init_with_path_object(self, tmp_path):
        """Initialize with Path object."""
        path = tmp_path / "backup.jsonl"
        store = JSONLBackupStore(path)
        assert store.backup_path == path

    def test_init_default_path(self):
        """Initialize with default path."""
        store = JSONLBackupStore()
        assert store.backup_path == Path("ralph_memory.jsonl")

    def test_exists_false_for_new_store(self, tmp_path):
        """New store should not exist until first write."""
        store = JSONLBackupStore(tmp_path / "new.jsonl")
        assert not store.exists()


class TestJSONLBackupStoreAppend:
    """Tests for JSONLBackupStore.append()."""

    def test_append_creates_file(self, tmp_path):
        """Append should create file if it doesn't exist."""
        path = tmp_path / "test.jsonl"
        store = JSONLBackupStore(path)

        result = store.append({"id": "1", "content": "test"})

        assert result is True
        assert path.exists()

    def test_append_creates_parent_directories(self, tmp_path):
        """Append should create parent directories."""
        path = tmp_path / "subdir" / "deep" / "test.jsonl"
        store = JSONLBackupStore(path)

        result = store.append({"id": "1", "content": "test"})

        assert result is True
        assert path.exists()

    def test_append_writes_valid_json(self, tmp_path):
        """Append should write valid JSON."""
        path = tmp_path / "test.jsonl"
        store = JSONLBackupStore(path)

        store.append({"id": "1", "content": "hello", "frame_type": "test"})

        with open(path) as f:
            line = f.readline()
            data = json.loads(line)

        assert data["id"] == "1"
        assert data["content"] == "hello"
        assert data["frame_type"] == "test"

    def test_append_adds_backup_timestamp(self, tmp_path):
        """Append should add _backup_timestamp field."""
        path = tmp_path / "test.jsonl"
        store = JSONLBackupStore(path)

        store.append({"id": "1", "content": "test"})

        with open(path) as f:
            data = json.loads(f.readline())

        assert "_backup_timestamp" in data
        assert "T" in data["_backup_timestamp"]  # ISO format

    def test_append_multiple_frames(self, tmp_path):
        """Append multiple frames creates multiple lines."""
        path = tmp_path / "test.jsonl"
        store = JSONLBackupStore(path)

        store.append({"id": "1", "content": "first"})
        store.append({"id": "2", "content": "second"})
        store.append({"id": "3", "content": "third"})

        with open(path) as f:
            lines = f.readlines()

        assert len(lines) == 3

    def test_append_handles_special_characters(self, tmp_path):
        """Append should handle special characters in content."""
        path = tmp_path / "test.jsonl"
        store = JSONLBackupStore(path)

        special_content = 'Line1\nLine2\t"quoted"\u2019smart'
        store.append({"id": "1", "content": special_content})

        with open(path) as f:
            data = json.loads(f.readline())

        assert data["content"] == special_content

    def test_append_serializes_non_json_types(self, tmp_path):
        """Append should serialize non-JSON types using default=str."""
        path = tmp_path / "test.jsonl"
        store = JSONLBackupStore(path)

        from datetime import datetime

        result = store.append({"id": "1", "created": datetime(2026, 1, 11)})

        assert result is True
        with open(path) as f:
            data = json.loads(f.readline())
        assert "2026" in data["created"]


class TestJSONLBackupStoreSearch:
    """Tests for JSONLBackupStore.search()."""

    @pytest.fixture
    def populated_store(self, tmp_path):
        """Create a store with test data."""
        path = tmp_path / "test.jsonl"
        store = JSONLBackupStore(path)

        frames = [
            {"id": "1", "content": "Error in module A", "frame_type": "error"},
            {"id": "2", "content": "Task completed successfully", "frame_type": "result"},
            {"id": "3", "content": "Another error occurred", "frame_type": "error"},
            {"id": "4", "content": "Learning about Python", "frame_type": "learning"},
            {"id": "5", "content": "Decision to use JSONL", "frame_type": "decision"},
        ]
        for frame in frames:
            store.append(frame)

        return store

    def test_search_finds_matching_content(self, populated_store):
        """Search should find frames with matching content."""
        results = populated_store.search("error")

        assert len(results) == 2
        assert all("error" in r["content"].lower() for r in results)

    def test_search_returns_most_recent_first(self, populated_store):
        """Search should return most recent matches first."""
        results = populated_store.search("error")

        # Most recent error (id=3) should be first
        assert results[0]["id"] == "3"
        assert results[1]["id"] == "1"

    def test_search_with_frame_type_filter(self, populated_store):
        """Search should filter by frame_type."""
        results = populated_store.search("*", frame_type="error")

        assert len(results) == 2
        assert all(r["frame_type"] == "error" for r in results)

    def test_search_respects_limit(self, populated_store):
        """Search should respect limit parameter."""
        results = populated_store.search("*", limit=2)

        assert len(results) == 2

    def test_search_case_insensitive_default(self, populated_store):
        """Search should be case-insensitive by default."""
        results = populated_store.search("ERROR")

        assert len(results) == 2

    def test_search_case_sensitive(self, populated_store):
        """Search can be case-sensitive."""
        results = populated_store.search("ERROR", case_insensitive=False)

        assert len(results) == 0

    def test_search_wildcard_returns_all(self, populated_store):
        """Search with '*' should return all frames."""
        results = populated_store.search("*", limit=100)

        assert len(results) == 5

    def test_search_no_matches(self, populated_store):
        """Search with no matches returns empty list."""
        results = populated_store.search("nonexistent")

        assert results == []

    def test_search_empty_file(self, tmp_path):
        """Search on non-existent file returns empty list."""
        store = JSONLBackupStore(tmp_path / "nonexistent.jsonl")

        results = store.search("test")

        assert results == []


class TestJSONLBackupStoreGetRecent:
    """Tests for JSONLBackupStore.get_recent()."""

    def test_get_recent_returns_n_frames(self, tmp_path):
        """get_recent should return up to N frames."""
        path = tmp_path / "test.jsonl"
        store = JSONLBackupStore(path)

        for i in range(10):
            store.append({"id": str(i), "content": f"Frame {i}"})

        results = store.get_recent(5)

        assert len(results) == 5

    def test_get_recent_most_recent_first(self, tmp_path):
        """get_recent should return most recent frames first."""
        path = tmp_path / "test.jsonl"
        store = JSONLBackupStore(path)

        for i in range(5):
            store.append({"id": str(i), "content": f"Frame {i}"})

        results = store.get_recent(3)

        assert results[0]["id"] == "4"  # Most recent
        assert results[1]["id"] == "3"
        assert results[2]["id"] == "2"

    def test_get_recent_fewer_than_n(self, tmp_path):
        """get_recent with fewer frames than N returns all frames."""
        path = tmp_path / "test.jsonl"
        store = JSONLBackupStore(path)

        store.append({"id": "1", "content": "Only one"})

        results = store.get_recent(10)

        assert len(results) == 1

    def test_get_recent_empty_file(self, tmp_path):
        """get_recent on non-existent file returns empty list."""
        store = JSONLBackupStore(tmp_path / "nonexistent.jsonl")

        results = store.get_recent(5)

        assert results == []

    def test_get_recent_default_n(self, tmp_path):
        """get_recent default is 10."""
        path = tmp_path / "test.jsonl"
        store = JSONLBackupStore(path)

        for i in range(20):
            store.append({"id": str(i), "content": f"Frame {i}"})

        results = store.get_recent()

        assert len(results) == 10


class TestJSONLBackupStoreCount:
    """Tests for JSONLBackupStore.count()."""

    def test_count_empty(self, tmp_path):
        """Count on non-existent file returns 0."""
        store = JSONLBackupStore(tmp_path / "nonexistent.jsonl")

        assert store.count() == 0

    def test_count_frames(self, tmp_path):
        """Count returns number of valid frames."""
        path = tmp_path / "test.jsonl"
        store = JSONLBackupStore(path)

        for i in range(5):
            store.append({"id": str(i), "content": f"Frame {i}"})

        assert store.count() == 5


class TestJSONLBackupStoreCorruptLineHandling:
    """Tests for handling corrupt/malformed lines."""

    def test_search_skips_corrupt_lines(self, tmp_path):
        """Search should skip corrupt JSON lines."""
        path = tmp_path / "test.jsonl"

        # Write valid and invalid lines
        with open(path, "w") as f:
            f.write('{"id": "1", "content": "valid"}\n')
            f.write("not valid json\n")
            f.write('{"id": "2", "content": "also valid"}\n')

        store = JSONLBackupStore(path)
        results = store.search("valid")

        assert len(results) == 2

    def test_get_recent_skips_corrupt_lines(self, tmp_path):
        """get_recent should skip corrupt JSON lines."""
        path = tmp_path / "test.jsonl"

        with open(path, "w") as f:
            f.write('{"id": "1", "content": "first"}\n')
            f.write("corrupt line\n")
            f.write('{"id": "2", "content": "second"}\n')

        store = JSONLBackupStore(path)
        results = store.get_recent(10)

        assert len(results) == 2

    def test_count_skips_corrupt_lines(self, tmp_path):
        """count should skip corrupt JSON lines."""
        path = tmp_path / "test.jsonl"

        with open(path, "w") as f:
            f.write('{"id": "1"}\n')
            f.write("corrupt\n")
            f.write('{"id": "2"}\n')

        store = JSONLBackupStore(path)

        assert store.count() == 2


class TestFrameConversion:
    """Tests for frame_to_dict and dict_to_frame conversions."""

    def test_frame_to_dict(self):
        """frame_to_dict should convert MemoryFrame to dict."""
        frame = MemoryFrame(
            id="test-id",
            content="Test content",
            frame_type="test",
            metadata={"key": "value"},
            timestamp="2026-01-11T12:00:00Z",
            session_id="session-1",
            tags=["tag1", "tag2"],
            score=0.95,
        )

        result = frame_to_dict(frame)

        assert result["id"] == "test-id"
        assert result["content"] == "Test content"
        assert result["frame_type"] == "test"
        assert result["metadata"] == {"key": "value"}
        assert result["tags"] == ["tag1", "tag2"]
        assert result["score"] == 0.95

    def test_dict_to_frame(self):
        """dict_to_frame should convert dict to MemoryFrame."""
        data = {
            "id": "test-id",
            "content": "Test content",
            "frame_type": "test",
            "metadata": {"key": "value"},
            "timestamp": "2026-01-11T12:00:00Z",
            "session_id": "session-1",
            "tags": ["tag1"],
            "score": 0.8,
        }

        frame = dict_to_frame(data)

        assert frame.id == "test-id"
        assert frame.content == "Test content"
        assert frame.frame_type == "test"
        assert frame.metadata == {"key": "value"}
        assert frame.session_id == "session-1"
        assert frame.tags == ["tag1"]
        assert frame.score == 0.8

    def test_dict_to_frame_with_missing_fields(self):
        """dict_to_frame should handle missing optional fields."""
        data = {"id": "test-id", "content": "Test"}

        frame = dict_to_frame(data)

        assert frame.id == "test-id"
        assert frame.content == "Test"
        assert frame.frame_type == "unknown"
        assert frame.metadata == {}
        assert frame.session_id is None
        assert frame.tags == []
        assert frame.score is None

    def test_roundtrip_conversion(self):
        """Converting frame->dict->frame should preserve data."""
        original = MemoryFrame(
            id="roundtrip-id",
            content="Roundtrip test",
            frame_type="test",
            metadata={"nested": {"data": True}},
            timestamp="2026-01-11T12:00:00Z",
            session_id="session-1",
            tags=["a", "b"],
            score=0.5,
        )

        converted = dict_to_frame(frame_to_dict(original))

        assert converted.id == original.id
        assert converted.content == original.content
        assert converted.frame_type == original.frame_type
        assert converted.metadata == original.metadata
        assert converted.session_id == original.session_id
        assert converted.tags == original.tags
        assert converted.score == original.score


class TestJSONLBackupStoreIntegration:
    """Integration tests for JSONLBackupStore."""

    def test_full_workflow(self, tmp_path):
        """Test complete workflow: append, search, get_recent."""
        path = tmp_path / "integration.jsonl"
        store = JSONLBackupStore(path)

        # Append frames
        for i in range(10):
            frame_type = "error" if i % 3 == 0 else "result"
            store.append({
                "id": str(i),
                "content": f"Frame {i} content",
                "frame_type": frame_type,
            })

        # Verify count
        assert store.count() == 10

        # Search for errors
        errors = store.search("*", frame_type="error")
        assert len(errors) == 4  # 0, 3, 6, 9

        # Get recent
        recent = store.get_recent(3)
        assert recent[0]["id"] == "9"

        # Search for specific content
        matches = store.search("Frame 5")
        assert len(matches) == 1
        assert matches[0]["id"] == "5"
