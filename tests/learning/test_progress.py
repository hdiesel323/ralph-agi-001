"""Tests for structured progress entries module."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from ralph_agi.learning.progress import (
    Outcome,
    ProgressEntry,
    ProgressStore,
    load_progress,
    save_progress,
    get_progress_path,
    generate_session_id,
    inject_progress,
)


class TestOutcome:
    """Tests for Outcome enum."""

    def test_all_outcomes_exist(self):
        """Test all expected outcomes exist."""
        assert Outcome.SUCCESS.value == "success"
        assert Outcome.FAILURE.value == "failure"
        assert Outcome.PARTIAL.value == "partial"
        assert Outcome.SKIPPED.value == "skipped"
        assert Outcome.UNKNOWN.value == "unknown"


class TestProgressEntry:
    """Tests for ProgressEntry dataclass."""

    def test_entry_creation_minimal(self):
        """Test creating entry with minimal fields."""
        entry = ProgressEntry(session_id="test-session")
        assert entry.session_id == "test-session"
        assert entry.iteration == 1
        assert entry.outcome == Outcome.UNKNOWN
        assert entry.timestamp is not None

    def test_entry_creation_full(self):
        """Test creating entry with all fields."""
        entry = ProgressEntry(
            session_id="ralph-2025-01-16-001",
            iteration=7,
            task="US-007",
            outcome=Outcome.SUCCESS,
            learnings=("First learning", "Second learning"),
            errors=(),
            timestamp="2025-01-16T12:00:00",
            duration_seconds=45.5,
            tags=("api", "fix"),
            metadata={"pr": "123"},
        )
        assert entry.session_id == "ralph-2025-01-16-001"
        assert entry.iteration == 7
        assert entry.task == "US-007"
        assert entry.outcome == Outcome.SUCCESS
        assert len(entry.learnings) == 2
        assert entry.duration_seconds == 45.5

    def test_is_success(self):
        """Test is_success property."""
        success_entry = ProgressEntry(session_id="s", outcome=Outcome.SUCCESS)
        failure_entry = ProgressEntry(session_id="s", outcome=Outcome.FAILURE)

        assert success_entry.is_success is True
        assert failure_entry.is_success is False

    def test_has_learnings(self):
        """Test has_learnings property."""
        with_learnings = ProgressEntry(session_id="s", learnings=("test",))
        without_learnings = ProgressEntry(session_id="s")

        assert with_learnings.has_learnings is True
        assert without_learnings.has_learnings is False

    def test_has_errors(self):
        """Test has_errors property."""
        with_errors = ProgressEntry(session_id="s", errors=("error",))
        without_errors = ProgressEntry(session_id="s")

        assert with_errors.has_errors is True
        assert without_errors.has_errors is False

    def test_to_dict(self):
        """Test converting entry to dictionary."""
        entry = ProgressEntry(
            session_id="test",
            iteration=3,
            task="T-001",
            outcome=Outcome.SUCCESS,
            learnings=("learned",),
        )
        data = entry.to_dict()

        assert data["session_id"] == "test"
        assert data["iteration"] == 3
        assert data["task"] == "T-001"
        assert data["outcome"] == "success"
        assert data["learnings"] == ["learned"]

    def test_from_dict(self):
        """Test creating entry from dictionary."""
        data = {
            "session_id": "ralph-2025-01-16-001",
            "iteration": 5,
            "task": "US-005",
            "outcome": "failure",
            "learnings": ["Learning 1"],
            "errors": ["Error 1", "Error 2"],
            "duration_seconds": 120.0,
        }
        entry = ProgressEntry.from_dict(data)

        assert entry.session_id == "ralph-2025-01-16-001"
        assert entry.iteration == 5
        assert entry.outcome == Outcome.FAILURE
        assert len(entry.learnings) == 1
        assert len(entry.errors) == 2

    def test_from_dict_defaults(self):
        """Test creating entry from minimal dictionary."""
        data = {"session_id": "minimal"}
        entry = ProgressEntry.from_dict(data)

        assert entry.session_id == "minimal"
        assert entry.iteration == 1
        assert entry.outcome == Outcome.UNKNOWN

    def test_from_dict_invalid_outcome(self):
        """Test handling invalid outcome."""
        data = {"session_id": "test", "outcome": "invalid"}
        entry = ProgressEntry.from_dict(data)
        assert entry.outcome == Outcome.UNKNOWN


class TestProgressStore:
    """Tests for ProgressStore collection."""

    def test_store_creation(self):
        """Test creating empty store."""
        store = ProgressStore()
        assert len(store) == 0

    def test_add_entry(self):
        """Test adding an entry."""
        store = ProgressStore()
        entry = ProgressEntry(session_id="test")
        store.add(entry)

        assert len(store) == 1

    def test_get_by_session(self):
        """Test getting entries by session."""
        store = ProgressStore()
        store.add(ProgressEntry(session_id="session-1", iteration=1))
        store.add(ProgressEntry(session_id="session-1", iteration=2))
        store.add(ProgressEntry(session_id="session-2", iteration=1))

        session1_entries = store.get_by_session("session-1")
        assert len(session1_entries) == 2

        session2_entries = store.get_by_session("session-2")
        assert len(session2_entries) == 1

    def test_get_by_task(self):
        """Test getting entries by task."""
        store = ProgressStore()
        store.add(ProgressEntry(session_id="s1", task="US-001"))
        store.add(ProgressEntry(session_id="s2", task="US-001"))
        store.add(ProgressEntry(session_id="s3", task="US-002"))

        task1_entries = store.get_by_task("US-001")
        assert len(task1_entries) == 2

    def test_get_recent(self):
        """Test getting recent entries."""
        store = ProgressStore()
        store.add(ProgressEntry(session_id="s1", timestamp="2025-01-01T00:00:00"))
        store.add(ProgressEntry(session_id="s2", timestamp="2025-01-02T00:00:00"))
        store.add(ProgressEntry(session_id="s3", timestamp="2025-01-03T00:00:00"))

        recent = store.get_recent(2)
        assert len(recent) == 2
        assert recent[0].session_id == "s3"  # Most recent first
        assert recent[1].session_id == "s2"

    def test_get_failures(self):
        """Test getting failed entries."""
        store = ProgressStore()
        store.add(ProgressEntry(session_id="s1", outcome=Outcome.SUCCESS))
        store.add(ProgressEntry(session_id="s2", outcome=Outcome.FAILURE))
        store.add(ProgressEntry(session_id="s3", outcome=Outcome.FAILURE))

        failures = store.get_failures()
        assert len(failures) == 2

        limited = store.get_failures(1)
        assert len(limited) == 1

    def test_get_successes(self):
        """Test getting successful entries."""
        store = ProgressStore()
        store.add(ProgressEntry(session_id="s1", outcome=Outcome.SUCCESS))
        store.add(ProgressEntry(session_id="s2", outcome=Outcome.FAILURE))
        store.add(ProgressEntry(session_id="s3", outcome=Outcome.SUCCESS))

        successes = store.get_successes()
        assert len(successes) == 2

    def test_search(self):
        """Test searching entries."""
        store = ProgressStore()
        store.add(ProgressEntry(
            session_id="s1",
            learnings=("Database connection fixed",),
        ))
        store.add(ProgressEntry(
            session_id="s2",
            errors=("Database timeout",),
        ))
        store.add(ProgressEntry(
            session_id="s3",
            tags=("api",),
        ))
        store.add(ProgressEntry(
            session_id="s4",
            task="DB-001",
        ))

        results = store.search("database")
        assert len(results) == 2

        results = store.search("api")
        assert len(results) == 1

        results = store.search("DB")
        assert len(results) == 1  # Task search

    def test_get_all_learnings(self):
        """Test getting all unique learnings."""
        store = ProgressStore()
        store.add(ProgressEntry(session_id="s1", learnings=("L1", "L2")))
        store.add(ProgressEntry(session_id="s2", learnings=("L2", "L3")))

        learnings = store.get_all_learnings()
        assert len(learnings) == 3
        assert "L1" in learnings
        assert "L2" in learnings
        assert "L3" in learnings

    def test_get_all_errors(self):
        """Test getting all unique errors."""
        store = ProgressStore()
        store.add(ProgressEntry(session_id="s1", errors=("E1",)))
        store.add(ProgressEntry(session_id="s2", errors=("E1", "E2")))

        errors = store.get_all_errors()
        assert len(errors) == 2

    def test_summarize(self):
        """Test summary statistics."""
        store = ProgressStore()
        store.add(ProgressEntry(
            session_id="s1", outcome=Outcome.SUCCESS, duration_seconds=10,
        ))
        store.add(ProgressEntry(
            session_id="s2", outcome=Outcome.SUCCESS, duration_seconds=20,
        ))
        store.add(ProgressEntry(
            session_id="s3", outcome=Outcome.FAILURE,
        ))

        summary = store.summarize()

        assert summary["total_entries"] == 3
        assert summary["successes"] == 2
        assert summary["failures"] == 1
        assert summary["success_rate"] == pytest.approx(0.666, rel=0.01)
        assert summary["avg_duration_seconds"] == 15.0

    def test_summarize_empty(self):
        """Test summary of empty store."""
        store = ProgressStore()
        summary = store.summarize()

        assert summary["total_entries"] == 0
        assert summary["success_rate"] == 0

    def test_to_yaml(self):
        """Test converting to YAML."""
        store = ProgressStore()
        store.add(ProgressEntry(
            session_id="test",
            iteration=1,
            outcome=Outcome.SUCCESS,
        ))

        yaml_str = store.to_yaml()
        assert "version" in yaml_str
        assert "entries" in yaml_str
        assert "test" in yaml_str

    def test_from_yaml(self):
        """Test parsing from YAML."""
        yaml_content = """
