"""Command registry for RALPH-AGI command palette.

Provides a centralized registry for all commands with metadata
for fuzzy search, categorization, and keyboard shortcuts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Union

logger = logging.getLogger(__name__)


class CommandCategory(str, Enum):
    """Categories for organizing commands."""

    TASKS = "tasks"
    GIT = "git"
    CONFIG = "config"
    RECIPES = "recipes"
    HELP = "help"
    NAVIGATION = "navigation"
    EDIT = "edit"
    FILE = "file"
    VIEW = "view"


@dataclass
class Command:
    """A command that can be executed from the command palette.

    Attributes:
        id: Unique identifier.
        name: Display name for the command.
        description: Human-readable description.
        category: Command category for grouping.
        handler: Callable to execute or action string.
        shortcut: Optional keyboard shortcut (e.g., "ctrl+p").
        aliases: Alternative names/keywords for search.
        icon: Optional icon/emoji for display.
        enabled: Whether the command is currently enabled.
        hidden: Whether to hide from palette (still searchable).
        priority: Higher priority appears first in results (default 0).
    """

    id: str
    name: str
    description: str = ""
    category: CommandCategory = CommandCategory.TASKS
    handler: Optional[Union[Callable[[], Any], str]] = None
    shortcut: Optional[str] = None
    aliases: tuple[str, ...] = field(default_factory=tuple)
    icon: str = ""
    enabled: bool = True
    hidden: bool = False
    priority: int = 0

    @property
    def search_text(self) -> str:
        """Get searchable text for this command."""
        parts = [
            self.id,
            self.name,
            self.description,
            self.category.value,
            *self.aliases,
        ]
        return " ".join(parts).lower()

    def execute(self, *args, **kwargs) -> Any:
        """Execute the command handler.

        Returns:
            Result from handler, or None if no handler.
        """
        if self.handler is None:
            return None
        if callable(self.handler):
            return self.handler(*args, **kwargs)
        return self.handler  # Return action string


class CommandRegistry:
    """Registry for managing and searching commands.

    Provides fuzzy search, category filtering, and command lookup.

    Example:
        >>> registry = CommandRegistry()
        >>> registry.register(Command(
        ...     id="task.run",
        ...     name="Run Task",
        ...     description="Start running the current task",
        ...     category=CommandCategory.TASKS,
        ...     shortcut="ctrl+enter",
        ... ))
        >>> results = registry.search("run")
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._commands: dict[str, Command] = {}
        self._by_shortcut: dict[str, Command] = {}
        self._by_category: dict[CommandCategory, list[Command]] = {
            cat: [] for cat in CommandCategory
        }

    def register(self, command: Command) -> None:
        """Register a command.

        Args:
            command: Command to register.
        """
        # Remove existing if same ID
        if command.id in self._commands:
            self.unregister(command.id)

        self._commands[command.id] = command

        # Index by shortcut
        if command.shortcut:
            self._by_shortcut[command.shortcut.lower()] = command

        # Index by category
        self._by_category[command.category].append(command)

    def unregister(self, command_id: str) -> Optional[Command]:
        """Unregister a command.

        Args:
            command_id: ID of command to remove.

        Returns:
            Removed command or None.
        """
        command = self._commands.pop(command_id, None)
        if command:
            if command.shortcut:
                self._by_shortcut.pop(command.shortcut.lower(), None)
            self._by_category[command.category] = [
                c for c in self._by_category[command.category]
                if c.id != command_id
            ]
        return command

    def get(self, command_id: str) -> Optional[Command]:
        """Get a command by ID.

        Args:
            command_id: Command ID.

        Returns:
            Command if found, None otherwise.
        """
        return self._commands.get(command_id)

    def get_by_shortcut(self, shortcut: str) -> Optional[Command]:
        """Get a command by keyboard shortcut.

        Args:
            shortcut: Keyboard shortcut (e.g., "ctrl+p").

        Returns:
            Command if found, None otherwise.
        """
        return self._by_shortcut.get(shortcut.lower())

    def get_by_category(self, category: CommandCategory) -> list[Command]:
        """Get all commands in a category.

        Args:
            category: Command category.

        Returns:
            List of commands in category.
        """
        return [c for c in self._by_category[category] if c.enabled and not c.hidden]

    def search(
        self,
        query: str,
        limit: int = 10,
        include_hidden: bool = False,
        categories: Optional[list[CommandCategory]] = None,
    ) -> list[tuple[Command, float]]:
        """Search commands with fuzzy matching.

        Args:
            query: Search query.
            limit: Maximum results to return.
            include_hidden: Whether to include hidden commands.
            categories: Filter to specific categories.

        Returns:
            List of (Command, score) tuples, sorted by score.
        """
        if not query:
            return self._get_default_results(limit, include_hidden, categories)

        # Try to import rapidfuzz for fuzzy search
        try:
            from rapidfuzz import fuzz, process
            return self._fuzzy_search_rapidfuzz(
                query, limit, include_hidden, categories
            )
        except ImportError:
            pass

        # Try fuzzywuzzy as fallback
        try:
            from fuzzywuzzy import fuzz, process
            return self._fuzzy_search_fuzzywuzzy(
                query, limit, include_hidden, categories
            )
        except ImportError:
            pass

        # Fall back to simple substring matching
        return self._simple_search(query, limit, include_hidden, categories)

    def _get_default_results(
        self,
        limit: int,
        include_hidden: bool,
        categories: Optional[list[CommandCategory]],
    ) -> list[tuple[Command, float]]:
        """Get default results when no query provided."""
        commands = []
        for cmd in self._commands.values():
            if not cmd.enabled:
                continue
            if cmd.hidden and not include_hidden:
                continue
            if categories and cmd.category not in categories:
                continue
            commands.append(cmd)

        # Sort by priority, then name
        commands.sort(key=lambda c: (-c.priority, c.name))
        return [(c, 100.0) for c in commands[:limit]]

    def _fuzzy_search_rapidfuzz(
        self,
        query: str,
        limit: int,
        include_hidden: bool,
        categories: Optional[list[CommandCategory]],
    ) -> list[tuple[Command, float]]:
        """Fuzzy search using rapidfuzz library."""
        from rapidfuzz import fuzz, process

        # Build choices
        choices = {}
        for cmd in self._commands.values():
            if not cmd.enabled:
                continue
            if cmd.hidden and not include_hidden:
                continue
            if categories and cmd.category not in categories:
                continue
            choices[cmd.id] = cmd.search_text

        if not choices:
            return []

        # Perform fuzzy search
        results = process.extract(
            query.lower(),
            choices,
            scorer=fuzz.WRatio,
            limit=limit,
        )

        # Convert to (Command, score) tuples
        return [
            (self._commands[match[2]], match[1])
            for match in results
            if match[1] > 30  # Minimum score threshold
        ]

    def _fuzzy_search_fuzzywuzzy(
        self,
        query: str,
        limit: int,
        include_hidden: bool,
        categories: Optional[list[CommandCategory]],
    ) -> list[tuple[Command, float]]:
        """Fuzzy search using fuzzywuzzy library."""
        from fuzzywuzzy import fuzz, process

        # Build choices
        choices = {}
        for cmd in self._commands.values():
            if not cmd.enabled:
                continue
            if cmd.hidden and not include_hidden:
                continue
            if categories and cmd.category not in categories:
                continue
            choices[cmd.id] = cmd.search_text

        if not choices:
            return []

        # Perform fuzzy search
        results = process.extract(
            query.lower(),
            choices,
            scorer=fuzz.WRatio,
            limit=limit,
        )

        # Convert to (Command, score) tuples
        return [
            (self._commands[match[2]], match[1])
            for match in results
            if match[1] > 30  # Minimum score threshold
        ]

    def _simple_search(
        self,
        query: str,
        limit: int,
        include_hidden: bool,
        categories: Optional[list[CommandCategory]],
    ) -> list[tuple[Command, float]]:
        """Simple substring search as fallback."""
        query_lower = query.lower()
        results = []

        for cmd in self._commands.values():
            if not cmd.enabled:
                continue
            if cmd.hidden and not include_hidden:
                continue
            if categories and cmd.category not in categories:
                continue

            search_text = cmd.search_text
            if query_lower in search_text:
                # Calculate simple score based on position
                pos = search_text.find(query_lower)
                score = 100 - (pos * 2)  # Earlier = higher score
                if search_text.startswith(query_lower):
                    score += 20  # Bonus for prefix match
                results.append((cmd, max(score, 30)))

        # Sort by score
        results.sort(key=lambda x: (-x[1], x[0].name))
        return results[:limit]

    def get_all(
        self,
        include_hidden: bool = False,
        include_disabled: bool = False,
    ) -> list[Command]:
        """Get all registered commands.

        Args:
            include_hidden: Include hidden commands.
            include_disabled: Include disabled commands.

        Returns:
            List of commands.
        """
        commands = []
        for cmd in self._commands.values():
            if not include_disabled and not cmd.enabled:
                continue
            if not include_hidden and cmd.hidden:
                continue
            commands.append(cmd)
        return sorted(commands, key=lambda c: (c.category.value, c.name))

    def __len__(self) -> int:
        """Get number of registered commands."""
        return len(self._commands)

    def __contains__(self, command_id: str) -> bool:
        """Check if command is registered."""
        return command_id in self._commands


