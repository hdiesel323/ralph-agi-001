"""Tests for the memory store module.

Tests cover:
- MemoryFrame dataclass
- MemoryStore initialization (lazy)
- Append functionality
- Search and retrieval
- Context manager support
- Error handling
"""

import sys
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from ralph_agi.memory.store import (
    MemoryFrame,
    MemoryQueryResult,
    MemoryStore,
    MemoryStoreError,
)


class TestMemoryFrame:
    """Tests for MemoryFrame dataclass."""

    def test_create_with_required_fields(self):
        """Test creating frame with only required fields."""
        frame = MemoryFrame(
            id="test-123",
            content="Test content",
            frame_type="general",
        )
        assert frame.id == "test-123"
        assert frame.content == "Test content"
        assert frame.frame_type == "general"
        assert frame.metadata == {}
        assert frame.tags == []
        assert frame.session_id is None

    def test_create_with_all_fields(self):
        """Test creating frame with all fields."""
        frame = MemoryFrame(
            id="test-456",
            content="Full content",
            frame_type="iteration_result",
            metadata={"iteration": 5},
            timestamp="2026-01-11T12:00:00+00:00",
            session_id="session-abc",
            tags=["important", "learning"],
        )
        assert frame.id == "test-456"
        assert frame.frame_type == "iteration_result"
        assert frame.metadata == {"iteration": 5}
        assert frame.session_id == "session-abc"
        assert "important" in frame.tags

    def test_default_timestamp_is_set(self):
        """Test that timestamp is auto-generated if not provided."""
        frame = MemoryFrame(
            id="test-789",
            content="Test",
            frame_type="general",
        )
        assert frame.timestamp is not None
        # Should be ISO format
        assert "T" in frame.timestamp

    def test_default_score_is_none(self):
        """Test that score defaults to None."""
        frame = MemoryFrame(
            id="test-000",
            content="Test",
            frame_type="general",
        )
        assert frame.score is None

    def test_create_with_score(self):
        """Test creating frame with explicit score."""
        frame = MemoryFrame(
            id="test-scored",
            content="Scored content",
            frame_type="general",
            score=0.85,
        )
        assert frame.score == 0.85

    def test_estimate_tokens(self):
        """Test token estimation."""
        # ~4 chars per token
        frame = MemoryFrame(
            id="test",
            content="a" * 100,  # 100 chars = ~25 tokens
            frame_type="general",
        )
        tokens = frame.estimate_tokens()
        assert tokens == 26  # 100 // 4 + 1


class TestMemoryQueryResult:
    """Tests for MemoryQueryResult dataclass."""

    def test_create_minimal(self):
        """Test creating result with minimal fields."""
        result = MemoryQueryResult(
            frames=[],
            query="test",
            mode="keyword",
            total_count=0,
        )
        assert result.frames == []
        assert result.query == "test"
        assert result.mode == "keyword"
        assert result.total_count == 0
        assert result.truncated is False
        assert result.query_time_ms == 0.0
        assert result.token_count == 0

    def test_create_with_all_fields(self):
        """Test creating result with all fields."""
        frames = [
            MemoryFrame(id="1", content="test", frame_type="general"),
        ]
        result = MemoryQueryResult(
            frames=frames,
            query="search",
            mode="hybrid",
            total_count=5,
            truncated=True,
            query_time_ms=15.5,
            token_count=100,
        )
        assert len(result.frames) == 1
        assert result.total_count == 5
        assert result.truncated is True
        assert result.query_time_ms == 15.5
        assert result.token_count == 100


class TestMemoryStoreInit:
    """Tests for MemoryStore initialization."""

    def test_init_with_default_path(self):
        """Test initialization with default path."""
        store = MemoryStore()
        assert store.store_path == Path("ralph_memory.mv2")
        assert store.initialized is False

    def test_init_with_custom_path(self, tmp_path):
        """Test initialization with custom path."""
        custom_path = tmp_path / "custom.mv2"
        store = MemoryStore(custom_path)
        assert store.store_path == custom_path
        assert store.initialized is False

    def test_lazy_initialization(self):
        """Test that store is not initialized until first use."""
        store = MemoryStore()
        assert store._mv is None
        assert store._initialized is False


