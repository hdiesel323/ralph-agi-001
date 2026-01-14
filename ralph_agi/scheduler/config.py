"""Configuration for RALPH-AGI scheduler.

Defines the scheduler configuration dataclass and related types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DaemonMode(str, Enum):
    """Daemon execution mode."""

    APSCHEDULER = "apscheduler"  # Cross-platform Python scheduler
    LAUNCHD = "launchd"  # macOS native
    SYSTEMD = "systemd"  # Linux native


class WakeHook(str, Enum):
    """Built-in wake hooks that can be triggered on scheduled wake."""

    CHECK_PROGRESS = "check_progress"  # Check if tasks are progressing
    RUN_TESTS = "run_tests"  # Run test suite
    COMMIT_IF_READY = "commit_if_ready"  # Commit if work is complete
    RESUME_CHECKPOINT = "resume_checkpoint"  # Resume from last checkpoint
    SEND_STATUS = "send_status"  # Send status notification


@dataclass
class SchedulerConfig:
    """Configuration for the RALPH-AGI scheduler.

    Attributes:
        enabled: Whether scheduling is enabled. Default: False
        cron: Cron expression for scheduled runs. Default: "0 */4 * * *" (every 4 hours)
        idle_timeout: Minutes of no progress before auto-sleep. Default: 30
        wake_hooks: List of hooks to execute on scheduled wake.
        daemon_mode: How to run the daemon (apscheduler, launchd, systemd).
        pid_file: Path to PID file for daemon. Default: ".ralph.pid"
        log_file: Path to daemon log file. Default: ".ralph-daemon.log"
        prd_path: Path to PRD.json for scheduled runs.
        config_path: Path to config.yaml for scheduled runs.
        max_consecutive_failures: Max failures before disabling schedule. Default: 3
        notify_on_completion: Send notification on completion. Default: False
        notify_on_failure: Send notification on failure. Default: True
    """

    enabled: bool = False
    cron: str = "0 */4 * * *"
    idle_timeout: int = 30
    wake_hooks: list[str] = field(
        default_factory=lambda: ["resume_checkpoint", "check_progress"]
    )
    daemon_mode: str = "apscheduler"
    pid_file: str = ".ralph.pid"
    log_file: str = ".ralph-daemon.log"
    prd_path: Optional[str] = None
    config_path: Optional[str] = None
    max_consecutive_failures: int = 3
    notify_on_completion: bool = False
    notify_on_failure: bool = True

    def __post_init__(self):
        """Validate configuration."""
        self._validate()

    def _validate(self) -> None:
        """Validate scheduler configuration values."""
        from ralph_agi.scheduler.cron import validate_cron, CronValidationError

        if self.enabled and not validate_cron(self.cron):
            raise CronValidationError(f"Invalid cron expression: {self.cron}")

        if self.idle_timeout < 0:
            raise ValueError("idle_timeout must be non-negative")

        if self.max_consecutive_failures < 1:
            raise ValueError("max_consecutive_failures must be at least 1")

        valid_modes = [mode.value for mode in DaemonMode]
        if self.daemon_mode not in valid_modes:
            raise ValueError(f"daemon_mode must be one of {valid_modes}")

        # Validate wake hooks
        valid_hooks = [hook.value for hook in WakeHook]
        for hook in self.wake_hooks:
            if hook not in valid_hooks:
                raise ValueError(f"Unknown wake hook: {hook}. Valid hooks: {valid_hooks}")


def load_scheduler_config(data: dict) -> SchedulerConfig:
    """Load scheduler config from a dictionary (typically from YAML).

    Args:
        data: Dictionary containing scheduler configuration.

    Returns:
        SchedulerConfig instance.
    """
    scheduler_data = data.get("scheduler", {})

    return SchedulerConfig(
        enabled=scheduler_data.get("enabled", False),
        cron=scheduler_data.get("cron", "0 */4 * * *"),
        idle_timeout=scheduler_data.get("idle_timeout", 30),
        wake_hooks=scheduler_data.get("wake_hooks", ["resume_checkpoint", "check_progress"]),
        daemon_mode=scheduler_data.get("daemon_mode", "apscheduler"),
        pid_file=scheduler_data.get("pid_file", ".ralph.pid"),
        log_file=scheduler_data.get("log_file", ".ralph-daemon.log"),
        prd_path=scheduler_data.get("prd_path"),
        config_path=scheduler_data.get("config_path"),
        max_consecutive_failures=scheduler_data.get("max_consecutive_failures", 3),
        notify_on_completion=scheduler_data.get("notify_on_completion", False),
        notify_on_failure=scheduler_data.get("notify_on_failure", True),
    )


def scheduler_config_to_dict(config: SchedulerConfig) -> dict:
    """Convert scheduler config to dictionary for YAML serialization.

    Args:
        config: SchedulerConfig instance.

    Returns:
        Dictionary representation.
    """
    return {
        "scheduler": {
            "enabled": config.enabled,
            "cron": config.cron,
            "idle_timeout": config.idle_timeout,
            "wake_hooks": config.wake_hooks,
            "daemon_mode": config.daemon_mode,
            "pid_file": config.pid_file,
            "log_file": config.log_file,
            "prd_path": config.prd_path,
            "config_path": config.config_path,
            "max_consecutive_failures": config.max_consecutive_failures,
            "notify_on_completion": config.notify_on_completion,
            "notify_on_failure": config.notify_on_failure,
        }
    }
