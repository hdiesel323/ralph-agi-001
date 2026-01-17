"""Tests for Confidence Scoring & Auto-Merge.

Tests the confidence calculation and auto-merge decision system.
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path

from ralph_agi.tasks.confidence import (
    ConfidenceScorer,
    ConfidenceFactors,
    ConfidenceResult,
    MergeDecision,
    AutoMerger,
    ReviewQueueItem,
    ConfigManager,
)


class TestConfidenceFactors:
    """Tests for ConfidenceFactors dataclass."""

    def test_valid_factors(self):
        """Test creating valid factors."""
        factors = ConfidenceFactors(
            test_pass_rate=0.95,
            critic_score=0.8,
            acceptance_rate=1.0,
            complexity_score=0.3,
        )

        assert factors.test_pass_rate == 0.95
        assert factors.critic_score == 0.8
        assert factors.acceptance_rate == 1.0
        assert factors.complexity_score == 0.3

    def test_invalid_factor_raises(self):
        """Test invalid factor values raise error."""
        with pytest.raises(ValueError):
            ConfidenceFactors(test_pass_rate=1.5)

        with pytest.raises(ValueError):
            ConfidenceFactors(critic_score=-0.1)

    def test_to_dict(self):
        """Test serialization to dictionary."""
        factors = ConfidenceFactors(
            test_pass_rate=0.9,
            critic_score=0.85,
            acceptance_rate=0.75,
            complexity_score=0.4,
        )

        data = factors.to_dict()

        assert data["test_pass_rate"] == 0.9
        assert data["critic_score"] == 0.85
        assert data["acceptance_rate"] == 0.75
        assert data["complexity_score"] == 0.4

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "test_pass_rate": 0.9,
            "critic_score": 0.85,
            "acceptance_rate": 0.75,
            "complexity_score": 0.4,
        }

        factors = ConfidenceFactors.from_dict(data)

        assert factors.test_pass_rate == 0.9
        assert factors.critic_score == 0.85

    def test_from_dict_with_defaults(self):
        """Test deserialization with missing fields uses defaults."""
        factors = ConfidenceFactors.from_dict({})

        assert factors.test_pass_rate == 0.0
        assert factors.critic_score == 0.0


class TestConfidenceScorer:
    """Tests for ConfidenceScorer class."""

    def test_default_threshold(self):
        """Test default threshold is 0.85."""
        scorer = ConfidenceScorer()
        assert scorer.threshold == 0.85

    def test_custom_threshold(self):
        """Test custom threshold."""
        scorer = ConfidenceScorer(threshold=0.9)
        assert scorer.threshold == 0.9

    def test_threshold_setter_validates(self):
        """Test threshold setter validates range."""
        scorer = ConfidenceScorer()

        scorer.threshold = 0.7
        assert scorer.threshold == 0.7

        with pytest.raises(ValueError):
            scorer.threshold = 1.5

        with pytest.raises(ValueError):
            scorer.threshold = -0.1

    def test_default_weights_sum_to_one(self):
        """Test default weights sum to 1.0."""
        scorer = ConfidenceScorer()
        assert abs(sum(scorer.weights.values()) - 1.0) < 0.001

    def test_custom_weights_validation(self):
        """Test custom weights must sum to 1.0."""
        with pytest.raises(ValueError):
            ConfidenceScorer(weights={"test_pass": 0.5, "critic": 0.3, "acceptance": 0.1, "complexity": 0.05})

    def test_calculate_perfect_score(self):
        """Test calculation with perfect scores."""
        scorer = ConfidenceScorer(threshold=0.85)
        result = scorer.calculate(
            test_pass_rate=1.0,
            critic_score=1.0,
            acceptance_rate=1.0,
            complexity_score=0.0,  # Low complexity = good
        )

        assert abs(result.score - 1.0) < 0.001  # Float tolerance
        assert result.decision == MergeDecision.AUTO_MERGE

    def test_calculate_with_formula(self):
        """Test calculation matches expected formula.

        confidence = 0.4*test_pass + 0.3*critic + 0.2*acceptance + 0.1*(1-complexity)
        """
        scorer = ConfidenceScorer()
        result = scorer.calculate(
            test_pass_rate=0.95,
            critic_score=0.8,
            acceptance_rate=1.0,
            complexity_score=0.3,
        )

        # 0.4*0.95 + 0.3*0.8 + 0.2*1.0 + 0.1*(1-0.3) = 0.38 + 0.24 + 0.2 + 0.07 = 0.89
        assert abs(result.score - 0.89) < 0.01

    def test_calculate_auto_merge_decision(self):
        """Test auto-merge decision when above threshold."""
        scorer = ConfidenceScorer(threshold=0.85)
        result = scorer.calculate(
            test_pass_rate=1.0,
            critic_score=0.9,
            acceptance_rate=1.0,
            complexity_score=0.2,
        )

        assert result.decision == MergeDecision.AUTO_MERGE

    def test_calculate_manual_review_decision(self):
        """Test manual review decision when below threshold but close."""
        scorer = ConfidenceScorer(threshold=0.85)
        # Score should be around 0.7-0.85 (70% of threshold)
        result = scorer.calculate(
            test_pass_rate=0.8,
            critic_score=0.7,
            acceptance_rate=0.7,
            complexity_score=0.5,
        )

        assert result.decision == MergeDecision.MANUAL_REVIEW

    def test_calculate_reject_decision(self):
        """Test reject decision when well below threshold."""
        scorer = ConfidenceScorer(threshold=0.85)
        result = scorer.calculate(
            test_pass_rate=0.3,
            critic_score=0.2,
            acceptance_rate=0.3,
            complexity_score=0.9,
        )

        assert result.decision == MergeDecision.REJECT

    def test_breakdown_in_result(self):
        """Test result includes breakdown of components."""
        scorer = ConfidenceScorer()
        result = scorer.calculate(
            test_pass_rate=0.9,
            critic_score=0.8,
            acceptance_rate=0.7,
            complexity_score=0.3,
        )

        assert "test_pass" in result.breakdown
        assert "critic" in result.breakdown
        assert "acceptance" in result.breakdown
        assert "complexity" in result.breakdown


class TestReviewQueueItem:
    """Tests for ReviewQueueItem dataclass."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        item = ReviewQueueItem(
            task_id="test-task",
            pr_url="https://github.com/test/pr/1",
            confidence=0.75,
            factors=ConfidenceFactors(test_pass_rate=0.8),
            notes="Needs review",
        )

        data = item.to_dict()

        assert data["task_id"] == "test-task"
        assert data["pr_url"] == "https://github.com/test/pr/1"
        assert data["confidence"] == 0.75
        assert "factors" in data
        assert data["notes"] == "Needs review"

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "task_id": "test-task",
            "pr_url": "https://github.com/test/pr/1",
            "confidence": 0.75,
            "factors": {"test_pass_rate": 0.8},
            "created_at": "2026-01-17T10:00:00+00:00",
            "notes": "Needs review",
        }

        item = ReviewQueueItem.from_dict(data)

        assert item.task_id == "test-task"
        assert item.confidence == 0.75
        assert item.factors.test_pass_rate == 0.8


