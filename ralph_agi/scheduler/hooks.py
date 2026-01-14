"""Wake hooks framework for RALPH-AGI scheduler.

Executes configured hooks when the scheduler triggers a wake event.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from ralph_agi.scheduler.config import WakeHook


class HookResult(str, Enum):
    """Result status of a hook execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


@dataclass
class HookExecutionResult:
    """Result of executing a wake hook.

    Attributes:
        hook: The hook that was executed.
        result: Success, failure, or skipped status.
        message: Human-readable result message.
        duration_ms: Execution time in milliseconds.
        data: Optional data returned by the hook.
    """

    hook: str
    result: HookResult
    message: str
    duration_ms: int
    data: Optional[dict[str, Any]] = None


class WakeHookExecutor:
    """Executes wake hooks on scheduled trigger.

    Provides built-in hooks for common AFK operations and supports
    custom hook registration.
    """

    def __init__(
        self,
        prd_path: Optional[str] = None,
        config_path: Optional[str] = None,
        checkpoint_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the hook executor.

        Args:
            prd_path: Path to PRD.json.
            config_path: Path to config.yaml.
            checkpoint_path: Path to checkpoint file.
            logger: Optional logger instance.
        """
        self.prd_path = prd_path
        self.config_path = config_path
        self.checkpoint_path = checkpoint_path
        self.logger = logger or logging.getLogger(__name__)
        self._custom_hooks: dict[str, Callable[[], HookExecutionResult]] = {}

        # Register built-in hooks
        self._builtin_hooks = {
            WakeHook.CHECK_PROGRESS.value: self._check_progress,
            WakeHook.RUN_TESTS.value: self._run_tests,
            WakeHook.COMMIT_IF_READY.value: self._commit_if_ready,
            WakeHook.RESUME_CHECKPOINT.value: self._resume_checkpoint,
            WakeHook.SEND_STATUS.value: self._send_status,
        }

    def register_hook(
        self, name: str, handler: Callable[[], HookExecutionResult]
    ) -> None:
        """Register a custom wake hook.

        Args:
            name: Unique name for the hook.
            handler: Callable that returns HookExecutionResult.
        """
        self._custom_hooks[name] = handler
        self.logger.info(f"Registered custom hook: {name}")

    def execute(self, hooks: list[str]) -> list[HookExecutionResult]:
        """Execute a list of wake hooks in order.

        Args:
            hooks: List of hook names to execute.

        Returns:
            List of execution results.
        """
        results = []
        for hook_name in hooks:
            result = self._execute_single(hook_name)
            results.append(result)

            # Log result
            if result.result == HookResult.SUCCESS:
                self.logger.info(f"Hook {hook_name}: {result.message}")
            elif result.result == HookResult.FAILURE:
                self.logger.error(f"Hook {hook_name} failed: {result.message}")
            else:
                self.logger.warning(f"Hook {hook_name} skipped: {result.message}")

        return results

    def _execute_single(self, hook_name: str) -> HookExecutionResult:
        """Execute a single hook.

        Args:
            hook_name: Name of the hook to execute.

        Returns:
            Execution result.
        """
        start_time = datetime.now()

        # Find the hook handler
        handler = self._builtin_hooks.get(hook_name) or self._custom_hooks.get(hook_name)

        if handler is None:
            return HookExecutionResult(
                hook=hook_name,
                result=HookResult.SKIPPED,
                message=f"Unknown hook: {hook_name}",
                duration_ms=0,
            )

        try:
            result = handler()
            result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return result
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return HookExecutionResult(
                hook=hook_name,
                result=HookResult.FAILURE,
                message=str(e),
                duration_ms=duration_ms,
            )

    def _check_progress(self) -> HookExecutionResult:
        """Check if tasks are making progress.

        Reads the PRD to determine task completion status.
        """
        if not self.prd_path:
            return HookExecutionResult(
                hook=WakeHook.CHECK_PROGRESS.value,
                result=HookResult.SKIPPED,
                message="No PRD path configured",
                duration_ms=0,
            )

        prd_file = Path(self.prd_path)
        if not prd_file.exists():
            return HookExecutionResult(
                hook=WakeHook.CHECK_PROGRESS.value,
                result=HookResult.FAILURE,
                message=f"PRD file not found: {self.prd_path}",
                duration_ms=0,
            )

        try:
            import json

            with open(prd_file) as f:
                prd_data = json.load(f)

            # Count task statuses
            tasks = prd_data.get("tasks", [])
            total = len(tasks)
            complete = sum(1 for t in tasks if t.get("status") == "complete")
            in_progress = sum(1 for t in tasks if t.get("status") == "in_progress")
            pending = total - complete - in_progress

            data = {
                "total_tasks": total,
                "complete": complete,
                "in_progress": in_progress,
                "pending": pending,
                "progress_pct": round(complete / total * 100, 1) if total > 0 else 0,
            }

            return HookExecutionResult(
                hook=WakeHook.CHECK_PROGRESS.value,
                result=HookResult.SUCCESS,
                message=f"Progress: {complete}/{total} tasks complete ({data['progress_pct']}%)",
                duration_ms=0,
                data=data,
            )
        except Exception as e:
            return HookExecutionResult(
                hook=WakeHook.CHECK_PROGRESS.value,
                result=HookResult.FAILURE,
                message=f"Failed to check progress: {e}",
                duration_ms=0,
            )

    def _run_tests(self) -> HookExecutionResult:
        """Run the test suite."""
        try:
            result = subprocess.run(
                ["pytest", "--tb=short", "-q"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                # Parse output for test count
                lines = result.stdout.strip().split("\n")
                summary = lines[-1] if lines else "Tests passed"

                return HookExecutionResult(
                    hook=WakeHook.RUN_TESTS.value,
                    result=HookResult.SUCCESS,
                    message=summary,
                    duration_ms=0,
                    data={"returncode": 0, "output": result.stdout[-500:]},
                )
            else:
                return HookExecutionResult(
                    hook=WakeHook.RUN_TESTS.value,
                    result=HookResult.FAILURE,
                    message=f"Tests failed with code {result.returncode}",
                    duration_ms=0,
                    data={
                        "returncode": result.returncode,
                        "stdout": result.stdout[-500:],
                        "stderr": result.stderr[-500:],
                    },
                )
        except subprocess.TimeoutExpired:
            return HookExecutionResult(
                hook=WakeHook.RUN_TESTS.value,
                result=HookResult.FAILURE,
                message="Test execution timed out (5 minutes)",
                duration_ms=300000,
            )
        except FileNotFoundError:
            return HookExecutionResult(
                hook=WakeHook.RUN_TESTS.value,
                result=HookResult.SKIPPED,
                message="pytest not found",
                duration_ms=0,
            )

    def _commit_if_ready(self) -> HookExecutionResult:
        """Commit changes if work is ready to commit."""
        try:
            # Check for uncommitted changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
            )

            if not status_result.stdout.strip():
                return HookExecutionResult(
                    hook=WakeHook.COMMIT_IF_READY.value,
                    result=HookResult.SKIPPED,
                    message="No changes to commit",
                    duration_ms=0,
                )

            # Stage and commit
            subprocess.run(["git", "add", "-A"], check=True)

            commit_result = subprocess.run(
                ["git", "commit", "-m", "chore: Auto-commit from scheduled wake"],
                capture_output=True,
                text=True,
            )

            if commit_result.returncode == 0:
                return HookExecutionResult(
                    hook=WakeHook.COMMIT_IF_READY.value,
                    result=HookResult.SUCCESS,
                    message="Changes committed successfully",
                    duration_ms=0,
                )
            else:
                return HookExecutionResult(
                    hook=WakeHook.COMMIT_IF_READY.value,
                    result=HookResult.FAILURE,
                    message=commit_result.stderr,
                    duration_ms=0,
                )
        except subprocess.CalledProcessError as e:
            return HookExecutionResult(
                hook=WakeHook.COMMIT_IF_READY.value,
                result=HookResult.FAILURE,
                message=str(e),
                duration_ms=0,
            )

    def _resume_checkpoint(self) -> HookExecutionResult:
        """Resume from the last checkpoint.

        This hook prepares for resumption but doesn't actually run the loop.
        The daemon will invoke the loop after hooks complete.
        """
        checkpoint_file = Path(self.checkpoint_path) if self.checkpoint_path else None

        if checkpoint_file is None:
            return HookExecutionResult(
                hook=WakeHook.RESUME_CHECKPOINT.value,
                result=HookResult.SKIPPED,
                message="No checkpoint path configured",
                duration_ms=0,
            )

        if not checkpoint_file.exists():
            return HookExecutionResult(
                hook=WakeHook.RESUME_CHECKPOINT.value,
                result=HookResult.SUCCESS,
                message="No checkpoint to resume from, will start fresh",
                duration_ms=0,
                data={"has_checkpoint": False},
            )

        try:
            import json

            with open(checkpoint_file) as f:
                checkpoint_data = json.load(f)

            iteration = checkpoint_data.get("iteration", 0)
            session_id = checkpoint_data.get("session_id", "unknown")

            return HookExecutionResult(
                hook=WakeHook.RESUME_CHECKPOINT.value,
                result=HookResult.SUCCESS,
                message=f"Ready to resume from iteration {iteration} (session: {session_id[:8]}...)",
                duration_ms=0,
                data={
                    "has_checkpoint": True,
                    "iteration": iteration,
                    "session_id": session_id,
                },
            )
        except Exception as e:
            return HookExecutionResult(
                hook=WakeHook.RESUME_CHECKPOINT.value,
                result=HookResult.FAILURE,
                message=f"Failed to load checkpoint: {e}",
                duration_ms=0,
            )

    def _send_status(self) -> HookExecutionResult:
        """Send a status notification.

        Currently logs status. Can be extended for email/Slack/webhook.
        """
        self.logger.info("Status notification: RALPH-AGI scheduler wake event")

        return HookExecutionResult(
            hook=WakeHook.SEND_STATUS.value,
            result=HookResult.SUCCESS,
            message="Status logged (extend for email/Slack/webhook)",
            duration_ms=0,
        )
