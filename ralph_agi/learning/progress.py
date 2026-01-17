"""Structured progress entries for contextual learning.

Layer 2 of the Contextual Learning System - provides structured
learnings tied to session IDs for quick reference of what worked
and what failed.

Progress entries are stored in .ralph/progress.yaml and include:
- Session/iteration identifiers
- Task outcomes (success/failure)
- Learnings and errors
- Duration metrics
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logger = logging.getLogger(__name__)


class Outcome(Enum):
    """Possible outcomes for a progress entry."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


@dataclass
class ProgressEntry:
    """A structured progress entry for a single iteration.

    Attributes:
        session_id: Unique session identifier.
        iteration: Iteration number within the session.
        task: Task identifier (e.g., "US-007").
        outcome: Result of the iteration.
        learnings: What was learned during this iteration.
        errors: Errors encountered.
        timestamp: When this entry was created.
        duration_seconds: How long the iteration took.
        tags: Additional tags for filtering.
        metadata: Additional structured data.
    """

    session_id: str
    iteration: int = 1
    task: Optional[str] = None
    outcome: Outcome = Outcome.UNKNOWN
    learnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    timestamp: Optional[str] = None
    duration_seconds: Optional[float] = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    @property
    def is_success(self) -> bool:
        """Check if this was a successful iteration."""
        return self.outcome == Outcome.SUCCESS

    @property
    def has_learnings(self) -> bool:
        """Check if there are any learnings."""
        return len(self.learnings) > 0

    @property
    def has_errors(self) -> bool:
        """Check if there were any errors."""
        return len(self.errors) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "iteration": self.iteration,
            "task": self.task,
            "outcome": self.outcome.value,
            "learnings": list(self.learnings),
            "errors": list(self.errors),
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "tags": list(self.tags),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProgressEntry:
        """Create from dictionary."""
        outcome = data.get("outcome", "unknown")
        if isinstance(outcome, str):
            try:
                outcome = Outcome(outcome)
            except ValueError:
                outcome = Outcome.UNKNOWN

        return cls(
            session_id=data.get("session_id", "unknown"),
            iteration=data.get("iteration", 1),
            task=data.get("task"),
            outcome=outcome,
            learnings=tuple(data.get("learnings", [])),
            errors=tuple(data.get("errors", [])),
            timestamp=data.get("timestamp"),
            duration_seconds=data.get("duration_seconds"),
            tags=tuple(data.get("tags", [])),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ProgressStore:
    """Collection of progress entries.

    Attributes:
        entries: List of progress entries.
        version: Schema version.
    """

    entries: list[ProgressEntry] = field(default_factory=list)
    version: str = "1.0"

    def add(self, entry: ProgressEntry) -> None:
        """Add a progress entry.

        Args:
            entry: Entry to add.
        """
        self.entries.append(entry)

    def get_by_session(self, session_id: str) -> list[ProgressEntry]:
        """Get entries for a specific session.

        Args:
            session_id: Session identifier.

        Returns:
            Entries for that session.
        """
        return [e for e in self.entries if e.session_id == session_id]

    def get_by_task(self, task: str) -> list[ProgressEntry]:
        """Get entries for a specific task.

        Args:
            task: Task identifier.

        Returns:
            Entries for that task.
        """
        return [e for e in self.entries if e.task == task]

    def get_recent(self, limit: int = 10) -> list[ProgressEntry]:
        """Get most recent entries.

        Args:
            limit: Maximum number of entries.

        Returns:
            Most recent entries.
        """
        sorted_entries = sorted(
            self.entries,
            key=lambda e: e.timestamp or "",
            reverse=True,
        )
        return sorted_entries[:limit]

    def get_failures(self, limit: Optional[int] = None) -> list[ProgressEntry]:
        """Get failed entries.

        Args:
            limit: Maximum number of entries.

        Returns:
            Failed entries.
        """
        failures = [e for e in self.entries if e.outcome == Outcome.FAILURE]
        # Sort by timestamp descending
        failures.sort(key=lambda e: e.timestamp or "", reverse=True)
        if limit:
            return failures[:limit]
        return failures

    def get_successes(self, limit: Optional[int] = None) -> list[ProgressEntry]:
        """Get successful entries.

        Args:
            limit: Maximum number of entries.

        Returns:
            Successful entries.
        """
        successes = [e for e in self.entries if e.outcome == Outcome.SUCCESS]
        successes.sort(key=lambda e: e.timestamp or "", reverse=True)
        if limit:
            return successes[:limit]
        return successes

    def search(self, query: str) -> list[ProgressEntry]:
        """Search entries by content.

        Searches learnings, errors, and tags.

        Args:
            query: Search query (case-insensitive).

        Returns:
            Matching entries.
        """
        query_lower = query.lower()
        results = []
        for entry in self.entries:
            # Search in learnings
            if any(query_lower in l.lower() for l in entry.learnings):
                results.append(entry)
                continue
            # Search in errors
            if any(query_lower in e.lower() for e in entry.errors):
                results.append(entry)
                continue
            # Search in tags
            if any(query_lower in t.lower() for t in entry.tags):
                results.append(entry)
                continue
            # Search in task
            if entry.task and query_lower in entry.task.lower():
                results.append(entry)
                continue
        return results

    def get_all_learnings(self) -> list[str]:
        """Get all learnings from all entries.

        Returns:
            All unique learnings.
        """
        learnings = set()
        for entry in self.entries:
            learnings.update(entry.learnings)
        return list(learnings)

    def get_all_errors(self) -> list[str]:
        """Get all errors from all entries.

        Returns:
            All unique errors.
        """
        errors = set()
        for entry in self.entries:
            errors.update(entry.errors)
        return list(errors)

    def summarize(self) -> dict[str, Any]:
        """Get summary statistics.

        Returns:
            Summary statistics.
        """
        total = len(self.entries)
        successes = len([e for e in self.entries if e.is_success])
        failures = len([e for e in self.entries if e.outcome == Outcome.FAILURE])

        # Calculate average duration
        durations = [e.duration_seconds for e in self.entries if e.duration_seconds]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total_entries": total,
            "successes": successes,
            "failures": failures,
            "success_rate": successes / total if total > 0 else 0,
            "avg_duration_seconds": avg_duration,
            "total_learnings": sum(len(e.learnings) for e in self.entries),
            "total_errors": sum(len(e.errors) for e in self.entries),
        }

    def __len__(self) -> int:
        """Get number of entries."""
        return len(self.entries)

    def to_yaml(self) -> str:
        """Convert to YAML format.

        Returns:
            YAML string.
        """
        data = {
            "version": self.version,
            "entries": [e.to_dict() for e in self.entries],
        }
        if HAS_YAML:
            return yaml.dump(data, default_flow_style=False, sort_keys=False)
        else:
            # Fallback to JSON with nice formatting
            return json.dumps(data, indent=2)

    @classmethod
    def from_yaml(cls, content: str) -> ProgressStore:
        """Parse from YAML content.

        Args:
            content: YAML string.

        Returns:
            ProgressStore instance.
        """
        try:
            if HAS_YAML:
                data = yaml.safe_load(content)
            else:
                data = json.loads(content)
        except Exception as e:
            logger.warning(f"Failed to parse progress content: {e}")
            return cls()

        if not data or not isinstance(data, dict):
            return cls()

        store = cls(version=data.get("version", "1.0"))
        for entry_data in data.get("entries", []):
            store.add(ProgressEntry.from_dict(entry_data))
        return store

    def to_json(self) -> str:
        """Convert to JSON format.

        Returns:
            JSON string.
        """
        data = {
            "version": self.version,
            "entries": [e.to_dict() for e in self.entries],
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, content: str) -> ProgressStore:
        """Parse from JSON content.

        Args:
            content: JSON string.

        Returns:
            ProgressStore instance.
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse progress JSON: {e}")
            return cls()

        store = cls(version=data.get("version", "1.0"))
        for entry_data in data.get("entries", []):
            store.add(ProgressEntry.from_dict(entry_data))
        return store


def get_progress_path(project_root: Optional[Path] = None) -> Path:
    """Get the path to progress.yaml file.

    Args:
        project_root: Project root directory. Uses CWD if None.

    Returns:
        Path to .ralph/progress.yaml
    """
    if project_root is None:
        project_root = Path.cwd()
    return project_root / ".ralph" / "progress.yaml"


def load_progress(path: Optional[Path] = None) -> ProgressStore:
    """Load progress from file.

    Args:
        path: Path to progress file. Uses default if None.

    Returns:
        ProgressStore instance (empty if file doesn't exist).
    """
    if path is None:
        path = get_progress_path()

    if not path.exists():
        logger.debug(f"Progress file not found: {path}")
        return ProgressStore()

    try:
        content = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            store = ProgressStore.from_json(content)
        else:
            store = ProgressStore.from_yaml(content)
        logger.debug(f"Loaded {len(store)} progress entries from {path}")
        return store
    except Exception as e:
        logger.warning(f"Failed to load progress: {e}")
        return ProgressStore()


def save_progress(store: ProgressStore, path: Optional[Path] = None) -> None:
    """Save progress to file.

    Args:
        store: Progress store to save.
        path: Path to save to. Uses default if None.
    """
    if path is None:
        path = get_progress_path()

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix == ".json":
        content = store.to_json()
    else:
        content = store.to_yaml()

    path.write_text(content, encoding="utf-8")
    logger.debug(f"Saved {len(store)} progress entries to {path}")


def generate_session_id() -> str:
    """Generate a unique session ID.

    Returns:
        Session ID in format: ralph-YYYY-MM-DD-NNN
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    # Add a unique suffix based on time
    time_suffix = datetime.now().strftime("%H%M%S")
    return f"ralph-{date_str}-{time_suffix}"


def inject_progress(
    store: ProgressStore,
    prompt: str,
    max_entries: int = 10,
    include_learnings: bool = True,
    include_errors: bool = True,
) -> str:
    """Inject progress context into a system prompt.

    Args:
        store: Progress store.
        prompt: Base system prompt.
        max_entries: Maximum number of entries to include.
        include_learnings: Include learnings section.
        include_errors: Include errors section.

    Returns:
        Prompt with progress context injected.
    """
    if len(store) == 0:
        return prompt

    lines = ["\n\n## Progress Context\n"]
    lines.append("Recent learnings and outcomes from previous iterations:\n")

    # Get recent entries
    recent = store.get_recent(max_entries)

    if include_learnings:
        # Collect unique learnings from recent entries
        all_learnings = []
        for entry in recent:
            for learning in entry.learnings:
                if learning not in all_learnings:
                    all_learnings.append(learning)

        if all_learnings:
            lines.append("\n### What Worked")
            for learning in all_learnings[:10]:
                lines.append(f"- {learning}")

    if include_errors:
        # Get recent failures
        failures = store.get_failures(5)
        if failures:
            lines.append("\n### Recent Issues")
            for entry in failures:
                for error in entry.errors:
                    lines.append(f"- [{entry.task or 'unknown'}] {error}")

    # Add summary
    summary = store.summarize()
    if summary["total_entries"] > 0:
        lines.append("\n### Summary")
        lines.append(
            f"- Success rate: {summary['success_rate']:.0%} "
            f"({summary['successes']}/{summary['total_entries']})"
        )

    progress_section = "\n".join(lines)
    return prompt + progress_section