class TestAutoMerger:
    """Tests for AutoMerger class."""

    @pytest.fixture
    def merger(self, tmp_path):
        """Create AutoMerger with temp directory."""
        return AutoMerger(project_root=tmp_path, threshold=0.85)

    def test_should_merge_above_threshold(self, merger):
        """Test should_merge returns True above threshold."""
        assert merger.should_merge(0.9) is True
        assert merger.should_merge(0.85) is True

    def test_should_merge_below_threshold(self, merger):
        """Test should_merge returns False below threshold."""
        assert merger.should_merge(0.84) is False
        assert merger.should_merge(0.5) is False

    def test_threshold_property(self, merger):
        """Test threshold getter and setter."""
        assert merger.threshold == 0.85

        merger.threshold = 0.9
        assert merger.threshold == 0.9

        with pytest.raises(ValueError):
            merger.threshold = 1.5

    def test_evaluate_auto_merge(self, merger):
        """Test evaluate returns auto-merge for high confidence."""
        factors = ConfidenceFactors(
            test_pass_rate=1.0,
            critic_score=0.9,
            acceptance_rate=1.0,
            complexity_score=0.1,
        )

        result = merger.evaluate("task-1", "https://pr/1", factors)

        assert result.decision == MergeDecision.AUTO_MERGE

    def test_evaluate_manual_review_queues_item(self, merger, tmp_path):
        """Test evaluate adds to review queue for medium confidence."""
        factors = ConfidenceFactors(
            test_pass_rate=0.8,
            critic_score=0.7,
            acceptance_rate=0.7,
            complexity_score=0.5,
        )

        result = merger.evaluate("task-1", "https://pr/1", factors)

        assert result.decision == MergeDecision.MANUAL_REVIEW

        # Check item was added to queue
        queue = merger.get_review_queue()
        assert len(queue) == 1
        assert queue[0].task_id == "task-1"

    def test_get_review_queue_empty(self, merger):
        """Test get_review_queue returns empty list initially."""
        queue = merger.get_review_queue()
        assert queue == []

    def test_get_review_queue_sorted_by_confidence(self, merger):
        """Test review queue is sorted by confidence (ascending)."""
        # Add items with different confidence levels
        factors_low = ConfidenceFactors(test_pass_rate=0.5)
        factors_mid = ConfidenceFactors(test_pass_rate=0.7)

        merger._add_to_review_queue("task-mid", "pr/2", 0.7, factors_mid)
        merger._add_to_review_queue("task-low", "pr/1", 0.5, factors_low)

        queue = merger.get_review_queue()

        assert len(queue) == 2
        assert queue[0].task_id == "task-low"  # Lower confidence first
        assert queue[1].task_id == "task-mid"

    def test_remove_from_queue(self, merger):
        """Test removing item from review queue."""
        factors = ConfidenceFactors(test_pass_rate=0.6)
        merger._add_to_review_queue("task-1", "pr/1", 0.6, factors)

        result = merger.remove_from_queue("task-1")

        assert result is True
        assert len(merger.get_review_queue()) == 0

    def test_remove_from_queue_not_found(self, merger):
        """Test removing non-existent item returns False."""
        result = merger.remove_from_queue("nonexistent")
        assert result is False

    def test_clear_queue(self, merger):
        """Test clearing review queue."""
        factors = ConfidenceFactors(test_pass_rate=0.6)
        merger._add_to_review_queue("task-1", "pr/1", 0.6, factors)
        merger._add_to_review_queue("task-2", "pr/2", 0.65, factors)

        count = merger.clear_queue()

        assert count == 2
        assert len(merger.get_review_queue()) == 0

    def test_stats(self, merger):
        """Test queue statistics."""
        factors = ConfidenceFactors(test_pass_rate=0.6)
        merger._add_to_review_queue("task-1", "pr/1", 0.6, factors)
        merger._add_to_review_queue("task-2", "pr/2", 0.7, factors)

        stats = merger.stats()

        assert stats["queue_length"] == 2
        assert abs(stats["avg_confidence"] - 0.65) < 0.001  # Float tolerance
        assert stats["min_confidence"] == 0.6
        assert stats["max_confidence"] == 0.7
        assert stats["threshold"] == 0.85


