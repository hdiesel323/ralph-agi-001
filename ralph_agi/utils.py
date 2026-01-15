"""Utility functions for RALPH-AGI."""

from __future__ import annotations

from ralph_agi import __version__


def get_version_string() -> str:
    """Return the current version string.
    
    Returns:
        str: The version string from ralph_agi.__version__
    """
    return __version__
