"""Long-term memory and persistent knowledge management.

This module provides structured observation types and knowledge queries
for persistent learning across sessions.

Design Principles:
- Typed observations for consistency
- Temporal queries for point-in-time knowledge
- Importance scoring for retention decisions
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ralph_agi.memory.store import MemoryFrame, MemoryQueryResult, MemoryStore

logger = logging.getLogger(__name__)


class ObservationType(Enum):
    """Types of observations that can be stored.

    Observations are categorized by type to enable structured queries
    and importance-based retention.
    """

    ERROR = "error"
    SUCCESS = "success"
    LEARNING = "learning"
    PREFERENCE = "preference"
    DECISION = "decision"
    CONTEXT = "context"
    SUMMARY = "summary"

    @property
    def importance(self) -> int:
        """Get the importance score for this type.

        Higher scores indicate more important observations
        that should be retained longer.

        Returns:
            Importance score (1-10).
        """
        scores = {
            ObservationType.ERROR: 10,  # Always keep errors
            ObservationType.DECISION: 9,  # Decisions are critical
            ObservationType.LEARNING: 8,  # Learnings inform future work
            ObservationType.PREFERENCE: 7,  # Preferences guide behavior
            ObservationType.SUCCESS: 5,  # Success is good but less critical
            ObservationType.SUMMARY: 4,  # Summaries are derived
            ObservationType.CONTEXT: 3,  # Context is transient
        }
        return scores.get(self, 5)


@dataclass(frozen=True)
class Observation:
    """A structured observation for long-term memory.

    Attributes:
        content: Main text content of the observation.
        observation_type: Type category (error, success, learning, etc.)
        source: Where this observation came from (task_id, file, etc.)
        confidence: Confidence level (0.0-1.0) in the observation.
        related_ids: IDs of related observations or tasks.
        tags: Additional tags for filtering.
        metadata: Additional structured data.
    """

    content: str
    observation_type: ObservationType
    source: Optional[str] = None
    confidence: float = 1.0
    related_ids: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def importance(self) -> int:
        """Get the importance score for this observation.

        Combines type importance with confidence.
        """
        base = self.observation_type.importance
        return int(base * self.confidence)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "content": self.content,
            "observation_type": self.observation_type.value,
            "source": self.source,
            "confidence": self.confidence,
            "related_ids": list(self.related_ids),
            "tags": list(self.tags),
            "importance": self.importance,
            **self.metadata,
        }


@dataclass(frozen=True)
class TemporalQuery:
    """Result of a temporal knowledge query.

    Attributes:
        query: The original query string.
        point_in_time: The datetime queried.
        observations: Observations known at that time.
        total_count: Total observations matching before time filter.
    """

    query: str
    point_in_time: datetime
    observations: tuple[MemoryFrame, ...]
    total_count: int


class KnowledgeStore:
    """Long-term knowledge management for persistent observations.

    Provides structured storage and retrieval of observations,
    with support for temporal queries and importance-based retention.

    Example:
        >>> ks = KnowledgeStore(memory_store)
        >>> ks.record_error(
        ...     "API timeout when calling external service",
        ...     source="task-123",
        ... )
        >>> ks.record_learning(
        ...     "Use exponential backoff for API retries",
        ...     confidence=0.9,
        ... )
        >>> errors = ks.get_errors(limit=10)
    """

    def __init__(self, memory_store: MemoryStore):
        """Initialize the knowledge store.

        Args:
            memory_store: The underlying MemoryStore for persistence.
        """
        self._store = memory_store

    def record(
        self,
        observation: Observation,
        session_id: Optional[str] = None,
    ) -> str:
        """Record an observation to long-term memory.

        Args:
            observation: The observation to record.
            session_id: Optional session identifier.

        Returns:
            The frame ID of the stored observation.
        """
        tags = [
            observation.observation_type.value,
            f"importance:{observation.importance}",
            *observation.tags,
        ]
        if observation.source:
            tags.append(f"source:{observation.source}")

        return self._store.append(
            content=observation.content,
            frame_type=observation.observation_type.value,
            metadata=observation.to_dict(),
            session_id=session_id,
            tags=list(tags),
        )

    def record_error(
        self,
        content: str,
        source: Optional[str] = None,
        confidence: float = 1.0,
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        **metadata: Any,
    ) -> str:
        """Record an error observation.

        Args:
            content: Error description.
            source: Error source (task, file, etc.)
            confidence: Confidence in the error assessment.
            tags: Additional tags.
            session_id: Optional session ID.
            **metadata: Additional metadata.

        Returns:
            Frame ID of the stored observation.
        """
        obs = Observation(
            content=content,
            observation_type=ObservationType.ERROR,
            source=source,
            confidence=confidence,
            tags=tuple(tags or []),
            metadata=metadata,
        )
        return self.record(obs, session_id)

    def record_success(
        self,
        content: str,
        source: Optional[str] = None,
        confidence: float = 1.0,
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        **metadata: Any,
    ) -> str:
        """Record a success observation.

        Args:
            content: Success description.
            source: Success source (task, file, etc.)
            confidence: Confidence level.
            tags: Additional tags.
            session_id: Optional session ID.
            **metadata: Additional metadata.

        Returns:
            Frame ID of the stored observation.
        """
        obs = Observation(
            content=content,
            observation_type=ObservationType.SUCCESS,
            source=source,
            confidence=confidence,
            tags=tuple(tags or []),
            metadata=metadata,
        )
        return self.record(obs, session_id)

    def record_learning(
        self,
        content: str,
        source: Optional[str] = None,
        confidence: float = 1.0,
        related_ids: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        **metadata: Any,
    ) -> str:
        """Record a learning observation.

        Args:
            content: What was learned.
            source: Learning source.
            confidence: Confidence in the learning.
            related_ids: Related observation/task IDs.
            tags: Additional tags.
            session_id: Optional session ID.
            **metadata: Additional metadata.

        Returns:
            Frame ID of the stored observation.
        """
        obs = Observation(
            content=content,
            observation_type=ObservationType.LEARNING,
            source=source,
            confidence=confidence,
            related_ids=tuple(related_ids or []),
            tags=tuple(tags or []),
            metadata=metadata,
        )
        return self.record(obs, session_id)

    def record_preference(
        self,
        content: str,
        source: Optional[str] = None,
        confidence: float = 1.0,
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        **metadata: Any,
    ) -> str:
        """Record a preference observation.

        Args:
            content: Preference description.
            source: Preference source.
            confidence: Confidence level.
            tags: Additional tags.
            session_id: Optional session ID.
            **metadata: Additional metadata.

        Returns:
            Frame ID of the stored observation.
        """
        obs = Observation(
            content=content,
            observation_type=ObservationType.PREFERENCE,
            source=source,
            confidence=confidence,
            tags=tuple(tags or []),
            metadata=metadata,
        )
        return self.record(obs, session_id)

    def record_decision(
        self,
        content: str,
        source: Optional[str] = None,
        confidence: float = 1.0,
        related_ids: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        **metadata: Any,
    ) -> str:
        """Record a decision observation.

        Args:
            content: Decision description and rationale.
            source: Decision source.
            confidence: Confidence in the decision.
            related_ids: Related observation/task IDs.
            tags: Additional tags.
            session_id: Optional session ID.
            **metadata: Additional metadata.

        Returns:
            Frame ID of the stored observation.
        """
        obs = Observation(
            content=content,
            observation_type=ObservationType.DECISION,
            source=source,
            confidence=confidence,
            related_ids=tuple(related_ids or []),
            tags=tuple(tags or []),
            metadata=metadata,
        )
        return self.record(obs, session_id)

    def get_by_type(
        self,
        observation_type: ObservationType,
        limit: int = 50,
    ) -> list[MemoryFrame]:
        """Get observations by type.

        Args:
            observation_type: Type to filter by.
            limit: Maximum results.

        Returns:
            List of matching MemoryFrame objects.
        """
        return self._store.get_by_type(observation_type.value, limit=limit)

    def get_errors(self, limit: int = 50) -> list[MemoryFrame]:
        """Get error observations."""
        return self.get_by_type(ObservationType.ERROR, limit)

    def get_learnings(self, limit: int = 50) -> list[MemoryFrame]:
        """Get learning observations."""
        return self.get_by_type(ObservationType.LEARNING, limit)

    def get_decisions(self, limit: int = 50) -> list[MemoryFrame]:
        """Get decision observations."""
        return self.get_by_type(ObservationType.DECISION, limit)

    def get_preferences(self, limit: int = 50) -> list[MemoryFrame]:
        """Get preference observations."""
        return self.get_by_type(ObservationType.PREFERENCE, limit)

    def query_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        observation_type: Optional[ObservationType] = None,
        limit: int = 100,
    ) -> MemoryQueryResult:
        """Query observations by date range.

        Args:
            start_date: Start date (ISO format).
            end_date: End date (ISO format).
            observation_type: Optional type filter.
            limit: Maximum results.

        Returns:
            MemoryQueryResult with matching observations.
        """
        return self._store.query(
            query="*",
            mode="keyword",
            limit=limit,
            frame_type=observation_type.value if observation_type else None,
            start_date=start_date,
            end_date=end_date,
        )

    def get_knowledge_at(
        self,
        point_in_time: datetime | str,
        query: str = "*",
        observation_types: Optional[list[ObservationType]] = None,
        limit: int = 50,
    ) -> TemporalQuery:
        """Get knowledge as it was at a specific point in time.

        This enables temporal queries like "what did I know about X
        before I made decision Y?"

        Args:
            point_in_time: The datetime to query at.
            query: Search query string.
            observation_types: Optional types to filter.
            limit: Maximum results.

        Returns:
            TemporalQuery with observations known at that time.
        """
        # Convert string to datetime if needed
        if isinstance(point_in_time, str):
            point_in_time = datetime.fromisoformat(point_in_time)

        # Ensure timezone aware
        if point_in_time.tzinfo is None:
            point_in_time = point_in_time.replace(tzinfo=timezone.utc)

        # Query with end_date filter
        end_date = point_in_time.isoformat()

        result = self._store.query(
            query=query,
            mode="hybrid",
            limit=limit * 2,  # Get extra to filter by type
            end_date=end_date,
        )

        # Filter by observation types if specified
        frames = result.frames
        if observation_types:
            type_values = {t.value for t in observation_types}
            frames = [f for f in frames if f.frame_type in type_values]

        # Limit results
        frames = frames[:limit]

        return TemporalQuery(
            query=query,
            point_in_time=point_in_time,
            observations=tuple(frames),
            total_count=result.total_count,
        )

    def get_related(
        self,
        observation_id: str,
        limit: int = 10,
    ) -> list[MemoryFrame]:
        """Get observations related to a given observation.

        Args:
            observation_id: ID of the observation to find related items for.
            limit: Maximum results.

        Returns:
            List of related observations.
        """
        # Search by the observation ID as a related_id tag
        return self._store.search(
            f"related:{observation_id}",
            limit=limit,
            mode="keyword",
        )

    def search_knowledge(
        self,
        query: str,
        observation_types: Optional[list[ObservationType]] = None,
        min_importance: Optional[int] = None,
        limit: int = 20,
    ) -> list[MemoryFrame]:
        """Search knowledge with filters.

        Args:
            query: Search query string.
            observation_types: Filter by types.
            min_importance: Minimum importance score.
            limit: Maximum results.

        Returns:
            List of matching observations.
        """
        # Use hybrid search for best results
        result = self._store.query(
            query=query,
            mode="hybrid",
            limit=limit * 3,  # Get extra for filtering
        )

        frames = result.frames

        # Filter by observation types
        if observation_types:
            type_values = {t.value for t in observation_types}
            frames = [f for f in frames if f.frame_type in type_values]

        # Filter by importance
        if min_importance is not None:
            frames = [
                f for f in frames
                if f.metadata.get("importance", 0) >= min_importance
            ]

        return frames[:limit]

    def get_high_importance(
        self,
        min_importance: int = 7,
        limit: int = 50,
    ) -> list[MemoryFrame]:
        """Get high-importance observations.

        Args:
            min_importance: Minimum importance threshold.
            limit: Maximum results.

        Returns:
            List of high-importance observations.
        """
        return self.search_knowledge(
            query="*",
            min_importance=min_importance,
            limit=limit,
        )

    def get_summary_stats(self) -> dict[str, int]:
        """Get summary statistics about stored knowledge.

        Returns:
            Dictionary with counts by observation type.
        """
        stats = {}
        for obs_type in ObservationType:
            frames = self.get_by_type(obs_type, limit=1000)
            stats[obs_type.value] = len(frames)

        stats["total"] = sum(stats.values())
        return stats