# Default registry singleton
_default_registry: Optional[CommandRegistry] = None


def get_default_registry() -> CommandRegistry:
    """Get the default command registry.

    Creates and populates with built-in commands on first call.

    Returns:
        Default CommandRegistry instance.
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = CommandRegistry()
        _register_builtin_commands(_default_registry)
    return _default_registry


def _register_builtin_commands(registry: CommandRegistry) -> None:
    """Register built-in commands to the registry."""
    # Task commands
    registry.register(Command(
        id="task.run",
        name="Run Task",
        description="Start running the current task",
        category=CommandCategory.TASKS,
        shortcut="ctrl+enter",
        icon="▶️",
        priority=10,
    ))
    registry.register(Command(
        id="task.pause",
        name="Pause Task",
        description="Pause the running task",
        category=CommandCategory.TASKS,
        shortcut="ctrl+p",
        icon="⏸️",
    ))
    registry.register(Command(
        id="task.stop",
        name="Stop Task",
        description="Stop and cancel the current task",
        category=CommandCategory.TASKS,
        shortcut="ctrl+c",
        icon="⏹️",
    ))
    registry.register(Command(
        id="task.restart",
        name="Restart Task",
        description="Restart the task from checkpoint",
        category=CommandCategory.TASKS,
        icon="🔄",
    ))
    registry.register(Command(
        id="task.select",
        name="Select Task",
        description="Choose a task to work on",
        category=CommandCategory.TASKS,
        shortcut="ctrl+t",
        icon="📋",
    ))

    # Git commands
    registry.register(Command(
        id="git.status",
        name="Git Status",
        description="Show git status and changes",
        category=CommandCategory.GIT,
        shortcut="ctrl+g",
        icon="📊",
    ))
    registry.register(Command(
        id="git.commit",
        name="Git Commit",
        description="Commit staged changes",
        category=CommandCategory.GIT,
        icon="💾",
    ))
    registry.register(Command(
        id="git.push",
        name="Git Push",
        description="Push commits to remote",
        category=CommandCategory.GIT,
        icon="⬆️",
    ))
    registry.register(Command(
        id="git.pull",
        name="Git Pull",
        description="Pull changes from remote",
        category=CommandCategory.GIT,
        icon="⬇️",
    ))
    registry.register(Command(
        id="git.pr",
        name="Create Pull Request",
        description="Create a new pull request",
        category=CommandCategory.GIT,
        icon="🔀",
    ))

    # Config commands
    registry.register(Command(
        id="config.edit",
        name="Edit Configuration",
        description="Open configuration for editing",
        category=CommandCategory.CONFIG,
        icon="⚙️",
    ))
    registry.register(Command(
        id="config.reload",
        name="Reload Configuration",
        description="Reload configuration from disk",
        category=CommandCategory.CONFIG,
        icon="🔃",
    ))
    registry.register(Command(
        id="config.export",
        name="Export Configuration",
        description="Export current configuration",
        category=CommandCategory.CONFIG,
        icon="📤",
    ))
    registry.register(Command(
        id="prd.edit",
        name="Edit PRD",
        description="Open PRD editor",
        category=CommandCategory.CONFIG,
        shortcut="ctrl+e",
        icon="📝",
    ))

    # Recipe commands
    registry.register(Command(
        id="recipe.list",
        name="List Recipes",
        description="Show available recipes",
        category=CommandCategory.RECIPES,
        icon="📚",
    ))
    registry.register(Command(
        id="recipe.run",
        name="Run Recipe",
        description="Execute a workflow recipe",
        category=CommandCategory.RECIPES,
        icon="▶️",
    ))
    registry.register(Command(
        id="recipe.create",
        name="Create Recipe",
        description="Create a new recipe",
        category=CommandCategory.RECIPES,
        icon="➕",
    ))

    # Navigation commands
    registry.register(Command(
        id="nav.palette",
        name="Command Palette",
        description="Open command palette",
        category=CommandCategory.NAVIGATION,
        shortcut="ctrl+shift+p",
        icon="🎨",
        priority=5,
    ))
    registry.register(Command(
        id="nav.logs",
        name="View Logs",
        description="Show log panel",
        category=CommandCategory.NAVIGATION,
        shortcut="ctrl+l",
        icon="📜",
    ))
    registry.register(Command(
        id="nav.metrics",
        name="View Metrics",
        description="Show metrics dashboard",
        category=CommandCategory.NAVIGATION,
        shortcut="ctrl+m",
        icon="📈",
    ))
    registry.register(Command(
        id="nav.stories",
        name="View Stories",
        description="Show story grid",
        category=CommandCategory.NAVIGATION,
        icon="📖",
    ))

    # Help commands
    registry.register(Command(
        id="help.docs",
        name="Documentation",
        description="Open documentation",
        category=CommandCategory.HELP,
        shortcut="f1",
        icon="📚",
    ))
    registry.register(Command(
        id="help.shortcuts",
        name="Keyboard Shortcuts",
        description="Show all keyboard shortcuts",
        category=CommandCategory.HELP,
        shortcut="ctrl+?",
        icon="⌨️",
    ))
    registry.register(Command(
        id="help.about",
        name="About RALPH-AGI",
        description="Show version and info",
        category=CommandCategory.HELP,
        icon="ℹ️",
    ))

    # View commands
    registry.register(Command(
        id="view.fullscreen",
        name="Toggle Fullscreen",
        description="Enter or exit fullscreen mode",
        category=CommandCategory.VIEW,
        shortcut="f11",
        icon="🔲",
    ))
    registry.register(Command(
        id="view.dark",
        name="Toggle Dark Mode",
        description="Switch between dark and light themes",
        category=CommandCategory.VIEW,
        icon="🌙",
    ))
