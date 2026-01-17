"""Tests for batch processing."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ralph_agi.tasks.batch import (
    DEFAULT_PARALLEL_LIMIT,
    BatchConfig,
    BatchExecutor,
    BatchProgress,
    WorkerProgress,
    WorkerStatus,
    format_batch_progress,
)


class TestWorkerStatus:
    """Tests for WorkerStatus enum."""

    def test_all_statuses(self):
        """Test all status values exist."""
        assert WorkerStatus.PENDING.value == "pending"
        assert WorkerStatus.STARTING.value == "starting"
        assert WorkerStatus.RUNNING.value == "running"
        assert WorkerStatus.COMPLETED.value == "completed"
        assert WorkerStatus.FAILED.value == "failed"
        assert WorkerStatus.CANCELLED.value == "cancelled"


class TestBatchConfig:
    """Tests for BatchConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = BatchConfig()
        assert config.parallel_limit == DEFAULT_PARALLEL_LIMIT
        assert config.worktree_base is None
        assert config.progress_dir is None
        assert config.cleanup_on_complete is True
        assert config.cleanup_on_failure is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = BatchConfig(
            parallel_limit=5,
            worktree_base=Path("/tmp/worktrees"),
            cleanup_on_complete=False,
            cleanup_on_failure=True,
        )
        assert config.parallel_limit == 5
        assert config.worktree_base == Path("/tmp/worktrees")
        assert config.cleanup_on_complete is False
        assert config.cleanup_on_failure is True


class TestWorkerProgress:
    """Tests for WorkerProgress."""

    def test_basic_progress(self):
        """Test basic worker progress."""
        progress = WorkerProgress(
            task_id="task-1",
            worker_id="batch-task-1",
        )
        assert progress.task_id == "task-1"
        assert progress.worker_id == "batch-task-1"
        assert progress.status == WorkerStatus.PENDING
        assert progress.iteration == 0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        progress = WorkerProgress(
            task_id="task-1",
            worker_id="batch-task-1",
            status=WorkerStatus.RUNNING,
            iteration=5,
            max_iterations=100,
        )
        data = progress.to_dict()

        assert data["task_id"] == "task-1"
        assert data["worker_id"] == "batch-task-1"
        assert data["status"] == "running"
        assert data["iteration"] == 5
        assert data["max_iterations"] == 100

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "task_id": "task-1",
            "worker_id": "batch-task-1",
            "status": "completed",
            "iteration": 10,
            "max_iterations": 100,
            "output": "Done",
        }
        progress = WorkerProgress.from_dict(data)

        assert progress.task_id == "task-1"
        assert progress.status == WorkerStatus.COMPLETED
        assert progress.iteration == 10
        assert progress.output == "Done"

    def test_roundtrip(self):
        """Test to_dict and from_dict roundtrip."""
        original = WorkerProgress(
            task_id="task-1",
            worker_id="batch-task-1",
            status=WorkerStatus.FAILED,
            iteration=3,
            error="Something went wrong",
        )
        data = original.to_dict()
        restored = WorkerProgress.from_dict(data)

        assert restored.task_id == original.task_id
        assert restored.status == original.status
        assert restored.error == original.error


class TestBatchProgress:
    """Tests for BatchProgress."""

    def test_empty_batch(self):
        """Test empty batch progress."""
        progress = BatchProgress(batch_id="abc123", total_tasks=0)
        assert progress.pending_count == 0
        assert progress.running_count == 0
        assert progress.completed_count == 0
        assert progress.failed_count == 0
        assert progress.is_complete is True

    def test_counts(self):
        """Test progress count calculations."""
        progress = BatchProgress(
            batch_id="abc123",
            total_tasks=5,
            workers={
                "w1": WorkerProgress("t1", "w1", status=WorkerStatus.PENDING),
                "w2": WorkerProgress("t2", "w2", status=WorkerStatus.RUNNING),
                "w3": WorkerProgress("t3", "w3", status=WorkerStatus.RUNNING),
                "w4": WorkerProgress("t4", "w4", status=WorkerStatus.COMPLETED),
                "w5": WorkerProgress("t5", "w5", status=WorkerStatus.FAILED),
            },
        )

        assert progress.pending_count == 1
        assert progress.running_count == 2
        assert progress.completed_count == 1
        assert progress.failed_count == 1

    def test_is_complete(self):
        """Test is_complete property."""
        # Not complete - has running
        progress = BatchProgress(
            batch_id="abc",
            total_tasks=2,
            workers={
                "w1": WorkerProgress("t1", "w1", status=WorkerStatus.RUNNING),
                "w2": WorkerProgress("t2", "w2", status=WorkerStatus.COMPLETED),
            },
        )
        assert progress.is_complete is False

        # Complete - all finished
        progress2 = BatchProgress(
            batch_id="abc",
            total_tasks=2,
            workers={
                "w1": WorkerProgress("t1", "w1", status=WorkerStatus.COMPLETED),
                "w2": WorkerProgress("t2", "w2", status=WorkerStatus.FAILED),
            },
        )
        assert progress2.is_complete is True


