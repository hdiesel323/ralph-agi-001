"""Recipe storage and persistence.

Handles loading and saving recipes from:
1. User-level: ~/.ralph/recipes.json
2. Project-level: .ralph/recipes.json

Project recipes are merged with user recipes, with project taking precedence.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from ralph_agi.recipes.models import Recipe, RecipeStore

logger = logging.getLogger(__name__)

# Default paths
USER_RECIPES_DIR = ".ralph"
USER_RECIPES_FILE = "recipes.json"
PROJECT_RECIPES_DIR = ".ralph"
PROJECT_RECIPES_FILE = "recipes.json"


def get_user_recipes_path() -> Path:
    """Get the path to user-level recipes file.

    Returns:
        Path to ~/.ralph/recipes.json
    """
    home = Path.home()
    return home / USER_RECIPES_DIR / USER_RECIPES_FILE


def get_project_recipes_path(project_root: Optional[Path] = None) -> Path:
    """Get the path to project-level recipes file.

    Args:
        project_root: Project root directory. Uses cwd if None.

    Returns:
        Path to .ralph/recipes.json in project.
    """
    if project_root is None:
        project_root = Path.cwd()
    return project_root / PROJECT_RECIPES_DIR / PROJECT_RECIPES_FILE


def load_recipes(
    path: Optional[Path] = None,
    include_builtins: bool = True,
) -> RecipeStore:
    """Load recipes from a JSON file.

    Args:
        path: Path to recipes.json file. Uses user path if None.
        include_builtins: Whether to include built-in recipes.

    Returns:
        RecipeStore with loaded recipes.
    """
    if path is None:
        path = get_user_recipes_path()

    store = RecipeStore()

    # Load built-ins first
    if include_builtins:
        from ralph_agi.recipes.builtins import BUILTIN_RECIPES
        for recipe in BUILTIN_RECIPES:
            store.add(recipe)

    # Load from file if exists
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            file_store = RecipeStore.from_dict(data)

            # Merge with store (file recipes override builtins with same ID)
            for recipe in file_store:
                store.add(recipe)

            logger.debug(f"Loaded {len(file_store)} recipes from {path}")
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in recipes file {path}: {e}")
        except Exception as e:
            logger.warning(f"Error loading recipes from {path}: {e}")

    return store


def save_recipes(
    store: RecipeStore,
    path: Optional[Path] = None,
    exclude_builtins: bool = True,
) -> None:
    """Save recipes to a JSON file.

    Uses atomic write (write to temp, then rename) for safety.

    Args:
        store: RecipeStore to save.
        path: Path to save to. Uses user path if None.
        exclude_builtins: Whether to exclude built-in recipes from save.
    """
    if path is None:
        path = get_user_recipes_path()

    # Create directory if needed
    path.parent.mkdir(parents=True, exist_ok=True)

    # Filter out builtins if requested
    if exclude_builtins:
        save_store = RecipeStore(version=store.version)
        for recipe in store:
            if not recipe.builtin:
                save_store.add(recipe)
    else:
        save_store = store

    data = save_store.to_dict()

    # Atomic write
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(
            suffix=".json.tmp",
            dir=path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except Exception:
            os.close(fd)
            raise

        os.replace(tmp_path, path)
        tmp_path = None
        logger.debug(f"Saved {len(save_store)} recipes to {path}")

    except Exception as e:
        logger.error(f"Failed to save recipes to {path}: {e}")
        raise
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def merge_recipe_stores(
    *stores: RecipeStore,
    prefer_later: bool = True,
) -> RecipeStore:
    """Merge multiple recipe stores.

    Useful for combining user and project recipes.

    Args:
        *stores: Recipe stores to merge (in order).
        prefer_later: If True, later stores override earlier on conflict.

    Returns:
        Merged RecipeStore.
    """
    merged = RecipeStore()

    for store in stores:
        for recipe in store:
            if prefer_later:
                # Later stores always override
                merged.add(recipe)
            else:
                # Only add if not already present
                if recipe.id not in merged.recipes:
                    merged.add(recipe)

    return merged


def load_all_recipes(
    project_root: Optional[Path] = None,
    include_builtins: bool = True,
) -> RecipeStore:
    """Load recipes from all sources, merged.

    Loads from:
    1. Built-in recipes
    2. User recipes (~/.ralph/recipes.json)
    3. Project recipes (.ralph/recipes.json)

    Later sources override earlier ones.

    Args:
        project_root: Project root for project recipes.
        include_builtins: Whether to include built-in recipes.

    Returns:
        Merged RecipeStore.
    """
    stores = []

    # Load user recipes (includes builtins)
    user_store = load_recipes(
        get_user_recipes_path(),
        include_builtins=include_builtins,
    )
    stores.append(user_store)

    # Load project recipes if they exist
    project_path = get_project_recipes_path(project_root)
    if project_path.exists():
        project_store = load_recipes(project_path, include_builtins=False)
        stores.append(project_store)

    return merge_recipe_stores(*stores)


def export_recipes(
    store: RecipeStore,
    path: Path,
    recipe_ids: Optional[list[str]] = None,
) -> int:
    """Export recipes to a JSON file.

    Args:
        store: RecipeStore to export from.
        path: Path to export file.
        recipe_ids: Specific recipe IDs to export. All if None.

    Returns:
        Number of recipes exported.
    """
    if recipe_ids:
        export_store = RecipeStore()
        for rid in recipe_ids:
            recipe = store.get(rid)
            if recipe:
                export_store.add(recipe)
    else:
        export_store = store

    save_recipes(export_store, path, exclude_builtins=False)
    return len(export_store)


def import_recipes(
    path: Path,
    target_store: RecipeStore,
    overwrite: bool = False,
) -> int:
    """Import recipes from a JSON file.

    Args:
        path: Path to import file.
        target_store: Store to import into.
        overwrite: Whether to overwrite existing recipes.

    Returns:
        Number of recipes imported.
    """
    imported = 0
    import_store = load_recipes(path, include_builtins=False)

    for recipe in import_store:
        if overwrite or recipe.id not in target_store.recipes:
            # Don't import as builtin
            recipe.builtin = False
            target_store.add(recipe)
            imported += 1

    return imported
