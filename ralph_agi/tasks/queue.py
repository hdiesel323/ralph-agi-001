"""Task Queue System for RALPH-AGI.

Enables the "sip coffee" workflow by providing a file-based task queue
that RALPH processes autonomously. Tasks are defined as YAML files in
`.ralph/tasks/` and progress through a lifecycle: pending → running →
complete/failed.

Usage:
    from ralph_agi.tasks.queue import TaskQueue, QueuedTask

    # Initialize queue
    queue = TaskQueue()

    # Add a task
    task = queue.add("Add dark mode toggle to settings page", priority="P1")

    # List pending tasks
    for task in queue.list(status="pending"):
        print(f"{task.id}: {task.description}")

    # Get next task to process
    next_task = queue.next()

    # Update task status
    queue.update_status(task.id, "running")
    queue.update_status(task.id, "complete", pr_url="https://github.com/...")
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import yaml

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task lifecycle status."""

    PENDING = "pending"
    PENDING_APPROVAL = "pending_approval"  # Awaiting human approval to start
    READY = "ready"  # Ready to run (dependencies met)
    RUNNING = "running"
    PENDING_MERGE = "pending_merge"  # Awaiting human approval to merge
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""

    P0 = 0  # Critical
    P1 = 1  # High
    P2 = 2  # Medium (default)
    P3 = 3  # Low
    P4 = 4  # Backlog

    @classmethod
    def from_string(cls, s: str) -> "TaskPriority":
        """Parse priority from string like 'P1' or '1'."""
        s = s.upper().strip()
        if s.startswith("P"):
            s = s[1:]
        try:
            return cls(int(s))
        except (ValueError, KeyError):
            return cls.P2  # Default to medium


class QueueError(Exception):
    """Base exception for queue operations."""

    pass


class TaskNotFoundError(QueueError):
    """Raised when a task is not found."""

    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f"Task not found: {task_id}")


class TaskValidationError(QueueError):
    """Raised when task validation fails."""

    pass


@dataclass
class ExecutionLog:
    """A single log entry from task execution."""

    timestamp: str
    level: str  # info, warn, error
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"timestamp": self.timestamp, "level": self.level, "message": self.message}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionLog":
        return cls(
            timestamp=data.get("timestamp", ""),
            level=data.get("level", "info"),
            message=data.get("message", ""),
        )


@dataclass
class TaskArtifact:
    """A file artifact produced by task execution."""

    path: str  # Relative path
    absolute_path: str | None = None
    file_type: str | None = None  # Extension
    size: int | None = None  # Bytes
    content: str | None = None  # Optional inline content (for small files)

    def to_dict(self) -> dict[str, Any]:
        data = {"path": self.path}
        if self.absolute_path:
            data["absolute_path"] = self.absolute_path
        if self.file_type:
            data["file_type"] = self.file_type
        if self.size is not None:
            data["size"] = self.size
        if self.content:
            data["content"] = self.content
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskArtifact":
        return cls(
            path=data.get("path", ""),
            absolute_path=data.get("absolute_path"),
            file_type=data.get("file_type"),
            size=data.get("size"),
            content=data.get("content"),
        )


@dataclass
class TaskOutput:
    """Output from task execution including results, logs, and artifacts."""

    summary: str | None = None  # Brief summary of what was done
    text: str | None = None  # Primary text output
    markdown: str | None = None  # Markdown formatted output
    artifacts: list[TaskArtifact] = field(default_factory=list)
    logs: list[ExecutionLog] = field(default_factory=list)
    tokens_used: int | None = None
    api_calls: int | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.summary:
            data["summary"] = self.summary
        if self.text:
            data["text"] = self.text
        if self.markdown:
            data["markdown"] = self.markdown
        if self.artifacts:
            data["artifacts"] = [a.to_dict() for a in self.artifacts]
        if self.logs:
            data["logs"] = [log.to_dict() for log in self.logs]
        if self.tokens_used is not None:
            data["tokens_used"] = self.tokens_used
        if self.api_calls is not None:
            data["api_calls"] = self.api_calls
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskOutput":
        return cls(
            summary=data.get("summary"),
            text=data.get("text"),
            markdown=data.get("markdown"),
            artifacts=[TaskArtifact.from_dict(a) for a in data.get("artifacts", [])],
            logs=[ExecutionLog.from_dict(log) for log in data.get("logs", [])],
            tokens_used=data.get("tokens_used"),
            api_calls=data.get("api_calls"),
        )


