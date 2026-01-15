"""Tests for wake hooks execution."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ralph_agi.scheduler.config import WakeHook
from ralph_agi.scheduler.hooks import (
    HookExecutionResult,
    HookResult,
    WakeHookExecutor,
)


class TestHookExecutionResult:
    """Tests for HookExecutionResult dataclass."""

    def test_success_result(self):
        """Should create success result."""
        result = HookExecutionResult(
            hook="test",
            result=HookResult.SUCCESS,
            message="Test passed",
            duration_ms=100,
        )
        assert result.result == HookResult.SUCCESS
        assert result.message == "Test passed"

    def test_failure_result(self):
        """Should create failure result."""
        result = HookExecutionResult(
            hook="test",
            result=HookResult.FAILURE,
            message="Test failed",
            duration_ms=50,
        )
        assert result.result == HookResult.FAILURE

    def test_result_with_data(self):
        """Should store optional data."""
        result = HookExecutionResult(
            hook="test",
            result=HookResult.SUCCESS,
            message="OK",
            duration_ms=10,
            data={"key": "value"},
        )
        assert result.data == {"key": "value"}


class TestWakeHookExecutor:
    """Tests for WakeHookExecutor class."""

    def test_create_executor(self):
        """Should create executor with optional paths."""
        executor = WakeHookExecutor(
            prd_path="/path/to/PRD.json",
            config_path="/path/to/config.yaml",
        )
        assert executor.prd_path == "/path/to/PRD.json"
        assert executor.config_path == "/path/to/config.yaml"

    def test_unknown_hook_skipped(self):
        """Unknown hooks should be skipped."""
        executor = WakeHookExecutor()
        results = executor.execute(["unknown_hook"])
        assert len(results) == 1
        assert results[0].result == HookResult.SKIPPED
        assert "unknown" in results[0].message.lower()

    def test_register_custom_hook(self):
        """Should be able to register custom hooks."""
        executor = WakeHookExecutor()

        def custom_handler():
            return HookExecutionResult(
                hook="custom",
                result=HookResult.SUCCESS,
                message="Custom hook ran",
                duration_ms=0,
            )

        executor.register_hook("custom", custom_handler)
        results = executor.execute(["custom"])

        assert len(results) == 1
        assert results[0].result == HookResult.SUCCESS
        assert results[0].hook == "custom"

    def test_execute_multiple_hooks(self):
        """Should execute multiple hooks in order."""
        executor = WakeHookExecutor()

        def hook1():
            return HookExecutionResult("h1", HookResult.SUCCESS, "OK", 0)

        def hook2():
            return HookExecutionResult("h2", HookResult.SUCCESS, "OK", 0)

        executor.register_hook("h1", hook1)
        executor.register_hook("h2", hook2)

        results = executor.execute(["h1", "h2"])
        assert len(results) == 2
        assert results[0].hook == "h1"
        assert results[1].hook == "h2"


class TestCheckProgressHook:
    """Tests for check_progress wake hook."""

    def test_no_prd_path_skips(self):
        """Should skip if no PRD path configured."""
        executor = WakeHookExecutor(prd_path=None)
        results = executor.execute([WakeHook.CHECK_PROGRESS.value])
        assert results[0].result == HookResult.SKIPPED

    def test_missing_prd_file_fails(self):
        """Should fail if PRD file doesn't exist."""
        executor = WakeHookExecutor(prd_path="/nonexistent/PRD.json")
        results = executor.execute([WakeHook.CHECK_PROGRESS.value])
        assert results[0].result == HookResult.FAILURE

    def test_valid_prd_succeeds(self, tmp_path):
        """Should succeed with valid PRD file."""
        prd_file = tmp_path / "PRD.json"
        prd_data = {
            "tasks": [
                {"id": "1", "status": "complete"},
                {"id": "2", "status": "in_progress"},
                {"id": "3", "status": "pending"},
            ]
        }
        prd_file.write_text(json.dumps(prd_data))

        executor = WakeHookExecutor(prd_path=str(prd_file))
        results = executor.execute([WakeHook.CHECK_PROGRESS.value])

        assert results[0].result == HookResult.SUCCESS
        assert results[0].data["total_tasks"] == 3
        assert results[0].data["complete"] == 1
        assert results[0].data["in_progress"] == 1
        assert results[0].data["pending"] == 1


class TestRunTestsHook:
    """Tests for run_tests wake hook."""

    @patch("subprocess.run")
    def test_tests_pass(self, mock_run):
        """Should succeed when tests pass."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="5 passed in 1.2s",
            stderr="",
        )

        executor = WakeHookExecutor()
        results = executor.execute([WakeHook.RUN_TESTS.value])

        assert results[0].result == HookResult.SUCCESS
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_tests_fail(self, mock_run):
        """Should fail when tests fail."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="2 failed",
        )

        executor = WakeHookExecutor()
        results = executor.execute([WakeHook.RUN_TESTS.value])

        assert results[0].result == HookResult.FAILURE

    @patch("subprocess.run")
    def test_pytest_not_found(self, mock_run):
        """Should skip if pytest not found."""
        mock_run.side_effect = FileNotFoundError("pytest not found")

        executor = WakeHookExecutor()
        results = executor.execute([WakeHook.RUN_TESTS.value])

        assert results[0].result == HookResult.SKIPPED


class TestResumeCheckpointHook:
    """Tests for resume_checkpoint wake hook."""

    def test_no_checkpoint_path_skips(self):
        """Should skip if no checkpoint path configured."""
        executor = WakeHookExecutor(checkpoint_path=None)
        results = executor.execute([WakeHook.RESUME_CHECKPOINT.value])
        assert results[0].result == HookResult.SKIPPED

    def test_no_checkpoint_file_succeeds(self, tmp_path):
        """Should succeed with message if no checkpoint exists."""
        checkpoint_path = tmp_path / "checkpoint.json"
        # Don't create the file

        executor = WakeHookExecutor(checkpoint_path=str(checkpoint_path))
        results = executor.execute([WakeHook.RESUME_CHECKPOINT.value])

        assert results[0].result == HookResult.SUCCESS
        assert results[0].data["has_checkpoint"] is False

    def test_valid_checkpoint_succeeds(self, tmp_path):
        """Should succeed and report checkpoint details."""
        checkpoint_path = tmp_path / "checkpoint.json"
        checkpoint_data = {
            "iteration": 5,
            "session_id": "abc123def456",
        }
        checkpoint_path.write_text(json.dumps(checkpoint_data))

        executor = WakeHookExecutor(checkpoint_path=str(checkpoint_path))
        results = executor.execute([WakeHook.RESUME_CHECKPOINT.value])

        assert results[0].result == HookResult.SUCCESS
        assert results[0].data["has_checkpoint"] is True
        assert results[0].data["iteration"] == 5


class TestSendStatusHook:
    """Tests for send_status wake hook."""

    def test_always_succeeds(self):
        """Send status should always succeed."""
        executor = WakeHookExecutor()
        results = executor.execute([WakeHook.SEND_STATUS.value])
        assert results[0].result == HookResult.SUCCESS
