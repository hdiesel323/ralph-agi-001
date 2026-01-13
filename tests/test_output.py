"""Tests for ralph_agi.output module."""

from __future__ import annotations

import io

import pytest

from ralph_agi.output import OutputFormatter, Verbosity


class TestVerbosity:
    """Tests for Verbosity enum."""

    def test_verbosity_levels(self):
        """Test verbosity level ordering."""
        assert Verbosity.QUIET.value < Verbosity.NORMAL.value
        assert Verbosity.NORMAL.value < Verbosity.VERBOSE.value


class TestOutputFormatterBasic:
    """Basic tests for OutputFormatter."""

    def test_default_initialization(self):
        """Test default formatter initialization."""
        formatter = OutputFormatter()
        assert formatter.verbosity == Verbosity.NORMAL

    def test_custom_verbosity(self):
        """Test formatter with custom verbosity."""
        formatter = OutputFormatter(verbosity=Verbosity.QUIET)
        assert formatter.verbosity == Verbosity.QUIET

    def test_custom_file(self):
        """Test formatter with custom output file."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.message("test")
        assert "test" in output.getvalue()


class TestOutputFormatterSeparator:
    """Tests for separator output."""

    def test_separator_prints_bar(self):
        """Test that separator prints a visual bar."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.separator()
        result = output.getvalue()
        # Should contain equals signs (the separator bar)
        assert len(result.strip()) > 0

    def test_separator_quiet_mode(self):
        """Test that separator is suppressed in quiet mode."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output, verbosity=Verbosity.QUIET)
        formatter.separator()
        assert output.getvalue() == ""


class TestOutputFormatterIterationHeader:
    """Tests for iteration header output."""

    def test_iteration_header_format(self):
        """Test iteration header contains expected content."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.iteration_header(3, 10)
        result = output.getvalue()
        assert "3" in result
        assert "10" in result

    def test_iteration_header_quiet_mode(self):
        """Test iteration header suppressed in quiet mode."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output, verbosity=Verbosity.QUIET)
        formatter.iteration_header(1, 10)
        assert output.getvalue() == ""


class TestOutputFormatterMessage:
    """Tests for message output."""

    def test_message_normal_mode(self):
        """Test message prints in normal mode."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.message("hello world")
        assert "hello world" in output.getvalue()

    def test_message_quiet_mode(self):
        """Test message suppressed in quiet mode."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output, verbosity=Verbosity.QUIET)
        formatter.message("hello world")
        assert output.getvalue() == ""


class TestOutputFormatterVerbose:
    """Tests for verbose message output."""

    def test_verbose_only_in_verbose_mode(self):
        """Test verbose messages only show in verbose mode."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output, verbosity=Verbosity.VERBOSE)
        formatter.verbose("debug info")
        assert "debug info" in output.getvalue()

    def test_verbose_hidden_in_normal_mode(self):
        """Test verbose messages hidden in normal mode."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output, verbosity=Verbosity.NORMAL)
        formatter.verbose("debug info")
        assert output.getvalue() == ""


class TestOutputFormatterSummary:
    """Tests for summary output."""

    def test_summary_with_changes(self):
        """Test summary displays changes."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.summary(["change 1", "change 2"])
        result = output.getvalue()
        assert "Summary" in result
        assert "change 1" in result
        assert "change 2" in result

    def test_summary_empty_list(self):
        """Test summary with empty list prints nothing."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.summary([])
        assert output.getvalue() == ""

    def test_summary_quiet_mode(self):
        """Test summary suppressed in quiet mode."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output, verbosity=Verbosity.QUIET)
        formatter.summary(["change 1"])
        assert output.getvalue() == ""


class TestOutputFormatterQualityStatus:
    """Tests for quality status output."""

    def test_quality_passed(self):
        """Test quality status shows pass."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.quality_status(passed=True)
        result = output.getvalue()
        assert "pass" in result.lower()

    def test_quality_failed(self):
        """Test quality status shows fail."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.quality_status(passed=False)
        result = output.getvalue()
        assert "fail" in result.lower()

    def test_quality_with_details(self):
        """Test quality status with details."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.quality_status(passed=True, details="all tests green")
        result = output.getvalue()
        assert "all tests green" in result


class TestOutputFormatterIterationComplete:
    """Tests for iteration complete output."""

    def test_iteration_complete_continuing(self):
        """Test iteration complete message when continuing."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.iteration_complete(5, continuing=True)
        result = output.getvalue()
        assert "5" in result
        assert "Continuing" in result

    def test_iteration_complete_final(self):
        """Test iteration complete message when done."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.iteration_complete(10, continuing=False)
        result = output.getvalue()
        assert "10" in result
        assert "Continuing" not in result


class TestOutputFormatterCompletionBanner:
    """Tests for completion banner output."""

    def test_completion_banner_success(self):
        """Test completion banner for successful completion."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.completion_banner(total_iterations=5, reason="completed")
        result = output.getvalue()
        assert "5" in result
        assert "Complete" in result or "Successfully" in result

    def test_completion_banner_interrupted(self):
        """Test completion banner for interrupted run."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.completion_banner(total_iterations=3, reason="interrupted")
        result = output.getvalue()
        assert "3" in result
        assert "Interrupted" in result or "Stopped" in result

    def test_completion_banner_max_iterations(self):
        """Test completion banner for max iterations reached."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.completion_banner(total_iterations=100, reason="max_iterations")
        result = output.getvalue()
        assert "100" in result

    def test_completion_banner_with_session(self):
        """Test completion banner includes session ID."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.completion_banner(
            total_iterations=5,
            session_id="abc123-def456",
            reason="completed",
        )
        result = output.getvalue()
        assert "abc123-def456" in result


class TestOutputFormatterError:
    """Tests for error output."""

    def test_error_always_shown(self):
        """Test error messages shown even in quiet mode."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output, verbosity=Verbosity.QUIET)
        formatter.error("something went wrong")
        result = output.getvalue()
        assert "Error" in result
        assert "something went wrong" in result

    def test_error_with_exception(self):
        """Test error with exception in verbose mode."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output, verbosity=Verbosity.VERBOSE)
        exc = ValueError("bad value")
        formatter.error("operation failed", exception=exc)
        result = output.getvalue()
        assert "operation failed" in result
        assert "ValueError" in result


class TestOutputFormatterWarning:
    """Tests for warning output."""

    def test_warning_normal_mode(self):
        """Test warning shown in normal mode."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        formatter.warning("careful!")
        result = output.getvalue()
        assert "Warning" in result
        assert "careful!" in result

    def test_warning_quiet_mode(self):
        """Test warning suppressed in quiet mode."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output, verbosity=Verbosity.QUIET)
        formatter.warning("careful!")
        assert output.getvalue() == ""


class TestOutputFormatterTTYDetection:
    """Tests for TTY detection."""

    def test_non_tty_detection(self):
        """Test that StringIO is detected as non-TTY."""
        output = io.StringIO()
        formatter = OutputFormatter(file=output)
        assert not formatter.is_tty
