"""Tests for TUI widgets."""

from datetime import datetime, timedelta

import pytest

from ralph_agi.tui.widgets.log_panel import LogEntry, LogPanel
from ralph_agi.tui.widgets.metrics_bar import MetricItem, Metrics, MetricsBar
from ralph_agi.tui.widgets.story_grid import StoryGrid, TaskInfo, TaskStatus


class TestTaskInfo:
    """Tests for TaskInfo dataclass."""

    def test_status_icons(self):
        """Each status should have a unique icon."""
        icons = set()
        for status in TaskStatus:
            task = TaskInfo("1", "Test", status)
            icons.add(task.status_icon)
        assert len(icons) == len(TaskStatus)

    def test_status_labels(self):
        """Each status should have a label."""
        for status in TaskStatus:
            task = TaskInfo("1", "Test", status)
            assert task.status_label
            assert isinstance(task.status_label, str)

    def test_progress_default(self):
        """Progress should default to 0."""
        task = TaskInfo("1", "Test", TaskStatus.PENDING)
        assert task.progress == 0.0


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_all_statuses_exist(self):
        """All expected statuses should exist."""
        expected = ["pending", "running", "done", "failed", "blocked"]
        for status in expected:
            assert hasattr(TaskStatus, status.upper())


class TestMetrics:
    """Tests for Metrics dataclass."""

    def test_default_values(self):
        """Default metrics should be zero/empty."""
        metrics = Metrics()
        assert metrics.iteration == 0
        assert metrics.cost == 0.0
        assert metrics.input_tokens == 0
        assert metrics.output_tokens == 0

    def test_total_tokens(self):
        """Total tokens should be sum of input and output."""
        metrics = Metrics(input_tokens=100, output_tokens=50)
        assert metrics.total_tokens == 150

    def test_elapsed_time(self):
        """Elapsed time should be calculated from start_time."""
        start = datetime.now() - timedelta(hours=1)
        metrics = Metrics(start_time=start)
        elapsed = metrics.elapsed_time
        assert elapsed.total_seconds() >= 3600  # At least 1 hour

    def test_elapsed_str_format(self):
        """Elapsed string should be in HH:MM:SS format."""
        metrics = Metrics()
        elapsed_str = metrics.elapsed_str
        assert len(elapsed_str) == 8  # "00:00:00"
        assert elapsed_str.count(":") == 2

    def test_iteration_str_format(self):
        """Iteration string should show current/max."""
        metrics = Metrics(iteration=5, max_iterations=100)
        assert metrics.iteration_str == "5/100"


class TestLogEntry:
    """Tests for LogEntry widget."""

    def test_info_level(self):
        """Info level should have correct class."""
        entry = LogEntry("Test message", level="info")
        assert entry.level == "info"
        assert "info" in entry.classes

    def test_error_level(self):
        """Error level should have correct class."""
        entry = LogEntry("Error message", level="error")
        assert entry.level == "error"
        assert "error" in entry.classes

    def test_custom_timestamp(self):
        """Should accept custom timestamp."""
        custom_time = datetime(2026, 1, 15, 12, 30, 45)
        entry = LogEntry("Test", timestamp=custom_time)
        assert entry.timestamp == custom_time

    def test_default_timestamp(self):
        """Should use current time if not provided."""
        before = datetime.now()
        entry = LogEntry("Test")
        after = datetime.now()
        assert before <= entry.timestamp <= after


class TestMetricItem:
    """Tests for MetricItem widget."""

    def test_creates_with_label_and_value(self):
        """Should store label and value."""
        item = MetricItem("Cost", "$2.34")
        assert item.label == "Cost"
        assert item.value == "$2.34"

    def test_update_value(self):
        """Should update value."""
        item = MetricItem("Cost", "$0.00")
        item.update_value("$5.00")
        assert item.value == "$5.00"


class TestStoryGridTaskInfo:
    """Tests for task info in story grid."""

    def test_pending_icon(self):
        """Pending tasks should show circle icon."""
        task = TaskInfo("1", "Test", TaskStatus.PENDING)
        assert task.status_icon == "○"

    def test_running_icon(self):
        """Running tasks should show play icon."""
        task = TaskInfo("1", "Test", TaskStatus.RUNNING)
        assert task.status_icon == "▶"

    def test_done_icon(self):
        """Done tasks should show filled circle."""
        task = TaskInfo("1", "Test", TaskStatus.DONE)
        assert task.status_icon == "●"

    def test_failed_icon(self):
        """Failed tasks should show X."""
        task = TaskInfo("1", "Test", TaskStatus.FAILED)
        assert task.status_icon == "✗"


class TestMetricsCalculations:
    """Tests for metrics calculations."""

    def test_cost_accumulation(self):
        """Cost should accumulate correctly."""
        metrics = Metrics(cost=1.50)
        metrics.cost += 0.50
        assert metrics.cost == 2.0

    def test_token_tracking(self):
        """Token counts should track separately."""
        metrics = Metrics()
        metrics.input_tokens = 1000
        metrics.output_tokens = 500
        assert metrics.total_tokens == 1500
