"""Tests for the PinnedBar TUI widget."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from ralph_agi.recipes.models import Recipe, RecipeCategory, RecipeStore
from ralph_agi.tui.widgets.pinned_bar import PinnedBar, PinnedRecipeButton


class TestPinnedRecipeButton:
    """Tests for PinnedRecipeButton widget."""

    def test_button_with_recipe(self):
        """Test creating button with a recipe."""
        recipe = Recipe(
            id="test",
            name="Test Recipe",
            command="echo test",
            icon="🧪",
        )
        button = PinnedRecipeButton(recipe, position=0)

        assert button.recipe == recipe
        assert button.position == 0
        label_text = str(button.label)
        assert "🧪" in label_text
        assert "Test Recip" in label_text  # Truncated to 10 chars

    def test_button_without_recipe(self):
        """Test creating button for empty slot."""
        button = PinnedRecipeButton(None, position=2)

        assert button.recipe is None
        assert button.position == 2
        label_text = str(button.label)
        assert "[3]" in label_text  # Position + 1 for display
        assert "---" in label_text
        assert "empty" in button.classes

    def test_button_tooltip_with_recipe(self):
        """Test tooltip for button with recipe."""
        recipe = Recipe(
            id="test",
            name="Test Recipe",
            command="echo test",
            description="A test recipe",
        )
        button = PinnedRecipeButton(recipe, position=3)

        assert "Test Recipe" in button.tooltip
        assert "A test recipe" in button.tooltip
        assert "Ctrl+4" in button.tooltip  # Position 3 -> Ctrl+4

    def test_button_tooltip_without_recipe(self):
        """Test tooltip for empty slot."""
        button = PinnedRecipeButton(None, position=5)

        assert "Empty slot" in button.tooltip
        assert "Ctrl+6" in button.tooltip


class TestPinnedBarInit:
    """Tests for PinnedBar initialization."""

    def test_init_empty(self):
        """Test creating empty pinned bar."""
        bar = PinnedBar()
        assert bar.pinned_count == 0
        assert bar._recipes == [None] * 9

    def test_init_with_store(self):
        """Test creating pinned bar with store."""
        store = RecipeStore()
        r1 = Recipe(id="r1", name="R1", command="cmd", pinned=True, pin_position=0)
        r2 = Recipe(id="r2", name="R2", command="cmd", pinned=True, pin_position=3)
        store.add(r1)
        store.add(r2)

        bar = PinnedBar(store=store)
        assert bar.pinned_count == 2
        assert bar._recipes[0] == r1
        assert bar._recipes[3] == r2
        assert bar._recipes[1] is None

    def test_init_with_callback(self):
        """Test creating pinned bar with execute callback."""
        callback = MagicMock()
        bar = PinnedBar(on_execute=callback)
        assert bar._on_execute == callback


class TestPinnedBarMethods:
    """Tests for PinnedBar methods."""

    def test_set_recipes(self):
        """Test setting recipes from store."""
        bar = PinnedBar()
        store = RecipeStore()
        recipe = Recipe(id="r1", name="R1", command="cmd", pinned=True, pin_position=2)
        store.add(recipe)

        # Mock _refresh_buttons since it requires mounted widget
        bar._refresh_buttons = MagicMock()
        bar.set_recipes(store)

        assert bar._recipes[2] == recipe
        assert bar.pinned_count == 1
        bar._refresh_buttons.assert_called_once()

    def test_pin_recipe(self):
        """Test pinning a recipe to a position."""
        bar = PinnedBar()
        bar._refresh_buttons = MagicMock()

        recipe = Recipe(id="r1", name="R1", command="cmd")
        bar.pin_recipe(recipe, position=4)

        assert bar._recipes[4] == recipe
        assert bar.pinned_count == 1

    def test_pin_recipe_invalid_position(self):
        """Test pinning with invalid position does nothing."""
        bar = PinnedBar()
        bar._refresh_buttons = MagicMock()

        recipe = Recipe(id="r1", name="R1", command="cmd")
        bar.pin_recipe(recipe, position=10)  # Invalid

        assert all(r is None for r in bar._recipes)

    def test_unpin_position(self):
        """Test unpinning a position."""
        bar = PinnedBar()
        bar._refresh_buttons = MagicMock()

        recipe = Recipe(id="r1", name="R1", command="cmd")
        bar._recipes[3] = recipe
        bar.pinned_count = 1

        bar.unpin_position(3)

        assert bar._recipes[3] is None
        assert bar.pinned_count == 0

    def test_unpin_invalid_position(self):
        """Test unpinning invalid position does nothing."""
        bar = PinnedBar()
        bar._refresh_buttons = MagicMock()

        bar.unpin_position(15)  # Should not raise

    def test_get_recipe_at(self):
        """Test getting recipe at position."""
        bar = PinnedBar()
        recipe = Recipe(id="r1", name="R1", command="cmd")
        bar._recipes[5] = recipe

        assert bar.get_recipe_at(5) == recipe
        assert bar.get_recipe_at(0) is None
        assert bar.get_recipe_at(10) is None  # Invalid position


class TestPinnedBarExecution:
    """Tests for recipe execution in PinnedBar."""

    def test_execute_position_with_recipe(self):
        """Test executing recipe at position."""
        bar = PinnedBar()
        bar.post_message = MagicMock()

        recipe = Recipe(id="r1", name="R1", command="cmd")
        bar._recipes[2] = recipe

        bar._execute_position(2)

        assert recipe.use_count == 1
        bar.post_message.assert_called_once()
        message = bar.post_message.call_args[0][0]
        assert isinstance(message, PinnedBar.RecipeExecuted)
        assert message.recipe == recipe

    def test_execute_position_with_callback(self):
        """Test executing recipe calls callback."""
        callback = MagicMock()
        bar = PinnedBar(on_execute=callback)
        bar.post_message = MagicMock()

        recipe = Recipe(id="r1", name="R1", command="cmd")
        bar._recipes[1] = recipe

        bar._execute_position(1)

        callback.assert_called_once_with(recipe)

    def test_execute_empty_slot(self):
        """Test executing empty slot sends slot clicked message."""
        bar = PinnedBar()
        bar.post_message = MagicMock()

        bar._execute_position(4)  # Empty slot

        bar.post_message.assert_called_once()
        message = bar.post_message.call_args[0][0]
        assert isinstance(message, PinnedBar.RecipeSlotClicked)
        assert message.position == 4

    def test_execute_invalid_position(self):
        """Test executing invalid position does nothing."""
        bar = PinnedBar()
        bar.post_message = MagicMock()

        bar._execute_position(15)  # Invalid

        bar.post_message.assert_not_called()


class TestPinnedBarActions:
    """Tests for keyboard shortcut actions."""

    def test_action_execute_all_positions(self):
        """Test all execute action methods."""
        bar = PinnedBar()
        bar._execute_position = MagicMock()

        bar.action_execute_1()
        bar._execute_position.assert_called_with(0)

        bar.action_execute_2()
        bar._execute_position.assert_called_with(1)

        bar.action_execute_3()
        bar._execute_position.assert_called_with(2)

        bar.action_execute_4()
        bar._execute_position.assert_called_with(3)

        bar.action_execute_5()
        bar._execute_position.assert_called_with(4)

        bar.action_execute_6()
        bar._execute_position.assert_called_with(5)

        bar.action_execute_7()
        bar._execute_position.assert_called_with(6)

        bar.action_execute_8()
        bar._execute_position.assert_called_with(7)

        bar.action_execute_9()
        bar._execute_position.assert_called_with(8)


class TestPinnedBarBindings:
    """Tests for keyboard bindings."""

    def test_bindings_defined(self):
        """Test that all bindings are defined."""
        bindings = {b.key: b for b in PinnedBar.BINDINGS}

        assert "ctrl+1" in bindings
        assert "ctrl+2" in bindings
        assert "ctrl+3" in bindings
        assert "ctrl+4" in bindings
        assert "ctrl+5" in bindings
        assert "ctrl+6" in bindings
        assert "ctrl+7" in bindings
        assert "ctrl+8" in bindings
        assert "ctrl+9" in bindings

    def test_bindings_actions(self):
        """Test that bindings map to correct actions."""
        bindings = {b.key: b for b in PinnedBar.BINDINGS}

        assert bindings["ctrl+1"].action == "execute_1"
        assert bindings["ctrl+5"].action == "execute_5"
        assert bindings["ctrl+9"].action == "execute_9"


class TestPinnedBarMessages:
    """Tests for message classes."""

    def test_recipe_executed_message(self):
        """Test RecipeExecuted message."""
        recipe = Recipe(id="r1", name="R1", command="cmd")
        message = PinnedBar.RecipeExecuted(recipe)

        assert message.recipe == recipe

    def test_recipe_slot_clicked_message(self):
        """Test RecipeSlotClicked message."""
        message = PinnedBar.RecipeSlotClicked(position=5)

        assert message.position == 5