@dataclass
class QueuedTask:
    """A task in the queue.

    Attributes:
        id: Unique task identifier (auto-generated from description)
        description: What the task should accomplish
        priority: Task priority (P0-P4)
        status: Current lifecycle status
        acceptance_criteria: List of criteria for completion
        dependencies: List of task IDs this task depends on
        created_at: When the task was created
        updated_at: When the task was last updated
        started_at: When the task started running
        completed_at: When the task completed
        worktree_path: Path to worktree (when running)
        branch: Git branch name (when running/complete)
        pr_url: Pull request URL (when complete)
        pr_number: Pull request number (when complete)
        confidence: Confidence score from evaluation (0.0-1.0)
        error: Error message (if failed)
        output: Task execution output (results, logs, artifacts)
        metadata: Additional key-value data
    """

    id: str
    description: str
    priority: TaskPriority = TaskPriority.P2
    status: TaskStatus = TaskStatus.PENDING
    acceptance_criteria: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    worktree_path: str | None = None
    branch: str | None = None
    pr_url: str | None = None
    pr_number: int | None = None
    confidence: float | None = None
    error: str | None = None
    output: TaskOutput | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    # Iteration tracking
    current_iteration: int = 0
    max_iterations: int = 10

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueuedTask":
        """Create task from dictionary (YAML data)."""
        # Parse priority
        priority_str = data.get("priority", "P2")
        if isinstance(priority_str, int):
            priority = TaskPriority(priority_str)
        else:
            priority = TaskPriority.from_string(str(priority_str))

        # Parse status
        status_str = data.get("status", "pending")
        try:
            status = TaskStatus(status_str)
        except ValueError:
            status = TaskStatus.PENDING

        # Parse datetimes
        def parse_datetime(val: Any) -> datetime | None:
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            if isinstance(val, str):
                try:
                    return datetime.fromisoformat(val.replace("Z", "+00:00"))
                except ValueError:
                    return None
            return None

        # Parse output
        output_data = data.get("output")
        output = TaskOutput.from_dict(output_data) if output_data else None

        return cls(
            id=data["id"],
            description=data["description"],
            priority=priority,
            status=status,
            acceptance_criteria=data.get("acceptance_criteria", []),
            dependencies=data.get("dependencies", []),
            created_at=parse_datetime(data.get("created_at")) or datetime.now(timezone.utc),
            updated_at=parse_datetime(data.get("updated_at")) or datetime.now(timezone.utc),
            started_at=parse_datetime(data.get("started_at")),
            completed_at=parse_datetime(data.get("completed_at")),
            worktree_path=data.get("worktree_path"),
            branch=data.get("branch"),
            pr_url=data.get("pr_url"),
            pr_number=data.get("pr_number"),
            confidence=data.get("confidence"),
            error=data.get("error"),
            output=output,
            metadata=data.get("metadata", {}),
            current_iteration=data.get("current_iteration", 0),
            max_iterations=data.get("max_iterations", 10),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        data = {
            "id": self.id,
            "description": self.description,
            "priority": f"P{self.priority.value}",
            "status": self.status.value,
        }

        # Only include non-empty optional fields
        if self.acceptance_criteria:
            data["acceptance_criteria"] = self.acceptance_criteria
        if self.dependencies:
            data["dependencies"] = self.dependencies
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            data["updated_at"] = self.updated_at.isoformat()
        if self.started_at:
            data["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        if self.worktree_path:
            data["worktree_path"] = self.worktree_path
        if self.branch:
            data["branch"] = self.branch
        if self.pr_url:
            data["pr_url"] = self.pr_url
        if self.pr_number:
            data["pr_number"] = self.pr_number
        if self.confidence is not None:
            data["confidence"] = self.confidence
        if self.error:
            data["error"] = self.error
        if self.output:
            data["output"] = self.output.to_dict()
        if self.metadata:
            data["metadata"] = self.metadata
        # Always include iteration tracking
        data["current_iteration"] = self.current_iteration
        data["max_iterations"] = self.max_iterations

        return data

    @property
    def is_actionable(self) -> bool:
        """Check if task can be picked up for execution."""
        return self.status == TaskStatus.READY

    @property
    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in (TaskStatus.COMPLETE, TaskStatus.FAILED, TaskStatus.CANCELLED)


def generate_task_id(description: str) -> str:
    """Generate a short, unique task ID from description.

    Creates a slug from the first few words plus a short hash
    for uniqueness. Example: "add-dark-mode-a1b2c3"
    """
    # Clean and slugify
    slug = description.lower()
    slug = re.sub(r"[^a-z0-9\s]", "", slug)
    words = slug.split()[:4]  # First 4 words
    slug = "-".join(words)

    # Add short hash for uniqueness
    hash_input = f"{description}{time.time()}"
    short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:6]

    return f"{slug}-{short_hash}"


class TaskQueue:
    """File-based task queue for autonomous processing.

    Tasks are stored as YAML files in `.ralph/tasks/`. Each task file
    contains the complete task definition and is updated in-place as
    the task progresses through its lifecycle.

    The queue supports:
    - Adding tasks via CLI or programmatically
    - Watching for new task files
    - Dependency tracking between tasks
    - Priority-based selection
    - Atomic file updates

    Example:
        queue = TaskQueue(project_root="/path/to/project")

        # Add a task
        task = queue.add("Fix login bug", priority="P1")

        # Get next task to process
        next_task = queue.next()

        # Mark as running
        queue.update_status(next_task.id, "running", worktree_path="/path/to/worktree")

        # Mark as complete
        queue.update_status(next_task.id, "complete", pr_url="https://...")
    """

    TASKS_DIR = ".ralph/tasks"

    def __init__(
        self,
        project_root: str | Path | None = None,
        on_task_added: Callable[[QueuedTask], None] | None = None,
        on_task_updated: Callable[[QueuedTask], None] | None = None,
    ):
        """Initialize task queue.

        Args:
            project_root: Root directory of the project (default: current dir)
            on_task_added: Callback when a new task is added
            on_task_updated: Callback when a task is updated
        """
        self._root = Path(project_root).resolve() if project_root else Path.cwd()
        self._tasks_dir = self._root / self.TASKS_DIR
        self._on_task_added = on_task_added
        self._on_task_updated = on_task_updated

        # Ensure tasks directory exists
        self._tasks_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"TaskQueue initialized: {self._tasks_dir}")

    @property
    def tasks_dir(self) -> Path:
        """Get the tasks directory path."""
        return self._tasks_dir

    def _task_path(self, task_id: str) -> Path:
        """Get file path for a task ID."""
        return self._tasks_dir / f"{task_id}.yaml"

    def _load_task(self, path: Path) -> QueuedTask | None:
        """Load a task from YAML file."""
        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            if not data:
                return None
            return QueuedTask.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load task {path}: {e}")
            return None

    def _save_task(self, task: QueuedTask) -> None:
        """Save a task to YAML file atomically."""
        path = self._task_path(task.id)

        # Write to temp file first
        temp_path = path.with_suffix(".yaml.tmp")

        try:
            # Serialize with nice formatting
            content = yaml.dump(
                task.to_dict(),
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

            # Write atomically
            with open(temp_path, "w") as f:
                f.write(content)

            # Atomic rename
            temp_path.replace(path)

            logger.debug(f"Saved task: {task.id}")

        except Exception as e:
            # Clean up temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            raise QueueError(f"Failed to save task {task.id}: {e}") from e

    def add(
        self,
        description: str,
        priority: str | TaskPriority = "P2",
        acceptance_criteria: list[str] | None = None,
        dependencies: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        task_id: str | None = None,
    ) -> QueuedTask:
        """Add a new task to the queue.

        Args:
            description: What the task should accomplish
            priority: Task priority (P0-P4 or TaskPriority)
            acceptance_criteria: List of criteria for completion
            dependencies: List of task IDs this task depends on
            metadata: Additional key-value data
            task_id: Optional custom task ID (auto-generated if not provided)

        Returns:
            The created QueuedTask

        Raises:
            TaskValidationError: If task is invalid
        """
        # Validate description
        if not description or not description.strip():
            raise TaskValidationError("Task description cannot be empty")

        # Parse priority
        if isinstance(priority, str):
            priority = TaskPriority.from_string(priority)

        # Generate ID
        if task_id is None:
            task_id = generate_task_id(description)

        # Check for duplicates
        if self._task_path(task_id).exists():
            raise TaskValidationError(f"Task already exists: {task_id}")

        # Validate dependencies exist
        if dependencies:
            for dep_id in dependencies:
                if not self._task_path(dep_id).exists():
                    logger.warning(f"Dependency not found: {dep_id}")

        # Create task
        task = QueuedTask(
            id=task_id,
            description=description.strip(),
            priority=priority,
            status=TaskStatus.PENDING,
            acceptance_criteria=acceptance_criteria or [],
            dependencies=dependencies or [],
            metadata=metadata or {},
        )

        # Save to file
        self._save_task(task)

        # Callback
        if self._on_task_added:
            self._on_task_added(task)

        logger.info(f"QUEUE_ADD: {task.id} - {task.description[:50]}")
        return task

    def get(self, task_id: str) -> QueuedTask:
        """Get a task by ID.

        Args:
            task_id: Task identifier

        Returns:
            The QueuedTask

        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        path = self._task_path(task_id)
        task = self._load_task(path)

        if task is None:
            raise TaskNotFoundError(task_id)

        return task

    def list(
        self,
        status: str | TaskStatus | list[str] | None = None,
        priority: str | TaskPriority | None = None,
        include_terminal: bool = False,
    ) -> list[QueuedTask]:
        """List tasks with optional filtering.

        Args:
            status: Filter by status (or list of statuses)
            priority: Filter by priority
            include_terminal: Include completed/failed/cancelled tasks

        Returns:
            List of matching tasks, sorted by priority then creation date
        """
        tasks = []

        # Parse status filter
        status_filter: set[TaskStatus] | None = None
        if status is not None:
            if isinstance(status, str):
                status_filter = {TaskStatus(status)}
            elif isinstance(status, TaskStatus):
                status_filter = {status}
            elif isinstance(status, list):
                status_filter = {TaskStatus(s) if isinstance(s, str) else s for s in status}

        # Parse priority filter
        priority_filter: TaskPriority | None = None
        if priority is not None:
            if isinstance(priority, str):
                priority_filter = TaskPriority.from_string(priority)
            else:
                priority_filter = priority

        # Load all tasks
        for path in self._tasks_dir.glob("*.yaml"):
            if path.suffix == ".tmp":
                continue

            task = self._load_task(path)
            if task is None:
                continue

            # Apply filters
            if status_filter and task.status not in status_filter:
                continue

            if priority_filter and task.priority != priority_filter:
                continue

            if not include_terminal and task.is_terminal:
                continue

            tasks.append(task)

        # Sort by priority (ascending) then creation date (ascending)
        tasks.sort(key=lambda t: (t.priority.value, t.created_at))

        return tasks

    def next(self) -> QueuedTask | None:
        """Get the next task to process.

        Returns the highest priority pending task whose dependencies
        are all complete.

        Returns:
            Next task to process, or None if queue is empty
        """
        pending = self.list(status=["pending", "ready"])

        for task in pending:
            # Check dependencies
            if self._dependencies_met(task):
                return task

        return None

    def _dependencies_met(self, task: QueuedTask) -> bool:
        """Check if all dependencies for a task are complete."""
        if not task.dependencies:
            return True

        for dep_id in task.dependencies:
            try:
                dep_task = self.get(dep_id)
                if dep_task.status != TaskStatus.COMPLETE:
                    return False
            except TaskNotFoundError:
                # Missing dependency - treat as not met
                logger.warning(f"Task {task.id} has missing dependency: {dep_id}")
                return False

        return True

    def update_status(
        self,
        task_id: str,
        status: str | TaskStatus,
        *,
        worktree_path: str | None = None,
        branch: str | None = None,
        pr_url: str | None = None,
        pr_number: int | None = None,
        confidence: float | None = None,
        error: str | None = None,
    ) -> QueuedTask:
        """Update task status and associated fields.

        Args:
            task_id: Task to update
            status: New status
            worktree_path: Path to worktree (for running)
            branch: Git branch name
            pr_url: Pull request URL (for complete)
            pr_number: Pull request number
            confidence: Confidence score (0.0-1.0)
            error: Error message (for failed)

        Returns:
            Updated task

        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        task = self.get(task_id)

        # Parse status
        if isinstance(status, str):
            status = TaskStatus(status)

        # Update fields
        task.status = status
        task.updated_at = datetime.now(timezone.utc)

        if status == TaskStatus.RUNNING:
            task.started_at = datetime.now(timezone.utc)

        if status in (TaskStatus.COMPLETE, TaskStatus.FAILED, TaskStatus.CANCELLED):
            task.completed_at = datetime.now(timezone.utc)

        if worktree_path is not None:
            task.worktree_path = worktree_path
        if branch is not None:
            task.branch = branch
        if pr_url is not None:
            task.pr_url = pr_url
        if pr_number is not None:
            task.pr_number = pr_number
        if confidence is not None:
            task.confidence = confidence
        if error is not None:
            task.error = error

        # Save
        self._save_task(task)

        # Callback
        if self._on_task_updated:
            self._on_task_updated(task)

        logger.info(f"QUEUE_UPDATE: {task.id} -> {status.value}")
        return task

    def remove(self, task_id: str) -> bool:
        """Remove a task from the queue.

        Args:
            task_id: Task to remove

        Returns:
            True if removed, False if not found
        """
        path = self._task_path(task_id)

        if not path.exists():
            return False

        path.unlink()
        logger.info(f"QUEUE_REMOVE: {task_id}")
        return True

    def clear(self, include_running: bool = False) -> int:
        """Clear completed/failed tasks from the queue.

        Args:
            include_running: Also clear running tasks

        Returns:
            Number of tasks removed
        """
        removed = 0

        for path in self._tasks_dir.glob("*.yaml"):
            task = self._load_task(path)
            if task is None:
                continue

            should_remove = task.is_terminal
            if include_running and task.status == TaskStatus.RUNNING:
                should_remove = True

            if should_remove:
                path.unlink()
                removed += 1

        logger.info(f"QUEUE_CLEAR: Removed {removed} tasks")
        return removed

    def stats(self) -> dict[str, int]:
        """Get queue statistics.

        Returns:
            Dict with counts by status
        """
        stats = {status.value: 0 for status in TaskStatus}
        stats["total"] = 0

        for path in self._tasks_dir.glob("*.yaml"):
            task = self._load_task(path)
            if task:
                stats[task.status.value] += 1
                stats["total"] += 1

        return stats

    def watch(
        self,
        callback: Callable[[QueuedTask], None],
        poll_interval: float = 1.0,
    ) -> None:
        """Watch for new tasks in the queue directory.

        This is a blocking call that polls the directory for new files.
        Use in a background thread or with asyncio.

        Args:
            callback: Function to call when new task is detected
            poll_interval: How often to check for new files (seconds)
        """
        seen_files: set[str] = set()

        # Initialize with existing files
        for path in self._tasks_dir.glob("*.yaml"):
            seen_files.add(path.name)

        logger.info(f"Watching for new tasks in {self._tasks_dir}")

        while True:
            try:
                current_files = {p.name for p in self._tasks_dir.glob("*.yaml")}
                new_files = current_files - seen_files

                for filename in new_files:
                    path = self._tasks_dir / filename
                    task = self._load_task(path)
                    if task:
                        logger.info(f"QUEUE_WATCH: New task detected: {task.id}")
                        callback(task)

                seen_files = current_files
                time.sleep(poll_interval)

            except KeyboardInterrupt:
                logger.info("Watch stopped")
                break
            except Exception as e:
                logger.error(f"Watch error: {e}")
                time.sleep(poll_interval)