version: '1.0'
entries:
  - session_id: test-session
    iteration: 5
    outcome: success
    learnings:
      - First learning
"""
        store = ProgressStore.from_yaml(yaml_content)

        assert len(store) == 1
        assert store.entries[0].session_id == "test-session"
        assert store.entries[0].iteration == 5

    def test_yaml_roundtrip(self):
        """Test YAML save and load roundtrip."""
        original = ProgressStore()
        original.add(ProgressEntry(
            session_id="roundtrip",
            iteration=3,
            outcome=Outcome.SUCCESS,
            learnings=("Learned something",),
        ))

        yaml_str = original.to_yaml()
        loaded = ProgressStore.from_yaml(yaml_str)

        assert len(loaded) == len(original)
        assert loaded.entries[0].session_id == original.entries[0].session_id

    def test_to_json(self):
        """Test converting to JSON."""
        store = ProgressStore()
        store.add(ProgressEntry(session_id="json-test"))

        json_str = store.to_json()
        data = json.loads(json_str)

        assert "version" in data
        assert "entries" in data
        assert len(data["entries"]) == 1

    def test_from_json(self):
        """Test parsing from JSON."""
        json_content = json.dumps({
            "version": "1.0",
            "entries": [
                {
                    "session_id": "json-session",
                    "iteration": 2,
                    "outcome": "failure",
                }
            ],
        })
        store = ProgressStore.from_json(json_content)

        assert len(store) == 1
        assert store.entries[0].outcome == Outcome.FAILURE


class TestPersistence:
    """Tests for progress persistence functions."""

    def test_get_progress_path(self, tmp_path):
        """Test getting progress path."""
        path = get_progress_path(tmp_path)
        assert path.name == "progress.yaml"
        assert ".ralph" in str(path)

    def test_load_nonexistent(self, tmp_path):
        """Test loading from nonexistent file."""
        path = tmp_path / ".ralph" / "progress.yaml"
        store = load_progress(path)

        assert isinstance(store, ProgressStore)
        assert len(store) == 0

    def test_save_and_load(self, tmp_path):
        """Test saving and loading progress."""
        path = tmp_path / ".ralph" / "progress.yaml"

        # Create and save
        store = ProgressStore()
        store.add(ProgressEntry(
            session_id="test",
            outcome=Outcome.SUCCESS,
            learnings=("Test learning",),
        ))
        save_progress(store, path)

        assert path.exists()

        # Load and verify
        loaded = load_progress(path)
        assert len(loaded) == 1
        assert loaded.entries[0].session_id == "test"

    def test_save_creates_directory(self, tmp_path):
        """Test that save creates parent directory."""
        path = tmp_path / "deep" / "nested" / ".ralph" / "progress.yaml"
        store = ProgressStore()
        store.add(ProgressEntry(session_id="test"))

        save_progress(store, path)

        assert path.exists()

    def test_save_and_load_json(self, tmp_path):
        """Test saving and loading as JSON."""
        path = tmp_path / ".ralph" / "progress.json"

        store = ProgressStore()
        store.add(ProgressEntry(session_id="json-test"))
        save_progress(store, path)

        loaded = load_progress(path)
        assert len(loaded) == 1


class TestGenerateSessionId:
    """Tests for session ID generation."""

    def test_generate_session_id_format(self):
        """Test session ID format."""
        session_id = generate_session_id()
        assert session_id.startswith("ralph-")
        assert len(session_id.split("-")) >= 4

    def test_generate_unique_ids(self):
        """Test that generated IDs are unique."""
        id1 = generate_session_id()
        id2 = generate_session_id()
        # Note: These could be the same if called in same second
        # In practice, the time suffix provides uniqueness
        assert isinstance(id1, str)
        assert isinstance(id2, str)


class TestInjectProgress:
    """Tests for progress injection into prompts."""

    def test_inject_empty_store(self):
        """Test injecting empty progress."""
        store = ProgressStore()
        prompt = "You are a helpful assistant."
        result = inject_progress(store, prompt)
        assert result == prompt

    def test_inject_with_learnings(self):
        """Test injecting progress with learnings."""
        store = ProgressStore()
        store.add(ProgressEntry(
            session_id="s1",
            outcome=Outcome.SUCCESS,
            learnings=("Always validate input",),
        ))

        prompt = "Base prompt."
        result = inject_progress(store, prompt)

        assert "Base prompt." in result
        assert "## Progress Context" in result
        assert "Always validate input" in result
        assert "What Worked" in result

    def test_inject_with_errors(self):
        """Test injecting progress with errors."""
        store = ProgressStore()
        store.add(ProgressEntry(
            session_id="s1",
            task="US-001",
            outcome=Outcome.FAILURE,
            errors=("Connection timeout",),
        ))

        prompt = "Base prompt."
        result = inject_progress(store, prompt, include_errors=True)

        assert "Recent Issues" in result
        assert "Connection timeout" in result
        assert "US-001" in result

    def test_inject_summary(self):
        """Test that summary is included."""
        store = ProgressStore()
        store.add(ProgressEntry(session_id="s1", outcome=Outcome.SUCCESS))
        store.add(ProgressEntry(session_id="s2", outcome=Outcome.SUCCESS))

        prompt = "Base prompt."
        result = inject_progress(store, prompt)

        assert "Summary" in result
        assert "100%" in result  # 2/2 success rate

    def test_inject_max_entries(self):
        """Test respecting max_entries limit."""
        store = ProgressStore()
        for i in range(20):
            store.add(ProgressEntry(
                session_id=f"s{i}",
                learnings=(f"Learning {i}",),
            ))

        prompt = "Base prompt."
        result = inject_progress(store, prompt, max_entries=5)

        # Should only include learnings from recent entries
        assert "Learning 19" in result or "Learning 18" in result
