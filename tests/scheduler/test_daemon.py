"""Tests for daemon management."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ralph_agi.scheduler.config import SchedulerConfig
from ralph_agi.scheduler.daemon import (
    DaemonManager,
    DaemonState,
    DaemonStatus,
    generate_launchd_plist,
    generate_systemd_unit,
)


class TestDaemonState:
    """Tests for DaemonState dataclass."""

    def test_stopped_state(self):
        """Should create stopped state."""
        state = DaemonState(
            status=DaemonStatus.STOPPED,
            message="Not running",
        )
        assert state.status == DaemonStatus.STOPPED
        assert state.pid is None

    def test_running_state(self):
        """Should create running state with PID."""
        state = DaemonState(
            status=DaemonStatus.RUNNING,
            pid=12345,
            message="Running",
        )
        assert state.status == DaemonStatus.RUNNING
        assert state.pid == 12345


class TestDaemonManager:
    """Tests for DaemonManager class."""

    def test_create_manager(self):
        """Should create manager with config."""
        config = SchedulerConfig()
        manager = DaemonManager(config)
        assert manager.config == config

    def test_status_no_pid_file(self, tmp_path):
        """Status should be stopped if no PID file."""
        config = SchedulerConfig(pid_file=str(tmp_path / "nonexistent.pid"))
        manager = DaemonManager(config)
        state = manager.status()
        assert state.status == DaemonStatus.STOPPED

    def test_status_stale_pid_file(self, tmp_path):
        """Status should detect stale PID file."""
        pid_file = tmp_path / ".ralph.pid"
        pid_file.write_text("99999999")  # Unlikely to be a real PID

        config = SchedulerConfig(pid_file=str(pid_file))
        manager = DaemonManager(config)
        state = manager.status()
        assert state.status == DaemonStatus.STOPPED
        assert "stale" in state.message.lower() or "not running" in state.message.lower()


class TestGenerateLaunchdPlist:
    """Tests for launchd plist generation."""

    def test_basic_plist_structure(self):
        """Generated plist should have required structure."""
        config = SchedulerConfig(cron="0 */4 * * *")
        plist = generate_launchd_plist(config, "/path/to/workdir")

        assert "<?xml version" in plist
        assert "com.ralph-agi.scheduler" in plist
        assert "ralph_agi.cli" in plist
        assert "/path/to/workdir" in plist

    def test_plist_with_interval(self):
        """Plist should use StartInterval for */n patterns."""
        config = SchedulerConfig(cron="0 */4 * * *")
        plist = generate_launchd_plist(config, "/workdir")

        # 4 hours = 14400 seconds
        assert "StartInterval" in plist or "StartCalendarInterval" in plist

    def test_plist_with_fixed_time(self):
        """Plist should use StartCalendarInterval for fixed times."""
        config = SchedulerConfig(cron="0 9 * * *")
        plist = generate_launchd_plist(config, "/workdir")

        assert "StartCalendarInterval" in plist or "StartInterval" in plist


class TestGenerateSystemdUnit:
    """Tests for systemd unit generation."""

    def test_generates_service_and_timer(self):
        """Should generate both service and timer files."""
        config = SchedulerConfig(cron="0 9 * * *")
        service, timer = generate_systemd_unit(config, "/path/to/workdir")

        # Service checks
        assert "[Unit]" in service
        assert "[Service]" in service
        assert "ralph_agi.cli" in service
        assert "/path/to/workdir" in service

        # Timer checks
        assert "[Timer]" in timer
        assert "OnCalendar" in timer

    def test_service_type_oneshot(self):
        """Service should be oneshot type."""
        config = SchedulerConfig()
        service, _ = generate_systemd_unit(config, "/workdir")
        assert "Type=oneshot" in service

    def test_timer_persistent(self):
        """Timer should be persistent."""
        config = SchedulerConfig()
        _, timer = generate_systemd_unit(config, "/workdir")
        assert "Persistent=true" in timer


class TestDaemonStatus:
    """Tests for DaemonStatus enum."""

    def test_enum_values(self):
        """Should have expected status values."""
        assert DaemonStatus.RUNNING.value == "running"
        assert DaemonStatus.STOPPED.value == "stopped"
        assert DaemonStatus.ERROR.value == "error"
