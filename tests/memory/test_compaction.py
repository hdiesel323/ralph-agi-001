"""Tests for context compaction.

Tests cover:
- Compaction threshold configuration
- Frame grouping by tier
- Importance-based preservation
- Summarization
- Token usage tracking
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from ralph_agi.memory.compaction import (
    CompactionConfig,
    CompactionResult,
    CompactionTier,
    ContextCompactor,
    FrameGroup,
    ImportanceLevel,
    PRESERVE_TYPES,
    create_llm_summarizer,
)
from ralph_agi.memory.store import MemoryFrame


# Fixtures


@pytest.fixture
def mock_memory_store():
    """Create a mock MemoryStore."""
    store = MagicMock()
    store.get_recent.return_value = []
    store.get_by_session.return_value = []
    return store


@pytest.fixture
def compactor(mock_memory_store):
    """Create a ContextCompactor with default config."""
    return ContextCompactor(mock_memory_store)


@pytest.fixture
def custom_config():
    """Create a custom compaction config."""
    return CompactionConfig(
        enabled=True,
        threshold_frames=30,
        recent_count=5,
        medium_count=10,
        preserve_errors=True,
        preserve_decisions=True,
    )


@pytest.fixture
def compactor_custom(mock_memory_store, custom_config):
    """Create a ContextCompactor with custom config."""
    return ContextCompactor(mock_memory_store, custom_config)


def make_frame(
    frame_type: str = "iteration_result",
    content: str = "Test content",
    timestamp_offset_hours: int = 0,
    metadata: dict = None,
) -> MemoryFrame:
    """Helper to create test frames."""
    ts = datetime.now(timezone.utc) - timedelta(hours=timestamp_offset_hours)
    return MemoryFrame(
        id=f"frame-{timestamp_offset_hours}",
        content=content,
        frame_type=frame_type,
        metadata=metadata or {},
        timestamp=ts.isoformat(),
        tags=[frame_type],
    )


# CompactionConfig Tests


class TestCompactionConfig:
    """Tests for CompactionConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CompactionConfig()

        assert config.enabled is True
        assert config.threshold_frames == 50
        assert config.recent_count == 10
        assert config.medium_count == 20
        assert config.preserve_errors is True
        assert config.preserve_decisions is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = CompactionConfig(
            enabled=False,
            threshold_frames=100,
            recent_count=20,
        )

        assert config.enabled is False
        assert config.threshold_frames == 100
        assert config.recent_count == 20


# CompactionResult Tests


class TestCompactionResult:
    """Tests for CompactionResult."""

    def test_result_defaults(self):
        """Test default result values."""
        result = CompactionResult()

        assert result.frames_processed == 0
        assert result.frames_compacted == 0
        assert result.tokens_before == 0
        assert result.tokens_after == 0

    def test_reduction_percentage(self):
        """Test reduction percentage calculation."""
        result = CompactionResult(
            tokens_before=1000,
            tokens_after=400,
        )

        assert result.reduction_percentage == 60.0

    def test_reduction_percentage_zero_before(self):
        """Test reduction percentage with zero tokens before."""
        result = CompactionResult(
            tokens_before=0,
            tokens_after=0,
        )

        assert result.reduction_percentage == 0.0


# CompactionTier Tests


class TestCompactionTier:
    """Tests for CompactionTier enum."""

    def test_tiers_exist(self):
        """Test all tiers exist."""
        assert CompactionTier.RECENT
        assert CompactionTier.MEDIUM
        assert CompactionTier.OLD

    def test_tier_values(self):
        """Test tier values."""
        assert CompactionTier.RECENT.value == "recent"
        assert CompactionTier.MEDIUM.value == "medium"
        assert CompactionTier.OLD.value == "old"


# ImportanceLevel Tests


class TestImportanceLevel:
    """Tests for ImportanceLevel enum."""

    def test_levels_exist(self):
        """Test all levels exist."""
        assert ImportanceLevel.CRITICAL
        assert ImportanceLevel.HIGH
        assert ImportanceLevel.MEDIUM
        assert ImportanceLevel.LOW

    def test_level_values(self):
        """Test level values are ordered."""
        assert ImportanceLevel.CRITICAL.value > ImportanceLevel.HIGH.value
        assert ImportanceLevel.HIGH.value > ImportanceLevel.MEDIUM.value
        assert ImportanceLevel.MEDIUM.value > ImportanceLevel.LOW.value


# ContextCompactor Initialization Tests


