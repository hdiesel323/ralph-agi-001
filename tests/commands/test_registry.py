"""Tests for command registry."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from ralph_agi.commands.registry import (
    Command,
    CommandCategory,
    CommandRegistry,
    get_default_registry,
)


class TestCommand:
    """Tests for Command dataclass."""

    def test_command_creation_minimal(self):
        """Test creating command with minimal fields."""
        cmd = Command(id="test", name="Test Command")
        assert cmd.id == "test"
        assert cmd.name == "Test Command"
        assert cmd.description == ""
        assert cmd.category == CommandCategory.TASKS
        assert cmd.enabled is True
        assert cmd.hidden is False

    def test_command_creation_full(self):
        """Test creating command with all fields."""
        handler = MagicMock()
        cmd = Command(
            id="test.full",
            name="Full Test",
            description="A full test command",
            category=CommandCategory.GIT,
            handler=handler,
            shortcut="ctrl+t",
            aliases=("ft", "fulltest"),
            icon="🧪",
            enabled=True,
            hidden=False,
            priority=10,
        )
        assert cmd.id == "test.full"
        assert cmd.name == "Full Test"
        assert cmd.description == "A full test command"
        assert cmd.category == CommandCategory.GIT
        assert cmd.handler == handler
        assert cmd.shortcut == "ctrl+t"
        assert cmd.aliases == ("ft", "fulltest")
        assert cmd.icon == "🧪"
        assert cmd.priority == 10

    def test_search_text(self):
        """Test search text property."""
        cmd = Command(
            id="test.search",
            name="Search Test",
            description="A searchable command",
            category=CommandCategory.CONFIG,
            aliases=("alias1", "alias2"),
        )
        search_text = cmd.search_text

        assert "test.search" in search_text
        assert "search test" in search_text
        assert "searchable command" in search_text
        assert "config" in search_text
        assert "alias1" in search_text
        assert "alias2" in search_text

    def test_execute_callable_handler(self):
        """Test executing command with callable handler."""
        handler = MagicMock(return_value="result")
        cmd = Command(id="test", name="Test", handler=handler)

        result = cmd.execute("arg1", kwarg="value")

        handler.assert_called_once_with("arg1", kwarg="value")
        assert result == "result"

    def test_execute_string_handler(self):
        """Test executing command with string action handler."""
        cmd = Command(id="test", name="Test", handler="action_name")
        result = cmd.execute()
        assert result == "action_name"

    def test_execute_no_handler(self):
        """Test executing command with no handler."""
        cmd = Command(id="test", name="Test")
        result = cmd.execute()
        assert result is None


class TestCommandCategory:
    """Tests for CommandCategory enum."""

    def test_all_categories_exist(self):
        """Test all expected categories exist."""
        assert CommandCategory.TASKS.value == "tasks"
        assert CommandCategory.GIT.value == "git"
        assert CommandCategory.CONFIG.value == "config"
        assert CommandCategory.RECIPES.value == "recipes"
        assert CommandCategory.HELP.value == "help"
        assert CommandCategory.NAVIGATION.value == "navigation"
        assert CommandCategory.EDIT.value == "edit"
        assert CommandCategory.FILE.value == "file"
        assert CommandCategory.VIEW.value == "view"


class TestCommandRegistry:
    """Tests for CommandRegistry."""

    def test_registry_creation(self):
        """Test creating empty registry."""
        registry = CommandRegistry()
        assert len(registry) == 0

    def test_register_command(self):
        """Test registering a command."""
        registry = CommandRegistry()
        cmd = Command(id="test", name="Test")
        registry.register(cmd)

        assert len(registry) == 1
        assert "test" in registry
        assert registry.get("test") == cmd

    def test_register_replaces_existing(self):
        """Test that registering same ID replaces existing."""
        registry = CommandRegistry()
        cmd1 = Command(id="test", name="Original")
        cmd2 = Command(id="test", name="Replacement")

        registry.register(cmd1)
        registry.register(cmd2)

        assert len(registry) == 1
        assert registry.get("test").name == "Replacement"

    def test_unregister_command(self):
        """Test unregistering a command."""
        registry = CommandRegistry()
        cmd = Command(id="test", name="Test")
        registry.register(cmd)

        removed = registry.unregister("test")

        assert removed == cmd
        assert len(registry) == 0
        assert "test" not in registry

    def test_unregister_nonexistent(self):
        """Test unregistering command that doesn't exist."""
        registry = CommandRegistry()
        assert registry.unregister("nonexistent") is None

    def test_get_by_shortcut(self):
        """Test getting command by shortcut."""
        registry = CommandRegistry()
        cmd = Command(id="test", name="Test", shortcut="ctrl+t")
        registry.register(cmd)

        assert registry.get_by_shortcut("ctrl+t") == cmd
        assert registry.get_by_shortcut("CTRL+T") == cmd  # Case insensitive
        assert registry.get_by_shortcut("ctrl+x") is None

    def test_get_by_category(self):
        """Test getting commands by category."""
        registry = CommandRegistry()
        cmd1 = Command(id="git1", name="Git 1", category=CommandCategory.GIT)
        cmd2 = Command(id="git2", name="Git 2", category=CommandCategory.GIT)
        cmd3 = Command(id="task1", name="Task 1", category=CommandCategory.TASKS)
        registry.register(cmd1)
        registry.register(cmd2)
        registry.register(cmd3)

        git_commands = registry.get_by_category(CommandCategory.GIT)
        assert len(git_commands) == 2
        assert cmd1 in git_commands
        assert cmd2 in git_commands

    def test_get_by_category_excludes_disabled(self):
        """Test that disabled commands are excluded from category."""
        registry = CommandRegistry()
        cmd1 = Command(id="git1", name="Git 1", category=CommandCategory.GIT)
        cmd2 = Command(id="git2", name="Git 2", category=CommandCategory.GIT, enabled=False)
        registry.register(cmd1)
        registry.register(cmd2)

        git_commands = registry.get_by_category(CommandCategory.GIT)
        assert len(git_commands) == 1
        assert cmd1 in git_commands

    def test_search_no_query(self):
        """Test search with empty query."""
        registry = CommandRegistry()
        cmd1 = Command(id="test1", name="Test 1", priority=10)
        cmd2 = Command(id="test2", name="Test 2", priority=5)
        registry.register(cmd1)
        registry.register(cmd2)

        results = registry.search("", limit=10)

        # Should return all enabled commands, sorted by priority
        assert len(results) == 2
        assert results[0][0] == cmd1  # Higher priority first

    def test_search_with_query(self):
        """Test search with query string."""
        registry = CommandRegistry()
        cmd1 = Command(id="task.run", name="Run Task", description="Start a task")
        cmd2 = Command(id="git.status", name="Git Status", description="Show status")
        registry.register(cmd1)
        registry.register(cmd2)

        results = registry.search("run")

        # Should find "Run Task"
        assert len(results) >= 1
        command_ids = [r[0].id for r in results]
        assert "task.run" in command_ids

    def test_search_excludes_hidden(self):
        """Test that hidden commands are excluded by default."""
        registry = CommandRegistry()
        cmd1 = Command(id="visible", name="Visible")
        cmd2 = Command(id="hidden", name="Hidden", hidden=True)
        registry.register(cmd1)
        registry.register(cmd2)

        results = registry.search("", limit=10)
        command_ids = [r[0].id for r in results]

        assert "visible" in command_ids
        assert "hidden" not in command_ids

    def test_search_includes_hidden_when_requested(self):
        """Test that hidden commands can be included."""
        registry = CommandRegistry()
        cmd1 = Command(id="visible", name="Visible")
        cmd2 = Command(id="hidden", name="Hidden", hidden=True)
        registry.register(cmd1)
        registry.register(cmd2)

        results = registry.search("", limit=10, include_hidden=True)
        command_ids = [r[0].id for r in results]

        assert "visible" in command_ids
        assert "hidden" in command_ids

    def test_search_filter_categories(self):
        """Test search with category filter."""
        registry = CommandRegistry()
        cmd1 = Command(id="git1", name="Git Cmd", category=CommandCategory.GIT)
        cmd2 = Command(id="task1", name="Task Cmd", category=CommandCategory.TASKS)
        registry.register(cmd1)
        registry.register(cmd2)

        results = registry.search("cmd", categories=[CommandCategory.GIT])
        command_ids = [r[0].id for r in results]

        assert "git1" in command_ids
        assert "task1" not in command_ids

    def test_get_all(self):
        """Test getting all commands."""
        registry = CommandRegistry()
        cmd1 = Command(id="cmd1", name="Cmd 1")
        cmd2 = Command(id="cmd2", name="Cmd 2", hidden=True)
        cmd3 = Command(id="cmd3", name="Cmd 3", enabled=False)
        registry.register(cmd1)
        registry.register(cmd2)
        registry.register(cmd3)

        # Default excludes hidden and disabled
        all_cmds = registry.get_all()
        ids = [c.id for c in all_cmds]
        assert "cmd1" in ids
        assert "cmd2" not in ids
        assert "cmd3" not in ids

        # Include hidden
        all_cmds = registry.get_all(include_hidden=True)
        ids = [c.id for c in all_cmds]
        assert "cmd2" in ids

        # Include disabled
        all_cmds = registry.get_all(include_disabled=True)
        ids = [c.id for c in all_cmds]
        assert "cmd3" in ids


class TestDefaultRegistry:
    """Tests for get_default_registry function."""

    def test_returns_registry(self):
        """Test that default registry is returned."""
        registry = get_default_registry()
        assert isinstance(registry, CommandRegistry)

    def test_has_builtin_commands(self):
        """Test that default registry has builtin commands."""
        registry = get_default_registry()
        assert len(registry) > 0

        # Check for some expected commands
        assert registry.get("task.run") is not None
        assert registry.get("git.status") is not None
        assert registry.get("help.docs") is not None

    def test_singleton(self):
        """Test that default registry is a singleton."""
        registry1 = get_default_registry()
        registry2 = get_default_registry()
        assert registry1 is registry2
