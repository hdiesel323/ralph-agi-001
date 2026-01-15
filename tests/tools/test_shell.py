"""Tests for ShellTools."""

from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ralph_agi.tools.shell import (
    CommandNotAllowedError,
    CommandResult,
    ShellError,
    ShellTools,
)


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_success_property(self) -> None:
        """Test success property for exit code 0."""
        result = CommandResult(
            command="echo hello",
            exit_code=0,
            stdout="hello\n",
            stderr="",
            duration_ms=10,
        )
        assert result.success is True
        assert result.failed is False

    def test_failed_property(self) -> None:
        """Test failed property for non-zero exit code."""
        result = CommandResult(
            command="false",
            exit_code=1,
            stdout="",
            stderr="error",
            duration_ms=5,
        )
        assert result.success is False
        assert result.failed is True

    def test_timed_out_is_failure(self) -> None:
        """Test that timed out command is considered failed."""
        result = CommandResult(
            command="sleep 100",
            exit_code=0,  # Even with exit 0
            stdout="",
            stderr="",
            duration_ms=1000,
            timed_out=True,
        )
        assert result.success is False
        assert result.failed is True

    def test_output_combined(self) -> None:
        """Test combined output property."""
        result = CommandResult(
            command="cmd",
            exit_code=0,
            stdout="out",
            stderr="err",
            duration_ms=10,
        )
        assert "out" in result.output
        assert "err" in result.output

    def test_output_empty(self) -> None:
        """Test output with empty stdout/stderr."""
        result = CommandResult(
            command="cmd",
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=10,
        )
        assert result.output == ""

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        result = CommandResult(
            command="test",
            exit_code=0,
            stdout="output",
            stderr="",
            duration_ms=100,
        )
        d = result.to_dict()

        assert d["command"] == "test"
        assert d["exit_code"] == 0
        assert d["stdout"] == "output"
        assert d["success"] is True
        assert "timestamp" in d


class TestShellToolsInit:
    """Tests for ShellTools initialization."""

    def test_default_init(self) -> None:
        """Test default initialization."""
        shell = ShellTools()
        assert shell._default_timeout == ShellTools.DEFAULT_TIMEOUT
        assert shell._inherit_env is True

    def test_custom_timeout(self) -> None:
        """Test custom timeout."""
        shell = ShellTools(default_timeout=30)
        assert shell._default_timeout == 30

    def test_max_timeout_capped(self) -> None:
        """Test timeout is capped at maximum."""
        shell = ShellTools(default_timeout=10000)
        assert shell._default_timeout == ShellTools.MAX_TIMEOUT

    def test_custom_cwd(self, tmp_path: Path) -> None:
        """Test custom default working directory."""
        shell = ShellTools(default_cwd=tmp_path)
        assert shell._default_cwd == tmp_path

    def test_blocked_commands(self) -> None:
        """Test custom blocked commands."""
        shell = ShellTools(blocked_commands=["dangerous"])
        assert "dangerous" in shell._blocked_commands

    def test_allowed_commands(self) -> None:
        """Test allowed commands whitelist."""
        shell = ShellTools(allowed_commands=["ls", "echo", "cat"])
        assert shell._allowed_commands == {"ls", "echo", "cat"}


