"""Pinned recipes bar widget for RALPH-AGI TUI.

Displays pinned recipes as a quick-access bar with keyboard shortcuts.
"""

from __future__ import annotations

from typing import Callable, ClassVar, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Static

from ralph_agi.recipes.models import Recipe, RecipeStore


class PinnedRecipeButton(Button):
    """A button for a pinned recipe."""

    DEFAULT_CSS = """
    PinnedRecipeButton {
        min-width: 12;
        height: 3;
        margin: 0 1;
        padding: 0 1;
    }
    PinnedRecipeButton.empty {
        color: $text-disabled;
        border: dashed $surface-lighten-2;
    }
    """

    def __init__(
        self,
        recipe: Optional[Recipe],
        position: int,
        **kwargs,
    ) -> None:
        """Initialize a pinned recipe button.

        Args:
            recipe: Recipe to display, or None for empty slot.
            position: Position in the bar (0-8).
            **kwargs: Button arguments.
        """
        self._recipe = recipe
        self._position = position

        if recipe:
            # Show icon and name
            icon = recipe.icon or "▶"
            label = f"{icon} {recipe.name[:10]}"
            classes = ""
        else:
            label = f"[{position + 1}] ---"
            classes = "empty"

        super().__init__(
            label,
            id=f"pinned-{position}",
            classes=classes,
            **kwargs,
        )
        self.tooltip = self._get_tooltip()

    def _get_tooltip(self) -> str:
        """Get tooltip text for the button."""
        if self._recipe:
            return f"{self._recipe.name}\n{self._recipe.description}\nCtrl+{self._position + 1}"
        return f"Empty slot (Ctrl+{self._position + 1})"

    @property
    def recipe(self) -> Optional[Recipe]:
        """Get the associated recipe."""
        return self._recipe

    @property
    def position(self) -> int:
        """Get the position in the bar."""
        return self._position


