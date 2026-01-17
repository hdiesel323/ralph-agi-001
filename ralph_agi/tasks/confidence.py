"""Confidence Scoring & Auto-Merge for RALPH-AGI.

Calculates confidence scores for completed tasks and decides
whether to auto-merge PRs or queue them for manual review.

Confidence Formula:
    confidence = 0.4*test_pass + 0.3*critic + 0.2*acceptance + 0.1*(1-complexity)

Where:
    - test_pass: Percentage of tests passing (0.0-1.0)
    - critic: Score from Critic agent review (0.0-1.0)
    - critic: Score from Critic agent review (0.0-1.0)
    - acceptance: Percentage of acceptance criteria met (0.0-1.0)
    - complexity: File complexity score (0.0-1.0, higher = more complex)

Usage:
    from ralph_agi.tasks.confidence import ConfidenceScorer, AutoMerger

    # Calculate confidence
    scorer = ConfidenceScorer()
    score = scorer.calculate(
        test_pass_rate=0.95,
        critic_score=0.8,
        acceptance_rate=1.0,
        complexity_score=0.3,
    )
    print(f"Confidence: {score:.2f}")  # 0.86

    # Auto-merge decision
    merger = AutoMerger(threshold=0.85)
    if merger.should_merge(score):
        merger.merge(pr_url)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MergeDecision(Enum):
    """Auto-merge decision."""

    AUTO_MERGE = "auto_merge"
    MANUAL_REVIEW = "manual_review"
    REJECT = "reject"


@dataclass
class ConfidenceFactors:
    """Individual factors contributing to confidence score.

    Attributes:
        test_pass_rate: Percentage of tests passing (0.0-1.0)
        critic_score: Score from Critic agent (0.0-1.0)
        acceptance_rate: Percentage of acceptance criteria met (0.0-1.0)
        complexity_score: Code complexity (0.0-1.0, higher = more complex)
    """

    test_pass_rate: float = 0.0
    critic_score: float = 0.0
    acceptance_rate: float = 0.0
    complexity_score: float = 0.0

    def __post_init__(self):
        """Validate all scores are in valid range."""
        for field_name in ["test_pass_rate", "critic_score", "acceptance_rate", "complexity_score"]:
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0, got {value}")

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "test_pass_rate": self.test_pass_rate,
            "critic_score": self.critic_score,
            "acceptance_rate": self.acceptance_rate,
            "complexity_score": self.complexity_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfidenceFactors":
        """Create from dictionary."""
        return cls(
            test_pass_rate=float(data.get("test_pass_rate", 0.0)),
            critic_score=float(data.get("critic_score", 0.0)),
            acceptance_rate=float(data.get("acceptance_rate", 0.0)),
            complexity_score=float(data.get("complexity_score", 0.0)),
        )


@dataclass
class ConfidenceResult:
    """Result of confidence calculation.

    Attributes:
        score: Overall confidence score (0.0-1.0)
        factors: Individual contributing factors
        decision: Auto-merge decision based on threshold
        threshold: Threshold used for decision
        breakdown: Weighted breakdown of score components
    """

    score: float
    factors: ConfidenceFactors
    decision: MergeDecision
    threshold: float
    breakdown: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "score": self.score,
            "factors": self.factors.to_dict(),
            "decision": self.decision.value,
            "threshold": self.threshold,
            "breakdown": self.breakdown,
        }


class ConfidenceScorer:
    """Calculates confidence scores for task execution results.

    Uses a weighted formula to combine multiple factors into
    a single confidence score.

    Weights:
        - test_pass_rate: 40%
        - critic_score: 30%
        - acceptance_rate: 20%
        - complexity: 10% (inverted - lower complexity = higher score)
    """

    # Default weights (must sum to 1.0)
    DEFAULT_WEIGHTS = {
        "test_pass": 0.4,
        "critic": 0.3,
        "acceptance": 0.2,
        "complexity": 0.1,
    }

    # Default threshold for auto-merge
    DEFAULT_THRESHOLD = 0.85

    def __init__(
        self,
        weights: Optional[dict[str, float]] = None,
        threshold: float = DEFAULT_THRESHOLD,
    ):
        """Initialize confidence scorer.

        Args:
            weights: Custom weights for factors (must sum to 1.0)
            threshold: Threshold for auto-merge decision
        """
        self._weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._threshold = threshold

        # Validate weights sum to 1.0
        weight_sum = sum(self._weights.values())
        if abs(weight_sum - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {weight_sum}")

    @property
    def threshold(self) -> float:
        """Get auto-merge threshold."""
        return self._threshold

    @threshold.setter
    def threshold(self, value: float) -> None:
        """Set auto-merge threshold."""
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {value}")
        self._threshold = value

    @property
    def weights(self) -> dict[str, float]:
        """Get current weights."""
        return self._weights.copy()

    def calculate(
        self,
        test_pass_rate: float = 0.0,
        critic_score: float = 0.0,
        acceptance_rate: float = 0.0,
        complexity_score: float = 0.0,
    ) -> ConfidenceResult:
        """Calculate confidence score from individual factors.

        Args:
            test_pass_rate: Percentage of tests passing (0.0-1.0)
            critic_score: Score from Critic agent (0.0-1.0)
            acceptance_rate: Percentage of acceptance criteria met (0.0-1.0)
            complexity_score: Code complexity (0.0-1.0)

        Returns:
            ConfidenceResult with score and decision
        """
        factors = ConfidenceFactors(
            test_pass_rate=test_pass_rate,
            critic_score=critic_score,
            acceptance_rate=acceptance_rate,
            complexity_score=complexity_score,
        )

        return self.calculate_from_factors(factors)

    def calculate_from_factors(self, factors: ConfidenceFactors) -> ConfidenceResult:
        """Calculate confidence score from ConfidenceFactors.

        Args:
            factors: ConfidenceFactors instance

        Returns:
            ConfidenceResult with score and decision
        """
        # Calculate weighted components
        breakdown = {
            "test_pass": factors.test_pass_rate * self._weights["test_pass"],
            "critic": factors.critic_score * self._weights["critic"],
            "acceptance": factors.acceptance_rate * self._weights["acceptance"],
            # Invert complexity - lower complexity = higher contribution
            "complexity": (1 - factors.complexity_score) * self._weights["complexity"],
        }

        # Sum for total score
        score = sum(breakdown.values())

        # Clamp to valid range
        score = max(0.0, min(1.0, score))

        # Determine decision
        if score >= self._threshold:
            decision = MergeDecision.AUTO_MERGE
        elif score >= self._threshold * 0.7:  # Within 70% of threshold
            decision = MergeDecision.MANUAL_REVIEW
        else:
            decision = MergeDecision.REJECT

        logger.debug(
            f"Confidence calculated: {score:.3f} (threshold={self._threshold}) "
            f"-> {decision.value}"
        )

        return ConfidenceResult(
            score=score,
            factors=factors,
            decision=decision,
            threshold=self._threshold,
            breakdown=breakdown,
        )


@dataclass
class ReviewQueueItem:
    """An item in the manual review queue.

    Attributes:
        task_id: ID of the task
        pr_url: URL of the pull request
        confidence: Confidence score
        factors: Confidence factors breakdown
        created_at: When added to queue
        notes: Optional notes for reviewer
    """

    task_id: str
    pr_url: str
    confidence: float
    factors: ConfidenceFactors
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "pr_url": self.pr_url,
            "confidence": self.confidence,
            "factors": self.factors.to_dict(),
            "created_at": self.created_at.isoformat(),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewQueueItem":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif created_at is None:
            created_at = datetime.now(timezone.utc)

        return cls(
            task_id=data["task_id"],
            pr_url=data["pr_url"],
            confidence=float(data["confidence"]),
            factors=ConfidenceFactors.from_dict(data.get("factors", {})),
            created_at=created_at,
            notes=data.get("notes", ""),
        )


class AutoMerger:
    """Handles auto-merge decisions and manual review queue.

    Manages the workflow of deciding whether to auto-merge PRs
    based on confidence scores, or queue them for manual review.
    """

    REVIEW_QUEUE_FILE = ".ralph/review-queue.json"

    def __init__(
        self,
        project_root: Path | str | None = None,
        threshold: float = ConfidenceScorer.DEFAULT_THRESHOLD,
        scorer: Optional[ConfidenceScorer] = None,
    ):
        """Initialize auto-merger.

        Args:
            project_root: Project root directory (default: cwd)
            threshold: Auto-merge threshold (0.0-1.0)
            scorer: Custom confidence scorer
        """
        self._project_root = Path(project_root).resolve() if project_root else Path.cwd()
        self._threshold = threshold
        self._scorer = scorer or ConfidenceScorer(threshold=threshold)
        self._review_queue_file = self._project_root / self.REVIEW_QUEUE_FILE

        # Ensure directory exists
        self._review_queue_file.parent.mkdir(parents=True, exist_ok=True)

    @property
    def threshold(self) -> float:
        """Get auto-merge threshold."""
        return self._threshold

    @threshold.setter
    def threshold(self, value: float) -> None:
        """Set auto-merge threshold."""
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {value}")
        self._threshold = value
        self._scorer.threshold = value

    def should_merge(self, confidence: float) -> bool:
        """Check if confidence meets auto-merge threshold.

        Args:
            confidence: Confidence score (0.0-1.0)

        Returns:
            True if should auto-merge
        """
        return confidence >= self._threshold

    def evaluate(
        self,
        task_id: str,
        pr_url: str,
        factors: ConfidenceFactors,
    ) -> ConfidenceResult:
        """Evaluate a task for auto-merge.

        Calculates confidence and takes appropriate action:
        - High confidence: Returns AUTO_MERGE decision
        - Medium confidence: Adds to review queue
        - Low confidence: Returns REJECT decision

        Args:
            task_id: ID of the task
            pr_url: URL of the pull request
            factors: Confidence factors

        Returns:
            ConfidenceResult with decision
        """
        result = self._scorer.calculate_from_factors(factors)

        if result.decision == MergeDecision.MANUAL_REVIEW:
            # Add to review queue
            self._add_to_review_queue(
                task_id=task_id,
                pr_url=pr_url,
                confidence=result.score,
                factors=factors,
            )
            logger.info(
                f"Task {task_id} added to review queue "
                f"(confidence={result.score:.2f}, threshold={self._threshold})"
            )

        elif result.decision == MergeDecision.AUTO_MERGE:
            logger.info(
                f"Task {task_id} approved for auto-merge "
                f"(confidence={result.score:.2f})"
            )

        else:
            logger.warning(
                f"Task {task_id} rejected "
                f"(confidence={result.score:.2f}, threshold={self._threshold})"
            )

        return result

    def _add_to_review_queue(
        self,
        task_id: str,
        pr_url: str,
        confidence: float,
        factors: ConfidenceFactors,
        notes: str = "",
    ) -> None:
        """Add item to manual review queue.

        Args:
            task_id: Task ID
            pr_url: PR URL
            confidence: Confidence score
            factors: Confidence factors
            notes: Optional notes
        """
        item = ReviewQueueItem(
            task_id=task_id,
            pr_url=pr_url,
            confidence=confidence,
            factors=factors,
            notes=notes,
        )

        queue = self._load_review_queue()
        queue.append(item)
        self._save_review_queue(queue)

    def _load_review_queue(self) -> list[ReviewQueueItem]:
        """Load review queue from file."""
        if not self._review_queue_file.exists():
            return []

        try:
            with open(self._review_queue_file) as f:
                data = json.load(f)
            return [ReviewQueueItem.from_dict(item) for item in data.get("items", [])]
        except Exception as e:
            logger.warning(f"Failed to load review queue: {e}")
            return []

    def _save_review_queue(self, queue: list[ReviewQueueItem]) -> None:
        """Save review queue to file."""
        data = {
            "items": [item.to_dict() for item in queue],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        temp_path = self._review_queue_file.with_suffix(".json.tmp")
        try:
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self._review_queue_file)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Failed to save review queue: {e}") from e

    def get_review_queue(self) -> list[ReviewQueueItem]:
        """Get all items in review queue.

        Returns:
            List of ReviewQueueItems sorted by confidence (ascending)
        """
        queue = self._load_review_queue()
        queue.sort(key=lambda x: x.confidence)
        return queue

    def remove_from_queue(self, task_id: str) -> bool:
        """Remove item from review queue.

        Args:
            task_id: Task ID to remove

        Returns:
            True if item was found and removed
        """
        queue = self._load_review_queue()
        original_len = len(queue)
        queue = [item for item in queue if item.task_id != task_id]

        if len(queue) < original_len:
            self._save_review_queue(queue)
            return True
        return False

    def clear_queue(self) -> int:
        """Clear all items from review queue.

        Returns:
            Number of items cleared
        """
        queue = self._load_review_queue()
        count = len(queue)
        self._save_review_queue([])
        return count

    def stats(self) -> dict[str, Any]:
        """Get review queue statistics.

        Returns:
            Dictionary with queue stats
        """
        queue = self._load_review_queue()

        if not queue:
            return {
                "queue_length": 0,
                "avg_confidence": 0.0,
                "threshold": self._threshold,
            }

        confidences = [item.confidence for item in queue]
        return {
            "queue_length": len(queue),
            "avg_confidence": sum(confidences) / len(confidences),
            "min_confidence": min(confidences),
            "max_confidence": max(confidences),
            "threshold": self._threshold,
        }


class ConfigManager:
    """Manages RALPH configuration including auto-merge threshold.

    Configuration is stored in .ralph/config.json
    """

    CONFIG_FILE = ".ralph/config.json"

    def __init__(self, project_root: Path | str | None = None):
        """Initialize config manager.

        Args:
            project_root: Project root directory
        """
        self._project_root = Path(project_root).resolve() if project_root else Path.cwd()
        self._config_file = self._project_root / self.CONFIG_FILE
        self._config_file.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        """Load configuration."""
        if not self._config_file.exists():
            return {}

        try:
            with open(self._config_file) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, config: dict[str, Any]) -> None:
        """Save configuration."""
        temp_path = self._config_file.with_suffix(".json.tmp")
        try:
            with open(temp_path, "w") as f:
                json.dump(config, f, indent=2)
            temp_path.replace(self._config_file)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Failed to save config: {e}") from e

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value
        """
        config = self._load()
        return config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value.

        Args:
            key: Configuration key
            value: Value to set
        """
        config = self._load()
        config[key] = value
        self._save(config)
        logger.info(f"Config set: {key} = {value}")

    def get_auto_merge_threshold(self) -> float:
        """Get auto-merge threshold.

        Returns:
            Threshold value (default: 0.85)
        """
        return float(self.get("auto-merge-threshold", ConfidenceScorer.DEFAULT_THRESHOLD))

    def set_auto_merge_threshold(self, threshold: float) -> None:
        """Set auto-merge threshold.

        Args:
            threshold: Threshold value (0.0-1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")
        self.set("auto-merge-threshold", threshold)

    def list_all(self) -> dict[str, Any]:
        """List all configuration values.

        Returns:
            Dictionary of all config values
        """
        return self._load()
