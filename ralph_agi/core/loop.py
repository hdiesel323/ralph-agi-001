"""Ralph Loop Engine - The core execution loop for RALPH-AGI.

This module implements the central mechanism that drives all agent activity,
processing one task at a time until all tasks are complete or max iterations reached.

Key Design Principles (from PRD FR-001):
- Uses WHILE loop (not FOR) for cleaner exit conditions
- Single task per iteration to prevent context bloat
- Comprehensive logging with timestamps
- Retry logic with exponential backoff
"""

from __future__ import annotations

import json
import logging
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional
from uuid import uuid4

if TYPE_CHECKING:
    from ralph_agi.core.config import RalphConfig
    from ralph_agi.memory.store import MemoryStore


@dataclass
class IterationResult:
    """Result of a single loop iteration.

    Attributes:
        success: Whether the iteration completed successfully.
        output: Optional output string from the iteration (for completion detection).
    """

    success: bool
    output: Optional[str] = None


class MaxRetriesExceeded(Exception):
    """Raised when maximum retry attempts are exhausted."""

    def __init__(self, message: str, attempts: int, last_error: Optional[Exception] = None):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


class LoopInterrupted(Exception):
    """Raised when the loop is interrupted by a signal (SIGINT/SIGTERM)."""

    def __init__(self, message: str, iteration: int, checkpoint_path: Optional[str] = None):
        super().__init__(message)
        self.iteration = iteration
        self.checkpoint_path = checkpoint_path


