"""Tests for recipe data models."""

from __future__ import annotations

import pytest
from datetime import datetime

from ralph_agi.recipes.models import Recipe, RecipeCategory, RecipeStore


class TestRecipe:
    """Tests for Recipe dataclass."""

    def test_recipe_creation_minimal(self):
        """Test creating a recipe with minimal fields."""
        recipe = Recipe(name="Test", command="echo hello")
        assert recipe.name == "Test"
        assert recipe.command == "echo hello"
        assert recipe.id is not None  # Auto-generated
        assert len(recipe.id) == 8
        assert recipe.description == ""
        assert recipe.category == RecipeCategory.CUSTOM
        assert recipe.parameters == {}
        assert recipe.pinned is False
        assert recipe.builtin is False

    def test_recipe_creation_full(self):
        """Test creating a recipe with all fields."""
        recipe = Recipe(
            id="test-id",
            name="Full Recipe",
            command="pytest {path} -v",
            description="Run tests",
            category=RecipeCategory.TEST,
            parameters={"path": "tests/"},
            shortcut="ctrl+t",
            pinned=True,
            pin_position=0,
            icon="🧪",
            tags=("test", "pytest"),
            builtin=True,
        )
        assert recipe.id == "test-id"
        assert recipe.name == "Full Recipe"
        assert recipe.command == "pytest {path} -v"
        assert recipe.description == "Run tests"
        assert recipe.category == RecipeCategory.TEST
        assert recipe.parameters == {"path": "tests/"}
        assert recipe.shortcut == "ctrl+t"
        assert recipe.pinned is True
        assert recipe.pin_position == 0
        assert recipe.icon == "🧪"
        assert recipe.tags == ("test", "pytest")
        assert recipe.builtin is True

    def test_execute_command_no_params(self):
        """Test executing a command without parameters."""
        recipe = Recipe(name="Test", command="echo hello")
        assert recipe.execute_command() == "echo hello"

    def test_execute_command_with_defaults(self):
        """Test executing a command with default parameters."""
        recipe = Recipe(
            name="Test",
            command="pytest {path} -v",
            parameters={"path": "tests/"},
        )
        assert recipe.execute_command() == "pytest tests/ -v"

    def test_execute_command_override_params(self):
        """Test executing a command with overridden parameters."""
        recipe = Recipe(
            name="Test",
            command="pytest {path} -v",
            parameters={"path": "tests/"},
        )
        assert recipe.execute_command(path="src/") == "pytest src/ -v"

    def test_execute_command_multiple_params(self):
        """Test executing a command with multiple parameters."""
        recipe = Recipe(
            name="Test",
            command='git commit -m "{message}" && git push {remote}',
            parameters={"message": "Update", "remote": "origin"},
        )
        result = recipe.execute_command(message="Fix bug")
        assert result == 'git commit -m "Fix bug" && git push origin'

    def test_record_use(self):
        """Test recording recipe usage."""
        recipe = Recipe(name="Test", command="echo hello")
        assert recipe.use_count == 0
        assert recipe.last_used is None

        recipe.record_use()
        assert recipe.use_count == 1
        assert recipe.last_used is not None
        # Verify it's a valid ISO format timestamp
        datetime.fromisoformat(recipe.last_used)

        recipe.record_use()
        assert recipe.use_count == 2

    def test_to_dict(self):
        """Test converting recipe to dictionary."""
        recipe = Recipe(
            id="test-id",
            name="Test",
            command="echo hello",
            category=RecipeCategory.GIT,
            tags=("git", "test"),
        )
        data = recipe.to_dict()
        assert data["id"] == "test-id"
        assert data["name"] == "Test"
        assert data["command"] == "echo hello"
        assert data["category"] == "git"
        assert data["tags"] == ["git", "test"]  # Tuple becomes list
        assert "created_at" in data

    def test_from_dict(self):
        """Test creating recipe from dictionary."""
        data = {
            "id": "test-id",
            "name": "Test",
            "command": "echo hello",
            "description": "A test recipe",
            "category": "test",
            "parameters": {"foo": "bar"},
            "pinned": True,
            "pin_position": 2,
            "tags": ["one", "two"],
        }
        recipe = Recipe.from_dict(data)
        assert recipe.id == "test-id"
        assert recipe.name == "Test"
        assert recipe.command == "echo hello"
        assert recipe.description == "A test recipe"
        assert recipe.category == RecipeCategory.TEST
        assert recipe.parameters == {"foo": "bar"}
        assert recipe.pinned is True
        assert recipe.pin_position == 2
        assert recipe.tags == ("one", "two")  # List becomes tuple

    def test_from_dict_minimal(self):
        """Test creating recipe from minimal dictionary."""
        data = {"name": "Test", "command": "echo hello"}
        recipe = Recipe.from_dict(data)
        assert recipe.name == "Test"
        assert recipe.command == "echo hello"
        assert recipe.category == RecipeCategory.CUSTOM  # Default
        assert recipe.pinned is False

    def test_roundtrip(self):
        """Test converting to dict and back."""
        original = Recipe(
            name="Test",
            command="pytest {path}",
            description="Test desc",
            category=RecipeCategory.TEST,
            parameters={"path": "tests/"},
            pinned=True,
            pin_position=3,
            tags=("tag1", "tag2"),
        )
        data = original.to_dict()
        restored = Recipe.from_dict(data)
        assert restored.name == original.name
        assert restored.command == original.command
        assert restored.description == original.description
        assert restored.category == original.category
        assert restored.parameters == original.parameters
        assert restored.pinned == original.pinned
        assert restored.pin_position == original.pin_position
        assert restored.tags == original.tags


