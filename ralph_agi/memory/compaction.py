"""Context compaction for memory management.

This module provides automatic summarization and compaction of older
memory frames to prevent context window overflow during long-running tasks.

Design Principles:
- Preserve errors and decisions with full detail
- LLM-based summarization for quality summaries
- Idempotent compaction (safe to run multiple times)
- Archive original frames (never delete)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional, Protocol

if TYPE_CHECKING:
    from ralph_agi.memory.store import MemoryFrame, MemoryStore

logger = logging.getLogger(__name__)


class CompactionTier(Enum):
    """Compaction tiers based on age."""

    RECENT = "recent"  # Full detail
    MEDIUM = "medium"  # Summarized
    OLD = "old"  # Key points / archived


class ImportanceLevel(Enum):
    """Importance levels for frame preservation."""

    CRITICAL = 10  # Never compact (errors, decisions)
    HIGH = 8  # Minimal compaction
    MEDIUM = 5  # Normal compaction
    LOW = 3  # Aggressive compaction


# Frame types that should never be compacted
PRESERVE_TYPES = frozenset({
    "error",
    "decision",
    "git_commit",
})

# Frame types that can be safely compacted
COMPACTABLE_TYPES = frozenset({
    "iteration_result",
    "context",
    "summary",
    "success",
})


class Summarizer(Protocol):
    """Protocol for summarization functions."""

    def __call__(self, frames: list[MemoryFrame]) -> str:
        """Summarize a list of frames into a single summary string."""
        ...


@dataclass
class CompactionConfig:
    """Configuration for context compaction.

    Attributes:
        enabled: Whether compaction is enabled.
        threshold_frames: Number of frames before compaction triggers.
        recent_count: Number of recent frames to keep at full detail.
        medium_count: Number of frames to keep summarized.
        preserve_errors: Always keep error frames at full detail.
        preserve_decisions: Always keep decision frames at full detail.
        summary_model: LLM model to use for summarization.
        max_summary_tokens: Maximum tokens per summary.
    """

    enabled: bool = True
    threshold_frames: int = 50
    recent_count: int = 10
    medium_count: int = 20
    preserve_errors: bool = True
    preserve_decisions: bool = True
    summary_model: str = "haiku"
    max_summary_tokens: int = 500


@dataclass
class CompactionResult:
    """Result of a compaction operation.

    Attributes:
        frames_processed: Number of frames processed.
        frames_compacted: Number of frames that were compacted.
        frames_preserved: Number of frames preserved at full detail.
        summaries_created: Number of summary frames created.
        tokens_before: Estimated tokens before compaction.
        tokens_after: Estimated tokens after compaction.
        reduction_percentage: Token reduction percentage.
    """

    frames_processed: int = 0
    frames_compacted: int = 0
    frames_preserved: int = 0
    summaries_created: int = 0
    tokens_before: int = 0
    tokens_after: int = 0

    @property
    def reduction_percentage(self) -> float:
        """Calculate token reduction percentage."""
        if self.tokens_before == 0:
            return 0.0
        return ((self.tokens_before - self.tokens_after) / self.tokens_before) * 100


@dataclass
class FrameGroup:
    """A group of frames for compaction.

    Attributes:
        frames: Frames in this group.
        tier: Compaction tier for this group.
        start_index: Index of first frame in original list.
        end_index: Index of last frame in original list.
    """

    frames: list[MemoryFrame]
    tier: CompactionTier
    start_index: int
    end_index: int

    @property
    def token_count(self) -> int:
        """Estimate total tokens in this group."""
        return sum(f.estimate_tokens() for f in self.frames)


class ContextCompactor:
    """Context compaction for memory management.

    Provides automatic summarization of older frames to prevent
    context window overflow. Preserves critical information (errors,
    decisions) while compacting routine observations.

    Example:
        >>> compactor = ContextCompactor(memory_store, config)
        >>> result = compactor.compact()
        >>> print(f"Reduced tokens by {result.reduction_percentage:.1f}%")
    """

    def __init__(
        self,
        memory_store: MemoryStore,
        config: Optional[CompactionConfig] = None,
        summarizer: Optional[Summarizer] = None,
    ):
        """Initialize the compactor.

        Args:
            memory_store: The MemoryStore to compact.
            config: Compaction configuration.
            summarizer: Custom summarization function. If not provided,
                       a simple concatenation summarizer is used.
        """
        self._store = memory_store
        self.config = config or CompactionConfig()
        self._summarizer = summarizer or self._default_summarizer

    def _default_summarizer(self, frames: list[MemoryFrame]) -> str:
        """Default summarizer that creates a compact summary.

        This is a fallback when no LLM summarizer is available.
        Real deployments should use an LLM-based summarizer.
        The default summarizer prioritizes size reduction over quality.
        """
        if not frames:
            return ""

        # Count frame types
        type_counts: dict[str, int] = {}
        for frame in frames:
            type_counts[frame.frame_type] = type_counts.get(frame.frame_type, 0) + 1

        # Build compact summary
        parts = [f"Compacted {len(frames)} frames:"]

        # Add type breakdown
        type_summary = ", ".join(f"{t}={c}" for t, c in sorted(type_counts.items()))
        parts.append(f"Types: {type_summary}")

        # Sample only first 3 frames with truncated content
        sample_count = min(3, len(frames))
        for frame in frames[:sample_count]:
            content = frame.content[:50]
            if len(frame.content) > 50:
                content += "..."
            parts.append(f"- {content}")

        if len(frames) > sample_count:
            parts.append(f"- ...and {len(frames) - sample_count} more")

        return "\n".join(parts)

    def get_importance(self, frame: MemoryFrame) -> ImportanceLevel:
        """Get the importance level for a frame.

        Args:
            frame: The frame to evaluate.

        Returns:
            ImportanceLevel for the frame.
        """
        # Check preserved types
        if frame.frame_type in PRESERVE_TYPES:
            return ImportanceLevel.CRITICAL

        # Check metadata importance
        meta_importance = frame.metadata.get("importance", 0)
        if meta_importance >= 9:
            return ImportanceLevel.CRITICAL
        elif meta_importance >= 7:
            return ImportanceLevel.HIGH

        # Check frame type
        if frame.frame_type in ("learning", "preference"):
            return ImportanceLevel.HIGH
        elif frame.frame_type in ("success",):
            return ImportanceLevel.MEDIUM

        return ImportanceLevel.LOW

    def should_preserve(self, frame: MemoryFrame) -> bool:
        """Check if a frame should be preserved at full detail.

        Args:
            frame: The frame to check.

        Returns:
            True if the frame should not be compacted.
        """
        importance = self.get_importance(frame)
        if importance == ImportanceLevel.CRITICAL:
            return True

        # Check config settings
        if self.config.preserve_errors and frame.frame_type == "error":
            return True
        if self.config.preserve_decisions and frame.frame_type == "decision":
            return True

        # Check for compacted flag (already compacted)
        if frame.metadata.get("compacted"):
            return True

        return False

    def get_tier(self, index: int, total: int) -> CompactionTier:
        """Determine the compaction tier for a frame based on position.

        Args:
            index: Frame index (0 = oldest).
            total: Total number of frames.

        Returns:
            CompactionTier for the frame.
        """
        # Calculate boundaries (from end of list)
        recent_start = total - self.config.recent_count
        medium_start = total - self.config.recent_count - self.config.medium_count

        if index >= recent_start:
            return CompactionTier.RECENT
        elif index >= medium_start:
            return CompactionTier.MEDIUM
        else:
            return CompactionTier.OLD

    def group_frames(
        self,
        frames: list[MemoryFrame],
    ) -> list[FrameGroup]:
        """Group frames by compaction tier.

        Args:
            frames: List of frames to group (oldest first).

        Returns:
            List of FrameGroup objects.
        """
        if not frames:
            return []

        groups = []
        current_tier = None
        current_frames = []
        start_index = 0

        for i, frame in enumerate(frames):
            tier = self.get_tier(i, len(frames))

            if tier != current_tier:
                # Save previous group
                if current_frames:
                    groups.append(FrameGroup(
                        frames=current_frames,
                        tier=current_tier,
                        start_index=start_index,
                        end_index=i - 1,
                    ))

                # Start new group
                current_tier = tier
                current_frames = [frame]
                start_index = i
            else:
                current_frames.append(frame)

        # Save final group
        if current_frames:
            groups.append(FrameGroup(
                frames=current_frames,
                tier=current_tier,
                start_index=start_index,
                end_index=len(frames) - 1,
            ))

        return groups

    def compact_group(
        self,
        group: FrameGroup,
        session_id: Optional[str] = None,
    ) -> tuple[list[MemoryFrame], int]:
        """Compact a group of frames.

        Args:
            group: The FrameGroup to compact.
            session_id: Optional session ID for new frames.

        Returns:
            Tuple of (compacted frames, summaries created count).
        """
        if group.tier == CompactionTier.RECENT:
            # Keep all recent frames at full detail
            return group.frames, 0

        # Separate preserved and compactable frames
        preserved = []
        compactable = []

        for frame in group.frames:
            if self.should_preserve(frame):
                preserved.append(frame)
            else:
                compactable.append(frame)

        if not compactable:
            return group.frames, 0

        # Create summary for compactable frames
        summary_content = self._summarizer(compactable)

        # Create summary frame
        summary_frame = self._create_summary_frame(
            compactable,
            summary_content,
            group.tier,
            session_id,
        )

        # Return preserved frames + summary
        # Note: In a real implementation, we'd store the summary
        # and mark original frames as archived
        result = preserved + [summary_frame]
        return result, 1

    def _create_summary_frame(
        self,
        original_frames: list[MemoryFrame],
        summary_content: str,
        tier: CompactionTier,
        session_id: Optional[str] = None,
    ) -> MemoryFrame:
        """Create a summary frame for compacted frames.

        Args:
            original_frames: Frames being summarized.
            summary_content: The summary text.
            tier: Compaction tier.
            session_id: Optional session ID.

        Returns:
            New MemoryFrame containing the summary.
        """
        from ralph_agi.memory.store import MemoryFrame

        # Collect original frame IDs
        original_ids = [f.id for f in original_frames]

        # Calculate token savings
        original_tokens = sum(f.estimate_tokens() for f in original_frames)

        return MemoryFrame(
            id=f"summary-{original_ids[0][:8]}",
            content=summary_content,
            frame_type="summary",
            metadata={
                "compacted": True,
                "tier": tier.value,
                "original_ids": original_ids,
                "original_count": len(original_frames),
                "original_tokens": original_tokens,
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            tags=["summary", "compacted", tier.value],
        )

    def needs_compaction(self, session_id: Optional[str] = None) -> bool:
        """Check if compaction is needed.

        Args:
            session_id: Optional session to check.

        Returns:
            True if compaction should be run.
        """
        if not self.config.enabled:
            return False

        # Get frame count
        if session_id:
            frames = self._store.get_by_session(session_id, limit=1000)
        else:
            frames = self._store.get_recent(1000)

        return len(frames) >= self.config.threshold_frames

    def compact(
        self,
        session_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> CompactionResult:
        """Run context compaction.

        Args:
            session_id: Optional session to compact.
            dry_run: If True, don't actually modify anything.

        Returns:
            CompactionResult with metrics.
        """
        result = CompactionResult()

        if not self.config.enabled:
            logger.info("Compaction is disabled")
            return result

        # Get frames to process
        if session_id:
            frames = self._store.get_by_session(session_id, limit=1000)
        else:
            frames = self._store.get_recent(1000)

        if len(frames) < self.config.threshold_frames:
            logger.debug(
                f"Skipping compaction: {len(frames)} frames < "
                f"threshold {self.config.threshold_frames}"
            )
            return result

        # Sort oldest first
        frames = sorted(frames, key=lambda f: f.timestamp)

        result.frames_processed = len(frames)
        result.tokens_before = sum(f.estimate_tokens() for f in frames)

        # Group frames by tier
        groups = self.group_frames(frames)

        # Compact each group
        compacted_frames = []
        for group in groups:
            compacted, summaries = self.compact_group(group, session_id)
            compacted_frames.extend(compacted)
            result.summaries_created += summaries

        # Calculate results
        result.frames_compacted = result.frames_processed - len(compacted_frames)
        result.frames_preserved = len([f for f in compacted_frames if not f.metadata.get("compacted")])
        result.tokens_after = sum(f.estimate_tokens() for f in compacted_frames)

        if not dry_run:
            # In a real implementation, we would:
            # 1. Store summary frames
            # 2. Mark original frames as archived
            # For now, we just log the operation
            logger.info(
                f"Compaction complete: {result.frames_compacted} frames compacted, "
                f"{result.summaries_created} summaries created, "
                f"{result.reduction_percentage:.1f}% token reduction"
            )

        return result

    def estimate_compaction(
        self,
        session_id: Optional[str] = None,
    ) -> CompactionResult:
        """Estimate compaction results without executing.

        Args:
            session_id: Optional session to estimate.

        Returns:
            CompactionResult with estimated metrics.
        """
        return self.compact(session_id=session_id, dry_run=True)


def create_llm_summarizer(
    model: str = "haiku",
    max_tokens: int = 500,
) -> Summarizer:
    """Create an LLM-based summarizer function.

    This is a factory function that returns a summarizer
    using the specified LLM model.

    Args:
        model: LLM model to use.
        max_tokens: Maximum output tokens.

    Returns:
        Summarizer function.

    Note:
        This is a placeholder. Real implementation would
        call an LLM API (Anthropic, OpenAI, etc.)
    """

    def llm_summarizer(frames: list[MemoryFrame]) -> str:
        """Summarize frames using LLM."""
        if not frames:
            return ""

        # This would be replaced with actual LLM API call
        # For now, use a simple template-based summary
        frame_types = {}
        for frame in frames:
            frame_types[frame.frame_type] = frame_types.get(frame.frame_type, 0) + 1

        summary_parts = [
            f"Summary of {len(frames)} observations:",
            f"- Types: {frame_types}",
        ]

        # Add key content from each frame
        for frame in frames[:5]:  # First 5 frames
            summary_parts.append(f"- [{frame.frame_type}] {frame.content[:100]}...")

        if len(frames) > 5:
            summary_parts.append(f"- ... and {len(frames) - 5} more")

        return "\n".join(summary_parts)

    return llm_summarizer