class RalphLoop:
    """The Ralph Loop Engine - core execution loop for RALPH-AGI.

    Implements the iterative cycle that processes tasks one at a time:
    1. Load Context
    2. Select Task
    3. Execute Task
    4. Verify
    5. Update State
    6. Check Completion

    Attributes:
        max_iterations: Maximum number of iterations before forced exit (default: 100)
        iteration: Current iteration number (0-indexed)
        complete: Whether the loop has received a completion signal
    """

    # Default retry configuration
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds

    def __init__(
        self,
        max_iterations: int = 100,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delays: Optional[list[int]] = None,
        log_file: Optional[str] = None,
        completion_promise: str = "<promise>COMPLETE</promise>",
        checkpoint_path: Optional[str] = None,
        memory_store: Optional[MemoryStore] = None,
        session_id: Optional[str] = None,
    ):
        """Initialize the Ralph Loop Engine.

        Args:
            max_iterations: Maximum iterations before forced exit. Default: 100
            max_retries: Maximum retry attempts per iteration. Default: 3
            retry_delays: List of delays (seconds) for exponential backoff.
                         Default: [1, 2, 4]
            log_file: Optional path to log file. If provided, logs to both
                     console and file.
            completion_promise: String to detect for task completion.
                         Default: "<promise>COMPLETE</promise>"
            checkpoint_path: Optional path for saving checkpoints on interrupt.
                         Default: None (no checkpointing)
            memory_store: Optional MemoryStore for persistent memory.
                         Default: None (no memory)
            session_id: Optional session identifier. If not provided, a new
                       UUID will be generated. Default: None
        """
        if max_iterations < 0:
            raise ValueError("max_iterations must be non-negative")

        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.retry_delays = retry_delays or self.DEFAULT_RETRY_DELAYS.copy()

        self.iteration = 0
        self.complete = False
        self._completion_signal = completion_promise
        self._checkpoint_path = checkpoint_path
        self._interrupted = False
        self._original_sigint_handler = None
        self._original_sigterm_handler = None

        # Session management
        self.session_id = session_id or str(uuid4())

        # Memory store (optional)
        self._memory_store = memory_store

        # Set up logging
        self._setup_logging(log_file)

    @classmethod
    def from_config(cls, config: RalphConfig) -> RalphLoop:
        """Create a RalphLoop instance from a RalphConfig.

        Args:
            config: RalphConfig instance with configuration values.

        Returns:
            Configured RalphLoop instance.
        """
        # Create memory store if enabled
        memory_store = None
        if config.memory_enabled:
            from ralph_agi.memory.store import MemoryStore
            memory_store = MemoryStore(config.memory_store_path)

        return cls(
            max_iterations=config.max_iterations,
            max_retries=config.max_retries,
            retry_delays=config.retry_delays,
            log_file=config.log_file,
            completion_promise=config.completion_promise,
            checkpoint_path=config.checkpoint_path,
            memory_store=memory_store,
        )

    def _setup_logging(self, log_file: Optional[str] = None) -> None:
        """Configure logging with ISO timestamp format.

        Args:
            log_file: Optional path to log file for dual output.
        """
        # Use instance-specific logger name to avoid conflicts with multiple RalphLoop instances
        self._logger_name = f"ralph-agi.{id(self)}"
        self.logger = logging.getLogger(self._logger_name)
        self.logger.setLevel(logging.DEBUG)
        # Note: propagate=True (default) allows pytest caplog to capture logs

        # Track handlers for cleanup
        self._handlers: list[logging.Handler] = []

        # Custom formatter with ISO timestamp in brackets
        class BracketedTimestampFormatter(logging.Formatter):
            def format(self, record):
                timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
                record.bracketed_time = f"[{timestamp}]"
                return super().format(record)

        formatter = BracketedTimestampFormatter(
            "%(bracketed_time)s %(message)s"
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        self._handlers.append(console_handler)

        # File handler (if specified)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            self._handlers.append(file_handler)

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful interrupt handling."""
        self._original_sigint_handler = signal.signal(signal.SIGINT, self._handle_interrupt)
        self._original_sigterm_handler = signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        if self._original_sigint_handler is not None:
            signal.signal(signal.SIGINT, self._original_sigint_handler)
        if self._original_sigterm_handler is not None:
            signal.signal(signal.SIGTERM, self._original_sigterm_handler)

    def _handle_interrupt(self, signum: int, frame: Any) -> None:
        """Handle interrupt signals (SIGINT/SIGTERM).

        Sets the interrupted flag to allow graceful shutdown.
        """
        signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        self.logger.warning(f"Received {signal_name}, initiating graceful shutdown...")
        self._interrupted = True

    def get_state(self) -> dict[str, Any]:
        """Get current loop state for checkpointing.

        Returns:
            Dictionary containing current loop state.
        """
        return {
            "iteration": self.iteration,
            "complete": self.complete,
            "max_iterations": self.max_iterations,
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def save_checkpoint(self, path: Optional[str] = None) -> str:
        """Save current state to a checkpoint file.

        Args:
            path: Path to save checkpoint. Uses _checkpoint_path if not provided.

        Returns:
            Path where checkpoint was saved.

        Raises:
            ValueError: If no checkpoint path is available.
        """
        checkpoint_path = path or self._checkpoint_path
        if not checkpoint_path:
            raise ValueError("No checkpoint path specified")

        state = self.get_state()
        checkpoint_file = Path(checkpoint_path)
        checkpoint_file.write_text(json.dumps(state, indent=2))

        self.logger.info(f"Checkpoint saved to {checkpoint_path}")
        return str(checkpoint_path)

    def load_checkpoint(self, path: Optional[str] = None) -> dict[str, Any]:
        """Load state from a checkpoint file.

        Args:
            path: Path to load checkpoint from. Uses _checkpoint_path if not provided.

        Returns:
            Dictionary containing loaded state.

        Raises:
            ValueError: If no checkpoint path is available.
            FileNotFoundError: If checkpoint file doesn't exist.
        """
        checkpoint_path = path or self._checkpoint_path
        if not checkpoint_path:
            raise ValueError("No checkpoint path specified")

        checkpoint_file = Path(checkpoint_path)
        if not checkpoint_file.exists():
            raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_path}")

        state = json.loads(checkpoint_file.read_text())
        self.logger.info(f"Checkpoint loaded from {checkpoint_path}")
        return state

    def resume_from_checkpoint(self, path: Optional[str] = None) -> None:
        """Resume loop state from a checkpoint file.

        Args:
            path: Path to load checkpoint from. Uses _checkpoint_path if not provided.
        """
        state = self.load_checkpoint(path)
        self.iteration = state.get("iteration", 0)
        self.complete = state.get("complete", False)
        # Restore session_id if available, otherwise keep the current one
        if "session_id" in state:
            self.session_id = state["session_id"]
        self.logger.info(f"Resumed from iteration {self.iteration} (session: {self.session_id[:8]}...)")

    def _log_iteration_start(self) -> None:
        """Log the start of an iteration with timestamp and iteration number."""
        self.logger.info(
            f"Iteration {self.iteration + 1}/{self.max_iterations}: Starting..."
        )

    def _log_iteration_end(self, success: bool, message: str = "") -> None:
        """Log the end of an iteration with status.

        Args:
            success: Whether the iteration completed successfully.
            message: Optional additional message.
        """
        status = "Success" if success else "Failed"
        msg = f"Iteration {self.iteration + 1}/{self.max_iterations}: {status}"
        if message:
            msg += f" - {message}"

        if success:
            self.logger.info(msg)
        else:
            self.logger.error(msg)

    def _execute_iteration(self) -> IterationResult:
        """Execute a single iteration of the loop.

        This is a stub implementation for Story 1.1. Future stories will
        implement actual task execution logic.

        Returns:
            IterationResult with success status and optional output.
        """
        # Stub implementation - to be expanded in future stories
        # For now, just returns success with no output
        return IterationResult(success=True, output=None)

    def _check_completion(self, output: Optional[str] = None) -> bool:
        """Check if the completion signal has been received.

        Args:
            output: Optional output string to check for completion signal.

        Returns:
            True if completion signal detected, False otherwise.
        """
        if output and self._completion_signal in output:
            return True
        return False

    def _store_iteration_result(self, result: IterationResult) -> Optional[str]:
        """Store an iteration result in memory.

        Args:
            result: The IterationResult from the completed iteration.

        Returns:
            Frame ID if stored successfully, None otherwise.
        """
        if self._memory_store is None:
            return None

        try:
            content = f"Iteration {self.iteration + 1} {'completed successfully' if result.success else 'failed'}"
            if result.output:
                content += f": {result.output[:500]}"  # Truncate long outputs

            frame_id = self._memory_store.append(
                content=content,
                frame_type="iteration_result",
                metadata={
                    "iteration": self.iteration + 1,
                    "success": result.success,
                    "has_output": result.output is not None,
                },
                session_id=self.session_id,
                tags=["iteration", f"iter-{self.iteration + 1}"],
            )
            self.logger.debug(f"Stored iteration result as frame {frame_id[:8]}")
            return frame_id

        except Exception as e:
            self.logger.warning(f"Failed to store iteration result in memory: {e}")
            return None

    def get_context(self, n: int = 10) -> list[Any]:
        """Get recent context from memory for the current session.

        Args:
            n: Maximum number of frames to retrieve. Default: 10

        Returns:
            List of MemoryFrame objects, most recent first.
        """
        if self._memory_store is None:
            return []

        try:
            return self._memory_store.get_by_session(self.session_id, limit=n)
        except Exception as e:
            self.logger.warning(f"Failed to load context from memory: {e}")
            return []

    def get_recent_context(self, n: int = 10) -> list[Any]:
        """Get recent context from memory across all sessions.

        Args:
            n: Maximum number of frames to retrieve. Default: 10

        Returns:
            List of MemoryFrame objects, most recent first.
        """
        if self._memory_store is None:
            return []

        try:
            return self._memory_store.get_recent(n)
        except Exception as e:
            self.logger.warning(f"Failed to load recent context from memory: {e}")
            return []

    def _execute_with_retry(
        self,
        func: Callable[[], IterationResult],
    ) -> IterationResult:
        """Execute a function with retry logic and exponential backoff.

        Args:
            func: The function to execute. Should return IterationResult.

        Returns:
            IterationResult if function succeeded (possibly after retries).

        Raises:
            MaxRetriesExceeded: If all retry attempts are exhausted.
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                result = func()
                if result.success:
                    return result
                # Function returned failure status - treat as failure
                raise RuntimeError("Iteration returned failure status")
            except Exception as e:
                last_error = e

                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    self.logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                        f"No more retries."
                    )

        raise MaxRetriesExceeded(
            f"Failed after {self.max_retries} attempts",
            attempts=self.max_retries,
            last_error=last_error,
        )

    def run(self, handle_signals: bool = True) -> bool:
        """Run the Ralph Loop until completion or max iterations.

        The loop continues while:
        - iteration < max_iterations AND
        - complete flag is False AND
        - not interrupted

        Args:
            handle_signals: Whether to set up signal handlers for graceful
                          interrupt handling. Default: True

        Returns:
            True if completed successfully (via completion signal),
            False if exited due to max iterations.

        Raises:
            MaxRetriesExceeded: If an iteration fails after all retries.
            LoopInterrupted: If interrupted by SIGINT/SIGTERM (with checkpoint saved).
        """
        self.logger.info(
            f"Ralph Loop starting (session: {self.session_id[:8]}..., max_iterations={self.max_iterations})"
        )

        # Set up signal handlers for AFK mode
        if handle_signals:
            self._setup_signal_handlers()

        try:
            # Handle edge case of 0 max iterations
            if self.max_iterations == 0:
                self.logger.info("Max iterations is 0, exiting immediately")
                return False

            # Main loop - use WHILE (not FOR) for cleaner exit conditions
            while self.iteration < self.max_iterations and not self.complete:
                # Check for interrupt before starting iteration
                if self._interrupted:
                    self._handle_graceful_shutdown()

                self._log_iteration_start()

                try:
                    # Execute with retry logic
                    result = self._execute_with_retry(self._execute_iteration)
                    self._log_iteration_end(result.success)

                    # Store iteration result in memory (non-blocking)
                    self._store_iteration_result(result)

                    # Check for completion signal in the iteration output
                    if self._check_completion(result.output):
                        self.complete = True
                        self.logger.info(
                            f"Completion signal detected after {self.iteration + 1} iterations"
                        )
                        break

                    self.iteration += 1

                    # Check for interrupt after completing iteration
                    if self._interrupted:
                        self._handle_graceful_shutdown()

                except MaxRetriesExceeded as e:
                    self._log_iteration_end(False, str(e))
                    raise

            # Log final status
            if self.complete:
                self.logger.info(
                    f"Ralph Loop completed successfully after {self.iteration + 1} iterations"
                )
                return True
            else:
                self.logger.info(
                    f"Ralph Loop reached max iterations ({self.max_iterations})"
                )
                return False

        finally:
            # Always restore signal handlers
            if handle_signals:
                self._restore_signal_handlers()

    def _handle_graceful_shutdown(self) -> None:
        """Handle graceful shutdown on interrupt.

        Saves checkpoint if path is configured, then raises LoopInterrupted.
        """
        checkpoint_path = None
        if self._checkpoint_path:
            checkpoint_path = self.save_checkpoint()

        self.logger.info(
            f"Graceful shutdown complete at iteration {self.iteration + 1}"
        )

        raise LoopInterrupted(
            f"Loop interrupted at iteration {self.iteration + 1}",
            iteration=self.iteration,
            checkpoint_path=checkpoint_path,
        )

    def set_complete(self) -> None:
        """Manually set the completion flag.

        This can be used to signal completion from external code.
        """
        self.complete = True

    def close(self) -> None:
        """Clean up resources (logging handlers, file handles, memory store).

        Should be called when the RalphLoop instance is no longer needed,
        especially if log_file was specified.
        """
        # Close memory store
        if self._memory_store is not None:
            try:
                self._memory_store.close()
            except Exception as e:
                self.logger.warning(f"Error closing memory store: {e}")
            self._memory_store = None

        # Close logging handlers
        for handler in self._handlers:
            handler.close()
            self.logger.removeHandler(handler)
        self._handlers.clear()
