"""Tests for recipe storage and persistence."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from ralph_agi.recipes.models import Recipe, RecipeCategory, RecipeStore
from ralph_agi.recipes.storage import (
    get_user_recipes_path,
    get_project_recipes_path,
    load_recipes,
    save_recipes,
    merge_recipe_stores,
    load_all_recipes,
    export_recipes,
    import_recipes,
)


class TestPaths:
    """Tests for path functions."""

    def test_user_recipes_path(self):
        """Test getting user recipes path."""
        path = get_user_recipes_path()
        assert path.name == "recipes.json"
        assert ".ralph" in str(path)
        assert str(Path.home()) in str(path)

    def test_project_recipes_path_default(self):
        """Test getting project recipes path with default cwd."""
        path = get_project_recipes_path()
        assert path.name == "recipes.json"
        assert ".ralph" in str(path)

    def test_project_recipes_path_custom(self, tmp_path):
        """Test getting project recipes path with custom root."""
        path = get_project_recipes_path(tmp_path)
        assert path == tmp_path / ".ralph" / "recipes.json"


class TestLoadRecipes:
    """Tests for load_recipes function."""

    def test_load_nonexistent_file_with_builtins(self, tmp_path):
        """Test loading from nonexistent file includes builtins."""
        path = tmp_path / "recipes.json"
        store = load_recipes(path, include_builtins=True)
        # Should have built-in recipes
        assert len(store) > 0
        assert any(r.builtin for r in store)

    def test_load_nonexistent_file_without_builtins(self, tmp_path):
        """Test loading from nonexistent file without builtins."""
        path = tmp_path / "recipes.json"
        store = load_recipes(path, include_builtins=False)
        assert len(store) == 0

    def test_load_valid_file(self, tmp_path):
        """Test loading from valid JSON file."""
        path = tmp_path / "recipes.json"
        data = {
            "version": "1.0",
            "recipes": [
                {"id": "r1", "name": "Recipe 1", "command": "cmd1"},
                {"id": "r2", "name": "Recipe 2", "command": "cmd2"},
            ],
        }
        path.write_text(json.dumps(data))

        store = load_recipes(path, include_builtins=False)
        assert len(store) == 2
        assert store.get("r1").name == "Recipe 1"

    def test_load_invalid_json(self, tmp_path):
        """Test loading from invalid JSON file."""
        path = tmp_path / "recipes.json"
        path.write_text("not valid json {{{")

        # Should not raise, returns store with builtins only
        store = load_recipes(path, include_builtins=True)
        assert any(r.builtin for r in store)

    def test_load_overrides_builtins(self, tmp_path):
        """Test that file recipes override builtins with same ID."""
        path = tmp_path / "recipes.json"
        # Use a builtin ID but with different values
        data = {
            "version": "1.0",
            "recipes": [
                {
                    "id": "builtin-run-tests",
                    "name": "Custom Tests",
                    "command": "custom test cmd",
                    "description": "Custom",
                },
            ],
        }
        path.write_text(json.dumps(data))

        store = load_recipes(path, include_builtins=True)
        recipe = store.get("builtin-run-tests")
        assert recipe.name == "Custom Tests"
        assert recipe.command == "custom test cmd"


class TestSaveRecipes:
    """Tests for save_recipes function."""

    def test_save_creates_directory(self, tmp_path):
        """Test that save creates parent directory if needed."""
        path = tmp_path / "subdir" / "recipes.json"
        store = RecipeStore()
        store.add(Recipe(id="r1", name="R1", command="cmd"))

        save_recipes(store, path)
        assert path.exists()
        assert path.parent.exists()

    def test_save_excludes_builtins(self, tmp_path):
        """Test that save excludes builtin recipes by default."""
        path = tmp_path / "recipes.json"
        store = RecipeStore()
        store.add(Recipe(id="r1", name="R1", command="cmd", builtin=False))
        store.add(Recipe(id="r2", name="R2", command="cmd", builtin=True))

        save_recipes(store, path, exclude_builtins=True)

        # Load back and verify
        data = json.loads(path.read_text())
        assert len(data["recipes"]) == 1
        assert data["recipes"][0]["id"] == "r1"

    def test_save_includes_builtins(self, tmp_path):
        """Test that save can include builtin recipes."""
        path = tmp_path / "recipes.json"
        store = RecipeStore()
        store.add(Recipe(id="r1", name="R1", command="cmd", builtin=False))
        store.add(Recipe(id="r2", name="R2", command="cmd", builtin=True))

        save_recipes(store, path, exclude_builtins=False)

        data = json.loads(path.read_text())
        assert len(data["recipes"]) == 2

    def test_save_atomic_write(self, tmp_path):
        """Test that save uses atomic write."""
        path = tmp_path / "recipes.json"
        store = RecipeStore()
        store.add(Recipe(id="r1", name="R1", command="cmd"))

        save_recipes(store, path)

        # File should exist and be valid
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data["recipes"]) == 1

    def test_save_overwrites_existing(self, tmp_path):
        """Test that save overwrites existing file."""
        path = tmp_path / "recipes.json"

        # Save first version
        store1 = RecipeStore()
        store1.add(Recipe(id="r1", name="Version 1", command="cmd"))
        save_recipes(store1, path)

        # Save second version
        store2 = RecipeStore()
        store2.add(Recipe(id="r2", name="Version 2", command="cmd"))
        save_recipes(store2, path)

        # Should have only second version
        data = json.loads(path.read_text())
        assert len(data["recipes"]) == 1
        assert data["recipes"][0]["id"] == "r2"


class TestMergeStores:
    """Tests for merge_recipe_stores function."""

    def test_merge_empty_stores(self):
        """Test merging empty stores."""
        merged = merge_recipe_stores(RecipeStore(), RecipeStore())
        assert len(merged) == 0

    def test_merge_disjoint_stores(self):
        """Test merging stores with different recipes."""
        store1 = RecipeStore()
        store1.add(Recipe(id="r1", name="R1", command="cmd1"))

        store2 = RecipeStore()
        store2.add(Recipe(id="r2", name="R2", command="cmd2"))

        merged = merge_recipe_stores(store1, store2)
        assert len(merged) == 2
        assert merged.get("r1") is not None
        assert merged.get("r2") is not None

    def test_merge_overlapping_prefer_later(self):
        """Test merging with overlap, later wins."""
        store1 = RecipeStore()
        store1.add(Recipe(id="r1", name="Old Name", command="cmd"))

        store2 = RecipeStore()
        store2.add(Recipe(id="r1", name="New Name", command="cmd"))

        merged = merge_recipe_stores(store1, store2, prefer_later=True)
        assert len(merged) == 1
        assert merged.get("r1").name == "New Name"

    def test_merge_overlapping_prefer_earlier(self):
        """Test merging with overlap, earlier wins."""
        store1 = RecipeStore()
        store1.add(Recipe(id="r1", name="Old Name", command="cmd"))

        store2 = RecipeStore()
        store2.add(Recipe(id="r1", name="New Name", command="cmd"))

        merged = merge_recipe_stores(store1, store2, prefer_later=False)
        assert len(merged) == 1
        assert merged.get("r1").name == "Old Name"

    def test_merge_multiple_stores(self):
        """Test merging more than two stores."""
        store1 = RecipeStore()
        store1.add(Recipe(id="r1", name="R1", command="cmd"))

        store2 = RecipeStore()
        store2.add(Recipe(id="r2", name="R2", command="cmd"))

        store3 = RecipeStore()
        store3.add(Recipe(id="r3", name="R3", command="cmd"))

        merged = merge_recipe_stores(store1, store2, store3)
        assert len(merged) == 3


class TestLoadAllRecipes:
    """Tests for load_all_recipes function."""

    def test_load_all_with_project_override(self, tmp_path):
        """Test loading all recipes with project overriding user."""
        # Create user recipes
        user_dir = tmp_path / "home" / ".ralph"
        user_dir.mkdir(parents=True)
        user_path = user_dir / "recipes.json"
        user_data = {
            "version": "1.0",
            "recipes": [
                {"id": "shared", "name": "User Version", "command": "user cmd"},
                {"id": "user-only", "name": "User Only", "command": "cmd"},
            ],
        }
        user_path.write_text(json.dumps(user_data))

        # Create project recipes
        project_dir = tmp_path / "project" / ".ralph"
        project_dir.mkdir(parents=True)
        project_path = project_dir / "recipes.json"
        project_data = {
            "version": "1.0",
            "recipes": [
                {"id": "shared", "name": "Project Version", "command": "proj cmd"},
                {"id": "project-only", "name": "Project Only", "command": "cmd"},
            ],
        }
        project_path.write_text(json.dumps(project_data))

        # Monkeypatch the path functions
        import ralph_agi.recipes.storage as storage

        original_user_path = storage.get_user_recipes_path
        original_project_path = storage.get_project_recipes_path

        storage.get_user_recipes_path = lambda: user_path
        storage.get_project_recipes_path = lambda root=None: project_path

        try:
            store = load_all_recipes(include_builtins=False)
            # Project should override user for shared ID
            assert store.get("shared").name == "Project Version"
            assert store.get("user-only") is not None
            assert store.get("project-only") is not None
        finally:
            storage.get_user_recipes_path = original_user_path
            storage.get_project_recipes_path = original_project_path


class TestExportImport:
    """Tests for export and import functions."""

    def test_export_all_recipes(self, tmp_path):
        """Test exporting all recipes."""
        store = RecipeStore()
        store.add(Recipe(id="r1", name="R1", command="cmd1"))
        store.add(Recipe(id="r2", name="R2", command="cmd2"))

        export_path = tmp_path / "export.json"
        count = export_recipes(store, export_path)

        assert count == 2
        assert export_path.exists()

        data = json.loads(export_path.read_text())
        assert len(data["recipes"]) == 2

    def test_export_specific_recipes(self, tmp_path):
        """Test exporting specific recipes."""
        store = RecipeStore()
        store.add(Recipe(id="r1", name="R1", command="cmd1"))
        store.add(Recipe(id="r2", name="R2", command="cmd2"))
        store.add(Recipe(id="r3", name="R3", command="cmd3"))

        export_path = tmp_path / "export.json"
        count = export_recipes(store, export_path, recipe_ids=["r1", "r3"])

        assert count == 2

        data = json.loads(export_path.read_text())
        ids = [r["id"] for r in data["recipes"]]
        assert "r1" in ids
        assert "r3" in ids
        assert "r2" not in ids

    def test_import_recipes(self, tmp_path):
        """Test importing recipes."""
        # Create import file
        import_path = tmp_path / "import.json"
        import_data = {
            "version": "1.0",
            "recipes": [
                {"id": "imported1", "name": "Imported 1", "command": "cmd1"},
                {"id": "imported2", "name": "Imported 2", "command": "cmd2"},
            ],
        }
        import_path.write_text(json.dumps(import_data))

        # Import into target store
        target = RecipeStore()
        count = import_recipes(import_path, target)

        assert count == 2
        assert target.get("imported1") is not None
        assert target.get("imported2") is not None
        # Imported recipes should not be marked as builtin
        assert target.get("imported1").builtin is False

    def test_import_no_overwrite(self, tmp_path):
        """Test importing without overwriting existing."""
        import_path = tmp_path / "import.json"
        import_data = {
            "version": "1.0",
            "recipes": [
                {"id": "existing", "name": "New Name", "command": "new cmd"},
            ],
        }
        import_path.write_text(json.dumps(import_data))

        target = RecipeStore()
        target.add(Recipe(id="existing", name="Old Name", command="old cmd"))

        count = import_recipes(import_path, target, overwrite=False)

        assert count == 0
        assert target.get("existing").name == "Old Name"

    def test_import_with_overwrite(self, tmp_path):
        """Test importing with overwriting existing."""
        import_path = tmp_path / "import.json"
        import_data = {
            "version": "1.0",
            "recipes": [
                {"id": "existing", "name": "New Name", "command": "new cmd"},
            ],
        }
        import_path.write_text(json.dumps(import_data))

        target = RecipeStore()
        target.add(Recipe(id="existing", name="Old Name", command="old cmd"))

        count = import_recipes(import_path, target, overwrite=True)

        assert count == 1
        assert target.get("existing").name == "New Name"
