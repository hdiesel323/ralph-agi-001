"""Daemon process management for RALPH-AGI scheduler.

Provides a cross-platform daemon that can be run via:
- APScheduler (default, works everywhere)
- launchd (macOS native)
- systemd (Linux native)
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from ralph_agi.scheduler.config import DaemonMode, SchedulerConfig
from ralph_agi.scheduler.cron import CronExpression
from ralph_agi.scheduler.hooks import WakeHookExecutor


class DaemonStatus(str, Enum):
    """Status of the daemon process."""

    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class DaemonState:
    """Current state of the daemon.

    Attributes:
        status: Running, stopped, or error.
        pid: Process ID if running.
        last_run: Timestamp of last scheduled run.
        next_run: Timestamp of next scheduled run.
        consecutive_failures: Number of consecutive failures.
        message: Status message.
    """

    status: DaemonStatus
    pid: Optional[int] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    consecutive_failures: int = 0
    message: str = ""


class DaemonManager:
    """Manages the RALPH-AGI scheduler daemon.

    Supports multiple backends for different platforms and use cases.
    """

    def __init__(
        self,
        config: SchedulerConfig,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the daemon manager.

        Args:
            config: Scheduler configuration.
            logger: Optional logger instance.
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._scheduler = None
        self._running = False

    def status(self) -> DaemonState:
        """Get the current daemon status.

        Returns:
            DaemonState with current status.
        """
        pid_file = Path(self.config.pid_file)

        if not pid_file.exists():
            return DaemonState(
                status=DaemonStatus.STOPPED,
                message="Daemon not running (no PID file)",
            )

        try:
            pid = int(pid_file.read_text().strip())

            # Check if process is running
            try:
                os.kill(pid, 0)  # Signal 0 checks if process exists
                cron = CronExpression(self.config.cron, "")
                return DaemonState(
                    status=DaemonStatus.RUNNING,
                    pid=pid,
                    next_run=cron.next_run(),
                    message=f"Daemon running with PID {pid}",
                )
            except OSError:
                # Process not running, stale PID file
                return DaemonState(
                    status=DaemonStatus.STOPPED,
                    message=f"Stale PID file (process {pid} not running)",
                )
        except (ValueError, OSError) as e:
            return DaemonState(
                status=DaemonStatus.ERROR,
                message=f"Error reading PID file: {e}",
            )

    def start(self, background: bool = True) -> DaemonState:
        """Start the scheduler daemon.

        Args:
            background: Whether to run in background (fork).

        Returns:
            DaemonState after start attempt.
        """
        current_status = self.status()
        if current_status.status == DaemonStatus.RUNNING:
            return DaemonState(
                status=DaemonStatus.RUNNING,
                pid=current_status.pid,
                message="Daemon already running",
            )

        mode = DaemonMode(self.config.daemon_mode)

        if mode == DaemonMode.APSCHEDULER:
            return self._start_apscheduler(background)
        elif mode == DaemonMode.LAUNCHD:
            return self._start_launchd()
        elif mode == DaemonMode.SYSTEMD:
            return self._start_systemd()
        else:
            return DaemonState(
                status=DaemonStatus.ERROR,
                message=f"Unknown daemon mode: {mode}",
            )

    def stop(self) -> DaemonState:
        """Stop the scheduler daemon.

        Returns:
            DaemonState after stop attempt.
        """
        current_status = self.status()
        if current_status.status != DaemonStatus.RUNNING:
            return DaemonState(
                status=DaemonStatus.STOPPED,
                message="Daemon not running",
            )

        mode = DaemonMode(self.config.daemon_mode)

        if mode == DaemonMode.APSCHEDULER:
            return self._stop_apscheduler(current_status.pid)
        elif mode == DaemonMode.LAUNCHD:
            return self._stop_launchd()
        elif mode == DaemonMode.SYSTEMD:
            return self._stop_systemd()
        else:
            return DaemonState(
                status=DaemonStatus.ERROR,
                message=f"Unknown daemon mode: {mode}",
            )

    def _start_apscheduler(self, background: bool) -> DaemonState:
        """Start the APScheduler-based daemon."""
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        if background:
            # Fork to background
            pid = os.fork()
            if pid > 0:
                # Parent process
                return DaemonState(
                    status=DaemonStatus.RUNNING,
                    pid=pid,
                    message=f"Daemon started in background with PID {pid}",
                )
            else:
                # Child process - continue to run scheduler
                # Detach from terminal
                os.setsid()
                # Redirect stdout/stderr to log file
                log_file = open(self.config.log_file, "a")
                sys.stdout = log_file
                sys.stderr = log_file

        # Write PID file
        pid = os.getpid()
        Path(self.config.pid_file).write_text(str(pid))

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        # Create and configure scheduler
        self._scheduler = BackgroundScheduler()

        # Parse cron expression for APScheduler
        parts = self.config.cron.split()
        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
        )

        # Add job
        self._scheduler.add_job(
            self._scheduled_wake,
            trigger,
            id="ralph_wake",
            name="RALPH-AGI Scheduled Wake",
            replace_existing=True,
        )

        self._scheduler.start()
        self._running = True
        self.logger.info(f"APScheduler daemon started with cron: {self.config.cron}")

        if not background:
            # If running in foreground, block until shutdown
            try:
                while self._running:
                    signal.pause()
            except KeyboardInterrupt:
                self._handle_shutdown(signal.SIGINT, None)

        cron = CronExpression(self.config.cron, "")
        return DaemonState(
            status=DaemonStatus.RUNNING,
            pid=pid,
            next_run=cron.next_run(),
            message="APScheduler daemon started",
        )

    def _stop_apscheduler(self, pid: Optional[int]) -> DaemonState:
        """Stop the APScheduler daemon."""
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                # Clean up PID file
                pid_file = Path(self.config.pid_file)
                if pid_file.exists():
                    pid_file.unlink()
                return DaemonState(
                    status=DaemonStatus.STOPPED,
                    message=f"Sent SIGTERM to daemon (PID {pid})",
                )
            except OSError as e:
                return DaemonState(
                    status=DaemonStatus.ERROR,
                    message=f"Failed to stop daemon: {e}",
                )
        else:
            return DaemonState(
                status=DaemonStatus.STOPPED,
                message="No PID to stop",
            )

    def _start_launchd(self) -> DaemonState:
        """Start via launchd (macOS)."""
        plist_path = Path("~/Library/LaunchAgents/com.ralph-agi.scheduler.plist").expanduser()

        if not plist_path.exists():
            return DaemonState(
                status=DaemonStatus.ERROR,
                message=f"launchd plist not found. Run 'ralph-agi daemon install' first.",
            )

        try:
            subprocess.run(
                ["launchctl", "load", str(plist_path)],
                check=True,
                capture_output=True,
            )
            return DaemonState(
                status=DaemonStatus.RUNNING,
                message="launchd service loaded",
            )
        except subprocess.CalledProcessError as e:
            return DaemonState(
                status=DaemonStatus.ERROR,
                message=f"Failed to load launchd service: {e.stderr.decode()}",
            )

    def _stop_launchd(self) -> DaemonState:
        """Stop via launchd (macOS)."""
        plist_path = Path("~/Library/LaunchAgents/com.ralph-agi.scheduler.plist").expanduser()

        try:
            subprocess.run(
                ["launchctl", "unload", str(plist_path)],
                check=True,
                capture_output=True,
            )
            return DaemonState(
                status=DaemonStatus.STOPPED,
                message="launchd service unloaded",
            )
        except subprocess.CalledProcessError as e:
            return DaemonState(
                status=DaemonStatus.ERROR,
                message=f"Failed to unload launchd service: {e.stderr.decode()}",
            )

    def _start_systemd(self) -> DaemonState:
        """Start via systemd (Linux)."""
        try:
            subprocess.run(
                ["systemctl", "--user", "start", "ralph-agi-scheduler"],
                check=True,
                capture_output=True,
            )
            return DaemonState(
                status=DaemonStatus.RUNNING,
                message="systemd service started",
            )
        except subprocess.CalledProcessError as e:
            return DaemonState(
                status=DaemonStatus.ERROR,
                message=f"Failed to start systemd service: {e.stderr.decode()}",
            )

    def _stop_systemd(self) -> DaemonState:
        """Stop via systemd (Linux)."""
        try:
            subprocess.run(
                ["systemctl", "--user", "stop", "ralph-agi-scheduler"],
                check=True,
                capture_output=True,
            )
            return DaemonState(
                status=DaemonStatus.STOPPED,
                message="systemd service stopped",
            )
        except subprocess.CalledProcessError as e:
            return DaemonState(
                status=DaemonStatus.ERROR,
                message=f"Failed to stop systemd service: {e.stderr.decode()}",
            )

    def _handle_shutdown(self, signum: int, frame) -> None:
        """Handle shutdown signal."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self._running = False

        if self._scheduler:
            self._scheduler.shutdown(wait=False)

        # Clean up PID file
        pid_file = Path(self.config.pid_file)
        if pid_file.exists():
            pid_file.unlink()

        self.logger.info("Daemon shutdown complete")

    def _scheduled_wake(self) -> None:
        """Execute scheduled wake - runs hooks and optionally the loop."""
        self.logger.info("=" * 50)
        self.logger.info(f"Scheduled wake at {datetime.now().isoformat()}")

        # Execute wake hooks
        executor = WakeHookExecutor(
            prd_path=self.config.prd_path,
            config_path=self.config.config_path,
            logger=self.logger,
        )

        results = executor.execute(self.config.wake_hooks)

        # Log results
        for result in results:
            self.logger.info(f"  {result.hook}: {result.result.value} - {result.message}")

        # Check if we should run the main loop
        should_run_loop = all(
            r.result != "failure" for r in results if r.hook == "check_progress"
        )

        if should_run_loop and self.config.prd_path:
            self.logger.info("Starting RALPH-AGI loop...")
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "ralph_agi.cli",
                        "run",
                        "--prd",
                        self.config.prd_path,
                    ]
                    + (["--config", self.config.config_path] if self.config.config_path else []),
                    capture_output=True,
                    text=True,
                    timeout=3600,  # 1 hour timeout
                )

                if result.returncode == 0:
                    self.logger.info("Loop completed successfully")
                else:
                    self.logger.error(f"Loop failed with code {result.returncode}")
                    self.logger.error(result.stderr[-1000:])
            except subprocess.TimeoutExpired:
                self.logger.error("Loop execution timed out (1 hour)")
            except Exception as e:
                self.logger.error(f"Failed to run loop: {e}")
        else:
            self.logger.info("Skipping loop execution (no PRD or pre-checks failed)")

        self.logger.info("Scheduled wake complete")
        self.logger.info("=" * 50)


