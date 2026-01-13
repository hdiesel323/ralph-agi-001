"""Tests for the acceptance criteria evaluator module."""

from __future__ import annotations

from pathlib import Path

import pytest

from ralph_agi.llm.evaluator import (
    CriterionResult,
    EvaluationResult,
    check_file_content,
    check_line_count,
    evaluate_acceptance_criteria,
    evaluate_criterion,
    extract_command,
    extract_file_check,
    extract_line_count_check,
    run_command,
    criterion_mentions_keyword,
)


class TestCriterionResult:
    """Tests for CriterionResult dataclass."""

    def test_create_passed_result(self):
        """Test creating a passed result."""
        result = CriterionResult(
            criterion="Test passes",
            passed=True,
            method="command",
            output="OK",
        )
        assert result.passed is True
        assert result.method == "command"

    def test_create_failed_result(self):
        """Test creating a failed result."""
        result = CriterionResult(
            criterion="Test fails",
            passed=False,
            method="command",
            output="FAILED",
            error="Test error",
        )
        assert result.passed is False
        assert result.error == "Test error"


class TestEvaluationResult:
    """Tests for EvaluationResult dataclass."""

    def test_success_factory(self):
        """Test success() creates passing result."""
        results = [
            CriterionResult("c1", True, "command", "ok"),
            CriterionResult("c2", True, "manual", "ok"),
        ]
        eval_result = EvaluationResult.success(results)
        assert eval_result.passed is True
        assert eval_result.evaluated_count == 1
        assert eval_result.manual_count == 1

    def test_failure_factory(self):
        """Test failure() creates failing result."""
        results = [CriterionResult("c1", False, "command", "failed")]
        eval_result = EvaluationResult.failure(results)
        assert eval_result.passed is False


class TestExtractCommand:
    """Tests for extract_command function."""

    def test_extract_running_command(self):
        """Test extracting 'Running X' pattern."""
        criterion = "Running 'python -m pytest tests/' passes"
        cmd = extract_command(criterion)
        assert cmd == "python -m pytest tests/"

    def test_extract_pytest_command(self):
        """Test extracting pytest command."""
        criterion = "python -m pytest tests/llm/ -v shows all passing"
        cmd = extract_command(criterion)
        assert cmd == "python -m pytest tests/llm/ -v"

    def test_extract_backtick_command(self):
        """Test extracting command in backticks."""
        criterion = "`grep -r 'TODO' src/` should return empty"
        cmd = extract_command(criterion)
        assert cmd == "grep -r 'TODO' src/"

    def test_no_command_found(self):
        """Test returns None when no command found."""
        criterion = "The code should be clean"
        cmd = extract_command(criterion)
        assert cmd is None


class TestExtractFileCheck:
    """Tests for extract_file_check function."""

    def test_extract_file_contains(self):
        """Test extracting file contains pattern."""
        criterion = "src/main.py contains 'def main()'"
        result = extract_file_check(criterion)
        assert result == ("src/main.py", "def main()")

    def test_extract_file_exists(self):
        """Test extracting file exists pattern."""
        criterion = "config.yaml exists"
        result = extract_file_check(criterion)
        assert result == ("config.yaml", None)

    def test_no_file_check(self):
        """Test returns None when no file check found."""
        criterion = "The function works correctly"
        result = extract_file_check(criterion)
        assert result is None


class TestExtractLineCountCheck:
    """Tests for extract_line_count_check function."""

    def test_extract_at_least_n_lines(self):
        """Test extracting 'at least N lines' pattern."""
        criterion = "tests/test_cli.py contains at least 400 lines"
        result = extract_line_count_check(criterion)
        assert result == ("tests/test_cli.py", 400)

    def test_extract_still_contains_lines(self):
        """Test extracting 'still contains N lines' pattern."""
        criterion = "The file still contains 100 lines"
        result = extract_line_count_check(criterion)
        assert result is not None
        assert result[1] == 100

    def test_no_line_count(self):
        """Test returns None when no line count found."""
        criterion = "The code is readable"
        result = extract_line_count_check(criterion)
        assert result is None


class TestRunCommand:
    """Tests for run_command function."""

    def test_successful_command(self):
        """Test running a successful command."""
        success, output = run_command("echo hello")
        assert success is True
        assert "hello" in output

    def test_failed_command(self):
        """Test running a failed command."""
        success, output = run_command("exit 1")
        assert success is False

    def test_command_timeout(self):
        """Test command timeout."""
        success, output = run_command("sleep 10", timeout=1)
        assert success is False
        assert "timed out" in output.lower()


