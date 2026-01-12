"""Tests for long-term knowledge management.

Tests cover:
- Observation types: error, success, learning, preference
- Structured observation schema with metadata
- Query by observation type and date range
- Temporal queries (what did I know at time X?)
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from ralph_agi.memory.knowledge import (
    KnowledgeStore,
    Observation,
    ObservationType,
    TemporalQuery,
)


# Fixtures


@pytest.fixture
def mock_memory_store():
    """Create a mock MemoryStore."""
    store = MagicMock()
    store.append.return_value = "frame-123"
    store.search.return_value = []
    store.get_by_type.return_value = []
    store.query.return_value = MagicMock(frames=[], total_count=0)
    return store


@pytest.fixture
def knowledge_store(mock_memory_store):
    """Create a KnowledgeStore with mock backend."""
    return KnowledgeStore(mock_memory_store)


# ObservationType Tests


class TestObservationType:
    """Tests for ObservationType enum."""

    def test_observation_types_exist(self):
        """Test all expected observation types exist."""
        assert ObservationType.ERROR
        assert ObservationType.SUCCESS
        assert ObservationType.LEARNING
        assert ObservationType.PREFERENCE
        assert ObservationType.DECISION
        assert ObservationType.CONTEXT
        assert ObservationType.SUMMARY

    def test_observation_type_values(self):
        """Test observation type values are strings."""
        assert ObservationType.ERROR.value == "error"
        assert ObservationType.SUCCESS.value == "success"
        assert ObservationType.LEARNING.value == "learning"
        assert ObservationType.PREFERENCE.value == "preference"
        assert ObservationType.DECISION.value == "decision"

    def test_importance_scores(self):
        """Test importance scores are ranked correctly."""
        # Errors should be most important
        assert ObservationType.ERROR.importance >= 9
        # Decisions should be very important
        assert ObservationType.DECISION.importance >= 8
        # Learnings should be important
        assert ObservationType.LEARNING.importance >= 7
        # Context should be least important
        assert ObservationType.CONTEXT.importance <= 5

    def test_importance_ordering(self):
        """Test importance ordering is correct."""
        assert ObservationType.ERROR.importance >= ObservationType.DECISION.importance
        assert ObservationType.DECISION.importance >= ObservationType.LEARNING.importance
        assert ObservationType.LEARNING.importance >= ObservationType.PREFERENCE.importance
        assert ObservationType.PREFERENCE.importance >= ObservationType.SUCCESS.importance


# Observation Tests


class TestObservation:
    """Tests for Observation dataclass."""

    def test_observation_basic(self):
        """Test basic observation creation."""
        obs = Observation(
            content="Test error occurred",
            observation_type=ObservationType.ERROR,
        )

        assert obs.content == "Test error occurred"
        assert obs.observation_type == ObservationType.ERROR
        assert obs.source is None
        assert obs.confidence == 1.0

    def test_observation_full(self):
        """Test observation with all fields."""
        obs = Observation(
            content="Use exponential backoff",
            observation_type=ObservationType.LEARNING,
            source="task-123",
            confidence=0.9,
            related_ids=("obs-1", "obs-2"),
            tags=("api", "retry"),
            metadata={"category": "best-practice"},
        )

        assert obs.content == "Use exponential backoff"
        assert obs.observation_type == ObservationType.LEARNING
        assert obs.source == "task-123"
        assert obs.confidence == 0.9
        assert obs.related_ids == ("obs-1", "obs-2")
        assert obs.tags == ("api", "retry")
        assert obs.metadata == {"category": "best-practice"}

    def test_observation_importance(self):
        """Test observation importance calculation."""
        error_obs = Observation(
            content="Error",
            observation_type=ObservationType.ERROR,
            confidence=1.0,
        )
        assert error_obs.importance == 10

        # Lower confidence reduces importance
        low_conf_obs = Observation(
            content="Maybe error",
            observation_type=ObservationType.ERROR,
            confidence=0.5,
        )
        assert low_conf_obs.importance == 5

    def test_observation_to_dict(self):
        """Test observation to_dict conversion."""
        obs = Observation(
            content="Test content",
            observation_type=ObservationType.LEARNING,
            source="test",
            confidence=0.8,
        )

        d = obs.to_dict()

        assert d["content"] == "Test content"
        assert d["observation_type"] == "learning"
        assert d["source"] == "test"
        assert d["confidence"] == 0.8
        assert "importance" in d

    def test_observation_immutable(self):
        """Test Observation is immutable."""
        obs = Observation(
            content="Test",
            observation_type=ObservationType.ERROR,
        )

        with pytest.raises(AttributeError):
            obs.content = "Changed"


# KnowledgeStore Recording Tests


class TestKnowledgeStoreRecording:
    """Tests for recording observations."""

    def test_record_basic(self, knowledge_store, mock_memory_store):
        """Test basic observation recording."""
        obs = Observation(
            content="Test error",
            observation_type=ObservationType.ERROR,
        )

        frame_id = knowledge_store.record(obs)

        assert frame_id == "frame-123"
        mock_memory_store.append.assert_called_once()
        call_kwargs = mock_memory_store.append.call_args[1]
        assert call_kwargs["content"] == "Test error"
        assert call_kwargs["frame_type"] == "error"

    def test_record_with_session(self, knowledge_store, mock_memory_store):
        """Test recording with session ID."""
        obs = Observation(
            content="Test",
            observation_type=ObservationType.SUCCESS,
        )

        knowledge_store.record(obs, session_id="session-123")

        call_kwargs = mock_memory_store.append.call_args[1]
        assert call_kwargs["session_id"] == "session-123"

    def test_record_error(self, knowledge_store, mock_memory_store):
        """Test record_error convenience method."""
        frame_id = knowledge_store.record_error(
            "API timeout occurred",
            source="api-client",
            confidence=0.95,
        )

        assert frame_id == "frame-123"
        call_kwargs = mock_memory_store.append.call_args[1]
        assert call_kwargs["frame_type"] == "error"
        assert "API timeout occurred" in call_kwargs["content"]

    def test_record_success(self, knowledge_store, mock_memory_store):
        """Test record_success convenience method."""
        frame_id = knowledge_store.record_success(
            "Task completed successfully",
            source="task-456",
        )

        assert frame_id == "frame-123"
        call_kwargs = mock_memory_store.append.call_args[1]
        assert call_kwargs["frame_type"] == "success"

    def test_record_learning(self, knowledge_store, mock_memory_store):
        """Test record_learning convenience method."""
        frame_id = knowledge_store.record_learning(
            "Always validate input before processing",
            related_ids=["error-001", "error-002"],
            tags=["validation", "input"],
        )

        assert frame_id == "frame-123"
        call_kwargs = mock_memory_store.append.call_args[1]
        assert call_kwargs["frame_type"] == "learning"

    def test_record_preference(self, knowledge_store, mock_memory_store):
        """Test record_preference convenience method."""
        frame_id = knowledge_store.record_preference(
            "Prefer async/await over callbacks",
            confidence=0.8,
        )

        assert frame_id == "frame-123"
        call_kwargs = mock_memory_store.append.call_args[1]
        assert call_kwargs["frame_type"] == "preference"

    def test_record_decision(self, knowledge_store, mock_memory_store):
        """Test record_decision convenience method."""
        frame_id = knowledge_store.record_decision(
            "Chose PostgreSQL over MongoDB for ACID compliance",
            related_ids=["research-001"],
        )

        assert frame_id == "frame-123"
        call_kwargs = mock_memory_store.append.call_args[1]
        assert call_kwargs["frame_type"] == "decision"

    def test_record_with_metadata(self, knowledge_store, mock_memory_store):
        """Test recording with custom metadata."""
        knowledge_store.record_error(
            "Database connection failed",
            error_code=500,
            retry_count=3,
        )

        call_kwargs = mock_memory_store.append.call_args[1]
        metadata = call_kwargs["metadata"]
        assert metadata["error_code"] == 500
        assert metadata["retry_count"] == 3


# KnowledgeStore Query Tests


class TestKnowledgeStoreQueries:
    """Tests for querying observations."""

    def test_get_by_type(self, knowledge_store, mock_memory_store):
        """Test get_by_type method."""
        mock_frame = MagicMock()
        mock_memory_store.get_by_type.return_value = [mock_frame]

        frames = knowledge_store.get_by_type(ObservationType.ERROR)

        assert len(frames) == 1
        mock_memory_store.get_by_type.assert_called_once_with("error", limit=50)

    def test_get_errors(self, knowledge_store, mock_memory_store):
        """Test get_errors convenience method."""
        knowledge_store.get_errors(limit=10)

        mock_memory_store.get_by_type.assert_called_once_with("error", limit=10)

    def test_get_learnings(self, knowledge_store, mock_memory_store):
        """Test get_learnings convenience method."""
        knowledge_store.get_learnings(limit=25)

        mock_memory_store.get_by_type.assert_called_once_with("learning", limit=25)

    def test_get_decisions(self, knowledge_store, mock_memory_store):
        """Test get_decisions convenience method."""
        knowledge_store.get_decisions()

        mock_memory_store.get_by_type.assert_called_once_with("decision", limit=50)

    def test_get_preferences(self, knowledge_store, mock_memory_store):
        """Test get_preferences convenience method."""
        knowledge_store.get_preferences()

        mock_memory_store.get_by_type.assert_called_once_with("preference", limit=50)


# Date Range Query Tests


class TestKnowledgeStoreDateRangeQueries:
    """Tests for date range queries."""

    def test_query_by_date_range(self, knowledge_store, mock_memory_store):
        """Test query_by_date_range method."""
        knowledge_store.query_by_date_range(
            start_date="2026-01-01",
            end_date="2026-01-31",
        )

        mock_memory_store.query.assert_called_once()
        call_kwargs = mock_memory_store.query.call_args[1]
        assert call_kwargs["start_date"] == "2026-01-01"
        assert call_kwargs["end_date"] == "2026-01-31"

    def test_query_by_date_range_with_type(self, knowledge_store, mock_memory_store):
        """Test query_by_date_range with type filter."""
        knowledge_store.query_by_date_range(
            start_date="2026-01-01",
            observation_type=ObservationType.ERROR,
        )

        call_kwargs = mock_memory_store.query.call_args[1]
        assert call_kwargs["frame_type"] == "error"

    def test_query_by_date_range_start_only(self, knowledge_store, mock_memory_store):
        """Test query_by_date_range with only start date."""
        knowledge_store.query_by_date_range(start_date="2026-01-01")

        call_kwargs = mock_memory_store.query.call_args[1]
        assert call_kwargs["start_date"] == "2026-01-01"
        assert call_kwargs["end_date"] is None


# Temporal Query Tests


class TestKnowledgeStoreTemporalQueries:
    """Tests for temporal (point-in-time) queries."""

    def test_get_knowledge_at_datetime(self, knowledge_store, mock_memory_store):
        """Test get_knowledge_at with datetime object."""
        point_in_time = datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc)

        result = knowledge_store.get_knowledge_at(point_in_time)

        assert isinstance(result, TemporalQuery)
        assert result.point_in_time == point_in_time

        call_kwargs = mock_memory_store.query.call_args[1]
        assert call_kwargs["end_date"] == point_in_time.isoformat()

    def test_get_knowledge_at_string(self, knowledge_store, mock_memory_store):
        """Test get_knowledge_at with ISO string."""
        result = knowledge_store.get_knowledge_at("2026-01-10T12:00:00+00:00")

        assert isinstance(result, TemporalQuery)
        mock_memory_store.query.assert_called_once()

    def test_get_knowledge_at_with_query(self, knowledge_store, mock_memory_store):
        """Test get_knowledge_at with search query."""
        point_in_time = datetime.now(timezone.utc)

        knowledge_store.get_knowledge_at(
            point_in_time,
            query="API timeout",
        )

        call_kwargs = mock_memory_store.query.call_args[1]
        assert call_kwargs["query"] == "API timeout"

    def test_get_knowledge_at_with_types(self, knowledge_store, mock_memory_store):
        """Test get_knowledge_at filters by observation types."""
        mock_frame1 = MagicMock()
        mock_frame1.frame_type = "error"
        mock_frame2 = MagicMock()
        mock_frame2.frame_type = "success"

        mock_memory_store.query.return_value = MagicMock(
            frames=[mock_frame1, mock_frame2],
            total_count=2,
        )

        result = knowledge_store.get_knowledge_at(
            datetime.now(timezone.utc),
            observation_types=[ObservationType.ERROR],
        )

        assert len(result.observations) == 1
        assert result.observations[0].frame_type == "error"

    def test_get_knowledge_at_naive_datetime(self, knowledge_store, mock_memory_store):
        """Test get_knowledge_at with naive datetime adds UTC."""
        naive_dt = datetime(2026, 1, 10, 12, 0, 0)

        result = knowledge_store.get_knowledge_at(naive_dt)

        # Should have added UTC timezone
        assert result.point_in_time.tzinfo == timezone.utc


# Search Tests


class TestKnowledgeStoreSearch:
    """Tests for knowledge search."""

    def test_search_knowledge_basic(self, knowledge_store, mock_memory_store):
        """Test basic knowledge search."""
        mock_memory_store.query.return_value = MagicMock(frames=[])

        knowledge_store.search_knowledge("API timeout")

        mock_memory_store.query.assert_called_once()
        call_kwargs = mock_memory_store.query.call_args[1]
        assert call_kwargs["query"] == "API timeout"
        assert call_kwargs["mode"] == "hybrid"

    def test_search_knowledge_with_types(self, knowledge_store, mock_memory_store):
        """Test search_knowledge filters by types."""
        mock_frame1 = MagicMock()
        mock_frame1.frame_type = "error"
        mock_frame2 = MagicMock()
        mock_frame2.frame_type = "learning"

        mock_memory_store.query.return_value = MagicMock(
            frames=[mock_frame1, mock_frame2],
            total_count=2,
        )

        results = knowledge_store.search_knowledge(
            "API",
            observation_types=[ObservationType.LEARNING],
        )

        assert len(results) == 1
        assert results[0].frame_type == "learning"

    def test_search_knowledge_with_min_importance(self, knowledge_store, mock_memory_store):
        """Test search_knowledge filters by importance."""
        mock_frame1 = MagicMock()
        mock_frame1.frame_type = "error"
        mock_frame1.metadata = {"importance": 10}
        mock_frame2 = MagicMock()
        mock_frame2.frame_type = "context"
        mock_frame2.metadata = {"importance": 3}

        mock_memory_store.query.return_value = MagicMock(
            frames=[mock_frame1, mock_frame2],
            total_count=2,
        )

        results = knowledge_store.search_knowledge(
            "test",
            min_importance=7,
        )

        assert len(results) == 1
        assert results[0].metadata["importance"] == 10

    def test_get_high_importance(self, knowledge_store, mock_memory_store):
        """Test get_high_importance method."""
        mock_frame = MagicMock()
        mock_frame.frame_type = "error"
        mock_frame.metadata = {"importance": 10}

        mock_memory_store.query.return_value = MagicMock(
            frames=[mock_frame],
            total_count=1,
        )

        results = knowledge_store.get_high_importance(min_importance=8)

        assert len(results) == 1


# Related Observations Tests


class TestKnowledgeStoreRelated:
    """Tests for related observation queries."""

    def test_get_related(self, knowledge_store, mock_memory_store):
        """Test get_related method."""
        knowledge_store.get_related("obs-123")

        mock_memory_store.search.assert_called_once()
        call_args = mock_memory_store.search.call_args
        assert "related:obs-123" in call_args[0][0]


# Statistics Tests


class TestKnowledgeStoreStats:
    """Tests for knowledge statistics."""

    def test_get_summary_stats(self, knowledge_store, mock_memory_store):
        """Test get_summary_stats method."""
        # Mock different counts for different types
        def mock_get_by_type(type_str, limit):
            if type_str == "error":
                return [MagicMock()] * 5
            elif type_str == "learning":
                return [MagicMock()] * 10
            return []

        mock_memory_store.get_by_type.side_effect = mock_get_by_type

        stats = knowledge_store.get_summary_stats()

        assert stats["error"] == 5
        assert stats["learning"] == 10
        assert stats["total"] >= 15


# TemporalQuery Tests


class TestTemporalQuery:
    """Tests for TemporalQuery dataclass."""

    def test_temporal_query_attributes(self):
        """Test TemporalQuery stores attributes."""
        point_in_time = datetime.now(timezone.utc)
        mock_frame = MagicMock()

        tq = TemporalQuery(
            query="test query",
            point_in_time=point_in_time,
            observations=(mock_frame,),
            total_count=5,
        )

        assert tq.query == "test query"
        assert tq.point_in_time == point_in_time
        assert len(tq.observations) == 1
        assert tq.total_count == 5

    def test_temporal_query_immutable(self):
        """Test TemporalQuery is immutable."""
        tq = TemporalQuery(
            query="test",
            point_in_time=datetime.now(timezone.utc),
            observations=(),
            total_count=0,
        )

        with pytest.raises(AttributeError):
            tq.query = "changed"