class TestConfigManager:
    """Tests for ConfigManager class."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create ConfigManager with temp directory."""
        return ConfigManager(project_root=tmp_path)

    def test_get_unset_returns_none(self, config):
        """Test get returns None for unset keys."""
        assert config.get("nonexistent") is None

    def test_get_unset_returns_default(self, config):
        """Test get returns default for unset keys."""
        assert config.get("nonexistent", "default") == "default"

    def test_set_and_get(self, config):
        """Test set and get roundtrip."""
        config.set("my-key", "my-value")
        assert config.get("my-key") == "my-value"

    def test_set_numeric_value(self, config):
        """Test setting numeric values."""
        config.set("threshold", 0.9)
        assert config.get("threshold") == 0.9

    def test_set_boolean_value(self, config):
        """Test setting boolean values."""
        config.set("enabled", True)
        assert config.get("enabled") is True

    def test_get_auto_merge_threshold_default(self, config):
        """Test default auto-merge threshold."""
        threshold = config.get_auto_merge_threshold()
        assert threshold == 0.85

    def test_set_auto_merge_threshold(self, config):
        """Test setting auto-merge threshold."""
        config.set_auto_merge_threshold(0.9)
        assert config.get_auto_merge_threshold() == 0.9

    def test_set_auto_merge_threshold_validates(self, config):
        """Test auto-merge threshold validation."""
        with pytest.raises(ValueError):
            config.set_auto_merge_threshold(1.5)

        with pytest.raises(ValueError):
            config.set_auto_merge_threshold(-0.1)

    def test_list_all_empty(self, config):
        """Test list_all returns empty dict initially."""
        assert config.list_all() == {}

    def test_list_all_returns_all_values(self, config):
        """Test list_all returns all set values."""
        config.set("key1", "value1")
        config.set("key2", 42)

        all_config = config.list_all()

        assert all_config["key1"] == "value1"
        assert all_config["key2"] == 42

    def test_config_persists(self, tmp_path):
        """Test configuration persists across instances."""
        config1 = ConfigManager(project_root=tmp_path)
        config1.set("persistent-key", "persistent-value")

        config2 = ConfigManager(project_root=tmp_path)
        assert config2.get("persistent-key") == "persistent-value"