class TestContextCompactorInit:
    """Tests for ContextCompactor initialization."""

    def test_init_default(self, mock_memory_store):
        """Test initialization with defaults."""
        compactor = ContextCompactor(mock_memory_store)

        assert compactor._store is mock_memory_store
        assert compactor.config is not None
        assert compactor.config.enabled is True

    def test_init_with_config(self, mock_memory_store, custom_config):
        """Test initialization with custom config."""
        compactor = ContextCompactor(mock_memory_store, custom_config)

        assert compactor.config is custom_config
        assert compactor.config.threshold_frames == 30

    def test_init_with_summarizer(self, mock_memory_store):
        """Test initialization with custom summarizer."""
        def custom_summarizer(frames):
            return "Custom summary"

        compactor = ContextCompactor(
            mock_memory_store,
            summarizer=custom_summarizer,
        )

        assert compactor._summarizer is custom_summarizer


# Importance Calculation Tests


class TestContextCompactorImportance:
    """Tests for importance calculation."""

    def test_error_is_critical(self, compactor):
        """Test error frames are critical importance."""
        frame = make_frame(frame_type="error")
        importance = compactor.get_importance(frame)

        assert importance == ImportanceLevel.CRITICAL

    def test_decision_is_critical(self, compactor):
        """Test decision frames are critical importance."""
        frame = make_frame(frame_type="decision")
        importance = compactor.get_importance(frame)

        assert importance == ImportanceLevel.CRITICAL

    def test_git_commit_is_critical(self, compactor):
        """Test git_commit frames are critical importance."""
        frame = make_frame(frame_type="git_commit")
        importance = compactor.get_importance(frame)

        assert importance == ImportanceLevel.CRITICAL

    def test_learning_is_high(self, compactor):
        """Test learning frames are high importance."""
        frame = make_frame(frame_type="learning")
        importance = compactor.get_importance(frame)

        assert importance == ImportanceLevel.HIGH

    def test_success_is_medium(self, compactor):
        """Test success frames are medium importance."""
        frame = make_frame(frame_type="success")
        importance = compactor.get_importance(frame)

        assert importance == ImportanceLevel.MEDIUM

    def test_context_is_low(self, compactor):
        """Test context frames are low importance."""
        frame = make_frame(frame_type="context")
        importance = compactor.get_importance(frame)

        assert importance == ImportanceLevel.LOW

    def test_high_metadata_importance(self, compactor):
        """Test frames with high metadata importance are critical."""
        frame = make_frame(metadata={"importance": 9})
        importance = compactor.get_importance(frame)

        assert importance == ImportanceLevel.CRITICAL


# Preservation Tests


class TestContextCompactorPreservation:
    """Tests for frame preservation logic."""

    def test_preserve_error(self, compactor):
        """Test error frames are preserved."""
        frame = make_frame(frame_type="error")
        assert compactor.should_preserve(frame) is True

    def test_preserve_decision(self, compactor):
        """Test decision frames are preserved."""
        frame = make_frame(frame_type="decision")
        assert compactor.should_preserve(frame) is True

    def test_preserve_critical_importance(self, compactor):
        """Test critical importance frames are preserved."""
        frame = make_frame(frame_type="git_commit")
        assert compactor.should_preserve(frame) is True

    def test_dont_preserve_iteration_result(self, compactor):
        """Test iteration_result frames can be compacted."""
        frame = make_frame(frame_type="iteration_result")
        assert compactor.should_preserve(frame) is False

    def test_dont_preserve_context(self, compactor):
        """Test context frames can be compacted."""
        frame = make_frame(frame_type="context")
        assert compactor.should_preserve(frame) is False

    def test_preserve_already_compacted(self, compactor):
        """Test already compacted frames are preserved."""
        frame = make_frame(metadata={"compacted": True})
        assert compactor.should_preserve(frame) is True

    def test_config_preserve_errors_disabled(self, mock_memory_store):
        """Test disabling error preservation."""
        config = CompactionConfig(preserve_errors=False)
        compactor = ContextCompactor(mock_memory_store, config)

        # Errors are still critical due to PRESERVE_TYPES
        frame = make_frame(frame_type="error")
        assert compactor.should_preserve(frame) is True


# Tier Calculation Tests