@pytest.fixture
def mock_memvid_sdk():
    """Fixture that mocks the memvid_sdk module."""
    mock_mv = MagicMock()
    mock_mv.find.return_value = {"hits": []}
    mock_mv.put.return_value = None
    mock_mv.seal.return_value = None

    mock_module = MagicMock()
    mock_module.create.return_value = mock_mv
    mock_module.use.return_value = mock_mv

    # Insert mock module into sys.modules
    original = sys.modules.get("memvid_sdk")
    sys.modules["memvid_sdk"] = mock_module

    yield {"module": mock_module, "mv": mock_mv}

    # Restore original
    if original is not None:
        sys.modules["memvid_sdk"] = original
    else:
        del sys.modules["memvid_sdk"]


class TestMemoryStoreWithMock:
    """Tests for MemoryStore operations using mocked memvid."""

    def test_append_creates_frame(self, tmp_path, mock_memvid_sdk):
        """Test that append creates a frame with correct data."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]

        # Need to reimport to pick up the mock
        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store = store_module.MemoryStore(store_path)
        frame_id = store.append(
            content="Test iteration completed",
            frame_type="iteration_result",
            metadata={"iteration": 1},
        )

        assert frame_id is not None
        assert len(frame_id) == 36  # UUID length
        mock_mv.put.assert_called_once()

        # Check the call arguments
        call_kwargs = mock_mv.put.call_args.kwargs
        assert call_kwargs["text"] == "Test iteration completed"
        assert call_kwargs["label"] == "iteration_result"
        assert "iteration_result" in call_kwargs["tags"]

    def test_append_with_session(self, tmp_path, mock_memvid_sdk):
        """Test append with session_id."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store = store_module.MemoryStore(store_path)
        store.append(
            content="Session content",
            frame_type="general",
            session_id="sess-123",
        )

        call_kwargs = mock_mv.put.call_args.kwargs
        assert "session:sess-123" in call_kwargs["tags"]
        assert call_kwargs["metadata"]["session_id"] == "sess-123"

    def test_get_recent_returns_frames(self, tmp_path, mock_memvid_sdk):
        """Test get_recent returns MemoryFrame objects."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]
        mock_mv.find.return_value = {
            "hits": [
                {
                    "id": "1",
                    "text": "First content",
                    "label": "general",
                    "metadata": {
                        "frame_id": "uuid-1",
                        "frame_type": "general",
                        "timestamp": "2026-01-11T12:00:00+00:00",
                    },
                    "tags": ["general"],
                },
                {
                    "id": "2",
                    "text": "Second content",
                    "label": "learning",
                    "metadata": {
                        "frame_id": "uuid-2",
                        "frame_type": "learning",
                        "timestamp": "2026-01-11T12:01:00+00:00",
                    },
                    "tags": ["learning"],
                },
            ]
        }

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        # Create a file so it opens instead of creates
        store_path.write_text("")

        store = store_module.MemoryStore(store_path)
        frames = store.get_recent(10)

        assert len(frames) == 2
        assert isinstance(frames[0], store_module.MemoryFrame)
        assert frames[0].content == "First content"
        assert frames[1].frame_type == "learning"

    def test_search_with_query(self, tmp_path, mock_memvid_sdk):
        """Test search returns matching frames."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]
        mock_mv.find.return_value = {
            "hits": [
                {
                    "id": "1",
                    "text": "Error in iteration 5",
                    "label": "error",
                    "metadata": {
                        "frame_id": "uuid-1",
                        "frame_type": "error",
                    },
                    "tags": ["error"],
                },
            ]
        }

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)
        frames = store.search("error", limit=5)

        mock_mv.find.assert_called()
        assert len(frames) == 1
        assert frames[0].frame_type == "error"

    def test_search_semantic_mode(self, tmp_path, mock_memvid_sdk):
        """Test search with semantic mode."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]
        mock_mv.find.return_value = {"hits": []}

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)
        store.search("similar concepts", mode="semantic")

        # Verify semantic mode was passed
        call_kwargs = mock_mv.find.call_args.kwargs
        assert call_kwargs["mode"] == "sem"

    def test_close_seals_store(self, tmp_path, mock_memvid_sdk):
        """Test close calls seal on memvid."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store = store_module.MemoryStore(store_path)
        store.append("test", "general")
        store.close()

        mock_mv.seal.assert_called_once()
        assert store._initialized is False
        assert store._mv is None

    def test_context_manager_closes_store(self, tmp_path, mock_memvid_sdk):
        """Test that context manager closes store on exit."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        with store_module.MemoryStore(store_path) as store:
            store.append("test", "general")

        mock_mv.seal.assert_called_once()


class TestMemoryStoreErrorHandling:
    """Tests for error handling."""

    def test_get_recent_without_init_returns_empty(self, tmp_path):
        """Test get_recent returns empty list if store not initialized."""
        store = MemoryStore(tmp_path / "nonexistent.mv2")
        # Store doesn't exist and create=False, so should return empty
        frames = store.get_recent()
        assert frames == []

    def test_search_without_init_returns_empty(self, tmp_path):
        """Test search returns empty list if store not initialized."""
        store = MemoryStore(tmp_path / "nonexistent.mv2")
        frames = store.search("anything")
        assert frames == []

    def test_get_by_session_without_init_returns_empty(self, tmp_path):
        """Test get_by_session returns empty list if store not initialized."""
        store = MemoryStore(tmp_path / "nonexistent.mv2")
        frames = store.get_by_session("any-session")
        assert frames == []


class TestSearchSimilar:
    """Tests for search_similar method."""

    def test_search_similar_uses_semantic_mode(self, tmp_path, mock_memvid_sdk):
        """Test search_similar uses semantic mode."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]
        mock_mv.find.return_value = {"hits": []}

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)
        store.search_similar("error handling patterns", limit=5)

        # Verify semantic mode was passed
        call_kwargs = mock_mv.find.call_args.kwargs
        assert call_kwargs["mode"] == "sem"

    def test_search_similar_returns_scored_frames(self, tmp_path, mock_memvid_sdk):
        """Test search_similar returns frames with scores."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]
        mock_mv.find.return_value = {
            "hits": [
                {
                    "id": "1",
                    "text": "Error handling code",
                    "label": "learning",
                    "score": 0.92,
                    "metadata": {"frame_id": "uuid-1", "frame_type": "learning"},
                    "tags": ["learning"],
                },
                {
                    "id": "2",
                    "text": "Other code patterns",
                    "label": "general",
                    "score": 0.75,
                    "metadata": {"frame_id": "uuid-2", "frame_type": "general"},
                    "tags": ["general"],
                },
            ]
        }

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)
        results = store.search_similar("error handling", limit=5)

        assert len(results) == 2
        assert results[0].score == 0.92
        assert results[1].score == 0.75

    def test_search_similar_without_init_returns_empty(self, tmp_path):
        """Test search_similar returns empty if store not initialized."""
        store = MemoryStore(tmp_path / "nonexistent.mv2")
        results = store.search_similar("anything")
        assert results == []


class TestSearchHybrid:
    """Tests for search_hybrid method."""

    def test_search_hybrid_combines_results(self, tmp_path, mock_memvid_sdk):
        """Test search_hybrid combines semantic and keyword results."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]

        # Different results for semantic vs keyword
        def find_side_effect(query, k=10, mode=None):
            if mode == "sem":
                return {
                    "hits": [
                        {
                            "id": "1",
                            "text": "Semantic match 1",
                            "label": "general",
                            "score": 0.9,
                            "metadata": {"frame_id": "uuid-1", "frame_type": "general"},
                            "tags": ["general"],
                        },
                    ]
                }
            else:
                return {
                    "hits": [
                        {
                            "id": "2",
                            "text": "Keyword match 1",
                            "label": "general",
                            "score": 0.8,
                            "metadata": {"frame_id": "uuid-2", "frame_type": "general"},
                            "tags": ["general"],
                        },
                    ]
                }

        mock_mv.find.side_effect = find_side_effect

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)
        results = store.search_hybrid("test query", limit=10)

        # Should have both results
        assert len(results) == 2
        # Both should have combined scores
        assert all(r.score is not None for r in results)

    def test_search_hybrid_deduplicates(self, tmp_path, mock_memvid_sdk):
        """Test search_hybrid deduplicates overlapping results."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]

        # Same frame appears in both results
        def find_side_effect(query, k=10, mode=None):
            return {
                "hits": [
                    {
                        "id": "1",
                        "text": "Common result",
                        "label": "general",
                        "score": 0.9 if mode == "sem" else 0.7,
                        "metadata": {"frame_id": "uuid-1", "frame_type": "general"},
                        "tags": ["general"],
                    },
                ]
            }

        mock_mv.find.side_effect = find_side_effect

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)
        results = store.search_hybrid("test query", limit=10)

        # Should deduplicate to single result
        assert len(results) == 1
        # Combined score: 0.9 * 0.7 + 0.7 * 0.3 = 0.63 + 0.21 = 0.84
        assert abs(results[0].score - 0.84) < 0.01

    def test_search_hybrid_respects_weights(self, tmp_path, mock_memvid_sdk):
        """Test search_hybrid applies weights correctly."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]

        def find_side_effect(query, k=10, mode=None):
            return {
                "hits": [
                    {
                        "id": "1",
                        "text": "Common result",
                        "label": "general",
                        "score": 1.0,  # Perfect score in both modes
                        "metadata": {"frame_id": "uuid-1", "frame_type": "general"},
                        "tags": ["general"],
                    },
                ]
            }

        mock_mv.find.side_effect = find_side_effect

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)

        # With 50/50 weights
        results = store.search_hybrid(
            "test", limit=10, semantic_weight=0.5, keyword_weight=0.5
        )
        assert len(results) == 1
        # 1.0 * 0.5 + 1.0 * 0.5 = 1.0
        assert abs(results[0].score - 1.0) < 0.01

    def test_search_hybrid_zero_weights_returns_empty(self, tmp_path, mock_memvid_sdk):
        """Test search_hybrid returns empty with zero weights."""
        store_path = tmp_path / "test.mv2"

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)
        results = store.search_hybrid(
            "test", semantic_weight=0.0, keyword_weight=0.0
        )
        assert results == []

    def test_search_hybrid_without_init_returns_empty(self, tmp_path):
        """Test search_hybrid returns empty if store not initialized."""
        store = MemoryStore(tmp_path / "nonexistent.mv2")
        results = store.search_hybrid("anything")
        assert results == []


