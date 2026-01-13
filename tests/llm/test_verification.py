"""Tests for the verification module."""

from __future__ import annotations

from pathlib import Path

import pytest

from ralph_agi.llm.verification import (
    VerificationResult,
    verify_files,
    verify_python_file,
    verify_python_syntax,
)


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_success_creates_passed_result(self):
        """Test success() creates a passing result."""
        result = VerificationResult.success(5)
        assert result.passed is True
        assert result.errors == []
        assert result.files_checked == 5

    def test_failure_creates_failed_result(self):
        """Test failure() creates a failing result."""
        errors = ["Error 1", "Error 2"]
        result = VerificationResult.failure(errors, 3)
        assert result.passed is False
        assert result.errors == errors
        assert result.files_checked == 3


class TestVerifyPythonSyntax:
    """Tests for verify_python_syntax function."""

    def test_valid_syntax(self, tmp_path: Path):
        """Test valid Python file passes."""
        file_path = tmp_path / "valid.py"
        file_path.write_text("def hello():\n    return 'world'\n")

        valid, error = verify_python_syntax(file_path)

        assert valid is True
        assert error is None

    def test_invalid_syntax(self, tmp_path: Path):
        """Test invalid Python file fails."""
        file_path = tmp_path / "invalid.py"
        file_path.write_text("def hello(\n    return 'missing paren'\n")

        valid, error = verify_python_syntax(file_path)

        assert valid is False
        assert "Syntax error" in error
        assert "invalid.py" in error

    def test_indentation_error(self, tmp_path: Path):
        """Test indentation error is caught."""
        file_path = tmp_path / "indent.py"
        file_path.write_text("def hello():\nreturn 'bad indent'\n")

        valid, error = verify_python_syntax(file_path)

        assert valid is False
        assert error is not None


class TestVerifyPythonFile:
    """Tests for verify_python_file function."""

    def test_valid_file_passes(self, tmp_path: Path):
        """Test valid file passes all checks."""
        file_path = tmp_path / "valid.py"
        file_path.write_text("import os\n\ndef main():\n    return os.getcwd()\n")

        valid, errors = verify_python_file(file_path, check_imports=False)

        assert valid is True
        assert errors == []

    def test_syntax_error_fails(self, tmp_path: Path):
        """Test file with syntax error fails."""
        file_path = tmp_path / "bad.py"
        file_path.write_text("def broken(:\n    pass\n")

        valid, errors = verify_python_file(file_path)

        assert valid is False
        assert len(errors) >= 1
        assert "Syntax" in errors[0]


class TestVerifyFiles:
    """Tests for verify_files function."""

    def test_empty_list_passes(self):
        """Test empty file list passes."""
        result = verify_files([])
        assert result.passed is True
        assert result.files_checked == 0

    def test_non_python_files_skipped(self, tmp_path: Path):
        """Test non-Python files are skipped."""
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("Not Python")

        result = verify_files([str(txt_file)], tmp_path)

        assert result.passed is True
        assert result.files_checked == 0

    def test_valid_python_passes(self, tmp_path: Path):
        """Test valid Python files pass."""
        file1 = tmp_path / "file1.py"
        file1.write_text("x = 1\n")
        file2 = tmp_path / "file2.py"
        file2.write_text("y = 2\n")

        result = verify_files([str(file1), str(file2)], tmp_path)

        assert result.passed is True
        assert result.files_checked == 2

    def test_invalid_python_fails(self, tmp_path: Path):
        """Test invalid Python files fail."""
        valid = tmp_path / "valid.py"
        valid.write_text("x = 1\n")
        invalid = tmp_path / "invalid.py"
        invalid.write_text("def broken(\n")

        result = verify_files([str(valid), str(invalid)], tmp_path)

        assert result.passed is False
        assert result.files_checked == 2
        assert len(result.errors) >= 1

    def test_relative_paths_resolved(self, tmp_path: Path):
        """Test relative paths are resolved against work_dir."""
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1\n")

        result = verify_files(["test.py"], tmp_path)

        assert result.passed is True
        assert result.files_checked == 1

    def test_nonexistent_files_skipped(self, tmp_path: Path):
        """Test nonexistent files are skipped."""
        result = verify_files(["does_not_exist.py"], tmp_path)

        assert result.passed is True
        assert result.files_checked == 0