def generate_launchd_plist(config: SchedulerConfig, working_dir: str) -> str:
    """Generate a launchd plist file for macOS.

    Args:
        config: Scheduler configuration.
        working_dir: Working directory for the daemon.

    Returns:
        plist XML content.
    """
    # Convert cron to launchd calendar interval
    parts = config.cron.split()
    minute, hour, day, month, weekday = parts[:5]

    # Build calendar interval dict
    calendar_interval = {}
    if minute != "*" and not minute.startswith("*/"):
        calendar_interval["Minute"] = int(minute)
    if hour != "*" and not hour.startswith("*/"):
        calendar_interval["Hour"] = int(hour)
    if day != "*":
        calendar_interval["Day"] = int(day)
    if weekday != "*":
        calendar_interval["Weekday"] = int(weekday)

    # For intervals like */4, we need StartInterval instead
    start_interval = None
    if hour.startswith("*/"):
        start_interval = int(hour[2:]) * 3600
    elif minute.startswith("*/"):
        start_interval = int(minute[2:]) * 60

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ralph-agi.scheduler</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>-m</string>
        <string>ralph_agi.cli</string>
        <string>daemon</string>
        <string>run-once</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{working_dir}</string>
    <key>StandardOutPath</key>
    <string>{working_dir}/{config.log_file}</string>
    <key>StandardErrorPath</key>
    <string>{working_dir}/{config.log_file}</string>