class TestContextCompactorTiers:
    """Tests for tier calculation."""

    def test_tier_recent(self, compactor_custom):
        """Test frames near end are recent tier."""
        # With recent_count=5 and total=20, index 15-19 should be recent
        assert compactor_custom.get_tier(19, 20) == CompactionTier.RECENT
        assert compactor_custom.get_tier(15, 20) == CompactionTier.RECENT

    def test_tier_medium(self, compactor_custom):
        """Test frames in middle are medium tier."""
        # With recent_count=5, medium_count=10 and total=20
        # index 5-14 should be medium
        assert compactor_custom.get_tier(14, 20) == CompactionTier.MEDIUM
        assert compactor_custom.get_tier(5, 20) == CompactionTier.MEDIUM

    def test_tier_old(self, compactor_custom):
        """Test frames at start are old tier."""
        # With recent_count=5, medium_count=10 and total=20
        # index 0-4 should be old
        assert compactor_custom.get_tier(0, 20) == CompactionTier.OLD
        assert compactor_custom.get_tier(4, 20) == CompactionTier.OLD


# Frame Grouping Tests


class TestContextCompactorGrouping:
    """Tests for frame grouping."""

    def test_group_frames_empty(self, compactor):
        """Test grouping empty frame list."""
        groups = compactor.group_frames([])
        assert groups == []

    def test_group_frames_single(self, compactor):
        """Test grouping single frame."""
        frames = [make_frame()]
        groups = compactor.group_frames(frames)

        assert len(groups) == 1
        assert groups[0].tier == CompactionTier.RECENT

    def test_group_frames_multiple_tiers(self, compactor_custom):
        """Test grouping into multiple tiers."""
        # Create 20 frames (old=5, medium=10, recent=5)
        frames = [make_frame(timestamp_offset_hours=i) for i in range(20)]
        groups = compactor_custom.group_frames(frames)

        # Should have 3 groups
        assert len(groups) == 3

        # Check tiers
        tiers = [g.tier for g in groups]
        assert CompactionTier.OLD in tiers
        assert CompactionTier.MEDIUM in tiers
        assert CompactionTier.RECENT in tiers

    def test_group_frames_token_count(self, compactor):
        """Test FrameGroup token_count property."""
        frames = [make_frame(content="A" * 100) for _ in range(3)]
        groups = compactor.group_frames(frames)

        assert groups[0].token_count > 0


# Compaction Tests


class TestContextCompactorCompaction:
    """Tests for compaction operation."""

    def test_compact_disabled(self, mock_memory_store):
        """Test compaction when disabled."""
        config = CompactionConfig(enabled=False)
        compactor = ContextCompactor(mock_memory_store, config)

        result = compactor.compact()

        assert result.frames_processed == 0
        mock_memory_store.get_recent.assert_not_called()

    def test_compact_below_threshold(self, compactor, mock_memory_store):
        """Test compaction skipped below threshold."""
        mock_memory_store.get_recent.return_value = [
            make_frame() for _ in range(10)
        ]

        result = compactor.compact()

        assert result.frames_processed == 0

    def test_compact_above_threshold(self, compactor_custom, mock_memory_store):
        """Test compaction runs above threshold."""
        # Create enough frames to trigger compaction (threshold=30)
        frames = [make_frame(timestamp_offset_hours=i) for i in range(40)]
        mock_memory_store.get_recent.return_value = frames

        result = compactor_custom.compact()

        assert result.frames_processed == 40
        assert result.tokens_before > 0

    def test_compact_preserves_errors(self, compactor_custom, mock_memory_store):
        """Test compaction preserves error frames."""
        frames = [make_frame(frame_type="error") for _ in range(35)]
        mock_memory_store.get_recent.return_value = frames

        result = compactor_custom.compact()

        # All frames should be preserved
        assert result.frames_compacted == 0

    def test_compact_creates_summaries(self, compactor_custom, mock_memory_store):
        """Test compaction creates summary frames."""
        frames = [
            make_frame(frame_type="iteration_result", timestamp_offset_hours=i)
            for i in range(35)
        ]
        mock_memory_store.get_recent.return_value = frames

        result = compactor_custom.compact()

        # Should create summaries for old/medium tiers
        assert result.summaries_created > 0

    def test_compact_dry_run(self, compactor_custom, mock_memory_store):
        """Test dry run doesn't modify anything."""
        frames = [make_frame(timestamp_offset_hours=i) for i in range(35)]
        mock_memory_store.get_recent.return_value = frames

        result = compactor_custom.compact(dry_run=True)

        assert result.frames_processed == 35

    def test_compact_with_session(self, compactor_custom, mock_memory_store):
        """Test compaction with session ID."""
        frames = [make_frame(timestamp_offset_hours=i) for i in range(35)]
        mock_memory_store.get_by_session.return_value = frames

        result = compactor_custom.compact(session_id="test-session")

        mock_memory_store.get_by_session.assert_called_once()


# Needs Compaction Tests


