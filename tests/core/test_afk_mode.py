"""Tests for AFK Mode functionality (Story 1.4).

Tests cover:
- Signal handling setup and restore
- Checkpoint save and load
- LoopInterrupted exception
- Graceful shutdown on interrupt
- Resume from checkpoint
"""

import json
import signal

import pytest

from ralph_agi.core.loop import IterationResult, LoopInterrupted, RalphLoop


class TestLoopInterruptedException:
    """Tests for LoopInterrupted exception."""

    def test_exception_attributes(self):
        """Test exception has correct attributes."""
        exc = LoopInterrupted(
            "Test interrupt",
            iteration=5,
            checkpoint_path="/path/to/checkpoint.json",
        )

        assert str(exc) == "Test interrupt"
        assert exc.iteration == 5
        assert exc.checkpoint_path == "/path/to/checkpoint.json"

    def test_exception_without_checkpoint(self):
        """Test exception can be created without checkpoint path."""
        exc = LoopInterrupted("Test", iteration=3)

        assert exc.iteration == 3
        assert exc.checkpoint_path is None


class TestSignalHandling:
    """Tests for signal handler setup and restore."""

    def test_signal_handlers_setup(self):
        """Test that signal handlers are set up correctly."""
        loop = RalphLoop(max_iterations=1)

        # Store original handlers
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)

        loop._setup_signal_handlers()

        # Verify handlers are changed
        assert signal.getsignal(signal.SIGINT) == loop._handle_interrupt
        assert signal.getsignal(signal.SIGTERM) == loop._handle_interrupt

        # Restore
        loop._restore_signal_handlers()

        # Verify handlers are restored
        assert signal.getsignal(signal.SIGINT) == original_sigint
        assert signal.getsignal(signal.SIGTERM) == original_sigterm

    def test_handle_interrupt_sets_flag(self):
        """Test that interrupt handler sets the interrupted flag."""
        loop = RalphLoop(max_iterations=10)

        assert loop._interrupted is False

        # Simulate interrupt
        loop._handle_interrupt(signal.SIGINT, None)

        assert loop._interrupted is True

    def test_run_restores_handlers_on_completion(self):
        """Test that run() restores signal handlers after completion."""
        loop = RalphLoop(max_iterations=2)

        original_sigint = signal.getsignal(signal.SIGINT)

        loop.run(handle_signals=True)

        # Handlers should be restored
        assert signal.getsignal(signal.SIGINT) == original_sigint

    def test_run_without_signal_handling(self):
        """Test that run() can skip signal handling."""
        loop = RalphLoop(max_iterations=2)

        original_sigint = signal.getsignal(signal.SIGINT)

        loop.run(handle_signals=False)

        # Handler should not have changed during run
        assert signal.getsignal(signal.SIGINT) == original_sigint


class TestCheckpointing:
    """Tests for checkpoint save and load."""

    def test_get_state(self):
        """Test that get_state returns correct state."""
        loop = RalphLoop(max_iterations=100)
        loop.iteration = 5
        loop.complete = False

        state = loop.get_state()

        assert state["iteration"] == 5
        assert state["complete"] is False
        assert state["max_iterations"] == 100
        assert "timestamp" in state

    def test_save_checkpoint(self, tmp_path):
        """Test saving checkpoint to file."""
        checkpoint_file = tmp_path / "checkpoint.json"
        loop = RalphLoop(max_iterations=100, checkpoint_path=str(checkpoint_file))
        loop.iteration = 10

        saved_path = loop.save_checkpoint()

        assert saved_path == str(checkpoint_file)
        assert checkpoint_file.exists()

        data = json.loads(checkpoint_file.read_text())
        assert data["iteration"] == 10

    def test_save_checkpoint_with_explicit_path(self, tmp_path):
        """Test saving checkpoint to explicit path."""
        checkpoint_file = tmp_path / "explicit.json"
        loop = RalphLoop(max_iterations=100)
        loop.iteration = 7

        saved_path = loop.save_checkpoint(str(checkpoint_file))

        assert saved_path == str(checkpoint_file)
        assert checkpoint_file.exists()

    def test_save_checkpoint_no_path_raises(self):
        """Test that save_checkpoint raises without path."""
        loop = RalphLoop(max_iterations=100)

        with pytest.raises(ValueError, match="No checkpoint path"):
            loop.save_checkpoint()

    def test_load_checkpoint(self, tmp_path):
        """Test loading checkpoint from file."""
        checkpoint_file = tmp_path / "checkpoint.json"
        checkpoint_file.write_text(json.dumps({
            "iteration": 15,
            "complete": False,
            "max_iterations": 100,
        }))

        loop = RalphLoop(max_iterations=100, checkpoint_path=str(checkpoint_file))

        state = loop.load_checkpoint()

        assert state["iteration"] == 15
        assert state["complete"] is False

    def test_load_checkpoint_file_not_found(self, tmp_path):
        """Test that load_checkpoint raises for missing file."""
        loop = RalphLoop(
            max_iterations=100,
            checkpoint_path=str(tmp_path / "nonexistent.json"),
        )

        with pytest.raises(FileNotFoundError):
            loop.load_checkpoint()

    def test_load_checkpoint_no_path_raises(self):
        """Test that load_checkpoint raises without path."""
        loop = RalphLoop(max_iterations=100)

        with pytest.raises(ValueError, match="No checkpoint path"):
            loop.load_checkpoint()

    def test_resume_from_checkpoint(self, tmp_path):
        """Test resuming loop state from checkpoint."""
        checkpoint_file = tmp_path / "checkpoint.json"
        checkpoint_file.write_text(json.dumps({
            "iteration": 20,
            "complete": False,
            "max_iterations": 100,
        }))

        loop = RalphLoop(max_iterations=100, checkpoint_path=str(checkpoint_file))

        assert loop.iteration == 0  # Initial state

        loop.resume_from_checkpoint()

        assert loop.iteration == 20


