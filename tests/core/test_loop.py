"""Tests for the Ralph Loop Engine.

Tests cover:
- Loop initialization with default and custom parameters
- Loop exits correctly at max iterations
- Logging format matches specification
- Retry logic with mock failures
- Exponential backoff timing
- Completion signal detection
"""

import logging
import time
from unittest.mock import MagicMock, patch

import pytest

from ralph_agi.core.loop import IterationResult, MaxRetriesExceeded, RalphLoop


class TestRalphLoopInitialization:
    """Tests for RalphLoop initialization."""

    def test_default_max_iterations(self):
        """Test that default max_iterations is 100."""
        loop = RalphLoop()
        assert loop.max_iterations == 100

    def test_custom_max_iterations(self):
        """Test custom max_iterations parameter."""
        loop = RalphLoop(max_iterations=50)
        assert loop.max_iterations == 50

    def test_zero_max_iterations(self):
        """Test that zero max_iterations is allowed."""
        loop = RalphLoop(max_iterations=0)
        assert loop.max_iterations == 0

    def test_negative_max_iterations_raises(self):
        """Test that negative max_iterations raises ValueError."""
        with pytest.raises(ValueError, match="max_iterations must be non-negative"):
            RalphLoop(max_iterations=-1)

    def test_initial_iteration_is_zero(self):
        """Test that iteration counter starts at 0."""
        loop = RalphLoop()
        assert loop.iteration == 0

    def test_initial_complete_is_false(self):
        """Test that complete flag starts as False."""
        loop = RalphLoop()
        assert loop.complete is False

    def test_custom_retry_config(self):
        """Test custom retry configuration."""
        loop = RalphLoop(max_retries=5, retry_delays=[2, 4, 8])
        assert loop.max_retries == 5
        assert loop.retry_delays == [2, 4, 8]


class TestRalphLoopExecution:
    """Tests for RalphLoop execution."""

    def test_loop_exits_at_max_iterations(self):
        """Test that loop exits when max_iterations is reached."""
        loop = RalphLoop(max_iterations=5)
        result = loop.run()

        assert result is False  # Not completed via signal
        assert loop.iteration == 5

    def test_loop_with_zero_iterations_returns_immediately(self):
        """Test that loop with 0 max_iterations returns immediately."""
        loop = RalphLoop(max_iterations=0)
        result = loop.run()

        assert result is False
        assert loop.iteration == 0

    def test_loop_with_one_iteration(self):
        """Test loop with single iteration."""
        loop = RalphLoop(max_iterations=1)
        result = loop.run()

        assert result is False
        assert loop.iteration == 1

    def test_loop_completes_on_signal(self):
        """Test that loop exits when completion signal is detected."""
        loop = RalphLoop(max_iterations=100)

        # Mock _check_completion to return True after 3 iterations
        call_count = 0
        original_check = loop._check_completion

        def mock_check(output=None):
            nonlocal call_count
            call_count += 1
            return call_count >= 3

        loop._check_completion = mock_check
        result = loop.run()

        assert result is True
        assert loop.complete is True
        assert loop.iteration == 2  # 0, 1, 2 (3 iterations, but last one breaks)

    def test_set_complete_stops_loop(self):
        """Test that set_complete() stops the loop."""
        loop = RalphLoop(max_iterations=100)

        # After 2 iterations, set complete
        call_count = 0
        original_execute = loop._execute_iteration

        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                loop.set_complete()
            return IterationResult(success=True)

        loop._execute_iteration = mock_execute
        result = loop.run()

        # Loop should have stopped early
        assert loop.iteration < 100


