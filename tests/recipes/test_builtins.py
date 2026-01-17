"""Tests for built-in recipes."""

from __future__ import annotations

import pytest

from ralph_agi.recipes.builtins import (
    BUILTIN_RECIPES,
    get_builtin_recipe,
    get_builtin_recipes_by_category,
    get_pinned_builtins,
)
from ralph_agi.recipes.models import RecipeCategory


class TestBuiltinRecipes:
    """Tests for built-in recipes list."""

    def test_builtins_not_empty(self):
        """Test that there are built-in recipes."""
        assert len(BUILTIN_RECIPES) > 0

    def test_all_builtins_marked(self):
        """Test all builtin recipes are marked as builtin."""
        for recipe in BUILTIN_RECIPES:
            assert recipe.builtin is True, f"{recipe.id} not marked as builtin"

    def test_all_builtins_have_id(self):
        """Test all builtin recipes have an ID starting with builtin-."""
        for recipe in BUILTIN_RECIPES:
            assert recipe.id.startswith("builtin-"), f"{recipe.id} doesn't start with builtin-"

    def test_all_builtins_have_name(self):
        """Test all builtin recipes have a name."""
        for recipe in BUILTIN_RECIPES:
            assert recipe.name, f"{recipe.id} has no name"

    def test_all_builtins_have_command(self):
        """Test all builtin recipes have a command."""
        for recipe in BUILTIN_RECIPES:
            assert recipe.command, f"{recipe.id} has no command"

    def test_all_builtins_have_description(self):
        """Test all builtin recipes have a description."""
        for recipe in BUILTIN_RECIPES:
            assert recipe.description, f"{recipe.id} has no description"

    def test_unique_ids(self):
        """Test all builtin recipes have unique IDs."""
        ids = [r.id for r in BUILTIN_RECIPES]
        assert len(ids) == len(set(ids)), "Duplicate IDs found"

    def test_unique_pin_positions(self):
        """Test pinned builtins have unique positions."""
        positions = [r.pin_position for r in BUILTIN_RECIPES if r.pinned and r.pin_position is not None]
        assert len(positions) == len(set(positions)), "Duplicate pin positions found"

    def test_pin_positions_valid_range(self):
        """Test pin positions are in valid range (0-8)."""
        for recipe in BUILTIN_RECIPES:
            if recipe.pin_position is not None:
                assert 0 <= recipe.pin_position <= 8, f"{recipe.id} has invalid pin position"


class TestGetBuiltinRecipe:
    """Tests for get_builtin_recipe function."""

    def test_get_existing(self):
        """Test getting an existing builtin recipe."""
        recipe = get_builtin_recipe("builtin-run-tests")
        assert recipe is not None
        assert recipe.name == "Run Tests"

    def test_get_nonexistent(self):
        """Test getting a nonexistent recipe."""
        recipe = get_builtin_recipe("nonexistent")
        assert recipe is None

    def test_get_all_builtins(self):
        """Test that all builtins can be retrieved."""
        for builtin in BUILTIN_RECIPES:
            recipe = get_builtin_recipe(builtin.id)
            assert recipe is not None
            assert recipe.id == builtin.id


class TestGetBuiltinRecipesByCategory:
    """Tests for get_builtin_recipes_by_category function."""

    def test_get_git_recipes(self):
        """Test getting Git category recipes."""
        git_recipes = get_builtin_recipes_by_category(RecipeCategory.GIT)
        assert len(git_recipes) > 0
        for recipe in git_recipes:
            assert recipe.category == RecipeCategory.GIT

    def test_get_test_recipes(self):
        """Test getting Test category recipes."""
        test_recipes = get_builtin_recipes_by_category(RecipeCategory.TEST)
        assert len(test_recipes) > 0
        for recipe in test_recipes:
            assert recipe.category == RecipeCategory.TEST

    def test_get_empty_category(self):
        """Test getting recipes from a category with no builtins."""
        # All categories should have at least some recipes based on builtins.py
        # but this tests the function handles the case gracefully
        recipes = get_builtin_recipes_by_category(RecipeCategory.DEPLOY)
        # Could be empty or not, just verify it returns a list
        assert isinstance(recipes, list)


class TestGetPinnedBuiltins:
    """Tests for get_pinned_builtins function."""

    def test_returns_pinned_only(self):
        """Test that only pinned recipes are returned."""
        pinned = get_pinned_builtins()
        for recipe in pinned:
            assert recipe.pinned is True

    def test_pinned_not_empty(self):
        """Test that there are some pinned builtins."""
        pinned = get_pinned_builtins()
        assert len(pinned) > 0

    def test_pinned_count_matches(self):
        """Test pinned count matches manual count."""
        pinned = get_pinned_builtins()
        expected_count = sum(1 for r in BUILTIN_RECIPES if r.pinned)
        assert len(pinned) == expected_count


class TestSpecificBuiltins:
    """Tests for specific builtin recipes."""

    def test_run_tests_recipe(self):
        """Test the Run Tests recipe."""
        recipe = get_builtin_recipe("builtin-run-tests")
        assert recipe is not None
        assert recipe.category == RecipeCategory.TEST
        assert "{path}" in recipe.command
        assert "path" in recipe.parameters
        assert recipe.pinned is True

    def test_commit_push_recipe(self):
        """Test the Commit & Push recipe."""
        recipe = get_builtin_recipe("builtin-commit-push")
        assert recipe is not None
        assert recipe.category == RecipeCategory.GIT
        assert "{message}" in recipe.command
        assert "message" in recipe.parameters

    def test_create_pr_recipe(self):
        """Test the Create PR recipe."""
        recipe = get_builtin_recipe("builtin-create-pr")
        assert recipe is not None
        assert recipe.category == RecipeCategory.GIT
        assert "gh pr create" in recipe.command

    def test_lint_recipe(self):
        """Test the Run Linting recipe."""
        recipe = get_builtin_recipe("builtin-lint")
        assert recipe is not None
        assert recipe.category == RecipeCategory.LINT
        assert "ruff" in recipe.command

    def test_ralph_run_recipe(self):
        """Test the Ralph Run recipe."""
        recipe = get_builtin_recipe("builtin-ralph-run")
        assert recipe is not None
        assert "ralph run" in recipe.command
        assert "prd" in recipe.parameters

    def test_recipe_execution(self):
        """Test that recipes can execute with parameters."""
        recipe = get_builtin_recipe("builtin-run-tests")
        cmd = recipe.execute_command(path="src/")
        assert cmd == "pytest src/ -v"

    def test_recipe_execution_defaults(self):
        """Test that recipes use default parameters."""
        recipe = get_builtin_recipe("builtin-run-tests")
        cmd = recipe.execute_command()
        assert cmd == "pytest tests/ -v"
