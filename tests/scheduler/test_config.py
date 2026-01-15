"""Tests for scheduler configuration."""

import pytest

from ralph_agi.scheduler.config import (
    DaemonMode,
    SchedulerConfig,
    WakeHook,
    load_scheduler_config,
    scheduler_config_to_dict,
)
from ralph_agi.scheduler.cron import CronValidationError


class TestSchedulerConfig:
    """Tests for SchedulerConfig dataclass."""

    def test_default_values(self):
        """Default config should have sensible values."""
        config = SchedulerConfig()
        assert config.enabled is False
        assert config.cron == "0 */4 * * *"
        assert config.idle_timeout == 30
        assert config.daemon_mode == "apscheduler"
        assert "resume_checkpoint" in config.wake_hooks

    def test_custom_values(self):
        """Should accept custom configuration values."""
        config = SchedulerConfig(
            enabled=True,
            cron="0 9 * * 1-5",
            idle_timeout=60,
            daemon_mode="launchd",
            prd_path="/path/to/PRD.json",
        )
        assert config.enabled is True
        assert config.cron == "0 9 * * 1-5"
        assert config.idle_timeout == 60
        assert config.daemon_mode == "launchd"
        assert config.prd_path == "/path/to/PRD.json"

    def test_invalid_cron_raises_when_enabled(self):
        """Invalid cron should raise when scheduler is enabled."""
        with pytest.raises(CronValidationError):
            SchedulerConfig(enabled=True, cron="invalid")

    def test_invalid_cron_allowed_when_disabled(self):
        """Invalid cron is ignored when scheduler is disabled."""
        # Should not raise - scheduler is disabled
        config = SchedulerConfig(enabled=False, cron="invalid")
        assert config.cron == "invalid"

    def test_negative_idle_timeout_raises(self):
        """Negative idle_timeout should raise."""
        with pytest.raises(ValueError, match="idle_timeout"):
            SchedulerConfig(idle_timeout=-1)

    def test_invalid_daemon_mode_raises(self):
        """Invalid daemon_mode should raise."""
        with pytest.raises(ValueError, match="daemon_mode"):
            SchedulerConfig(daemon_mode="invalid")

    def test_invalid_wake_hook_raises(self):
        """Invalid wake hook should raise."""
        with pytest.raises(ValueError, match="Unknown wake hook"):
            SchedulerConfig(wake_hooks=["invalid_hook"])

    def test_zero_max_failures_raises(self):
        """Zero max_consecutive_failures should raise."""
        with pytest.raises(ValueError, match="max_consecutive_failures"):
            SchedulerConfig(max_consecutive_failures=0)


class TestDaemonMode:
    """Tests for DaemonMode enum."""

    def test_enum_values(self):
        """Should have expected daemon mode values."""
        assert DaemonMode.APSCHEDULER.value == "apscheduler"
        assert DaemonMode.LAUNCHD.value == "launchd"
        assert DaemonMode.SYSTEMD.value == "systemd"


class TestWakeHook:
    """Tests for WakeHook enum."""

    def test_enum_values(self):
        """Should have expected wake hook values."""
        assert WakeHook.CHECK_PROGRESS.value == "check_progress"
        assert WakeHook.RUN_TESTS.value == "run_tests"
        assert WakeHook.COMMIT_IF_READY.value == "commit_if_ready"
        assert WakeHook.RESUME_CHECKPOINT.value == "resume_checkpoint"
        assert WakeHook.SEND_STATUS.value == "send_status"


class TestLoadSchedulerConfig:
    """Tests for loading scheduler config from dict."""

    def test_empty_dict_returns_defaults(self):
        """Empty dict should return default config."""
        config = load_scheduler_config({})
        assert config.enabled is False
        assert config.cron == "0 */4 * * *"

    def test_nested_scheduler_section(self):
        """Should load from nested scheduler section."""
        data = {
            "scheduler": {
                "enabled": True,
                "cron": "0 9 * * *",
                "idle_timeout": 45,
            }
        }
        config = load_scheduler_config(data)
        assert config.enabled is True
        assert config.cron == "0 9 * * *"
        assert config.idle_timeout == 45

    def test_partial_config(self):
        """Should use defaults for missing fields."""
        data = {
            "scheduler": {
                "enabled": True,
            }
        }
        config = load_scheduler_config(data)
        assert config.enabled is True
        assert config.cron == "0 */4 * * *"  # Default
        assert config.idle_timeout == 30  # Default


class TestSchedulerConfigToDict:
    """Tests for converting config to dict."""

    def test_roundtrip(self):
        """Config should survive dict roundtrip."""
        original = SchedulerConfig(
            enabled=True,
            cron="0 */6 * * *",
            idle_timeout=60,
            prd_path="/path/to/PRD.json",
        )
        data = scheduler_config_to_dict(original)
        restored = load_scheduler_config(data)

        assert restored.enabled == original.enabled
        assert restored.cron == original.cron
        assert restored.idle_timeout == original.idle_timeout
        assert restored.prd_path == original.prd_path

    def test_output_structure(self):
        """Output should have scheduler key at top level."""
        config = SchedulerConfig()
        data = scheduler_config_to_dict(config)
        assert "scheduler" in data
        assert "enabled" in data["scheduler"]
        assert "cron" in data["scheduler"]
