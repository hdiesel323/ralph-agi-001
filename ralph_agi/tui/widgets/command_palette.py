"""Command palette widget for RALPH-AGI TUI.

Provides a fuzzy-searchable command palette with keyboard navigation.
"""

from __future__ import annotations

from typing import ClassVar, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, ListItem, ListView, Static

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


class CommandListItem(ListItem):
    """A single item in the command list."""

    DEFAULT_CSS = """
    CommandListItem {
        height: auto;
        padding: 0 1;
    }

    CommandListItem > .command-name {
        text-style: bold;
    }

    CommandListItem > .command-description {
        color: $text-muted;
    }

    CommandListItem > .command-shortcut {
        color: $accent;
        text-align: right;
    }

    CommandListItem.--highlight {
        background: $primary;
    }
    """

    def __init__(self, command: Command, score: float = 100.0, **kwargs) -> None:
        """Initialize command list item.

        Args:
            command: Command to display.
            score: Search match score.
            **kwargs: Widget arguments.
        """
        super().__init__(**kwargs)
        self._command = command
        self._score = score

    @property
    def command(self) -> Command:
        """Get the associated command."""
        return self._command

    def compose(self) -> ComposeResult:
        """Compose the list item content."""
        icon = self._command.icon if self._command.icon else ">"
        shortcut = self._command.shortcut or ""

        yield Static(
            f"{icon} {self._command.name}",
            classes="command-name",
        )
        yield Static(
            self._command.description,
            classes="command-description",
        )
        if shortcut:
            yield Static(
                shortcut.upper(),
                classes="command-shortcut",
            )