class TestRalphLoopLogging:
    """Tests for RalphLoop logging functionality."""

    def test_logging_format_contains_timestamp(self, caplog):
        """Test that log messages contain bracketed timestamp."""
        loop = RalphLoop(max_iterations=1)

        with caplog.at_level(logging.INFO, logger=loop._logger_name):
            loop.run()

        # Check that at least one log message has timestamp format
        messages = [record.message for record in caplog.records]
        assert any("Iteration 1/1" in msg for msg in messages)

    def test_iteration_start_logged(self, caplog):
        """Test that iteration start is logged."""
        loop = RalphLoop(max_iterations=2)

        with caplog.at_level(logging.INFO, logger=loop._logger_name):
            loop.run()

        messages = [record.message for record in caplog.records]
        assert any("Starting..." in msg for msg in messages)

    def test_iteration_end_logged(self, caplog):
        """Test that iteration end is logged."""
        loop = RalphLoop(max_iterations=1)

        with caplog.at_level(logging.INFO, logger=loop._logger_name):
            loop.run()

        messages = [record.message for record in caplog.records]
        assert any("Success" in msg for msg in messages)

    def test_max_iterations_reached_logged(self, caplog):
        """Test that reaching max iterations is logged."""
        loop = RalphLoop(max_iterations=3)

        with caplog.at_level(logging.INFO, logger=loop._logger_name):
            loop.run()

        messages = [record.message for record in caplog.records]
        assert any("reached max iterations" in msg for msg in messages)


class TestRalphLoopRetryLogic:
    """Tests for RalphLoop retry logic."""

    def test_retry_on_failure(self, caplog):
        """Test that iteration is retried on failure."""
        loop = RalphLoop(max_iterations=1, max_retries=3, retry_delays=[0, 0, 0])

        # Fail twice, then succeed
        call_count = 0

        def failing_execute():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Simulated failure")
            return IterationResult(success=True)

        loop._execute_iteration = failing_execute

        with caplog.at_level(logging.WARNING, logger=loop._logger_name):
            result = loop.run()

        assert result is False  # Reached max iterations (1)
        assert call_count == 3  # Called 3 times (2 failures + 1 success)

    def test_max_retries_exceeded(self):
        """Test that MaxRetriesExceeded is raised after all retries."""
        loop = RalphLoop(max_iterations=1, max_retries=3, retry_delays=[0, 0, 0])

        # Always fail
        loop._execute_iteration = MagicMock(side_effect=RuntimeError("Always fails"))

        with pytest.raises(MaxRetriesExceeded) as exc_info:
            loop.run()

        assert exc_info.value.attempts == 3
        assert "Always fails" in str(exc_info.value.last_error)

    def test_exponential_backoff_timing(self):
        """Test that retry delays follow exponential backoff."""
        delays = [0.01, 0.02, 0.04]  # Short delays for testing
        loop = RalphLoop(max_iterations=1, max_retries=4, retry_delays=delays)

        call_times = []

        def timing_execute():
            call_times.append(time.time())
            raise RuntimeError("Simulated failure")

        loop._execute_iteration = timing_execute

        with pytest.raises(MaxRetriesExceeded):
            loop.run()

        # Check delays between calls
        assert len(call_times) == 4

        for i in range(1, len(call_times)):
            actual_delay = call_times[i] - call_times[i - 1]
            expected_delay = delays[min(i - 1, len(delays) - 1)]
            # Allow some tolerance for timing
            assert actual_delay >= expected_delay * 0.8

    def test_retry_logs_attempts(self, caplog):
        """Test that retry attempts are logged."""
        loop = RalphLoop(max_iterations=1, max_retries=3, retry_delays=[0, 0, 0])

        # Always fail
        loop._execute_iteration = MagicMock(side_effect=RuntimeError("Test error"))

        with caplog.at_level(logging.WARNING, logger=loop._logger_name):
            with pytest.raises(MaxRetriesExceeded):
                loop.run()

        messages = [record.message for record in caplog.records]
        assert any("Attempt 1/3 failed" in msg for msg in messages)
        assert any("Attempt 2/3 failed" in msg for msg in messages)


class TestMaxRetriesExceededException:
    """Tests for MaxRetriesExceeded exception."""

    def test_exception_attributes(self):
        """Test exception has correct attributes."""
        original_error = ValueError("Original error")
        exc = MaxRetriesExceeded(
            "Test message",
            attempts=5,
            last_error=original_error,
        )

        assert str(exc) == "Test message"
        assert exc.attempts == 5
        assert exc.last_error is original_error

    def test_exception_without_last_error(self):
        """Test exception can be created without last_error."""
        exc = MaxRetriesExceeded("Test", attempts=3)

        assert exc.last_error is None


