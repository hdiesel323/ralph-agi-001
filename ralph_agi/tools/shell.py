"""Shell execution tools for RALPH-AGI.

Provides secure shell command execution with timeout handling,
output capture, and configurable safety constraints.
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)


class ShellError(Exception):
    """Base exception for shell operations."""

    pass


class CommandTimeoutError(ShellError):
    """Raised when a command times out."""

    def __init__(self, command: str, timeout: float):
        self.command = command
        self.timeout = timeout
        super().__init__(f"Command timed out after {timeout}s: {command}")


class CommandNotAllowedError(ShellError):
    """Raised when a command is blocked by security policy."""

    def __init__(self, command: str, reason: str):
        self.command = command
        self.reason = reason
        super().__init__(f"Command not allowed: {reason}")


@dataclass
class CommandResult:
    """Result of shell command execution.

    Attributes:
        command: The executed command string
        exit_code: Process exit code (0 typically means success)
        stdout: Standard output (decoded as UTF-8)
        stderr: Standard error (decoded as UTF-8)
        duration_ms: Execution time in milliseconds
        timed_out: Whether the command was killed due to timeout
        cwd: Working directory where command was executed
        timestamp: When execution started (UTC)
    """

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False
    cwd: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success(self) -> bool:
        """Check if command succeeded (exit code 0)."""
        return self.exit_code == 0 and not self.timed_out

    @property
    def failed(self) -> bool:
        """Check if command failed."""
        return not self.success

    @property
    def output(self) -> str:
        """Get combined stdout and stderr."""
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "timed_out": self.timed_out,
            "cwd": self.cwd,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
        }


class ShellTools:
    """Shell command execution with safety constraints.

    Provides a secure interface for executing shell commands with
    timeout handling, output capture, and optional command filtering.

    Usage:
        # Create with defaults
        shell = ShellTools()

        # Execute simple command
        result = shell.execute("ls -la")
        if result.success:
            print(result.stdout)

        # Execute with working directory
        result = shell.execute("npm test", cwd="/path/to/project")

        # Execute with timeout
        result = shell.execute("long_command", timeout=300)

        # Execute with custom environment
        result = shell.execute("echo $MY_VAR", env={"MY_VAR": "hello"})

    Security:
        - Commands executed via subprocess (no shell injection via variables)
        - Configurable timeout prevents runaway processes
        - Optional command allowlist/blocklist
        - Working directory validation
    """

    # Default timeout in seconds
    DEFAULT_TIMEOUT = 60.0

    # Maximum timeout allowed
    MAX_TIMEOUT = 3600.0  # 1 hour

    # Default blocked commands (dangerous operations)
    DEFAULT_BLOCKED_COMMANDS = frozenset({
        "rm -rf /",
        "rm -rf /*",
        "mkfs",
        "dd if=/dev/zero",
        ":(){ :|:& };:",  # fork bomb
        "> /dev/sda",
    })

    def __init__(
        self,
        default_timeout: float = DEFAULT_TIMEOUT,
        default_cwd: Path | str | None = None,
        blocked_commands: Sequence[str] | None = None,
        allowed_commands: Sequence[str] | None = None,
        inherit_env: bool = True,
    ):
        """Initialize shell tools.

        Args:
            default_timeout: Default timeout for commands in seconds
            default_cwd: Default working directory
            blocked_commands: Commands that are never allowed
            allowed_commands: If set, ONLY these commands are allowed
            inherit_env: Whether to inherit parent environment
        """
        self._default_timeout = min(default_timeout, self.MAX_TIMEOUT)
        self._default_cwd = Path(default_cwd) if default_cwd else None
        self._blocked_commands = (
            set(blocked_commands)
            if blocked_commands is not None
            else set(self.DEFAULT_BLOCKED_COMMANDS)
        )
        self._allowed_commands = set(allowed_commands) if allowed_commands else None
        self._inherit_env = inherit_env

        logger.debug(
            f"ShellTools initialized: timeout={self._default_timeout}s, "
            f"cwd={self._default_cwd}"
        )

    def execute(
        self,
        command: str,
        cwd: str | Path | None = None,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
        capture_output: bool = True,
        shell: bool = True,
    ) -> CommandResult:
        """Execute a shell command.

        Args:
            command: Shell command to execute
            cwd: Working directory (default: default_cwd or current)
            timeout: Max execution time in seconds (default: default_timeout)
            env: Additional environment variables to set
            capture_output: Whether to capture stdout/stderr
            shell: Whether to execute through shell (default: True)

        Returns:
            CommandResult with exit code, output, and timing

        Raises:
            CommandNotAllowedError: If command is blocked
        """
        # Validate command
        self._validate_command(command)

        # Resolve working directory
        work_dir = self._resolve_cwd(cwd)

        # Resolve timeout
        timeout = timeout if timeout is not None else self._default_timeout
        timeout = min(timeout, self.MAX_TIMEOUT)

        # Build environment
        process_env = self._build_env(env)

        # Record start time
        start_time = time.time()
        timestamp = datetime.now(timezone.utc)

        # Log execution
        logger.info(f"SHELL_EXEC: {command[:100]}{'...' if len(command) > 100 else ''}")

        try:
            # Execute command
            if shell:
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=work_dir,
                    env=process_env,
                    capture_output=capture_output,
                    timeout=timeout,
                    text=True,
                )
            else:
                # Parse command into args
                args = shlex.split(command)
                result = subprocess.run(
                    args,
                    cwd=work_dir,
                    env=process_env,
                    capture_output=capture_output,
                    timeout=timeout,
                    text=True,
                )

            duration_ms = int((time.time() - start_time) * 1000)

            cmd_result = CommandResult(
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                duration_ms=duration_ms,
                timed_out=False,
                cwd=str(work_dir) if work_dir else None,
                timestamp=timestamp,
            )

            self._log_result(cmd_result)
            return cmd_result

        except subprocess.TimeoutExpired as e:
            duration_ms = int((time.time() - start_time) * 1000)

            cmd_result = CommandResult(
                command=command,
                exit_code=-1,
                stdout=e.stdout.decode("utf-8", errors="replace") if e.stdout else "",
                stderr=e.stderr.decode("utf-8", errors="replace") if e.stderr else "",
                duration_ms=duration_ms,
                timed_out=True,
                cwd=str(work_dir) if work_dir else None,
                timestamp=timestamp,
            )

            logger.warning(f"SHELL_TIMEOUT: {command[:50]} after {timeout}s")
            return cmd_result

        except FileNotFoundError as e:
            duration_ms = int((time.time() - start_time) * 1000)

            return CommandResult(
                command=command,
                exit_code=127,  # Standard "command not found" exit code
                stdout="",
                stderr=str(e),
                duration_ms=duration_ms,
                timed_out=False,
                cwd=str(work_dir) if work_dir else None,
                timestamp=timestamp,
            )

        except PermissionError as e:
            duration_ms = int((time.time() - start_time) * 1000)

            return CommandResult(
                command=command,
                exit_code=126,  # Standard "permission denied" exit code
                stdout="",
                stderr=str(e),
                duration_ms=duration_ms,
                timed_out=False,
                cwd=str(work_dir) if work_dir else None,
                timestamp=timestamp,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            logger.error(f"SHELL_ERROR: {command[:50]} - {e}")

            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {e}",
                duration_ms=duration_ms,
                timed_out=False,
                cwd=str(work_dir) if work_dir else None,
                timestamp=timestamp,
            )

    def execute_script(
        self,
        script: str,
        cwd: str | Path | None = None,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        """Execute a multi-line shell script.

        Args:
            script: Multi-line shell script
            cwd: Working directory
            timeout: Max execution time in seconds
            env: Additional environment variables

        Returns:
            CommandResult with combined output
        """
        # Wrap script in bash -c for multi-line support
        # Using heredoc-style execution
        wrapped = f'bash -c {shlex.quote(script)}'
        return self.execute(wrapped, cwd=cwd, timeout=timeout, env=env, shell=True)

    def run_in_background(
        self,
        command: str,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.Popen:
        """Start a command in the background.

        Args:
            command: Shell command to execute
            cwd: Working directory
            env: Additional environment variables

        Returns:
            Popen object for the background process

        Note:
            Caller is responsible for managing the process lifecycle.
        """
        self._validate_command(command)
        work_dir = self._resolve_cwd(cwd)
        process_env = self._build_env(env)

        logger.info(f"SHELL_BACKGROUND: {command[:100]}")

        return subprocess.Popen(
            command,
            shell=True,
            cwd=work_dir,
            env=process_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def which(self, command: str) -> str | None:
        """Find the path to a command.

        Args:
            command: Command name to find

        Returns:
            Full path to command, or None if not found
        """
        result = self.execute(f"which {shlex.quote(command)}", timeout=5)
        if result.success and result.stdout.strip():
            return result.stdout.strip()
        return None

    def _validate_command(self, command: str) -> None:
        """Validate command against security policies."""
        # Check blocklist
        command_lower = command.lower().strip()
        for blocked in self._blocked_commands:
            if blocked.lower() in command_lower:
                raise CommandNotAllowedError(command, f"Blocked command: {blocked}")

        # Check allowlist (if set)
        if self._allowed_commands is not None:
            # Extract base command (first word)
            base_cmd = command.split()[0] if command.split() else ""
            if base_cmd not in self._allowed_commands:
                raise CommandNotAllowedError(
                    command,
                    f"Command not in allowlist: {base_cmd}",
                )

    def _resolve_cwd(self, cwd: str | Path | None) -> Path | None:
        """Resolve working directory."""
        if cwd is not None:
            return Path(cwd).resolve()
        if self._default_cwd is not None:
            return self._default_cwd.resolve()
        return None

    def _build_env(self, extra_env: dict[str, str] | None) -> dict[str, str]:
        """Build environment for subprocess."""
        if self._inherit_env:
            env = os.environ.copy()
        else:
            env = {}

        if extra_env:
            env.update(extra_env)

        return env

    def _log_result(self, result: CommandResult) -> None:
        """Log command result."""
        if result.success:
            logger.info(
                f"SHELL_SUCCESS: exit={result.exit_code} "
                f"duration={result.duration_ms}ms"
            )
        else:
            logger.warning(
                f"SHELL_FAILED: exit={result.exit_code} "
                f"duration={result.duration_ms}ms"
            )
            if result.stderr:
                # Log first line of stderr
                first_line = result.stderr.split("\n")[0][:100]
                logger.warning(f"SHELL_STDERR: {first_line}")