class TestFormatBatchProgress:
    """Tests for format_batch_progress function."""

    def test_format_empty(self):
        """Test formatting empty progress."""
        progress = BatchProgress(batch_id="abc", total_tasks=0)
        output = format_batch_progress(progress)

        assert "abc" in output
        assert "0 tasks" in output

    def test_format_with_workers(self):
        """Test formatting progress with workers."""
        progress = BatchProgress(
            batch_id="abc",
            total_tasks=3,
            workers={
                "w1": WorkerProgress(
                    "task-1", "w1",
                    status=WorkerStatus.RUNNING,
                    iteration=5,
                    max_iterations=100,
                ),
                "w2": WorkerProgress(
                    "task-2", "w2",
                    status=WorkerStatus.COMPLETED,
                    output="done in 10 iterations",
                ),
                "w3": WorkerProgress(
                    "task-3", "w3",
                    status=WorkerStatus.FAILED,
                    error="Out of memory",
                ),
            },
        )
        output = format_batch_progress(progress)

        assert "3 tasks" in output
        assert "task-1" in output
        assert "task-2" in output
        assert "task-3" in output
        assert "5/100" in output  # Running iteration
        assert "done in 10 iterations" in output  # Completed output
        assert "Out of memory" in output  # Failed error


class TestBatchExecutorInit:
    """Tests for BatchExecutor initialization."""

    def test_basic_init(self, tmp_path):
        """Test basic initialization."""
        prd_path = tmp_path / "PRD.json"
        prd_path.write_text('{"project": {"name": "Test"}, "features": []}')

        config_path = tmp_path / "config.yaml"
        config_path.write_text("max_iterations: 10")

        executor = BatchExecutor(
            prd_path=prd_path,
            config_path=config_path,
        )

        assert executor._prd_path == prd_path.resolve()
        assert executor._config_path == config_path.resolve()
        assert executor._batch_config.parallel_limit == DEFAULT_PARALLEL_LIMIT

    def test_custom_config(self, tmp_path):
        """Test initialization with custom config."""
        prd_path = tmp_path / "PRD.json"
        prd_path.write_text('{"project": {"name": "Test"}, "features": []}')

        config_path = tmp_path / "config.yaml"
        config_path.write_text("max_iterations: 10")

        batch_config = BatchConfig(parallel_limit=5)
        executor = BatchExecutor(
            prd_path=prd_path,
            config_path=config_path,
            batch_config=batch_config,
        )

        assert executor._batch_config.parallel_limit == 5


class TestBatchExecutorProgress:
    """Tests for BatchExecutor progress tracking."""

    def test_get_progress_before_run(self, tmp_path):
        """Test getting progress before run returns None."""
        prd_path = tmp_path / "PRD.json"
        prd_path.write_text('{"project": {"name": "Test"}, "features": []}')

        config_path = tmp_path / "config.yaml"
        config_path.write_text("max_iterations: 10")

        executor = BatchExecutor(
            prd_path=prd_path,
            config_path=config_path,
        )

        assert executor.get_progress() is None


class TestBatchExecutorNoTasks:
    """Tests for BatchExecutor with no tasks."""

    def test_run_with_no_tasks(self, tmp_path):
        """Test running with no ready tasks."""
        # Create PRD with all complete tasks
        prd_data = {
            "project": {"name": "Test", "description": "Test project"},
            "features": [
                {
                    "id": "task-1",
                    "description": "Test task",
                    "priority": 1,
                    "status": "complete",
                    "passes": True,
                    "steps": ["Step 1"],
                    "acceptance_criteria": ["Criterion 1"],
                }
            ],
        }
        prd_path = tmp_path / "PRD.json"
        prd_path.write_text(json.dumps(prd_data))

        config_path = tmp_path / "config.yaml"
        config_path.write_text("max_iterations: 10")

        executor = BatchExecutor(
            prd_path=prd_path,
            config_path=config_path,
        )

        progress = executor.run()

        assert progress.total_tasks == 0
        assert progress.is_complete is True


class TestWorkerProgressPersistence:
    """Tests for worker progress file persistence."""

    def test_progress_file_roundtrip(self, tmp_path):
        """Test reading and writing progress files."""
        progress = WorkerProgress(
            task_id="task-1",
            worker_id="w1",
            status=WorkerStatus.RUNNING,
            iteration=5,
        )

        # Write
        progress_file = tmp_path / "w1.progress.json"
        with open(progress_file, "w") as f:
            json.dump(progress.to_dict(), f)

        # Read
        with open(progress_file) as f:
            data = json.load(f)
        restored = WorkerProgress.from_dict(data)

        assert restored.task_id == "task-1"
        assert restored.status == WorkerStatus.RUNNING
        assert restored.iteration == 5


class TestCLIBatchArgs:
    """Tests for CLI batch arguments."""

    def test_parser_has_batch_flag(self):
        """Test that CLI parser has batch flag."""
        from ralph_agi.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["run", "--batch", "--prd", "test.json"])

        assert args.batch is True

    def test_parser_has_parallel_limit(self):
        """Test that CLI parser has parallel-limit option."""
        from ralph_agi.cli import create_parser

        parser = create_parser()
        args = parser.parse_args([
            "run", "--batch", "--prd", "test.json", "--parallel-limit", "5"
        ])

        assert args.parallel_limit == 5

    def test_parallel_limit_default(self):
        """Test parallel-limit default value."""
        from ralph_agi.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["run", "--batch", "--prd", "test.json"])

        assert args.parallel_limit == 3
