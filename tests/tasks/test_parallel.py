"""Tests for Parallel Task Executor.

Tests the parallel execution system using worktrees.
"""

from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from ralph_agi.tasks.parallel import (
    ParallelExecutor,
    TaskResult,
    ExecutionProgress,
    ExecutionState,
    create_executor,
)
from ralph_agi.tasks.queue import TaskQueue, QueuedTask, TaskStatus, TaskPriority


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_success_result(self):
        """Test successful task result."""
        result = TaskResult(
            task_id="test-task",
            success=True,
            worktree_path=Path("/tmp/worktree"),
            branch="ralph/test-task",
            started_at=datetime(2026, 1, 17, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2026, 1, 17, 10, 5, 0, tzinfo=timezone.utc),
            confidence=0.85,
        )

        assert result.success is True
        assert result.task_id == "test-task"
        assert result.duration_seconds == 300.0  # 5 minutes
        assert result.error is None

    def test_failed_result(self):
        """Test failed task result."""
        result = TaskResult(
            task_id="test-task",
            success=False,
            error="Task execution failed",
            started_at=datetime(2026, 1, 17, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2026, 1, 17, 10, 1, 0, tzinfo=timezone.utc),
        )

        assert result.success is False
        assert result.error == "Task execution failed"
        assert result.duration_seconds == 60.0

    def test_duration_none_when_missing_times(self):
        """Test duration is None when times not set."""
        result = TaskResult(task_id="test", success=True)
        assert result.duration_seconds is None


class TestExecutionProgress:
    """Tests for ExecutionProgress dataclass."""

    def test_initial_progress(self):
        """Test initial empty progress."""
        progress = ExecutionProgress()

        assert progress.total_tasks == 0
        assert progress.completed == 0
        assert progress.failed == 0
        assert progress.running == 0
        assert progress.pending == 0
        assert progress.success_rate == 0.0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        progress = ExecutionProgress(
            total_tasks=10,
            completed=8,
            failed=2,
        )

        assert progress.success_rate == 80.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        progress = ExecutionProgress(
            total_tasks=5,
            completed=3,
            failed=1,
            running=1,
            pending=0,
        )

        data = progress.to_dict()

        assert data["total_tasks"] == 5
        assert data["completed"] == 3
        assert data["failed"] == 1
        assert data["running"] == 1
        assert "success_rate" in data