class TestExecuteBasic:
    """Tests for basic command execution."""

    def test_echo_command(self) -> None:
        """Test simple echo command."""
        shell = ShellTools()
        result = shell.execute("echo hello")

        assert result.success is True
        assert result.exit_code == 0
        assert "hello" in result.stdout

    def test_command_with_args(self) -> None:
        """Test command with arguments."""
        shell = ShellTools()
        result = shell.execute("echo -n test")

        assert result.success is True
        assert "test" in result.stdout

    def test_pipe_command(self) -> None:
        """Test piped command."""
        shell = ShellTools()
        result = shell.execute("echo hello | cat")

        assert result.success is True
        assert "hello" in result.stdout

    def test_multi_command(self) -> None:
        """Test multiple commands with &&."""
        shell = ShellTools()
        result = shell.execute("echo a && echo b")

        assert result.success is True
        assert "a" in result.stdout
        assert "b" in result.stdout

    def test_failed_command(self) -> None:
        """Test command that fails."""
        shell = ShellTools()
        result = shell.execute("false")

        assert result.success is False
        assert result.exit_code != 0

    def test_command_not_found(self) -> None:
        """Test non-existent command."""
        shell = ShellTools()
        result = shell.execute("nonexistent_command_xyz123")

        assert result.success is False
        # Exit code 127 is "command not found"
        assert result.exit_code in (127, 1)

    def test_stderr_capture(self) -> None:
        """Test stderr capture."""
        shell = ShellTools()
        result = shell.execute("echo error >&2")

        assert "error" in result.stderr

    def test_duration_recorded(self) -> None:
        """Test duration is recorded."""
        shell = ShellTools()
        result = shell.execute("echo fast")

        assert result.duration_ms >= 0

    def test_timestamp_recorded(self) -> None:
        """Test timestamp is recorded."""
        shell = ShellTools()
        before = datetime.now(timezone.utc)
        result = shell.execute("echo test")
        after = datetime.now(timezone.utc)

        assert before <= result.timestamp <= after


class TestExecuteWithCwd:
    """Tests for command execution with working directory."""

    def test_cwd_changes_directory(self, tmp_path: Path) -> None:
        """Test working directory is respected."""
        shell = ShellTools()

        # Create a file in tmp
        (tmp_path / "marker.txt").write_text("found")

        result = shell.execute("cat marker.txt", cwd=tmp_path)

        assert result.success is True
        assert "found" in result.stdout

    def test_cwd_recorded(self, tmp_path: Path) -> None:
        """Test cwd is recorded in result."""
        shell = ShellTools()
        result = shell.execute("pwd", cwd=tmp_path)

        assert result.cwd is not None
        assert str(tmp_path.resolve()) in result.cwd

    def test_default_cwd_used(self, tmp_path: Path) -> None:
        """Test default cwd is used."""
        shell = ShellTools(default_cwd=tmp_path)
        result = shell.execute("pwd")

        assert str(tmp_path.resolve()) in result.stdout


class TestExecuteWithTimeout:
    """Tests for timeout handling."""

    def test_command_within_timeout(self) -> None:
        """Test command completes within timeout."""
        shell = ShellTools()
        result = shell.execute("echo fast", timeout=10)

        assert result.success is True
        assert result.timed_out is False

    def test_command_timeout(self) -> None:
        """Test command exceeds timeout."""
        shell = ShellTools()
        result = shell.execute("sleep 10", timeout=0.1)

        assert result.timed_out is True
        assert result.success is False

    def test_timeout_capped(self) -> None:
        """Test timeout is capped at maximum."""
        shell = ShellTools()
        # Should not actually wait this long
        result = shell.execute("echo fast", timeout=10000)

        assert result.success is True


class TestExecuteWithEnv:
    """Tests for environment variable handling."""

    def test_custom_env_var(self) -> None:
        """Test custom environment variable."""
        shell = ShellTools()
        result = shell.execute("echo $MY_TEST_VAR", env={"MY_TEST_VAR": "hello123"})

        assert "hello123" in result.stdout

    def test_inherit_env(self) -> None:
        """Test environment inheritance."""
        shell = ShellTools(inherit_env=True)
        result = shell.execute("echo $PATH")

        # PATH should be non-empty
        assert len(result.stdout.strip()) > 0

    def test_no_inherit_env(self) -> None:
        """Test without environment inheritance."""
        shell = ShellTools(inherit_env=False)
        result = shell.execute("echo ${MY_VAR:-empty}", env={})

        # Should show empty or fail
        assert "empty" in result.stdout or result.stdout.strip() == ""


