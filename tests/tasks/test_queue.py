"""Tests for Task Queue System.

Tests the file-based task queue for autonomous processing.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from pathlib import Path

from ralph_agi.tasks.queue import (
    TaskQueue,
    QueuedTask,
    TaskStatus,
    TaskPriority,
    QueueError,
    TaskNotFoundError,
    TaskValidationError,
    generate_task_id,
)


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_from_string_p_prefix(self):
        """Test parsing priority with P prefix."""
        assert TaskPriority.from_string("P0") == TaskPriority.P0
        assert TaskPriority.from_string("P1") == TaskPriority.P1
        assert TaskPriority.from_string("P2") == TaskPriority.P2
        assert TaskPriority.from_string("P3") == TaskPriority.P3
        assert TaskPriority.from_string("P4") == TaskPriority.P4

    def test_from_string_lowercase(self):
        """Test parsing priority lowercase."""
        assert TaskPriority.from_string("p0") == TaskPriority.P0
        assert TaskPriority.from_string("p1") == TaskPriority.P1

    def test_from_string_number_only(self):
        """Test parsing priority as number only."""
        assert TaskPriority.from_string("0") == TaskPriority.P0
        assert TaskPriority.from_string("2") == TaskPriority.P2

    def test_from_string_invalid_defaults_p2(self):
        """Test invalid priority defaults to P2."""
        assert TaskPriority.from_string("invalid") == TaskPriority.P2
        assert TaskPriority.from_string("P9") == TaskPriority.P2
        assert TaskPriority.from_string("") == TaskPriority.P2


class TestGenerateTaskId:
    """Tests for generate_task_id function."""

    def test_creates_slug_from_description(self):
        """Test ID is created from description words."""
        task_id = generate_task_id("Add dark mode toggle")
        assert task_id.startswith("add-dark-mode-toggle-")

    def test_includes_hash_suffix(self):
        """Test ID includes hash for uniqueness."""
        task_id = generate_task_id("Test task")
        parts = task_id.split("-")
        assert len(parts[-1]) == 6  # 6-char hash

    def test_removes_special_characters(self):
        """Test special characters are removed."""
        task_id = generate_task_id("Fix bug #123 (urgent!)")
        assert "#" not in task_id
        assert "(" not in task_id
        assert "!" not in task_id

    def test_truncates_long_descriptions(self):
        """Test long descriptions are truncated to 4 words."""
        task_id = generate_task_id("This is a very long task description that should be truncated")
        # Should only have first 4 words plus hash
        parts = task_id.rsplit("-", 1)  # Split off hash
        word_count = len(parts[0].split("-"))
        assert word_count <= 4


class TestQueuedTask:
    """Tests for QueuedTask dataclass."""

    def test_from_dict_minimal(self):
        """Test creating task from minimal dict."""
        data = {
            "id": "test-task",
            "description": "Test description",
        }
        task = QueuedTask.from_dict(data)

        assert task.id == "test-task"
        assert task.description == "Test description"
        assert task.priority == TaskPriority.P2  # Default
        assert task.status == TaskStatus.PENDING  # Default

    def test_from_dict_full(self):
        """Test creating task from full dict."""
        data = {
            "id": "test-task",
            "description": "Test description",
            "priority": "P1",
            "status": "running",
            "acceptance_criteria": ["Criterion 1", "Criterion 2"],
            "dependencies": ["dep-1", "dep-2"],
            "pr_url": "https://github.com/test/pr/1",
            "confidence": 0.85,
        }
        task = QueuedTask.from_dict(data)

        assert task.id == "test-task"
        assert task.priority == TaskPriority.P1
        assert task.status == TaskStatus.RUNNING
        assert task.acceptance_criteria == ["Criterion 1", "Criterion 2"]
        assert task.dependencies == ["dep-1", "dep-2"]
        assert task.pr_url == "https://github.com/test/pr/1"
        assert task.confidence == 0.85

    def test_to_dict_roundtrip(self):
        """Test dict serialization roundtrip."""
        original = QueuedTask(
            id="test-task",
            description="Test description",
            priority=TaskPriority.P1,
            status=TaskStatus.RUNNING,
            acceptance_criteria=["Criterion 1"],
            confidence=0.9,
        )

        data = original.to_dict()
        restored = QueuedTask.from_dict(data)

        assert restored.id == original.id
        assert restored.description == original.description
        assert restored.priority == original.priority
        assert restored.status == original.status
        assert restored.acceptance_criteria == original.acceptance_criteria
        assert restored.confidence == original.confidence

    def test_is_actionable(self):
        """Test is_actionable property."""
        pending = QueuedTask(id="1", description="", status=TaskStatus.PENDING)
        ready = QueuedTask(id="2", description="", status=TaskStatus.READY)
        running = QueuedTask(id="3", description="", status=TaskStatus.RUNNING)
        complete = QueuedTask(id="4", description="", status=TaskStatus.COMPLETE)

        assert pending.is_actionable is True
        assert ready.is_actionable is True
        assert running.is_actionable is False
        assert complete.is_actionable is False

    def test_is_terminal(self):
        """Test is_terminal property."""
        pending = QueuedTask(id="1", description="", status=TaskStatus.PENDING)
        running = QueuedTask(id="2", description="", status=TaskStatus.RUNNING)
        complete = QueuedTask(id="3", description="", status=TaskStatus.COMPLETE)
        failed = QueuedTask(id="4", description="", status=TaskStatus.FAILED)

        assert pending.is_terminal is False
        assert running.is_terminal is False
        assert complete.is_terminal is True
        assert failed.is_terminal is True


class TestTaskQueue:
    """Tests for TaskQueue class."""

    @pytest.fixture
    def queue(self, tmp_path):
        """Create a task queue in a temp directory."""
        return TaskQueue(project_root=tmp_path)

    def test_init_creates_tasks_dir(self, tmp_path):
        """Test initialization creates tasks directory."""
        queue = TaskQueue(project_root=tmp_path)
        assert queue.tasks_dir.exists()
        assert queue.tasks_dir == tmp_path / ".ralph/tasks"

    def test_add_creates_task_file(self, queue):
        """Test adding a task creates YAML file."""
        task = queue.add("Add dark mode toggle")

        task_file = queue.tasks_dir / f"{task.id}.yaml"
        assert task_file.exists()

    def test_add_returns_queued_task(self, queue):
        """Test add returns properly populated QueuedTask."""
        task = queue.add(
            "Add dark mode toggle",
            priority="P1",
            acceptance_criteria=["Toggle visible in settings"],
        )

        assert task.description == "Add dark mode toggle"
        assert task.priority == TaskPriority.P1
        assert task.status == TaskStatus.PENDING
        assert task.acceptance_criteria == ["Toggle visible in settings"]

    def test_add_validates_description(self, queue):
        """Test add validates non-empty description."""
        with pytest.raises(TaskValidationError):
            queue.add("")

        with pytest.raises(TaskValidationError):
            queue.add("   ")

    def test_add_prevents_duplicates(self, queue):
        """Test add prevents duplicate task IDs."""
        task = queue.add("Test task", task_id="custom-id")

        with pytest.raises(TaskValidationError):
            queue.add("Another task", task_id="custom-id")

    def test_get_retrieves_task(self, queue):
        """Test get retrieves existing task."""
        created = queue.add("Test task")
        retrieved = queue.get(created.id)

        assert retrieved.id == created.id
        assert retrieved.description == created.description

    def test_get_raises_for_missing_task(self, queue):
        """Test get raises TaskNotFoundError for missing task."""
        with pytest.raises(TaskNotFoundError):
            queue.get("nonexistent-task")

    def test_list_returns_all_pending(self, queue):
        """Test list returns pending tasks by default."""
        queue.add("Task 1")
        queue.add("Task 2")
        task3 = queue.add("Task 3")
        queue.update_status(task3.id, "complete")

        tasks = queue.list()

        assert len(tasks) == 2
        for task in tasks:
            assert task.status == TaskStatus.PENDING

    def test_list_with_status_filter(self, queue):
        """Test list filters by status."""
        task1 = queue.add("Task 1")
        task2 = queue.add("Task 2")
        queue.update_status(task1.id, "running")

        pending = queue.list(status="pending")
        running = queue.list(status="running")

        assert len(pending) == 1
        assert pending[0].id == task2.id
        assert len(running) == 1
        assert running[0].id == task1.id

    def test_list_sorted_by_priority(self, queue):
        """Test list returns tasks sorted by priority."""
        queue.add("Low priority", priority="P3")
        queue.add("High priority", priority="P0")
        queue.add("Medium priority", priority="P2")

        tasks = queue.list()

        assert tasks[0].priority == TaskPriority.P0
        assert tasks[1].priority == TaskPriority.P2
        assert tasks[2].priority == TaskPriority.P3

    def test_next_returns_highest_priority(self, queue):
        """Test next returns highest priority task."""
        queue.add("Low priority", priority="P3")
        high = queue.add("High priority", priority="P0")
        queue.add("Medium priority", priority="P2")

        next_task = queue.next()

        assert next_task.id == high.id

    def test_next_respects_dependencies(self, queue):
        """Test next skips tasks with incomplete dependencies."""
        dep = queue.add("Dependency task", priority="P2")
        blocked = queue.add("Blocked task", priority="P0", dependencies=[dep.id])
        unblocked = queue.add("Unblocked task", priority="P1")

        next_task = queue.next()

        # Should return P1 task, not P0 (which is blocked)
        assert next_task.id == unblocked.id

    def test_next_returns_none_when_empty(self, queue):
        """Test next returns None for empty queue."""
        next_task = queue.next()
        assert next_task is None

    def test_update_status_changes_status(self, queue):
        """Test update_status changes task status."""
        task = queue.add("Test task")
        updated = queue.update_status(task.id, "running")

        assert updated.status == TaskStatus.RUNNING

        # Verify persisted
        reloaded = queue.get(task.id)
        assert reloaded.status == TaskStatus.RUNNING

    def test_update_status_sets_timestamps(self, queue):
        """Test update_status sets appropriate timestamps."""
        task = queue.add("Test task")

        # Running sets started_at
        running = queue.update_status(task.id, "running")
        assert running.started_at is not None

        # Complete sets completed_at
        complete = queue.update_status(task.id, "complete")
        assert complete.completed_at is not None

    def test_update_status_sets_optional_fields(self, queue):
        """Test update_status sets optional fields."""
        task = queue.add("Test task")
        updated = queue.update_status(
            task.id,
            "complete",
            pr_url="https://github.com/test/pr/1",
            pr_number=123,
            confidence=0.95,
        )

        assert updated.pr_url == "https://github.com/test/pr/1"
        assert updated.pr_number == 123
        assert updated.confidence == 0.95

    def test_remove_deletes_task_file(self, queue):
        """Test remove deletes the task file."""
        task = queue.add("Test task")
        task_file = queue.tasks_dir / f"{task.id}.yaml"

        assert task_file.exists()

        result = queue.remove(task.id)

        assert result is True
        assert not task_file.exists()

    def test_remove_returns_false_for_missing(self, queue):
        """Test remove returns False for missing task."""
        result = queue.remove("nonexistent")
        assert result is False

    def test_clear_removes_terminal_tasks(self, queue):
        """Test clear removes completed/failed tasks."""
        task1 = queue.add("Task 1")
        task2 = queue.add("Task 2")
        queue.update_status(task1.id, "complete")
        queue.update_status(task2.id, "running")

        removed = queue.clear()

        assert removed == 1  # Only task1 (complete)

        tasks = queue.list(include_terminal=True)
        assert len(tasks) == 1
        assert tasks[0].id == task2.id

    def test_stats_returns_counts(self, queue):
        """Test stats returns correct counts."""
        task1 = queue.add("Task 1")
        task2 = queue.add("Task 2")
        task3 = queue.add("Task 3")
        queue.update_status(task1.id, "running")
        queue.update_status(task2.id, "complete")

        stats = queue.stats()

        assert stats["total"] == 3
        assert stats["pending"] == 1
        assert stats["running"] == 1
        assert stats["complete"] == 1


class TestTaskQueueCallbacks:
    """Tests for TaskQueue callbacks."""

    def test_on_task_added_callback(self, tmp_path):
        """Test on_task_added callback is called."""
        added_tasks = []

        def on_added(task):
            added_tasks.append(task)

        queue = TaskQueue(project_root=tmp_path, on_task_added=on_added)
        task = queue.add("Test task")

        assert len(added_tasks) == 1
        assert added_tasks[0].id == task.id

    def test_on_task_updated_callback(self, tmp_path):
        """Test on_task_updated callback is called."""
        updated_tasks = []

        def on_updated(task):
            updated_tasks.append(task)

        queue = TaskQueue(project_root=tmp_path, on_task_updated=on_updated)
        task = queue.add("Test task")
        queue.update_status(task.id, "running")

        assert len(updated_tasks) == 1
        assert updated_tasks[0].status == TaskStatus.RUNNING