class TestParallelExecutor:
    """Tests for ParallelExecutor class."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create executor with mocked dependencies."""
        with patch('ralph_agi.tasks.parallel.TaskQueue') as mock_queue_class, \
             patch('ralph_agi.tasks.parallel.WorktreeManager') as mock_wt_class:
            mock_queue = MagicMock()
            mock_wt = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_wt_class.return_value = mock_wt

            executor = ParallelExecutor(
                project_root=tmp_path,
                max_concurrent=3,
            )

            # Store mocks for test access
            executor._mock_queue = mock_queue
            executor._mock_worktree = mock_wt

            return executor

    def test_init_sets_defaults(self, tmp_path):
        """Test initialization sets default values."""
        with patch('ralph_agi.tasks.parallel.TaskQueue'), \
             patch('ralph_agi.tasks.parallel.WorktreeManager'):
            executor = ParallelExecutor(project_root=tmp_path)

            assert executor.max_concurrent == 3
            assert executor.state == ExecutionState.IDLE

    def test_max_concurrent_validation(self, executor):
        """Test max_concurrent setter validation."""
        executor.max_concurrent = 5
        assert executor.max_concurrent == 5

        with pytest.raises(ValueError):
            executor.max_concurrent = 0

    def test_get_status(self, executor):
        """Test get_status returns correct info."""
        status = executor.get_status()

        assert status["state"] == "idle"
        assert status["max_concurrent"] == 3
        assert "progress" in status
        assert "worktree_stats" in status
        assert "queue_stats" in status

    def test_get_ready_tasks_no_dependencies(self, executor):
        """Test _get_ready_tasks returns tasks without dependencies."""
        task1 = QueuedTask(id="task-1", description="Task 1")
        task2 = QueuedTask(id="task-2", description="Task 2")

        executor._mock_queue.list.return_value = [task1, task2]
        executor._queue = executor._mock_queue

        ready = executor._get_ready_tasks()

        assert len(ready) == 2
        assert task1 in ready
        assert task2 in ready

    def test_get_ready_tasks_respects_dependencies(self, executor):
        """Test _get_ready_tasks respects dependencies."""
        task1 = QueuedTask(id="task-1", description="Task 1")
        task2 = QueuedTask(id="task-2", description="Task 2", dependencies=["task-1"])

        executor._mock_queue.list.return_value = [task1, task2]

        # task-1 is pending, so task-2 should be blocked
        def mock_get(task_id):
            if task_id == "task-1":
                return QueuedTask(id="task-1", description="Task 1", status=TaskStatus.PENDING)
            raise Exception("Not found")

        executor._mock_queue.get = mock_get
        executor._queue = executor._mock_queue

        ready = executor._get_ready_tasks()

        assert len(ready) == 1
        assert task1 in ready
        assert task2 not in ready

    def test_get_ready_tasks_allows_completed_dependencies(self, executor):
        """Test _get_ready_tasks allows tasks with completed dependencies."""
        task1 = QueuedTask(id="task-1", description="Task 1")
        task2 = QueuedTask(id="task-2", description="Task 2", dependencies=["task-1"])

        executor._mock_queue.list.return_value = [task1, task2]

        # task-1 is complete, so task-2 should be ready
        def mock_get(task_id):
            if task_id == "task-1":
                return QueuedTask(id="task-1", description="Task 1", status=TaskStatus.COMPLETE)
            raise Exception("Not found")

        executor._mock_queue.get = mock_get
        executor._queue = executor._mock_queue

        ready = executor._get_ready_tasks()

        assert len(ready) == 2


class TestParallelExecutorCallbacks:
    """Tests for ParallelExecutor callbacks."""

    @pytest.fixture
    def executor_with_callbacks(self, tmp_path):
        """Create executor with callback tracking."""
        started_tasks = []
        completed_results = []
        progress_updates = []

        with patch('ralph_agi.tasks.parallel.TaskQueue') as mock_queue_class, \
             patch('ralph_agi.tasks.parallel.WorktreeManager') as mock_wt_class:
            mock_queue = MagicMock()
            mock_wt = MagicMock()
            mock_queue_class.return_value = mock_queue
            mock_wt_class.return_value = mock_wt

            executor = ParallelExecutor(
                project_root=tmp_path,
                on_task_start=lambda t: started_tasks.append(t),
                on_task_complete=lambda r: completed_results.append(r),
                on_progress=lambda p: progress_updates.append(p),
            )

            executor._mock_queue = mock_queue
            executor._mock_worktree = mock_wt
            executor._started_tasks = started_tasks
            executor._completed_results = completed_results
            executor._progress_updates = progress_updates

            return executor

    def test_callbacks_are_stored(self, executor_with_callbacks):
        """Test callbacks are properly stored."""
        assert executor_with_callbacks._on_task_start is not None
        assert executor_with_callbacks._on_task_complete is not None
        assert executor_with_callbacks._on_progress is not None


class TestCreateExecutor:
    """Tests for create_executor factory function."""

    def test_creates_executor(self, tmp_path):
        """Test factory creates executor with defaults."""
        with patch('ralph_agi.tasks.parallel.TaskQueue'), \
             patch('ralph_agi.tasks.parallel.WorktreeManager'):
            executor = create_executor(project_root=tmp_path)

            assert isinstance(executor, ParallelExecutor)
            assert executor.max_concurrent == 3

    def test_creates_executor_with_custom_concurrency(self, tmp_path):
        """Test factory respects custom concurrency."""
        with patch('ralph_agi.tasks.parallel.TaskQueue'), \
             patch('ralph_agi.tasks.parallel.WorktreeManager'):
            executor = create_executor(project_root=tmp_path, max_concurrent=5)

            assert executor.max_concurrent == 5