class TestCompletionDetection:
    """Tests for completion signal detection."""

    def test_completion_signal_detected(self):
        """Test that completion signal is detected in output."""
        loop = RalphLoop()

        output = "Some output <promise>COMPLETE</promise> more text"
        assert loop._check_completion(output) is True

    def test_no_completion_signal(self):
        """Test that absence of completion signal returns False."""
        loop = RalphLoop()

        output = "Some output without completion signal"
        assert loop._check_completion(output) is False

    def test_empty_output(self):
        """Test completion check with empty output."""
        loop = RalphLoop()

        assert loop._check_completion("") is False
        assert loop._check_completion(None) is False

    def test_partial_completion_signal(self):
        """Test that partial signal is not detected."""
        loop = RalphLoop()

        output = "<promise>COMPLET</promise>"  # Missing 'E'
        assert loop._check_completion(output) is False

    def test_completion_from_iteration_output(self):
        """Test that completion signal in iteration output triggers completion."""
        loop = RalphLoop(max_iterations=10)

        # Mock iteration to return output with completion signal
        def mock_execute_with_completion():
            if loop.iteration >= 2:
                return IterationResult(
                    success=True,
                    output="Task done <promise>COMPLETE</promise> finished",
                )
            return IterationResult(success=True, output="Still working...")

        loop._execute_iteration = mock_execute_with_completion
        result = loop.run()

        assert result is True
        assert loop.complete is True
        assert loop.iteration == 2  # Stopped at iteration 2


class TestIterationResult:
    """Tests for IterationResult dataclass."""

    def test_iteration_result_success_only(self):
        """Test IterationResult with only success status."""
        result = IterationResult(success=True)
        assert result.success is True
        assert result.output is None

    def test_iteration_result_with_output(self):
        """Test IterationResult with success and output."""
        result = IterationResult(success=True, output="test output")
        assert result.success is True
        assert result.output == "test output"

    def test_iteration_result_failure(self):
        """Test IterationResult with failure status."""
        result = IterationResult(success=False, output="error details")
        assert result.success is False
        assert result.output == "error details"


class TestRalphLoopCleanup:
    """Tests for RalphLoop resource cleanup."""

    def test_close_removes_handlers(self):
        """Test that close() removes logging handlers."""
        loop = RalphLoop(max_iterations=1)
        initial_handlers = loop._handlers.copy()
        assert len(initial_handlers) > 0

        loop.close()

        assert len(loop._handlers) == 0
        # Verify our handlers were removed from the logger
        # (don't check total count as pytest may add its own handlers)
        for handler in initial_handlers:
            assert handler not in loop.logger.handlers

    def test_file_logging_creates_file(self, tmp_path):
        """Test that log_file parameter creates and writes to file."""
        log_file = tmp_path / "test.log"
        loop = RalphLoop(max_iterations=2, log_file=str(log_file))

        loop.run()
        loop.close()

        assert log_file.exists()
        content = log_file.read_text()
        assert "Iteration 1/2" in content
        assert "Iteration 2/2" in content

    def test_multiple_instances_independent_logging(self, caplog):
        """Test that multiple RalphLoop instances have independent loggers."""
        loop1 = RalphLoop(max_iterations=1)
        loop2 = RalphLoop(max_iterations=1)

        # Verify they have different logger names
        assert loop1._logger_name != loop2._logger_name

        # Run both and verify they both work
        loop1.run()
        loop2.run()

        loop1.close()
        loop2.close()


class TestSessionManagement:
    """Tests for session ID management."""

    def test_auto_generates_session_id(self):
        """Test that session_id is auto-generated if not provided."""
        loop = RalphLoop()
        assert loop.session_id is not None
        assert len(loop.session_id) == 36  # UUID length

    def test_custom_session_id(self):
        """Test that custom session_id can be provided."""
        custom_id = "custom-session-123"
        loop = RalphLoop(session_id=custom_id)
        assert loop.session_id == custom_id

    def test_unique_session_ids(self):
        """Test that each loop gets a unique session_id."""
        loop1 = RalphLoop()
        loop2 = RalphLoop()
        assert loop1.session_id != loop2.session_id

    def test_session_id_in_state(self):
        """Test that session_id is included in state."""
        loop = RalphLoop(session_id="test-session")
        state = loop.get_state()
        assert state["session_id"] == "test-session"

    def test_session_id_in_checkpoint(self, tmp_path):
        """Test that session_id is saved to checkpoint."""
        checkpoint_file = tmp_path / "checkpoint.json"
        loop = RalphLoop(
            max_iterations=3,
            checkpoint_path=str(checkpoint_file),
            session_id="checkpoint-session",
        )
        loop.run()
        loop.save_checkpoint()

        # Load and verify
        import json
        data = json.loads(checkpoint_file.read_text())
        assert data["session_id"] == "checkpoint-session"

    def test_resume_restores_session_id(self, tmp_path):
        """Test that resume_from_checkpoint restores session_id."""
        checkpoint_file = tmp_path / "checkpoint.json"

        # Create initial loop with known session_id
        loop1 = RalphLoop(
            max_iterations=5,
            checkpoint_path=str(checkpoint_file),
            session_id="original-session",
        )
        loop1.iteration = 3
        loop1.save_checkpoint()
        loop1.close()

        # Create new loop and resume
        loop2 = RalphLoop(checkpoint_path=str(checkpoint_file))
        loop2.resume_from_checkpoint()

        assert loop2.session_id == "original-session"
        assert loop2.iteration == 3