class TestUnifiedQuery:
    """Tests for the unified query() method."""

    def test_query_returns_result_object(self, tmp_path, mock_memvid_sdk):
        """Test query returns MemoryQueryResult."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]
        mock_mv.find.return_value = {"hits": []}

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)
        result = store.query("test query")

        assert isinstance(result, store_module.MemoryQueryResult)
        assert result.query == "test query"
        assert result.mode == "keyword"
        assert result.total_count == 0

    def test_query_with_semantic_mode(self, tmp_path, mock_memvid_sdk):
        """Test query with semantic mode."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]
        mock_mv.find.return_value = {"hits": []}

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)
        result = store.query("test", mode="semantic")

        assert result.mode == "semantic"
        # Verify semantic mode was used
        call_kwargs = mock_mv.find.call_args.kwargs
        assert call_kwargs["mode"] == "sem"

    def test_query_with_frame_type_filter(self, tmp_path, mock_memvid_sdk):
        """Test query filters by frame_type."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]
        mock_mv.find.return_value = {
            "hits": [
                {
                    "id": "1",
                    "text": "Error message",
                    "label": "error",
                    "metadata": {"frame_id": "uuid-1", "frame_type": "error"},
                    "tags": ["error"],
                },
                {
                    "id": "2",
                    "text": "Learning note",
                    "label": "learning",
                    "metadata": {"frame_id": "uuid-2", "frame_type": "learning"},
                    "tags": ["learning"],
                },
            ]
        }

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)
        result = store.query("*", frame_type="error")

        assert len(result.frames) == 1
        assert result.frames[0].frame_type == "error"

    def test_query_with_date_filter(self, tmp_path, mock_memvid_sdk):
        """Test query filters by date range."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]
        mock_mv.find.return_value = {
            "hits": [
                {
                    "id": "1",
                    "text": "Old frame",
                    "label": "general",
                    "metadata": {
                        "frame_id": "uuid-1",
                        "frame_type": "general",
                        "timestamp": "2026-01-01T12:00:00+00:00",
                    },
                    "tags": ["general"],
                },
                {
                    "id": "2",
                    "text": "New frame",
                    "label": "general",
                    "metadata": {
                        "frame_id": "uuid-2",
                        "frame_type": "general",
                        "timestamp": "2026-01-11T12:00:00+00:00",
                    },
                    "tags": ["general"],
                },
            ]
        }

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)
        result = store.query("*", start_date="2026-01-10")

        assert len(result.frames) == 1
        assert result.frames[0].content == "New frame"

    def test_query_with_tag_filter(self, tmp_path, mock_memvid_sdk):
        """Test query filters by tags."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]
        mock_mv.find.return_value = {
            "hits": [
                {
                    "id": "1",
                    "text": "Important frame",
                    "label": "general",
                    "metadata": {"frame_id": "uuid-1", "frame_type": "general"},
                    "tags": ["general", "important"],
                },
                {
                    "id": "2",
                    "text": "Regular frame",
                    "label": "general",
                    "metadata": {"frame_id": "uuid-2", "frame_type": "general"},
                    "tags": ["general"],
                },
            ]
        }

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)
        result = store.query("*", tags=["important"])

        assert len(result.frames) == 1
        assert "important" in result.frames[0].tags

    def test_query_with_token_limit(self, tmp_path, mock_memvid_sdk):
        """Test query truncates to token budget."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]
        mock_mv.find.return_value = {
            "hits": [
                {
                    "id": "1",
                    "text": "a" * 100,  # ~25 tokens
                    "label": "general",
                    "metadata": {"frame_id": "uuid-1", "frame_type": "general"},
                    "tags": ["general"],
                },
                {
                    "id": "2",
                    "text": "b" * 100,  # ~25 tokens
                    "label": "general",
                    "metadata": {"frame_id": "uuid-2", "frame_type": "general"},
                    "tags": ["general"],
                },
            ]
        }

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)
        result = store.query("*", max_tokens=30)  # Only fits 1 frame

        assert len(result.frames) == 1
        assert result.truncated is True
        assert result.total_count == 2

    def test_query_includes_timing(self, tmp_path, mock_memvid_sdk):
        """Test query includes timing info."""
        store_path = tmp_path / "test.mv2"
        mock_mv = mock_memvid_sdk["mv"]
        mock_mv.find.return_value = {"hits": []}

        from importlib import reload
        import ralph_agi.memory.store as store_module
        reload(store_module)

        store_path.write_text("")
        store = store_module.MemoryStore(store_path)
        result = store.query("test")

        assert result.query_time_ms > 0

    def test_query_without_init_returns_empty_result(self, tmp_path):
        """Test query returns empty result if store not initialized."""
        # Use fresh import to avoid class identity issues after reloads
        from ralph_agi.memory.store import MemoryQueryResult as MQR, MemoryStore as MS

        store = MS(tmp_path / "nonexistent.mv2")
        result = store.query("anything")

        assert isinstance(result, MQR)
        assert result.frames == []
        assert result.total_count == 0


