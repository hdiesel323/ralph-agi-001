"""Memory store implementation using Memvid.

This module provides the MemoryStore class that wraps Memvid's API
for RALPH-AGI's persistent memory needs.

Design Principles:
- Lazy initialization (create on first use)
- Crash-safe (Memvid's append-only design)
- Simple API for common operations
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class MemoryFrame:
    """A single frame of memory.

    Attributes:
        id: Unique identifier for this frame.
        content: The main text content of the frame.
        frame_type: Category of memory (iteration_result, error, learning, etc.)
        metadata: Additional structured data.
        timestamp: When this frame was created (ISO format).
        session_id: Optional session identifier for grouping.
        tags: Optional list of tags for filtering.
        score: Optional relevance score (0.0-1.0) from search results.
    """

    id: str
    content: str
    frame_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    session_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    score: Optional[float] = None

    def estimate_tokens(self) -> int:
        """Estimate token count for this frame.

        Uses simple heuristic: ~4 characters per token for English text.
        """
        return len(self.content) // 4 + 1


@dataclass
class MemoryQueryResult:
    """Result of a memory query operation.

    Attributes:
        frames: List of matching MemoryFrame objects.
        query: The original query string.
        mode: Search mode used (keyword, semantic, hybrid).
        total_count: Total matches before limit/truncation.
        truncated: Whether results were truncated for token budget.
        query_time_ms: Query execution time in milliseconds.
        token_count: Estimated total tokens in returned frames.
    """

    frames: list[MemoryFrame]
    query: str
    mode: str
    total_count: int
    truncated: bool = False
    query_time_ms: float = 0.0
    token_count: int = 0


class MemoryStoreError(Exception):
    """Base exception for memory store errors."""

    pass


class MemoryStore:
    """Persistent memory store using Memvid.

    Provides a simple interface for storing and retrieving memory frames.
    The store is lazily initialized - the Memvid file is only created
    when the first write operation occurs.

    Attributes:
        store_path: Path to the .mv2 file.
        initialized: Whether the store has been initialized.

    Example:
        >>> store = MemoryStore("ralph_memory.mv2")
        >>> frame_id = store.append(
        ...     content="Task completed successfully",
        ...     frame_type="iteration_result",
        ...     metadata={"iteration": 5}
        ... )
        >>> recent = store.get_recent(10)
    """

    def __init__(self, store_path: str | Path = "ralph_memory.mv2"):
        """Initialize the memory store.

        Args:
            store_path: Path to the Memvid .mv2 file. Will be created
                       on first write if it doesn't exist.
        """
        self.store_path = Path(store_path)
        self._mv = None
        self._initialized = False

    @property
    def initialized(self) -> bool:
        """Whether the store has been initialized."""
        return self._initialized

    def _ensure_initialized(self, create: bool = True) -> bool:
        """Ensure the Memvid store is initialized.

        Args:
            create: If True, create the store if it doesn't exist.

        Returns:
            True if initialized successfully, False otherwise.
        """
        if self._initialized:
            return True

        try:
            # Import here to allow graceful fallback if memvid not installed
            from memvid_sdk import create as mv_create, use

            if self.store_path.exists():
                self._mv = use("basic", str(self.store_path), mode="open")
                logger.info(f"Opened existing memory store at {self.store_path}")
            elif create:
                # Ensure parent directory exists
                self.store_path.parent.mkdir(parents=True, exist_ok=True)
                self._mv = mv_create(str(self.store_path))
                logger.info(f"Created new memory store at {self.store_path}")
            else:
                return False

            self._initialized = True
            return True

        except ImportError:
            logger.warning(
                "memvid-sdk not installed. Memory features will be disabled. "
                "Install with: pip install memvid-sdk"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to initialize memory store: {e}")
            raise MemoryStoreError(f"Failed to initialize memory store: {e}") from e

    def append(
        self,
        content: str,
        frame_type: str = "general",
        metadata: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> str:
        """Append a new frame to the memory store.

        Args:
            content: The main text content to store.
            frame_type: Category of this memory (e.g., "iteration_result",
                       "error", "learning", "decision").
            metadata: Additional structured data to store with the frame.
            session_id: Optional session identifier for grouping related frames.
            tags: Optional list of tags for filtering.

        Returns:
            The unique ID of the created frame.

        Raises:
            MemoryStoreError: If the store cannot be initialized or write fails.
        """
        if not self._ensure_initialized(create=True):
            raise MemoryStoreError("Memory store not available")

        frame_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        # Build metadata
        full_metadata = {
            "frame_id": frame_id,
            "frame_type": frame_type,
            "timestamp": timestamp,
            **(metadata or {}),
        }
        if session_id:
            full_metadata["session_id"] = session_id

        # Build tags
        all_tags = [frame_type]
        if tags:
            all_tags.extend(tags)
        if session_id:
            all_tags.append(f"session:{session_id}")

        try:
            self._mv.put(
                title=f"{frame_type}:{frame_id[:8]}",
                label=frame_type,
                text=content,
                metadata=full_metadata,
                tags=all_tags,
            )
            logger.debug(f"Appended frame {frame_id[:8]} of type {frame_type}")
            return frame_id

        except Exception as e:
            raise MemoryStoreError(f"Failed to append frame: {e}") from e

    def get_recent(self, n: int = 10) -> list[MemoryFrame]:
        """Get the most recent N frames.

        Args:
            n: Maximum number of frames to return.

        Returns:
            List of MemoryFrame objects, most recent first.
        """
        if not self._ensure_initialized(create=False):
            return []

        try:
            # Search for all, sorted by recency
            # Using empty query to match all, then limiting
            results = self._mv.find("*", k=n)
            return self._convert_results(results)
        except Exception as e:
            logger.error(f"Failed to get recent frames: {e}")
            return []

    def search(
        self,
        query: str,
        frame_type: Optional[str] = None,
        limit: int = 10,
        mode: str = "keyword",
    ) -> list[MemoryFrame]:
        """Search memory frames.

        Args:
            query: Search query string.
            frame_type: Optional filter by frame type.
            limit: Maximum number of results.
            mode: Search mode - "keyword" (BM25) or "semantic".

        Returns:
            List of matching MemoryFrame objects, ranked by relevance.
        """
        if not self._ensure_initialized(create=False):
            return []

        try:
            search_mode = "sem" if mode == "semantic" else None
            results = self._mv.find(query, k=limit, mode=search_mode)

            frames = self._convert_results(results)

            # Filter by type if specified
            if frame_type:
                frames = [f for f in frames if f.frame_type == frame_type]

            return frames

        except Exception as e:
            logger.error(f"Failed to search memory: {e}")
            return []

    def get_by_type(self, frame_type: str, limit: int = 50) -> list[MemoryFrame]:
        """Get frames of a specific type.

        Args:
            frame_type: The type of frames to retrieve.
            limit: Maximum number of results.

        Returns:
            List of matching MemoryFrame objects.
        """
        return self.search(frame_type, frame_type=frame_type, limit=limit)

    def get_by_session(self, session_id: str, limit: int = 100) -> list[MemoryFrame]:
        """Get all frames from a specific session.

        Args:
            session_id: The session identifier.
            limit: Maximum number of results.

        Returns:
            List of MemoryFrame objects from the session.
        """
        if not self._ensure_initialized(create=False):
            return []

        try:
            # Search by session tag
            results = self._mv.find(f"session:{session_id}", k=limit)
            return self._convert_results(results)
        except Exception as e:
            logger.error(f"Failed to get session frames: {e}")
            return []

    def search_similar(self, query: str, limit: int = 10) -> list[MemoryFrame]:
        """Search for semantically similar frames.

        Convenience method for semantic search over memory frames.
        Uses embedding-based similarity to find relevant past observations.

        Args:
            query: Natural language query describing what to find.
            limit: Maximum number of results to return.

        Returns:
            List of MemoryFrame objects ranked by semantic similarity,
            with scores in the score field.

        Example:
            >>> results = store.search_similar("error handling patterns", limit=5)
            >>> for frame in results:
            ...     print(f"{frame.content} (score: {frame.score:.3f})")
        """
        return self.search(query, limit=limit, mode="semantic")

    def search_hybrid(
        self,
        query: str,
        limit: int = 10,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> list[MemoryFrame]:
        """Search using both semantic and keyword matching.

        Combines semantic (embedding-based) and keyword (BM25) search
        results for improved recall and precision.

        Args:
            query: Search query string.
            limit: Maximum number of results to return.
            semantic_weight: Weight for semantic search scores (0.0-1.0).
            keyword_weight: Weight for keyword search scores (0.0-1.0).

        Returns:
            List of MemoryFrame objects ranked by combined score,
            with the weighted score in the score field.

        Example:
            >>> results = store.search_hybrid(
            ...     query="error handling",
            ...     limit=10,
            ...     semantic_weight=0.7,
            ...     keyword_weight=0.3,
            ... )
        """
        if not self._ensure_initialized(create=False):
            return []

        # Normalize weights
        total_weight = semantic_weight + keyword_weight
        if total_weight == 0:
            return []
        sem_w = semantic_weight / total_weight
        kw_w = keyword_weight / total_weight

        try:
            # Run both searches
            # Request more results to account for deduplication
            fetch_limit = min(limit * 2, 100)

            semantic_results = self.search(query, limit=fetch_limit, mode="semantic")
            keyword_results = self.search(query, limit=fetch_limit, mode="keyword")

            # Build score map by frame ID
            scores: dict[str, dict] = {}

            for frame in semantic_results:
                scores[frame.id] = {
                    "frame": frame,
                    "sem_score": frame.score or 0.0,
                    "kw_score": 0.0,
                }

            for frame in keyword_results:
                if frame.id in scores:
                    scores[frame.id]["kw_score"] = frame.score or 0.0
                else:
                    scores[frame.id] = {
                        "frame": frame,
                        "sem_score": 0.0,
                        "kw_score": frame.score or 0.0,
                    }

            # Calculate combined scores
            combined: list[tuple[float, MemoryFrame]] = []
            for frame_id, data in scores.items():
                combined_score = (data["sem_score"] * sem_w) + (data["kw_score"] * kw_w)
                frame = data["frame"]
                frame.score = combined_score
                combined.append((combined_score, frame))

            # Sort by combined score (descending) and return top N
            combined.sort(key=lambda x: x[0], reverse=True)
            return [frame for _, frame in combined[:limit]]

        except Exception as e:
            logger.error(f"Failed to perform hybrid search: {e}")
            return []

    def query(
        self,
        query: str = "*",
        mode: Literal["keyword", "semantic", "hybrid"] = "keyword",
        limit: int = 10,
        frame_type: Optional[str] = None,
        session_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        tags: Optional[list[str]] = None,
        match_all_tags: bool = False,
        max_tokens: Optional[int] = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> MemoryQueryResult:
        """Unified query API for memory searches.

        Single entry point for all memory queries with full filtering support.

        Args:
            query: Search query string. Use "*" for all frames.
            mode: Search mode - "keyword" (BM25), "semantic", or "hybrid".
            limit: Maximum number of results to return.
            frame_type: Filter by frame type (e.g., "error", "learning").
            session_id: Filter by session identifier.
            start_date: Filter frames created on or after this date (ISO format).
            end_date: Filter frames created on or before this date (ISO format).
            tags: Filter by tags. Frames must have at least one matching tag
                  (or all if match_all_tags=True).
            match_all_tags: If True, frames must have ALL specified tags.
            max_tokens: Maximum total tokens in returned frames. Results
                       will be truncated to fit within this budget.
            semantic_weight: Weight for semantic scores in hybrid mode.
            keyword_weight: Weight for keyword scores in hybrid mode.

        Returns:
            MemoryQueryResult with matching frames and query metadata.

        Example:
            >>> result = store.query(
            ...     query="error handling",
            ...     mode="hybrid",
            ...     limit=10,
            ...     frame_type="error",
            ...     start_date="2026-01-10",
            ...     max_tokens=4000,
            ... )
            >>> print(f"Found {result.total_count} matches")
            >>> for frame in result.frames:
            ...     print(frame.content)
        """
        start_time = time.time()

        if not self._ensure_initialized(create=False):
            return MemoryQueryResult(
                frames=[],
                query=query,
                mode=mode,
                total_count=0,
            )

        try:
            # Execute search based on mode
            # Request extra results to account for filtering
            fetch_limit = min(limit * 3, 200)

            if mode == "hybrid":
                frames = self.search_hybrid(
                    query,
                    limit=fetch_limit,
                    semantic_weight=semantic_weight,
                    keyword_weight=keyword_weight,
                )
            elif mode == "semantic":
                frames = self.search(query, limit=fetch_limit, mode="semantic")
            else:
                frames = self.search(query, limit=fetch_limit, mode="keyword")

            # Apply filters
            frames = self._apply_filters(
                frames,
                frame_type=frame_type,
                session_id=session_id,
                start_date=start_date,
                end_date=end_date,
                tags=tags,
                match_all_tags=match_all_tags,
            )

            total_count = len(frames)

            # Apply limit
            frames = frames[:limit]

            # Apply token budget
            truncated = False
            if max_tokens is not None:
                frames, truncated = self._truncate_to_tokens(frames, max_tokens)

            # Calculate token count
            token_count = sum(f.estimate_tokens() for f in frames)

            query_time_ms = (time.time() - start_time) * 1000

            return MemoryQueryResult(
                frames=frames,
                query=query,
                mode=mode,
                total_count=total_count,
                truncated=truncated,
                query_time_ms=query_time_ms,
                token_count=token_count,
            )

        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return MemoryQueryResult(
                frames=[],
                query=query,
                mode=mode,
                total_count=0,
            )

    def _apply_filters(
        self,
        frames: list[MemoryFrame],
        frame_type: Optional[str] = None,
        session_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        tags: Optional[list[str]] = None,
        match_all_tags: bool = False,
    ) -> list[MemoryFrame]:
        """Apply filters to a list of frames."""
        result = frames

        if frame_type:
            result = [f for f in result if f.frame_type == frame_type]

        if session_id:
            result = [f for f in result if f.session_id == session_id]

        if start_date:
            result = [f for f in result if f.timestamp >= start_date]

        if end_date:
            # Add time to end_date to include the whole day
            end_with_time = end_date if "T" in end_date else f"{end_date}T23:59:59"
            result = [f for f in result if f.timestamp <= end_with_time]

        if tags:
            if match_all_tags:
                result = [f for f in result if all(t in f.tags for t in tags)]
            else:
                result = [f for f in result if any(t in f.tags for t in tags)]

        return result

    def _truncate_to_tokens(
        self, frames: list[MemoryFrame], max_tokens: int
    ) -> tuple[list[MemoryFrame], bool]:
        """Truncate frames to fit within token budget.

        Returns:
            Tuple of (truncated_frames, was_truncated).
        """
        result = []
        total_tokens = 0
        truncated = False

        for frame in frames:
            frame_tokens = frame.estimate_tokens()
            if total_tokens + frame_tokens <= max_tokens:
                result.append(frame)
                total_tokens += frame_tokens
            else:
                truncated = True
                break

        return result, truncated

    def _convert_results(self, results: dict) -> list[MemoryFrame]:
        """Convert Memvid search results to MemoryFrame objects."""
        frames = []
        for hit in results.get("hits", []):
            metadata = hit.get("metadata", {})
            # Extract score if present (Memvid returns score for ranked results)
            score = hit.get("score")
            if score is not None:
                # Normalize score to 0.0-1.0 range if needed
                score = float(score)
            frames.append(
                MemoryFrame(
                    id=metadata.get("frame_id", hit.get("id", "")),
                    content=hit.get("text", hit.get("snippet", "")),
                    frame_type=metadata.get("frame_type", hit.get("label", "unknown")),
                    metadata=metadata,
                    timestamp=metadata.get("timestamp", ""),
                    session_id=metadata.get("session_id"),
                    tags=hit.get("tags", []),
                    score=score,
                )
            )
        return frames

    def close(self) -> None:
        """Close the memory store and release resources.

        Should be called when done using the store to ensure
        all data is properly flushed.
        """
        if self._mv is not None:
            try:
                self._mv.seal()
                logger.info(f"Closed memory store at {self.store_path}")
            except Exception as e:
                logger.error(f"Error closing memory store: {e}")
            finally:
                self._mv = None
                self._initialized = False

    def __enter__(self) -> MemoryStore:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensures store is closed."""
        self.close()

    def __del__(self):
        """Destructor - attempt to close store if not already closed."""
        if self._initialized:
            try:
                self.close()
            except Exception:
                pass  # Best effort cleanup