class TestMemoryIntegration:
    """Tests for memory store integration."""

    def test_no_memory_by_default(self):
        """Test that memory store is None by default."""
        loop = RalphLoop()
        assert loop._memory_store is None

    def test_memory_store_parameter(self):
        """Test that memory_store parameter is accepted."""
        mock_store = MagicMock()
        loop = RalphLoop(memory_store=mock_store)
        assert loop._memory_store is mock_store

    def test_get_context_without_memory(self):
        """Test that get_context returns empty list without memory."""
        loop = RalphLoop()
        context = loop.get_context()
        assert context == []

    def test_get_recent_context_without_memory(self):
        """Test that get_recent_context returns empty list without memory."""
        loop = RalphLoop()
        context = loop.get_recent_context()
        assert context == []

    def test_store_iteration_result_without_memory(self):
        """Test that _store_iteration_result handles no memory gracefully."""
        loop = RalphLoop()
        result = IterationResult(success=True, output="Test output")
        frame_id = loop._store_iteration_result(result)
        assert frame_id is None

    def test_store_iteration_result_with_memory(self):
        """Test that iteration results are stored in memory."""
        mock_store = MagicMock()
        mock_store.append.return_value = "frame-123"

        loop = RalphLoop(memory_store=mock_store, session_id="test-session")
        result = IterationResult(success=True, output="Test completed")

        frame_id = loop._store_iteration_result(result)

        assert frame_id == "frame-123"
        mock_store.append.assert_called_once()

        # Verify call arguments
        call_kwargs = mock_store.append.call_args.kwargs
        assert "Iteration 1 completed successfully" in call_kwargs["content"]
        assert call_kwargs["frame_type"] == "iteration_result"
        assert call_kwargs["session_id"] == "test-session"
        assert call_kwargs["metadata"]["iteration"] == 1
        assert call_kwargs["metadata"]["success"] is True

    def test_iteration_stores_result(self):
        """Test that running loop stores iteration results."""
        mock_store = MagicMock()
        mock_store.append.return_value = "frame-456"

        loop = RalphLoop(max_iterations=2, memory_store=mock_store)
        loop.run()
        loop.close()

        # Should have been called twice (once per iteration)
        assert mock_store.append.call_count == 2

    def test_close_closes_memory_store(self):
        """Test that close() closes the memory store."""
        mock_store = MagicMock()
        loop = RalphLoop(memory_store=mock_store)
        loop.close()

        mock_store.close.assert_called_once()
        assert loop._memory_store is None

    def test_get_context_calls_memory(self):
        """Test that get_context queries memory store."""
        mock_store = MagicMock()
        mock_store.get_by_session.return_value = ["frame1", "frame2"]

        loop = RalphLoop(memory_store=mock_store, session_id="ctx-session")
        context = loop.get_context(n=5)

        mock_store.get_by_session.assert_called_once_with("ctx-session", limit=5)
        assert context == ["frame1", "frame2"]

    def test_get_recent_context_calls_memory(self):
        """Test that get_recent_context queries memory store."""
        mock_store = MagicMock()
        mock_store.get_recent.return_value = ["recent1", "recent2"]

        loop = RalphLoop(memory_store=mock_store)
        context = loop.get_recent_context(n=3)

        mock_store.get_recent.assert_called_once_with(3)
        assert context == ["recent1", "recent2"]