"""

    if start_interval:
        plist += f"""    <key>StartInterval</key>
    <integer>{start_interval}</integer>
"""
    elif calendar_interval:
        plist += """    <key>StartCalendarInterval</key>
    <dict>
"""
        for key, value in calendar_interval.items():
            plist += f"""        <key>{key}</key>
        <integer>{value}</integer>
"""
        plist += """    </dict>
"""

    plist += """</dict>
</plist>
"""
    return plist


def generate_systemd_unit(config: SchedulerConfig, working_dir: str) -> tuple[str, str]:
    """Generate systemd service and timer units for Linux.

    Args:
        config: Scheduler configuration.
        working_dir: Working directory for the daemon.

    Returns:
        Tuple of (service_content, timer_content).
    """
    # Convert cron to systemd OnCalendar format
    parts = config.cron.split()
    minute, hour, day, month, weekday = parts[:5]

    # Build OnCalendar string
    # Format: DayOfWeek Year-Month-Day Hour:Minute:Second
    day_str = "*" if day == "*" else day
    month_str = "*" if month == "*" else month

    weekday_map = {
        "0": "Sun",
        "1": "Mon",
        "2": "Tue",
        "3": "Wed",
        "4": "Thu",
        "5": "Fri",
        "6": "Sat",
        "7": "Sun",
        "*": "*",
    }
    weekday_str = weekday_map.get(weekday, "*")

    hour_str = "*" if hour == "*" else hour.replace("*/", "/")
    minute_str = "0" if minute == "*" else minute.replace("*/", "/")

    on_calendar = f"{weekday_str} *-{month_str}-{day_str} {hour_str}:{minute_str}:00"

    service = f"""[Unit]
Description=RALPH-AGI Scheduled Wake
After=network.target

[Service]
Type=oneshot
WorkingDirectory={working_dir}
ExecStart={sys.executable} -m ralph_agi.cli daemon run-once
StandardOutput=append:{working_dir}/{config.log_file}
StandardError=append:{working_dir}/{config.log_file}

[Install]
WantedBy=default.target
"""

    timer = f"""[Unit]
Description=RALPH-AGI Scheduler Timer

[Timer]
OnCalendar={on_calendar}
Persistent=true

[Install]
WantedBy=timers.target
"""

    return service, timer