class TestMemoryStoreIntegration:
    """Integration tests (require memvid-sdk installed)."""

    @pytest.mark.skipif(
        True,  # Skip by default, enable when memvid-sdk is installed
        reason="Requires memvid-sdk to be installed",
    )
    def test_real_append_and_retrieve(self, tmp_path):
        """Test real append and retrieve operations."""
        store_path = tmp_path / "integration_test.mv2"

        with MemoryStore(store_path) as store:
            # Append some frames
            id1 = store.append(
                content="First iteration completed successfully",
                frame_type="iteration_result",
                metadata={"iteration": 1},
            )

            id2 = store.append(
                content="Learned: Use smaller context windows",
                frame_type="learning",
                tags=["optimization", "context"],
            )

            # Retrieve recent
            recent = store.get_recent(2)
            assert len(recent) == 2

            # Search
            results = store.search("context", limit=5)
            assert any("context" in r.content.lower() for r in results)


class TestDualWriteAndFallback:
    """Tests for JSONL dual-write and fallback functionality."""

    def test_append_creates_jsonl_backup(self, tmp_path):
        """Append should write to both Memvid and JSONL."""
        store_path = tmp_path / "test.mv2"
        jsonl_path = tmp_path / "test.jsonl"

        store = MemoryStore(store_path)

        # Mock Memvid to avoid dependency
        mock_mv = MagicMock()
        store._mv = mock_mv
        store._initialized = True

        store.append(
            content="Test content",
            frame_type="test",
            metadata={"key": "value"},
        )

        # Verify JSONL backup was created
        assert jsonl_path.exists()

        # Verify content in JSONL
        import json
        with open(jsonl_path) as f:
            data = json.loads(f.readline())
        assert data["content"] == "Test content"
        assert data["frame_type"] == "test"

    def test_jsonl_backup_path_matches_store_path(self, tmp_path):
        """JSONL backup path should be .mv2 path with .jsonl extension."""
        store_path = tmp_path / "memory.mv2"
        store = MemoryStore(store_path)

        expected_jsonl_path = tmp_path / "memory.jsonl"
        assert store._jsonl_backup.backup_path == expected_jsonl_path

    def test_get_recent_falls_back_to_jsonl(self, tmp_path):
        """get_recent should fall back to JSONL if Memvid unavailable."""
        store_path = tmp_path / "test.mv2"
        jsonl_path = tmp_path / "test.jsonl"

        # Pre-populate JSONL with data
        import json
        with open(jsonl_path, "w") as f:
            f.write(json.dumps({"id": "1", "content": "From JSONL", "frame_type": "test"}) + "\n")

        store = MemoryStore(store_path)
        # Don't initialize Memvid - simulate it being unavailable

        results = store.get_recent(5)

        assert len(results) == 1
        assert results[0].content == "From JSONL"

    def test_search_falls_back_to_jsonl(self, tmp_path):
        """search should fall back to JSONL if Memvid unavailable."""
        store_path = tmp_path / "test.mv2"
        jsonl_path = tmp_path / "test.jsonl"

        # Pre-populate JSONL with data
        import json
        with open(jsonl_path, "w") as f:
            f.write(json.dumps({"id": "1", "content": "Error in module", "frame_type": "error"}) + "\n")
            f.write(json.dumps({"id": "2", "content": "Success message", "frame_type": "result"}) + "\n")

        store = MemoryStore(store_path)
        # Don't initialize Memvid

        results = store.search("Error")

        assert len(results) == 1
        assert results[0].content == "Error in module"

    def test_query_result_includes_backend_memvid(self, tmp_path):
        """query should return backend='memvid' when Memvid succeeds."""
        store_path = tmp_path / "test.mv2"
        store = MemoryStore(store_path)

        # Mock Memvid
        mock_mv = MagicMock()
        mock_mv.find.return_value = {"hits": []}
        store._mv = mock_mv
        store._initialized = True

        result = store.query("test")

        assert result.backend == "memvid"

    def test_query_result_includes_backend_jsonl_fallback(self, tmp_path):
        """query should return backend='jsonl_fallback' when using JSONL."""
        store_path = tmp_path / "test.mv2"
        jsonl_path = tmp_path / "test.jsonl"

        # Create empty JSONL
        jsonl_path.touch()

        store = MemoryStore(store_path)
        # Don't initialize Memvid - simulate fallback

        result = store.query("test")

        assert result.backend == "jsonl_fallback"

    def test_dual_write_failure_does_not_fail_append(self, tmp_path):
        """JSONL write failure should not fail the main append."""
        store_path = tmp_path / "test.mv2"
        store = MemoryStore(store_path)

        # Mock Memvid
        mock_mv = MagicMock()
        store._mv = mock_mv
        store._initialized = True

        # Mock JSONL backup to fail
        store._jsonl_backup.append = MagicMock(return_value=False)

        # Should not raise
        frame_id = store.append(content="Test", frame_type="test")

        assert frame_id is not None
        mock_mv.put.assert_called_once()

    def test_fallback_with_frame_type_filter(self, tmp_path):
        """Fallback search should support frame_type filter."""
        store_path = tmp_path / "test.mv2"
        jsonl_path = tmp_path / "test.jsonl"

        import json
        with open(jsonl_path, "w") as f:
            f.write(json.dumps({"id": "1", "content": "Error A", "frame_type": "error"}) + "\n")
            f.write(json.dumps({"id": "2", "content": "Result B", "frame_type": "result"}) + "\n")
            f.write(json.dumps({"id": "3", "content": "Error C", "frame_type": "error"}) + "\n")

        store = MemoryStore(store_path)

        results = store.search("*", frame_type="error")

        assert len(results) == 2
        assert all(r.frame_type == "error" for r in results)
