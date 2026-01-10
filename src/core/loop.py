"""Ralph Loop Engine - The core execution loop for RALPH-AGI.

This module implements the central mechanism that drives all agent activity,
processing one task at a time until all tasks are complete or max iterations reached.

Key Design Principles (from PRD FR-001):
- Uses WHILE loop (not FOR) for cleaner exit conditions
- Single task per iteration to prevent context bloat
- Comprehensive logging with timestamps
- Retry logic with exponential backoff
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional


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
    ):
        """Initialize the Ralph Loop Engine.

        Args:
            max_iterations: Maximum iterations before forced exit. Default: 100
            max_retries: Maximum retry attempts per iteration. Default: 3
            retry_delays: List of delays (seconds) for exponential backoff.
                         Default: [1, 2, 4]
            log_file: Optional path to log file. If provided, logs to both
                     console and file.
        """
        if max_iterations < 0:
            raise ValueError("max_iterations must be non-negative")

        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.retry_delays = retry_delays or self.DEFAULT_RETRY_DELAYS.copy()

        self.iteration = 0
        self.complete = False
        self._completion_signal = "<promise>COMPLETE</promise>"

        # Set up logging
        self._setup_logging(log_file)

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

    def run(self) -> bool:
        """Run the Ralph Loop until completion or max iterations.

        The loop continues while:
        - iteration < max_iterations AND
        - complete flag is False

        Returns:
            True if completed successfully (via completion signal),
            False if exited due to max iterations.

        Raises:
            MaxRetriesExceeded: If an iteration fails after all retries.
        """
        self.logger.info(
            f"Ralph Loop starting with max_iterations={self.max_iterations}"
        )

        # Handle edge case of 0 max iterations
        if self.max_iterations == 0:
            self.logger.info("Max iterations is 0, exiting immediately")
            return False

        # Main loop - use WHILE (not FOR) for cleaner exit conditions
        while self.iteration < self.max_iterations and not self.complete:
            self._log_iteration_start()

            try:
                # Execute with retry logic
                result = self._execute_with_retry(self._execute_iteration)
                self._log_iteration_end(result.success)

                # Check for completion signal in the iteration output
                if self._check_completion(result.output):
                    self.complete = True
                    self.logger.info(
                        f"Completion signal detected after {self.iteration + 1} iterations"
                    )
                    break

                self.iteration += 1

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

    def set_complete(self) -> None:
        """Manually set the completion flag.

        This can be used to signal completion from external code.
        """
        self.complete = True

    def close(self) -> None:
        """Clean up resources (logging handlers, file handles).

        Should be called when the RalphLoop instance is no longer needed,
        especially if log_file was specified.
        """
        for handler in self._handlers:
            handler.close()
            self.logger.removeHandler(handler)
        self._handlers.clear()