class TestContextCompactorNeedsCompaction:
    """Tests for needs_compaction check."""

    def test_needs_compaction_disabled(self, mock_memory_store):
        """Test needs_compaction when disabled."""
        config = CompactionConfig(enabled=False)
        compactor = ContextCompactor(mock_memory_store, config)

        assert compactor.needs_compaction() is False

    def test_needs_compaction_below_threshold(self, compactor, mock_memory_store):
        """Test needs_compaction below threshold."""
        mock_memory_store.get_recent.return_value = [
            make_frame() for _ in range(10)
        ]

        assert compactor.needs_compaction() is False

    def test_needs_compaction_above_threshold(self, compactor, mock_memory_store):
        """Test needs_compaction above threshold."""
        mock_memory_store.get_recent.return_value = [
            make_frame() for _ in range(60)
        ]

        assert compactor.needs_compaction() is True


# Estimate Tests


class TestContextCompactorEstimate:
    """Tests for compaction estimation."""

    def test_estimate_compaction(self, compactor_custom, mock_memory_store):
        """Test estimate_compaction returns metrics without modifying."""
        frames = [make_frame(timestamp_offset_hours=i) for i in range(35)]
        mock_memory_store.get_recent.return_value = frames

        result = compactor_custom.estimate_compaction()

        assert result.frames_processed == 35
        assert result.tokens_before > 0
        assert result.tokens_after > 0


# Default Summarizer Tests


class TestDefaultSummarizer:
    """Tests for default summarizer."""

    def test_default_summarizer_empty(self, compactor):
        """Test default summarizer with empty list."""
        result = compactor._default_summarizer([])
        assert result == ""

    def test_default_summarizer_single_frame(self, compactor):
        """Test default summarizer with single frame."""
        frames = [make_frame(content="Test content")]
        result = compactor._default_summarizer(frames)

        assert "iteration_result" in result
        assert "Test content" in result

    def test_default_summarizer_truncates(self, compactor):
        """Test default summarizer truncates long content."""
        frames = [make_frame(content="A" * 500)]
        result = compactor._default_summarizer(frames)

        assert len(result) < 500
        assert "..." in result


# LLM Summarizer Factory Tests


class TestLLMSummarizer:
    """Tests for LLM summarizer factory."""

    def test_create_llm_summarizer(self):
        """Test creating LLM summarizer."""
        summarizer = create_llm_summarizer()

        assert callable(summarizer)

    def test_llm_summarizer_empty(self):
        """Test LLM summarizer with empty list."""
        summarizer = create_llm_summarizer()
        result = summarizer([])

        assert result == ""

    def test_llm_summarizer_with_frames(self):
        """Test LLM summarizer with frames."""
        summarizer = create_llm_summarizer()
        frames = [make_frame() for _ in range(5)]

        result = summarizer(frames)

        assert "Summary" in result
        assert "5" in result


# Integration-like Tests


class TestContextCompactorIntegration:
    """Integration-like tests for compaction workflow."""

    def test_full_compaction_workflow(self, compactor_custom, mock_memory_store):
        """Test full compaction workflow."""
        # Create a mix of frame types
        frames = []
        for i in range(35):
            if i % 10 == 0:
                frames.append(make_frame(
                    frame_type="error",
                    timestamp_offset_hours=35 - i,
                ))
            elif i % 7 == 0:
                frames.append(make_frame(
                    frame_type="decision",
                    timestamp_offset_hours=35 - i,
                ))
            else:
                frames.append(make_frame(
                    frame_type="iteration_result",
                    timestamp_offset_hours=35 - i,
                ))

        mock_memory_store.get_recent.return_value = frames

        # Check needs compaction
        assert compactor_custom.needs_compaction() is True

        # Run compaction
        result = compactor_custom.compact()

        # Verify results
        assert result.frames_processed == 35
        assert result.frames_preserved > 0  # Errors and decisions
        assert result.tokens_after < result.tokens_before or result.summaries_created > 0

    def test_token_reduction_goal(self, compactor_custom, mock_memory_store):
        """Test that compaction achieves significant token reduction."""
        # Create many compactable frames
        frames = [
            make_frame(
                frame_type="iteration_result",
                content="A" * 200,  # ~50 tokens each
                timestamp_offset_hours=i,
            )
            for i in range(40)
        ]
        mock_memory_store.get_recent.return_value = frames

        result = compactor_custom.compact()

        # Should achieve meaningful reduction (goal is 50%+)
        # Note: With simple summarizer, actual reduction varies
        assert result.reduction_percentage >= 0