class TestCommandValidation:
    """Tests for command security validation."""

    def test_blocked_command_rejected(self) -> None:
        """Test blocked command is rejected."""
        shell = ShellTools(blocked_commands=["dangerous_cmd"])

        with pytest.raises(CommandNotAllowedError) as exc:
            shell.execute("dangerous_cmd arg")

        assert "dangerous_cmd" in str(exc.value)

    def test_default_blocked_commands(self) -> None:
        """Test default dangerous commands are blocked."""
        shell = ShellTools()

        with pytest.raises(CommandNotAllowedError):
            shell.execute("rm -rf /")

    def test_allowed_commands_whitelist(self) -> None:
        """Test only allowed commands work."""
        shell = ShellTools(allowed_commands=["echo", "cat"])

        # Allowed command works
        result = shell.execute("echo hello")
        assert result.success is True

        # Non-allowed command rejected
        with pytest.raises(CommandNotAllowedError) as exc:
            shell.execute("ls -la")

        assert "not in allowlist" in str(exc.value)


class TestExecuteScript:
    """Tests for multi-line script execution."""

    def test_simple_script(self) -> None:
        """Test simple multi-line script."""
        shell = ShellTools()
        script = """
echo "line 1"
echo "line 2"
"""
        result = shell.execute_script(script)

        assert result.success is True
        assert "line 1" in result.stdout
        assert "line 2" in result.stdout

    def test_script_with_variables(self) -> None:
        """Test script with variables."""
        shell = ShellTools()
        script = """
VAR="hello"
echo $VAR
"""
        result = shell.execute_script(script)

        assert result.success is True
        assert "hello" in result.stdout

    def test_script_with_conditionals(self) -> None:
        """Test script with conditionals."""
        shell = ShellTools()
        script = """
if true; then
    echo "yes"
fi
"""
        result = shell.execute_script(script)

        assert result.success is True
        assert "yes" in result.stdout


class TestRunInBackground:
    """Tests for background process execution."""

    def test_background_process(self) -> None:
        """Test starting background process."""
        shell = ShellTools()
        process = shell.run_in_background("sleep 0.1 && echo done")

        try:
            assert process.poll() is None  # Still running initially
            process.wait(timeout=5)
            stdout, _ = process.communicate(timeout=1)
            assert "done" in stdout or process.returncode == 0
        finally:
            process.kill()

    def test_background_returns_popen(self) -> None:
        """Test background returns Popen object."""
        shell = ShellTools()
        process = shell.run_in_background("echo test")

        try:
            assert isinstance(process, subprocess.Popen)
        finally:
            process.wait(timeout=5)


class TestWhich:
    """Tests for which command."""

    def test_which_existing_command(self) -> None:
        """Test finding existing command."""
        shell = ShellTools()
        result = shell.which("echo")

        assert result is not None
        assert "echo" in result

    def test_which_nonexistent_command(self) -> None:
        """Test finding non-existent command."""
        shell = ShellTools()
        result = shell.which("nonexistent_xyz123")

        assert result is None


class TestShellIntegration:
    """Integration tests for realistic shell usage."""

    def test_run_python_command(self) -> None:
        """Test running Python via shell."""
        shell = ShellTools()
        result = shell.execute('python3 -c "print(1+1)"')

        assert result.success is True
        assert "2" in result.stdout

    def test_check_git_version(self) -> None:
        """Test checking git version."""
        shell = ShellTools()
        result = shell.execute("git --version")

        assert result.success is True
        assert "git" in result.stdout.lower()

    def test_run_pytest_help(self) -> None:
        """Test running pytest help."""
        shell = ShellTools()
        result = shell.execute("python3 -m pytest --version", timeout=30)

        assert result.success is True
        assert "pytest" in result.stdout.lower()

    def test_file_operations(self, tmp_path: Path) -> None:
        """Test file operations via shell."""
        shell = ShellTools()

        # Create, read, delete
        result = shell.execute(
            f'echo "test content" > test.txt && cat test.txt && rm test.txt',
            cwd=tmp_path,
        )

        assert result.success is True
        assert "test content" in result.stdout
