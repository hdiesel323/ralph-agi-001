"""Tests for ralph_agi.utils module."""

from __future__ import annotations

import pytest

from ralph_agi.utils import get_version_string


class TestGetVersionString:
    """Tests for get_version_string function."""

    def test_get_version_string_returns_string(self):
        """Test that get_version_string returns a string."""
        version = get_version_string()
        assert isinstance(version, str)

    def test_get_version_string_not_empty(self):
        """Test that get_version_string returns a non-empty string."""
        version = get_version_string()
        assert len(version) > 0

    def test_get_version_string_format(self):
        """Test that get_version_string returns a valid version format."""
        version = get_version_string()
        # Should contain at least one digit
        assert any(char.isdigit() for char in version)
