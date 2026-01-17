"""Data models for workflow recipes.

Recipes are saved commands that can be executed with a single action.
They support parameters, descriptions, and can be organized by category.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class RecipeCategory(str, Enum):
    """Categories for organizing recipes."""

    GIT = "git"
    TEST = "test"
    BUILD = "build"
    DEPLOY = "deploy"
    LINT = "lint"
    CUSTOM = "custom"


@dataclass
class Recipe:
    """A saved command/workflow recipe.

    Recipes encapsulate commands that can be executed with customizable
    parameters. They can be pinned for quick access.

    Attributes:
        id: Unique identifier.
        name: Display name.
        command: The command template to execute.
        description: Human-readable description.
        category: Recipe category for organization.
        parameters: Parameter definitions with defaults.
        shortcut: Optional keyboard shortcut (e.g., "ctrl+1").
        pinned: Whether this recipe is pinned to quick-access bar.
        pin_position: Position in pinned bar (0-8 for Ctrl+1 through Ctrl+9).
        icon: Optional icon/emoji for display.
        created_at: When the recipe was created.
        last_used: When the recipe was last executed.
        use_count: Number of times executed.
        tags: Optional tags for filtering.
        builtin: Whether this is a built-in recipe.

    Example:
        >>> recipe = Recipe(
        ...     name="Run Tests",
        ...     command="pytest {path} -v",
        ...     description="Run pytest on specified path",
        ...     parameters={"path": "tests/"},
        ...     shortcut="ctrl+1",
        ...     pinned=True,
        ... )
    """

    name: str
    command: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    category: RecipeCategory = RecipeCategory.CUSTOM
    parameters: dict[str, Any] = field(default_factory=dict)
    shortcut: Optional[str] = None
    pinned: bool = False
    pin_position: Optional[int] = None
    icon: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    last_used: Optional[str] = None
    use_count: int = 0
    tags: tuple[str, ...] = field(default_factory=tuple)
    builtin: bool = False

    def execute_command(self, **kwargs: Any) -> str:
        """Get the command with parameters substituted.

        Args:
            **kwargs: Parameter values to substitute.

        Returns:
            Command string with parameters filled in.

        Example:
            >>> recipe = Recipe(name="test", command="pytest {path}")
            >>> recipe.execute_command(path="tests/unit")
            'pytest tests/unit'
        """
        # Merge defaults with provided parameters
        params = {**self.parameters, **kwargs}
        return self.command.format(**params)

    def record_use(self) -> None:
        """Record that this recipe was used."""
        self.last_used = datetime.now().isoformat()
        self.use_count += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters,
            "shortcut": self.shortcut,
            "pinned": self.pinned,
            "pin_position": self.pin_position,
            "icon": self.icon,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "tags": list(self.tags),
            "builtin": self.builtin,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Recipe:
        """Create a Recipe from a dictionary.

        Args:
            data: Dictionary from JSON.

        Returns:
            Recipe instance.
        """
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data["name"],
            command=data["command"],
            description=data.get("description", ""),
            category=RecipeCategory(data.get("category", "custom")),
            parameters=data.get("parameters", {}),
            shortcut=data.get("shortcut"),
            pinned=data.get("pinned", False),
            pin_position=data.get("pin_position"),
            icon=data.get("icon", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_used=data.get("last_used"),
            use_count=data.get("use_count", 0),
            tags=tuple(data.get("tags", [])),
            builtin=data.get("builtin", False),
        )


@dataclass
class RecipeStore:
    """Collection of recipes with management methods.

    Manages a collection of recipes, handling pinning, searching,
    and organization.

    Attributes:
        recipes: Dictionary mapping recipe ID to Recipe.
        version: Store format version for migrations.
    """

    recipes: dict[str, Recipe] = field(default_factory=dict)
    version: str = "1.0"

    def add(self, recipe: Recipe) -> None:
        """Add a recipe to the store.

        Args:
            recipe: Recipe to add.
        """
        self.recipes[recipe.id] = recipe

    def remove(self, recipe_id: str) -> Optional[Recipe]:
        """Remove a recipe from the store.

        Args:
            recipe_id: ID of recipe to remove.

        Returns:
            Removed recipe, or None if not found.
        """
        return self.recipes.pop(recipe_id, None)

    def get(self, recipe_id: str) -> Optional[Recipe]:
        """Get a recipe by ID.

        Args:
            recipe_id: Recipe ID.

        Returns:
            Recipe if found, None otherwise.
        """
        return self.recipes.get(recipe_id)

    def get_by_name(self, name: str) -> Optional[Recipe]:
        """Get a recipe by name.

        Args:
            name: Recipe name.

        Returns:
            Recipe if found, None otherwise.
        """
        for recipe in self.recipes.values():
            if recipe.name.lower() == name.lower():
                return recipe
        return None

    def get_pinned(self) -> list[Recipe]:
        """Get all pinned recipes, sorted by pin position.

        Returns:
            List of pinned recipes.
        """
        pinned = [r for r in self.recipes.values() if r.pinned]
        return sorted(
            pinned,
            key=lambda r: (999 if r.pin_position is None else r.pin_position, r.name),
        )

    def get_by_category(self, category: RecipeCategory) -> list[Recipe]:
        """Get recipes by category.

        Args:
            category: Recipe category.

        Returns:
            List of recipes in category.
        """
        return [r for r in self.recipes.values() if r.category == category]

    def search(self, query: str) -> list[Recipe]:
        """Search recipes by name, description, or tags.

        Args:
            query: Search query.

        Returns:
            List of matching recipes.
        """
        query = query.lower()
        results = []
        for recipe in self.recipes.values():
            if (
                query in recipe.name.lower()
                or query in recipe.description.lower()
                or any(query in tag.lower() for tag in recipe.tags)
            ):
                results.append(recipe)
        return results

    def pin(self, recipe_id: str, position: Optional[int] = None) -> bool:
        """Pin a recipe to the quick-access bar.

        Args:
            recipe_id: Recipe ID to pin.
            position: Pin position (0-8). Auto-assigns if None.

        Returns:
            True if pinned successfully.
        """
        recipe = self.get(recipe_id)
        if recipe is None:
            return False

        recipe.pinned = True

        if position is not None:
            recipe.pin_position = position
        else:
            # Find next available position
            used_positions = {r.pin_position for r in self.get_pinned()}
            for i in range(9):
                if i not in used_positions:
                    recipe.pin_position = i
                    break

        return True

    def unpin(self, recipe_id: str) -> bool:
        """Unpin a recipe from the quick-access bar.

        Args:
            recipe_id: Recipe ID to unpin.

        Returns:
            True if unpinned successfully.
        """
        recipe = self.get(recipe_id)
        if recipe is None:
            return False

        recipe.pinned = False
        recipe.pin_position = None
        return True

    def get_by_shortcut(self, shortcut: str) -> Optional[Recipe]:
        """Get recipe by keyboard shortcut.

        Args:
            shortcut: Keyboard shortcut (e.g., "ctrl+1").

        Returns:
            Recipe if found, None otherwise.
        """
        for recipe in self.recipes.values():
            if recipe.shortcut == shortcut:
                return recipe
        return None

    def get_recent(self, limit: int = 10) -> list[Recipe]:
        """Get recently used recipes.

        Args:
            limit: Maximum number of recipes to return.

        Returns:
            List of recently used recipes.
        """
        used = [r for r in self.recipes.values() if r.last_used]
        sorted_recipes = sorted(
            used,
            key=lambda r: r.last_used or "",
            reverse=True,
        )
        return sorted_recipes[:limit]

    def get_frequent(self, limit: int = 10) -> list[Recipe]:
        """Get most frequently used recipes.

        Args:
            limit: Maximum number of recipes to return.

        Returns:
            List of frequently used recipes.
        """
        used = [r for r in self.recipes.values() if r.use_count > 0]
        sorted_recipes = sorted(
            used,
            key=lambda r: r.use_count,
            reverse=True,
        )
        return sorted_recipes[:limit]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "recipes": [r.to_dict() for r in self.recipes.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecipeStore:
        """Create a RecipeStore from a dictionary.

        Args:
            data: Dictionary from JSON.

        Returns:
            RecipeStore instance.
        """
        store = cls(version=data.get("version", "1.0"))
        for recipe_data in data.get("recipes", []):
            recipe = Recipe.from_dict(recipe_data)
            store.add(recipe)
        return store

    def __len__(self) -> int:
        """Get the number of recipes."""
        return len(self.recipes)

    def __iter__(self):
        """Iterate over recipes."""
        return iter(self.recipes.values())