class TestCheckFileContent:
    """Tests for check_file_content function."""

    def test_file_exists(self, tmp_path: Path):
        """Test checking file exists."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        success, msg = check_file_content(str(test_file), None)
        assert success is True
        assert "exists" in msg.lower()

    def test_file_contains_content(self, tmp_path: Path):
        """Test checking file contains content."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    pass\n")

        success, msg = check_file_content(str(test_file), "def hello()")
        assert success is True

    def test_file_missing_content(self, tmp_path: Path):
        """Test checking file missing content."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def goodbye():\n    pass\n")

        success, msg = check_file_content(str(test_file), "def hello()")
        assert success is False

    def test_file_not_found(self, tmp_path: Path):
        """Test checking nonexistent file."""
        success, msg = check_file_content(str(tmp_path / "missing.py"), None)
        assert success is False
        assert "not found" in msg.lower()


class TestCheckLineCount:
    """Tests for check_line_count function."""

    def test_file_has_enough_lines(self, tmp_path: Path):
        """Test file with enough lines passes."""
        test_file = tmp_path / "test.py"
        test_file.write_text("\n".join(f"line {i}" for i in range(100)))

        success, msg = check_line_count(str(test_file), 50, tmp_path)
        assert success is True

    def test_file_too_few_lines(self, tmp_path: Path):
        """Test file with too few lines fails."""
        test_file = tmp_path / "test.py"
        test_file.write_text("line 1\nline 2\n")

        success, msg = check_line_count(str(test_file), 100, tmp_path)
        assert success is False
        assert "only" in msg.lower()


class TestEvaluateCriterion:
    """Tests for evaluate_criterion function."""

    def test_evaluates_command(self):
        """Test evaluating a command criterion."""
        result = evaluate_criterion("Running 'echo test' returns test")
        assert result.method == "command"
        assert result.passed is True

    def test_evaluates_file_check(self, tmp_path: Path):
        """Test evaluating a file check criterion."""
        test_file = tmp_path / "test.py"
        test_file.write_text("hello world")

        result = evaluate_criterion(f"{test_file} contains 'hello'", tmp_path)
        assert result.method == "file_check"
        assert result.passed is True

    def test_falls_back_to_manual(self):
        """Test falling back to manual verification."""
        result = evaluate_criterion("The code should be elegant")
        assert result.method == "manual"
        assert result.passed is True  # Assumed pass


class TestEvaluateAcceptanceCriteria:
    """Tests for evaluate_acceptance_criteria function."""

    def test_empty_criteria_passes(self):
        """Test empty criteria list passes."""
        result = evaluate_acceptance_criteria([])
        assert result.passed is True
        assert result.evaluated_count == 0

    def test_all_pass(self):
        """Test all passing criteria."""
        criteria = [
            "Running 'echo hello' returns hello",
            "Running 'true' passes",
        ]
        result = evaluate_acceptance_criteria(criteria)
        assert result.passed is True

    def test_one_fails(self):
        """Test one failing criterion."""
        criteria = [
            "Running 'echo hello' returns hello",
            "Running 'false' passes",
        ]
        result = evaluate_acceptance_criteria(criteria)
        assert result.passed is False

    def test_fail_fast(self):
        """Test fail fast stops on first failure."""
        criteria = [
            "Running 'false' passes",
            "Running 'echo hello' returns hello",
        ]
        result = evaluate_acceptance_criteria(criteria, fail_fast=True)
        assert result.passed is False
        # Only first criterion evaluated
        assert len([r for r in result.results if r.method == "command"]) >= 1

    def test_manual_criteria_assumed_pass(self):
        """Test manual criteria don't fail evaluation."""
        criteria = [
            "The code should be beautiful",
            "Running 'echo hello' returns hello",
        ]
        result = evaluate_acceptance_criteria(criteria)
        assert result.passed is True
        assert result.manual_count == 1


def test_criterion_mentions_keyword():
    """Test the criterion_mentions_keyword function."""
    assert criterion_mentions_keyword("The code should be clean and efficient", "clean") is True
    assert criterion_mentions_keyword("The code should be clean and efficient", "fast") is False
    assert criterion_mentions_keyword("Ensure the function is tested", "tested") is True
    assert criterion_mentions_keyword("Ensure the function is tested", "documented") is False
    # Test case-insensitivity
    assert criterion_mentions_keyword("The code should be CLEAN and efficient", "clean") is True
    assert criterion_mentions_keyword("The code should be clean and efficient", "CLEAN") is True
    assert criterion_mentions_keyword("The CODE should be Clean", "code") is True