class CommandPalette(Vertical):
    """Command palette with fuzzy search.

    A modal overlay that provides quick access to all commands.
    Supports keyboard navigation and fuzzy search.

    Example:
        >>> palette = CommandPalette()
        >>> # In TUI app, handle CommandExecuted message
    """

    DEFAULT_CSS = """
    CommandPalette {
        width: 60;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1;
        layer: dialog;
    }

    CommandPalette.hidden {
        display: none;
    }

    CommandPalette > #search-input {
        width: 100%;
        margin-bottom: 1;
    }

    CommandPalette > #results-container {
        height: auto;
        max-height: 20;
    }

    CommandPalette > .section-header {
        color: $text-muted;
        text-style: italic;
        padding: 0 1;
        margin-top: 1;
    }

    CommandPalette > #no-results {
        color: $text-disabled;
        text-align: center;
        padding: 2;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "close", "Close", show=True),
        Binding("enter", "execute", "Execute", show=True),
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("ctrl+n", "move_down", "Next", show=False),
        Binding("ctrl+p", "move_up", "Previous", show=False),
    ]

    class CommandExecuted(Message):
        """Sent when a command is executed."""

        def __init__(self, command: Command) -> None:
            super().__init__()
            self.command = command

    class PaletteClosed(Message):
        """Sent when the palette is closed."""

        pass

    # Reactive query
    query: reactive[str] = reactive("", init=False)
    selected_index: reactive[int] = reactive(0)

    def __init__(
        self,
        registry: Optional[CommandRegistry] = None,
        history: Optional[CommandHistory] = None,
        **kwargs,
    ) -> None:
        """Initialize command palette.

        Args:
            registry: Command registry. Uses default if None.
            history: Command history. Loads from file if None.
            **kwargs: Widget arguments.
        """
        super().__init__(**kwargs)
        self._registry = registry or get_default_registry()
        self._history = history or load_history()
        self._results: list[tuple[Command, float]] = []
        self._list_items: list[CommandListItem] = []

    def compose(self) -> ComposeResult:
        """Compose the palette."""
        yield Input(
            placeholder="Type to search commands...",
            id="search-input",
        )
        yield VerticalScroll(id="results-container")
        yield Static("No matching commands", id="no-results")

    def on_mount(self) -> None:
        """Handle mount - focus search input."""
        self._update_results()
        # Focus the search input
        try:
            self.query_one("#search-input", Input).focus()
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self.query = event.value
            self._update_results()
            self.selected_index = 0

    def _update_results(self) -> None:
        """Update search results based on query."""
        container = self.query_one("#results-container", VerticalScroll)
        no_results = self.query_one("#no-results", Static)

        # Clear existing items
        container.remove_children()

        if not self.query:
            # Show recent commands when no query
            self._show_recent_and_frequent(container)
        else:
            # Search commands
            self._results = self._registry.search(self.query, limit=15)

            if not self._results:
                no_results.display = True
                return

            no_results.display = False

            # Group by category
            by_category: dict[CommandCategory, list[tuple[Command, float]]] = {}
            for cmd, score in self._results:
                if cmd.category not in by_category:
                    by_category[cmd.category] = []
                by_category[cmd.category].append((cmd, score))

            # Add results by category
            self._list_items = []
            for category in sorted(by_category.keys(), key=lambda c: c.value):
                commands = by_category[category]
                # Add category header
                container.mount(Static(
                    f"[{category.value.title()}]",
                    classes="section-header",
                ))
                # Add commands
                for cmd, score in commands:
                    item = CommandListItem(cmd, score)
                    container.mount(item)
                    self._list_items.append(item)

        self._highlight_selected()

    def _show_recent_and_frequent(self, container: VerticalScroll) -> None:
        """Show recent and frequent commands."""
        no_results = self.query_one("#no-results", Static)
        no_results.display = False

        self._list_items = []

        # Recent commands
        recent_ids = self._history.get_recent(5)
        if recent_ids:
            container.mount(Static("[Recent]", classes="section-header"))
            for cmd_id in recent_ids:
                cmd = self._registry.get(cmd_id)
                if cmd and cmd.enabled:
                    item = CommandListItem(cmd)
                    container.mount(item)
                    self._list_items.append(item)

        # Frequent commands
        frequent_ids = self._history.get_frequent(5)
        # Filter out ones already in recent
        frequent_ids = [fid for fid in frequent_ids if fid not in recent_ids]
        if frequent_ids:
            container.mount(Static("[Frequent]", classes="section-header"))
            for cmd_id in frequent_ids:
                cmd = self._registry.get(cmd_id)
                if cmd and cmd.enabled:
                    item = CommandListItem(cmd)
                    container.mount(item)
                    self._list_items.append(item)

        # All commands if nothing in history
        if not self._list_items:
            all_results = self._registry.search("", limit=10)
            if all_results:
                container.mount(Static("[All Commands]", classes="section-header"))
                for cmd, score in all_results:
                    item = CommandListItem(cmd, score)
                    container.mount(item)
                    self._list_items.append(item)

        self._highlight_selected()

    def _highlight_selected(self) -> None:
        """Highlight the selected item."""
        for i, item in enumerate(self._list_items):
            if i == self.selected_index:
                item.add_class("--highlight")
            else:
                item.remove_class("--highlight")

    def watch_selected_index(self, index: int) -> None:
        """React to selection changes."""
        self._highlight_selected()

    def action_close(self) -> None:
        """Close the palette."""
        self.post_message(self.PaletteClosed())
        self.add_class("hidden")

    def action_execute(self) -> None:
        """Execute the selected command."""
        if not self._list_items:
            return

        if 0 <= self.selected_index < len(self._list_items):
            item = self._list_items[self.selected_index]
            cmd = item.command

            # Record in history
            self._history.record(cmd.id)
            try:
                save_history(self._history)
            except Exception:
                pass

            # Post message and close
            self.post_message(self.CommandExecuted(cmd))
            self.action_close()

    def action_move_up(self) -> None:
        """Move selection up."""
        if self._list_items:
            self.selected_index = (self.selected_index - 1) % len(self._list_items)

    def action_move_down(self) -> None:
        """Move selection down."""
        if self._list_items:
            self.selected_index = (self.selected_index + 1) % len(self._list_items)

    def show(self) -> None:
        """Show the palette."""
        self.remove_class("hidden")
        self.query = ""
        self.selected_index = 0
        self._update_results()
        try:
            input_widget = self.query_one("#search-input", Input)
            input_widget.value = ""
            input_widget.focus()
        except Exception:
            pass

    def hide(self) -> None:
        """Hide the palette."""
        self.add_class("hidden")

    @property
    def is_visible(self) -> bool:
        """Check if palette is visible."""
        return "hidden" not in self.classes

    def on_list_item_selected(self, event: ListView.Selected) -> None:
        """Handle item selection from list."""
        if hasattr(event, "item") and isinstance(event.item, CommandListItem):
            cmd = event.item.command
            self._history.record(cmd.id)
            try:
                save_history(self._history)
            except Exception:
                pass
            self.post_message(self.CommandExecuted(cmd))
            self.action_close()