class TestRecipeCategory:
    """Tests for RecipeCategory enum."""

    def test_category_values(self):
        """Test all category values exist."""
        assert RecipeCategory.GIT.value == "git"
        assert RecipeCategory.TEST.value == "test"
        assert RecipeCategory.BUILD.value == "build"
        assert RecipeCategory.DEPLOY.value == "deploy"
        assert RecipeCategory.LINT.value == "lint"
        assert RecipeCategory.CUSTOM.value == "custom"

    def test_category_from_string(self):
        """Test creating category from string."""
        assert RecipeCategory("git") == RecipeCategory.GIT
        assert RecipeCategory("test") == RecipeCategory.TEST
        assert RecipeCategory("custom") == RecipeCategory.CUSTOM


class TestRecipeStore:
    """Tests for RecipeStore."""

    def test_store_creation(self):
        """Test creating an empty store."""
        store = RecipeStore()
        assert len(store) == 0
        assert store.version == "1.0"

    def test_add_recipe(self):
        """Test adding a recipe."""
        store = RecipeStore()
        recipe = Recipe(id="test", name="Test", command="echo hello")
        store.add(recipe)
        assert len(store) == 1
        assert store.get("test") == recipe

    def test_remove_recipe(self):
        """Test removing a recipe."""
        store = RecipeStore()
        recipe = Recipe(id="test", name="Test", command="echo hello")
        store.add(recipe)
        removed = store.remove("test")
        assert removed == recipe
        assert len(store) == 0
        assert store.get("test") is None

    def test_remove_nonexistent(self):
        """Test removing a recipe that doesn't exist."""
        store = RecipeStore()
        assert store.remove("nonexistent") is None

    def test_get_recipe(self):
        """Test getting a recipe by ID."""
        store = RecipeStore()
        recipe = Recipe(id="test", name="Test", command="echo hello")
        store.add(recipe)
        assert store.get("test") == recipe
        assert store.get("nonexistent") is None

    def test_get_by_name(self):
        """Test getting a recipe by name."""
        store = RecipeStore()
        recipe = Recipe(id="test", name="My Recipe", command="echo hello")
        store.add(recipe)
        assert store.get_by_name("My Recipe") == recipe
        assert store.get_by_name("my recipe") == recipe  # Case insensitive
        assert store.get_by_name("Other") is None

    def test_get_pinned(self):
        """Test getting pinned recipes."""
        store = RecipeStore()
        r1 = Recipe(id="r1", name="R1", command="cmd", pinned=True, pin_position=2)
        r2 = Recipe(id="r2", name="R2", command="cmd", pinned=True, pin_position=0)
        r3 = Recipe(id="r3", name="R3", command="cmd", pinned=False)
        store.add(r1)
        store.add(r2)
        store.add(r3)

        pinned = store.get_pinned()
        assert len(pinned) == 2
        # Should be sorted by pin_position
        assert pinned[0].pin_position == 0
        assert pinned[1].pin_position == 2

    def test_get_by_category(self):
        """Test getting recipes by category."""
        store = RecipeStore()
        r1 = Recipe(id="r1", name="R1", command="cmd", category=RecipeCategory.GIT)
        r2 = Recipe(id="r2", name="R2", command="cmd", category=RecipeCategory.TEST)
        r3 = Recipe(id="r3", name="R3", command="cmd", category=RecipeCategory.GIT)
        store.add(r1)
        store.add(r2)
        store.add(r3)

        git_recipes = store.get_by_category(RecipeCategory.GIT)
        assert len(git_recipes) == 2
        assert r1 in git_recipes
        assert r3 in git_recipes

    def test_search_by_name(self):
        """Test searching recipes by name."""
        store = RecipeStore()
        store.add(Recipe(id="r1", name="Run Tests", command="pytest"))
        store.add(Recipe(id="r2", name="Git Status", command="git status"))
        store.add(Recipe(id="r3", name="Build", command="make"))

        results = store.search("test")
        assert len(results) == 1
        assert results[0].id == "r1"

    def test_search_by_description(self):
        """Test searching recipes by description."""
        store = RecipeStore()
        store.add(Recipe(id="r1", name="Cmd1", command="cmd", description="Run the tests"))
        store.add(Recipe(id="r2", name="Cmd2", command="cmd", description="Build project"))

        results = store.search("tests")
        assert len(results) == 1
        assert results[0].id == "r1"

    def test_search_by_tag(self):
        """Test searching recipes by tag."""
        store = RecipeStore()
        store.add(Recipe(id="r1", name="Cmd1", command="cmd", tags=("quality", "lint")))
        store.add(Recipe(id="r2", name="Cmd2", command="cmd", tags=("build",)))

        results = store.search("quality")
        assert len(results) == 1
        assert results[0].id == "r1"

    def test_pin_recipe(self):
        """Test pinning a recipe."""
        store = RecipeStore()
        recipe = Recipe(id="test", name="Test", command="cmd")
        store.add(recipe)

        assert store.pin("test", position=3) is True
        assert recipe.pinned is True
        assert recipe.pin_position == 3

    def test_pin_auto_position(self):
        """Test pinning with auto-assigned position."""
        store = RecipeStore()
        r1 = Recipe(id="r1", name="R1", command="cmd")
        r2 = Recipe(id="r2", name="R2", command="cmd", pinned=True, pin_position=0)
        store.add(r1)
        store.add(r2)

        store.pin("r1")  # Should get position 1 (0 is taken)
        assert r1.pinned is True
        assert r1.pin_position == 1

    def test_pin_nonexistent(self):
        """Test pinning a recipe that doesn't exist."""
        store = RecipeStore()
        assert store.pin("nonexistent") is False

    def test_unpin_recipe(self):
        """Test unpinning a recipe."""
        store = RecipeStore()
        recipe = Recipe(id="test", name="Test", command="cmd", pinned=True, pin_position=2)
        store.add(recipe)

        assert store.unpin("test") is True
        assert recipe.pinned is False
        assert recipe.pin_position is None

    def test_unpin_nonexistent(self):
        """Test unpinning a recipe that doesn't exist."""
        store = RecipeStore()
        assert store.unpin("nonexistent") is False

    def test_get_by_shortcut(self):
        """Test getting recipe by shortcut."""
        store = RecipeStore()
        recipe = Recipe(id="test", name="Test", command="cmd", shortcut="ctrl+t")
        store.add(recipe)

        assert store.get_by_shortcut("ctrl+t") == recipe
        assert store.get_by_shortcut("ctrl+x") is None

    def test_get_recent(self):
        """Test getting recently used recipes."""
        store = RecipeStore()
        r1 = Recipe(id="r1", name="R1", command="cmd")
        r2 = Recipe(id="r2", name="R2", command="cmd")
        r3 = Recipe(id="r3", name="R3", command="cmd")
        store.add(r1)
        store.add(r2)
        store.add(r3)

        # Record usage
        r2.record_use()
        r1.record_use()  # r1 used after r2

        recent = store.get_recent(limit=2)
        assert len(recent) == 2
        assert recent[0] == r1  # Most recent first
        assert recent[1] == r2

    def test_get_frequent(self):
        """Test getting frequently used recipes."""
        store = RecipeStore()
        r1 = Recipe(id="r1", name="R1", command="cmd")
        r2 = Recipe(id="r2", name="R2", command="cmd")
        r3 = Recipe(id="r3", name="R3", command="cmd")
        store.add(r1)
        store.add(r2)
        store.add(r3)

        # Record usage
        r2.record_use()
        r2.record_use()
        r2.record_use()
        r1.record_use()

        frequent = store.get_frequent(limit=2)
        assert len(frequent) == 2
        assert frequent[0] == r2  # Most frequent first
        assert frequent[1] == r1

    def test_to_dict(self):
        """Test converting store to dictionary."""
        store = RecipeStore()
        store.add(Recipe(id="r1", name="R1", command="cmd1"))
        store.add(Recipe(id="r2", name="R2", command="cmd2"))

        data = store.to_dict()
        assert data["version"] == "1.0"
        assert len(data["recipes"]) == 2

    def test_from_dict(self):
        """Test creating store from dictionary."""
        data = {
            "version": "1.0",
            "recipes": [
                {"id": "r1", "name": "R1", "command": "cmd1"},
                {"id": "r2", "name": "R2", "command": "cmd2"},
            ],
        }
        store = RecipeStore.from_dict(data)
        assert len(store) == 2
        assert store.get("r1").name == "R1"
        assert store.get("r2").name == "R2"

    def test_iterate(self):
        """Test iterating over recipes."""
        store = RecipeStore()
        store.add(Recipe(id="r1", name="R1", command="cmd1"))
        store.add(Recipe(id="r2", name="R2", command="cmd2"))

        names = [r.name for r in store]
        assert "R1" in names
        assert "R2" in names