class PinnedBar(Horizontal):
    """Quick-access bar for pinned recipes.

    Displays up to 9 pinned recipes with Ctrl+1 through Ctrl+9 shortcuts.

    Example:
        >>> bar = PinnedBar()
        >>> bar.set_recipes(store)  # Load from RecipeStore
        >>> # In TUI app, handle RecipeExecuted message
    """

    DEFAULT_CSS = """
    PinnedBar {
        dock: bottom;
        height: 3;
        background: $surface;
        padding: 0 1;
        border-top: solid $primary;
    }
    PinnedBar .bar-label {
        width: auto;
        padding: 1 1 0 0;
        color: $text-muted;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+1", "execute_1", "Recipe 1", show=False),
        Binding("ctrl+2", "execute_2", "Recipe 2", show=False),
        Binding("ctrl+3", "execute_3", "Recipe 3", show=False),
        Binding("ctrl+4", "execute_4", "Recipe 4", show=False),
        Binding("ctrl+5", "execute_5", "Recipe 5", show=False),
        Binding("ctrl+6", "execute_6", "Recipe 6", show=False),
        Binding("ctrl+7", "execute_7", "Recipe 7", show=False),
        Binding("ctrl+8", "execute_8", "Recipe 8", show=False),
        Binding("ctrl+9", "execute_9", "Recipe 9", show=False),
    ]

    class RecipeExecuted(Message):
        """Message sent when a recipe is executed."""

        def __init__(self, recipe: Recipe) -> None:
            super().__init__()
            self.recipe = recipe

    class RecipeSlotClicked(Message):
        """Message sent when an empty slot is clicked."""

        def __init__(self, position: int) -> None:
            super().__init__()
            self.position = position

    # Reactive list of pinned recipes
    pinned_count: reactive[int] = reactive(0)

    def __init__(
        self,
        store: Optional[RecipeStore] = None,
        on_execute: Optional[Callable[[Recipe], None]] = None,
        **kwargs,
    ) -> None:
        """Initialize the pinned bar.

        Args:
            store: RecipeStore to load pinned recipes from.
            on_execute: Callback when a recipe is executed.
            **kwargs: Container arguments.
        """
        super().__init__(**kwargs)
        self._store = store
        self._on_execute = on_execute
        self._recipes: list[Optional[Recipe]] = [None] * 9

        if store:
            self._load_from_store(store)

    def _load_from_store(self, store: RecipeStore) -> None:
        """Load pinned recipes from store.

        Args:
            store: RecipeStore to load from.
        """
        self._recipes = [None] * 9
        for recipe in store.get_pinned():
            if recipe.pin_position is not None and 0 <= recipe.pin_position < 9:
                self._recipes[recipe.pin_position] = recipe
        self.pinned_count = sum(1 for r in self._recipes if r is not None)

    def compose(self) -> ComposeResult:
        """Compose the pinned bar."""
        yield Static("⚡ Quick:", classes="bar-label")
        for i in range(9):
            yield PinnedRecipeButton(self._recipes[i], i)

    def set_recipes(self, store: RecipeStore) -> None:
        """Set recipes from a store.

        Args:
            store: RecipeStore to load from.
        """
        self._store = store
        self._load_from_store(store)
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        """Refresh all button displays."""
        for i in range(9):
            try:
                old_btn = self.query_one(f"#pinned-{i}", PinnedRecipeButton)
                old_btn.remove()
            except Exception:
                pass

        # Mount new buttons
        label = self.query_one(".bar-label", Static)
        for i in range(9):
            btn = PinnedRecipeButton(self._recipes[i], i)
            self.mount(btn, after=label if i == 0 else f"#pinned-{i-1}")

    def pin_recipe(self, recipe: Recipe, position: int) -> None:
        """Pin a recipe to a specific position.

        Args:
            recipe: Recipe to pin.
            position: Position (0-8).
        """
        if 0 <= position < 9:
            self._recipes[position] = recipe
            self.pinned_count = sum(1 for r in self._recipes if r is not None)
            self._refresh_buttons()

    def unpin_position(self, position: int) -> None:
        """Unpin the recipe at a position.

        Args:
            position: Position to unpin (0-8).
        """
        if 0 <= position < 9:
            self._recipes[position] = None
            self.pinned_count = sum(1 for r in self._recipes if r is not None)
            self._refresh_buttons()

    def _execute_position(self, position: int) -> None:
        """Execute the recipe at a position.

        Args:
            position: Position (0-8).
        """
        if 0 <= position < 9 and self._recipes[position]:
            recipe = self._recipes[position]
            recipe.record_use()
            self.post_message(self.RecipeExecuted(recipe))
            if self._on_execute:
                self._on_execute(recipe)
        elif 0 <= position < 9:
            self.post_message(self.RecipeSlotClicked(position))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if isinstance(event.button, PinnedRecipeButton):
            btn = event.button
            if btn.recipe:
                btn.recipe.record_use()
                self.post_message(self.RecipeExecuted(btn.recipe))
                if self._on_execute:
                    self._on_execute(btn.recipe)
            else:
                self.post_message(self.RecipeSlotClicked(btn.position))

    # Action handlers for keyboard shortcuts
    def action_execute_1(self) -> None:
        """Execute recipe in position 1."""
        self._execute_position(0)

    def action_execute_2(self) -> None:
        """Execute recipe in position 2."""
        self._execute_position(1)

    def action_execute_3(self) -> None:
        """Execute recipe in position 3."""
        self._execute_position(2)

    def action_execute_4(self) -> None:
        """Execute recipe in position 4."""
        self._execute_position(3)

    def action_execute_5(self) -> None:
        """Execute recipe in position 5."""
        self._execute_position(4)

    def action_execute_6(self) -> None:
        """Execute recipe in position 6."""
        self._execute_position(5)

    def action_execute_7(self) -> None:
        """Execute recipe in position 7."""
        self._execute_position(6)

    def action_execute_8(self) -> None:
        """Execute recipe in position 8."""
        self._execute_position(7)

    def action_execute_9(self) -> None:
        """Execute recipe in position 9."""
        self._execute_position(8)

    def get_recipe_at(self, position: int) -> Optional[Recipe]:
        """Get the recipe at a position.

        Args:
            position: Position (0-8).

        Returns:
            Recipe if present, None otherwise.
        """
        if 0 <= position < 9:
            return self._recipes[position]
        return None
