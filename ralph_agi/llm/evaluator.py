"""External acceptance criteria evaluator for RALPH-AGI.

This module provides an independent evaluation system that runs acceptance
criteria checks externally, preventing the Builder from "gaming" the results.
The evaluator can run shell commands, pytest tests, and grep patterns to
verify that acceptance criteria are actually met.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CriterionResult:
    """Result of evaluating a single acceptance criterion.

    Attributes:
        criterion: The original criterion text.
        passed: Whether the criterion was met.
        method: How it was evaluated (command, pattern, manual).
        output: Output from evaluation (stdout, match result).
        error: Error message if evaluation failed.
    """
    criterion: str
    passed: bool
    method: str = "manual"
    output: str = ""
    error: Optional[str] = None


@dataclass
class EvaluationResult:
    """Result of evaluating all acceptance criteria.

    Attributes:
        passed: Whether all evaluable criteria passed.
        results: Individual results for each criterion.
        evaluated_count: Number of criteria that were automatically evaluated.
        manual_count: Number of criteria requiring manual verification.
    """
    passed: bool
    results: list[CriterionResult] = field(default_factory=list)
    evaluated_count: int = 0
    manual_count: int = 0

    @classmethod
    def success(cls, results: list[CriterionResult]) -> "EvaluationResult":
        """Create a successful evaluation result."""
        evaluated = sum(1 for r in results if r.method != "manual")
        manual = sum(1 for r in results if r.method == "manual")
        return cls(
            passed=True,
            results=results,
            evaluated_count=evaluated,
            manual_count=manual,
        )

    @classmethod
    def failure(cls, results: list[CriterionResult]) -> "EvaluationResult":
        """Create a failed evaluation result."""
        evaluated = sum(1 for r in results if r.method != "manual")
        manual = sum(1 for r in results if r.method == "manual")
        return cls(
            passed=False,
            results=results,
            evaluated_count=evaluated,
            manual_count=manual,
        )


# Patterns to detect executable criteria
COMMAND_PATTERNS = [
    # Explicit command format: Running 'command' shows/returns/outputs...
    r"[Rr]unning ['\"](.+?)['\"]",
    # pytest/python -m pytest format
    r"(python -m pytest .+?)(?:\s+shows|\s+passes|\s+returns|$)",
    # Shell command in backticks
    r"`([^`]+)`\s+(?:should|returns|shows|outputs|passes)",
]

# Patterns to detect file existence checks
FILE_PATTERNS = [
    # "file X contains Y" or "X contains Y"
    r"(.+?\.(?:py|js|ts|json|yaml|yml|md|txt))\s+contains?\s+['\"]?([^'\"]+)['\"]?",
    # "file X exists"
    r"(.+?\.(?:py|js|ts|json|yaml|yml|md|txt))\s+exists?",
]

# Patterns to detect line count checks
LINE_COUNT_PATTERNS = [
    # "file contains at least N lines"
    r"(?:file\s+)?(.+?)\s+(?:still\s+)?contains?\s+(?:at\s+least\s+)?(\d+)\s+lines?",
]


def extract_command(criterion: str) -> Optional[str]:
    """Extract an executable command from a criterion.

    Args:
        criterion: Acceptance criterion text.

    Returns:
        Command string if found, None otherwise.
    """
    for pattern in COMMAND_PATTERNS:
        match = re.search(pattern, criterion)
        if match:
            return match.group(1).strip()
    return None


def extract_file_check(criterion: str) -> Optional[tuple[str, Optional[str]]]:
    """Extract a file existence/content check from a criterion.

    Args:
        criterion: Acceptance criterion text.

    Returns:
        Tuple of (filepath, content_to_find) or None.
    """
    # Check for content patterns first (more specific)
    for pattern in FILE_PATTERNS:
        match = re.search(pattern, criterion)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                return (groups[0], groups[1])
            return (groups[0], None)
    return None


def extract_line_count_check(criterion: str) -> Optional[tuple[str, int]]:
    """Extract a line count check from a criterion.

    Args:
        criterion: Acceptance criterion text.

    Returns:
        Tuple of (filepath, min_lines) or None.
    """
    for pattern in LINE_COUNT_PATTERNS:
        match = re.search(pattern, criterion)
        if match:
            filepath = match.group(1).strip()
            min_lines = int(match.group(2))
            return (filepath, min_lines)
    return None


def run_command(
    command: str,
    work_dir: Optional[Path] = None,
    timeout: int = 60,
) -> tuple[bool, str]:
    """Run a shell command and return success/output.

    Args:
        command: Command to execute.
        work_dir: Working directory for execution.
        timeout: Maximum execution time in seconds.

    Returns:
        Tuple of (success, output).
    """
    work_dir = work_dir or Path.cwd()

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=timeout,
            cwd=work_dir,
        )

        output = result.stdout.decode() + result.stderr.decode()
        success = result.returncode == 0

        return (success, output.strip())

    except subprocess.TimeoutExpired:
        return (False, f"Command timed out after {timeout}s")
    except Exception as e:
        return (False, f"Command failed: {e}")


def check_file_content(
    filepath: str,
    content: Optional[str],
    work_dir: Optional[Path] = None,
) -> tuple[bool, str]:
    """Check if a file exists and optionally contains specific content.

    Args:
        filepath: Path to the file.
        content: Content to search for (None for existence only).
        work_dir: Working directory to resolve relative paths.

    Returns:
        Tuple of (success, message).
    """
    work_dir = work_dir or Path.cwd()

    path = Path(filepath)
    if not path.is_absolute():
        path = work_dir / path

    if not path.exists():
        return (False, f"File not found: {filepath}")

    if content is None:
        return (True, f"File exists: {filepath}")

    try:
        file_content = path.read_text()
        if content in file_content:
            return (True, f"File contains '{content}'")
        return (False, f"File does not contain '{content}'")
    except Exception as e:
        return (False, f"Error reading file: {e}")


def check_line_count(
    filepath: str,
    min_lines: int,
    work_dir: Optional[Path] = None,
) -> tuple[bool, str]:
    """Check if a file has at least a minimum number of lines.

    Args:
        filepath: Path to the file.
        min_lines: Minimum required lines.
        work_dir: Working directory to resolve relative paths.

    Returns:
        Tuple of (success, message).
    """
    work_dir = work_dir or Path.cwd()

    path = Path(filepath)
    if not path.is_absolute():
        path = work_dir / path

    if not path.exists():
        return (False, f"File not found: {filepath}")

    try:
        content = path.read_text()
        line_count = content.count('\n') + (1 if content and not content.endswith('\n') else 0)

        if line_count >= min_lines:
            return (True, f"File has {line_count} lines (>= {min_lines})")
        return (False, f"File has only {line_count} lines (need >= {min_lines})")
    except Exception as e:
        return (False, f"Error reading file: {e}")


def evaluate_criterion(
    criterion: str,
    work_dir: Optional[Path] = None,
) -> CriterionResult:
    """Evaluate a single acceptance criterion.

    This function attempts to automatically evaluate the criterion by:
    1. Looking for executable commands
    2. Looking for file existence/content checks
    3. Looking for line count checks
    4. Falling back to manual verification

    Args:
        criterion: Acceptance criterion text.
        work_dir: Working directory for execution.

    Returns:
        CriterionResult with evaluation details.
    """
    # Try to extract and run a command
    command = extract_command(criterion)
    if command:
        success, output = run_command(command, work_dir)
        return CriterionResult(
            criterion=criterion,
            passed=success,
            method="command",
            output=output[:500],  # Truncate long output
        )

    # Try to check line count (do this before file check since it's more specific)
    line_check = extract_line_count_check(criterion)
    if line_check:
        filepath, min_lines = line_check
        success, message = check_line_count(filepath, min_lines, work_dir)
        return CriterionResult(
            criterion=criterion,
            passed=success,
            method="line_count",
            output=message,
        )

    # Try to check file existence/content
    file_check = extract_file_check(criterion)
    if file_check:
        filepath, content = file_check
        success, message = check_file_content(filepath, content, work_dir)
        return CriterionResult(
            criterion=criterion,
            passed=success,
            method="file_check",
            output=message,
        )

    # Fall back to manual verification
    return CriterionResult(
        criterion=criterion,
        passed=True,  # Assume pass for manual criteria
        method="manual",
        output="Requires manual verification",
    )


def evaluate_acceptance_criteria(
    criteria: list[str],
    work_dir: Optional[Path] = None,
    fail_fast: bool = False,
) -> EvaluationResult:
    """Evaluate all acceptance criteria for a task.

    This is the main entry point for acceptance criteria evaluation.
    It runs each criterion through automatic evaluation where possible.

    Args:
        criteria: List of acceptance criterion strings.
        work_dir: Working directory for execution.
        fail_fast: Stop on first failure if True.

    Returns:
        EvaluationResult with all results.
    """
    if not criteria:
        return EvaluationResult.success([])

    results: list[CriterionResult] = []
    all_passed = True

    for criterion in criteria:
        result = evaluate_criterion(criterion, work_dir)
        results.append(result)

        # Only count automated checks against pass/fail
        if result.method != "manual" and not result.passed:
            all_passed = False
            logger.warning(f"Criterion failed: {criterion}")
            logger.warning(f"  Output: {result.output}")

            if fail_fast:
                break
        elif result.method != "manual":
            logger.info(f"Criterion passed: {criterion}")

    if all_passed:
        return EvaluationResult.success(results)
    return EvaluationResult.failure(results)
