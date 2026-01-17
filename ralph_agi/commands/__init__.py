"""Command palette and command registry for RALPH-AGI.

Provides a unified command system with fuzzy search, history,
and keyboard shortcuts.
"""

from ralph_agi.commands.registry import (
    Command,
    CommandCategory,
    CommandRegistry,
    get_default_registry,
)
from ralph_agi.commands.history import (
    CommandHistory,
    load_history,
    save_history,
)

__all__ = [
    # Registry
    "Command",
    "CommandCategory",
    "CommandRegistry",
    "get_default_registry",
    # History
    "CommandHistory",
    "load_history",
    "save_history",
]
