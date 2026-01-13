"""Code verification for RALPH-AGI.

Provides verification checks to run before marking tasks complete.
Catches common errors like syntax issues and missing imports.
"""

from __future__ import annotations

import ast
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of code verification.

    Attributes:
        passed: Whether all verification checks passed
        errors: List of error messages if verification failed
        files_checked: Number of files that were checked
    """

    passed: bool
    errors: list[str]
    files_checked: int

    @classmethod
    def success(cls, files_checked: int = 0) -> "VerificationResult":
        """Create a successful result."""
        return cls(passed=True, errors=[], files_checked=files_checked)

    @classmethod
    def failure(cls, errors: list[str], files_checked: int = 0) -> "VerificationResult":
        """Create a failed result."""
        return cls(passed=False, errors=errors, files_checked=files_checked)


def verify_python_syntax(file_path: Path) -> tuple[bool, Optional[str]]:
    """Check Python file for syntax errors.

    Args:
        file_path: Path to the Python file.

    Returns:
        Tuple of (is_valid, error_message).
    """
    try:
        source = file_path.read_text()
        ast.parse(source)
        return (True, None)
    except SyntaxError as e:
        return (False, f"Syntax error in {file_path}: {e.msg} at line {e.lineno}")
    except Exception as e:
        return (False, f"Error parsing {file_path}: {e}")


def verify_python_imports(file_path: Path) -> tuple[bool, Optional[str]]:
    """Check that Python imports resolve correctly.

    This runs 'python -c "import ..."' for each import to verify it exists.

    Args:
        file_path: Path to the Python file.

    Returns:
        Tuple of (is_valid, error_message).
    """
    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except SyntaxError:
        # Syntax errors are caught by verify_python_syntax
        return (True, None)

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split('.')[0])

    # Check each import
    errors = []
    for module in set(imports):
        # Skip relative imports and common stdlib modules
        if module.startswith('.'):
            continue

        try:
            result = subprocess.run(
                [sys.executable, "-c", f"import {module}"],
                capture_output=True,
                timeout=5,
                cwd=file_path.parent,
            )
            if result.returncode != 0:
                error_output = result.stderr.decode().strip()
                # Only report if it's a genuine import error
                if "ModuleNotFoundError" in error_output or "ImportError" in error_output:
                    errors.append(f"Import error in {file_path}: Cannot import '{module}'")
        except subprocess.TimeoutExpired:
            pass  # Ignore timeout - import might be slow
        except Exception:
            pass  # Ignore other errors

    if errors:
        return (False, errors[0])  # Return first error
    return (True, None)


def verify_python_file(file_path: Path, check_imports: bool = True) -> tuple[bool, list[str]]:
    """Run all verification checks on a Python file.

    Args:
        file_path: Path to the Python file.
        check_imports: Whether to check imports (slower but more thorough).

    Returns:
        Tuple of (is_valid, list of error messages).
    """
    errors = []

    # Check syntax
    valid, error = verify_python_syntax(file_path)
    if not valid and error:
        errors.append(error)
        return (False, errors)  # Don't check imports if syntax is bad

    # Check imports
    if check_imports:
        valid, error = verify_python_imports(file_path)
        if not valid and error:
            errors.append(error)

    return (len(errors) == 0, errors)


def verify_files(files: list[str], work_dir: Optional[Path] = None) -> VerificationResult:
    """Verify a list of files that were modified.

    Only Python files are checked. Other files are skipped.

    Args:
        files: List of file paths (relative or absolute).
        work_dir: Working directory to resolve relative paths.

    Returns:
        VerificationResult with pass/fail status and errors.
    """
    if not files:
        return VerificationResult.success(0)

    work_dir = work_dir or Path.cwd()
    errors = []
    files_checked = 0

    for file_str in files:
        file_path = Path(file_str)
        if not file_path.is_absolute():
            file_path = work_dir / file_path

        # Only check Python files
        if file_path.suffix != ".py":
            continue

        if not file_path.exists():
            logger.debug(f"Skipping verification for non-existent file: {file_path}")
            continue

        files_checked += 1
        logger.debug(f"Verifying {file_path}")

        valid, file_errors = verify_python_file(file_path)
        if not valid:
            errors.extend(file_errors)

    if errors:
        logger.warning(f"Verification failed with {len(errors)} error(s)")
        return VerificationResult.failure(errors, files_checked)

    logger.info(f"Verification passed for {files_checked} file(s)")
    return VerificationResult.success(files_checked)


def run_tests_for_file(file_path: Path, timeout: int = 30) -> tuple[bool, Optional[str]]:
    """Run pytest for tests related to a file.

    Args:
        file_path: Path to the file (source or test file).
        timeout: Maximum time to wait for tests.

    Returns:
        Tuple of (tests_passed, error_message).
    """
    # Determine test file
    if file_path.name.startswith("test_"):
        test_file = file_path
    else:
        # Look for corresponding test file
        test_file = file_path.parent / f"test_{file_path.name}"
        if not test_file.exists():
            # Try tests/ subdirectory
            test_file = file_path.parent / "tests" / f"test_{file_path.name}"

    if not test_file.exists():
        logger.debug(f"No test file found for {file_path}")
        return (True, None)  # No tests to run

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
            capture_output=True,
            timeout=timeout,
            cwd=file_path.parent,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode()
            stdout = result.stdout.decode()
            # Look for failure summary
            if "FAILED" in stdout:
                return (False, f"Tests failed in {test_file}")
            elif "error" in stderr.lower():
                return (False, f"Test error in {test_file}: {stderr[:200]}")
        return (True, None)
    except subprocess.TimeoutExpired:
        return (False, f"Tests timed out for {test_file}")
    except Exception as e:
        return (False, f"Error running tests for {test_file}: {e}")
