"""Story grid widget for displaying task status."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class TaskInfo:
    """Information about a task."""

    id: str
    name: str
    status: TaskStatus
    progress: float = 0.0  # 0-100

    @property
    def status_icon(self) -> str:
        """Get status icon."""
        icons = {
            TaskStatus.PENDING: "○",
            TaskStatus.RUNNING: "▶",
            TaskStatus.DONE: "●",
            TaskStatus.FAILED: "✗",
            TaskStatus.BLOCKED: "⊘",
        }
        return icons.get(self.status, "?")

    @property
    def status_label(self) -> str:
        """Get status label."""
        labels = {
            TaskStatus.PENDING: "PENDING",
            TaskStatus.RUNNING: "RUNNING",
            TaskStatus.DONE: "DONE ✓",
            TaskStatus.FAILED: "FAILED",
            TaskStatus.BLOCKED: "BLOCKED",
        }
        return labels.get(self.status, "UNKNOWN")


class TaskRow(Static):
    """A single task row in the grid."""

    DEFAULT_CSS = """
    TaskRow {
        height: 1;
        padding: 0 1;
    }
    TaskRow.pending {
        color: $text-muted;
    }
    TaskRow.running {
        color: $warning;
        text-style: bold;
    }
    TaskRow.done {
        color: $success;
    }
    TaskRow.failed {
        color: $error;
        text-style: bold;
    }
    TaskRow.blocked {
        color: $text-disabled;
    }
    """

    def __init__(self, task: TaskInfo) -> None:
        """Initialize a task row.

        Args:
            task: Task information.
        """
        self._task_info = task

        # Format: ● 2.1 PRD Parser              DONE ✓
        icon = task.status_icon
        name = f"{task.id} {task.name}"[:30].ljust(30)
        status = task.status_label.rjust(10)

        content = f"{icon} {name} {status}"
        super().__init__(content, classes=task.status.value)

    @property
    def task(self) -> TaskInfo:
        """Get the task info."""
        return self._task_info

    def update_task(self, task: TaskInfo) -> None:
        """Update the task information.

        Args:
            task: New task information.
        """
        self._task_info = task
        icon = task.status_icon
        name = f"{task.id} {task.name}"[:30].ljust(30)
        status = task.status_label.rjust(10)

        self.update(f"{icon} {name} {status}")
        self.set_classes(task.status.value)


class StoryGrid(VerticalScroll):
    """Grid displaying task/story status."""

    DEFAULT_CSS = """
    StoryGrid {
        border: solid $primary;
        height: 100%;
        min-height: 8;
    }
    StoryGrid > .grid-title {
        dock: top;
        background: $primary;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    """

    TITLE: ClassVar[str] = "Stories"

    def __init__(self, title: str = "Stories", **kwargs) -> None:
        """Initialize the story grid.

        Args:
            title: Panel title.
            **kwargs: Additional arguments for VerticalScroll.
        """
        super().__init__(**kwargs)
        self._title = title
        self._tasks: dict[str, TaskRow] = {}

    def compose(self) -> ComposeResult:
        """Compose the grid layout."""
        yield Static(f" {self._title} ", classes="grid-title")

    def add_task(self, task: TaskInfo) -> None:
        """Add or update a task in the grid.

        Args:
            task: Task information.
        """
        if task.id in self._tasks:
            self._tasks[task.id].update_task(task)
        else:
            row = TaskRow(task)
            self._tasks[task.id] = row
            self.mount(row)

    def update_task(self, task_id: str, status: TaskStatus, progress: float = 0.0) -> None:
        """Update a task's status.

        Args:
            task_id: ID of the task.
            status: New status.
            progress: Progress percentage (0-100).
        """
        if task_id in self._tasks:
            task = self._tasks[task_id].task
            task.status = status
            task.progress = progress
            self._tasks[task_id].update_task(task)

    def set_tasks(self, tasks: list[TaskInfo]) -> None:
        """Set all tasks at once.

        Args:
            tasks: List of task information.
        """
        # Clear existing
        for row in self._tasks.values():
            row.remove()
        self._tasks.clear()

        # Add new tasks
        for task in tasks:
            self.add_task(task)

    def get_task(self, task_id: str) -> TaskInfo | None:
        """Get task information by ID.

        Args:
            task_id: ID of the task.

        Returns:
            Task info or None if not found.
        """
        if task_id in self._tasks:
            return self._tasks[task_id].task
        return None

    @property
    def task_count(self) -> int:
        """Get total task count."""
        return len(self._tasks)

    @property
    def completed_count(self) -> int:
        """Get count of completed tasks."""
        return sum(1 for row in self._tasks.values() if row.task.status == TaskStatus.DONE)

    @property
    def progress_percent(self) -> float:
        """Get overall progress percentage."""
        if not self._tasks:
            return 0.0
        return (self.completed_count / self.task_count) * 100