class TestGracefulShutdown:
    """Tests for graceful shutdown on interrupt."""

    def test_interrupt_raises_loop_interrupted(self):
        """Test that interrupt raises LoopInterrupted."""
        loop = RalphLoop(max_iterations=100)
        loop._interrupted = True

        with pytest.raises(LoopInterrupted) as exc_info:
            loop.run(handle_signals=False)

        assert exc_info.value.iteration == 0

    def test_interrupt_saves_checkpoint(self, tmp_path):
        """Test that interrupt saves checkpoint before raising."""
        checkpoint_file = tmp_path / "checkpoint.json"
        loop = RalphLoop(
            max_iterations=100,
            checkpoint_path=str(checkpoint_file),
        )
        loop.iteration = 5
        loop._interrupted = True

        with pytest.raises(LoopInterrupted) as exc_info:
            loop.run(handle_signals=False)

        assert exc_info.value.checkpoint_path == str(checkpoint_file)
        assert checkpoint_file.exists()

        data = json.loads(checkpoint_file.read_text())
        assert data["iteration"] == 5

    def test_interrupt_without_checkpoint_path(self):
        """Test interrupt without checkpoint path configured."""
        loop = RalphLoop(max_iterations=100)
        loop._interrupted = True

        with pytest.raises(LoopInterrupted) as exc_info:
            loop.run(handle_signals=False)

        assert exc_info.value.checkpoint_path is None

    def test_interrupt_mid_execution(self):
        """Test interrupt occurring during execution."""
        loop = RalphLoop(max_iterations=100)

        call_count = 0

        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                loop._interrupted = True
            return IterationResult(success=True)

        loop._execute_iteration = mock_execute

        with pytest.raises(LoopInterrupted) as exc_info:
            loop.run(handle_signals=False)

        # Should have completed 3 iterations before interrupt was detected
        assert exc_info.value.iteration == 3


class TestAFKModeIntegration:
    """Integration tests for AFK mode."""

    def test_full_afk_workflow(self, tmp_path):
        """Test complete AFK workflow: run, interrupt, resume."""
        checkpoint_file = tmp_path / "checkpoint.json"
        log_file = tmp_path / "output.log"

        # Create loop and simulate interrupt after 5 iterations
        loop1 = RalphLoop(
            max_iterations=100,
            checkpoint_path=str(checkpoint_file),
            log_file=str(log_file),
        )

        call_count = 0

        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count >= 5:
                loop1._interrupted = True
            return IterationResult(success=True)

        loop1._execute_iteration = mock_execute

        with pytest.raises(LoopInterrupted):
            loop1.run(handle_signals=False)

        loop1.close()

        # Verify checkpoint was saved
        assert checkpoint_file.exists()
        state = json.loads(checkpoint_file.read_text())
        assert state["iteration"] == 5

        # Create new loop and resume
        loop2 = RalphLoop(
            max_iterations=10,
            checkpoint_path=str(checkpoint_file),
        )
        loop2.resume_from_checkpoint()

        assert loop2.iteration == 5

        # Run to completion
        result = loop2.run(handle_signals=False)

        assert result is False  # Hit max iterations
        assert loop2.iteration == 10

    def test_no_user_input_required(self):
        """Test that loop runs without any user input."""
        loop = RalphLoop(max_iterations=5)

        # This should complete without any prompts or input
        result = loop.run(handle_signals=False)

        assert result is False  # Hit max iterations
        assert loop.iteration == 5

    def test_progress_logged_to_file_and_console(self, tmp_path, caplog):
        """Test that progress is logged to both file and console."""
        import logging

        log_file = tmp_path / "test.log"
        loop = RalphLoop(max_iterations=3, log_file=str(log_file))

        with caplog.at_level(logging.INFO, logger=loop._logger_name):
            loop.run(handle_signals=False)

        loop.close()

        # Check console logs (via caplog)
        messages = [record.message for record in caplog.records]
        assert any("Iteration 1/3" in msg for msg in messages)
        assert any("Iteration 2/3" in msg for msg in messages)
        assert any("Iteration 3/3" in msg for msg in messages)

        # Check file logs
        log_content = log_file.read_text()
        assert "Iteration 1/3" in log_content
        assert "Iteration 2/3" in log_content
        assert "Iteration 3/3" in log_content
