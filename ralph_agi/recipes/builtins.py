"""Built-in workflow recipes for RALPH-AGI.

These are pre-defined recipes for common development workflows.
They are always available and cannot be deleted (though they can be hidden).
"""

from __future__ import annotations

from typing import Optional

from ralph_agi.recipes.models import Recipe, RecipeCategory


# Built-in recipes
BUILTIN_RECIPES: list[Recipe] = [
    # Git workflows
    Recipe(
        id="builtin-run-tests",
        name="Run Tests",
        command="pytest {path} -v",
        description="Run pytest test suite",
        category=RecipeCategory.TEST,
        parameters={"path": "tests/"},
        icon="🧪",
        pinned=True,
        pin_position=0,
        tags=("test", "pytest", "quality"),
        builtin=True,
    ),
    Recipe(
        id="builtin-commit-push",
        name="Commit & Push",
        command='git add -A && git commit -m "{message}" && git push',
        description="Stage all changes, commit with message, and push",
        category=RecipeCategory.GIT,
        parameters={"message": "Update"},
        icon="📤",
        pinned=True,
        pin_position=1,
        tags=("git", "commit", "push"),
        builtin=True,
    ),
    Recipe(
        id="builtin-create-pr",
        name="Create PR",
        command='gh pr create --title "{title}" --body "{body}"',
        description="Create a pull request from current branch",
        category=RecipeCategory.GIT,
        parameters={"title": "", "body": ""},
        icon="🔀",
        pinned=True,
        pin_position=2,
        tags=("git", "pr", "github"),
        builtin=True,
    ),
    Recipe(
        id="builtin-lint",
        name="Run Linting",
        command="ruff check {path} && ruff format --check {path}",
        description="Run ruff linter and format checker",
        category=RecipeCategory.LINT,
        parameters={"path": "."},
        icon="🔍",
        pinned=True,
        pin_position=3,
        tags=("lint", "ruff", "quality"),
        builtin=True,
    ),
    Recipe(
        id="builtin-format",
        name="Format Code",
        command="ruff format {path}",
        description="Format code with ruff",
        category=RecipeCategory.LINT,
        parameters={"path": "."},
        icon="✨",
        tags=("format", "ruff", "style"),
        builtin=True,
    ),
    # Build workflows
    Recipe(
        id="builtin-build",
        name="Build Project",
        command="{build_cmd}",
        description="Build the project",
        category=RecipeCategory.BUILD,
        parameters={"build_cmd": "python -m build"},
        icon="🔨",
        tags=("build", "package"),
        builtin=True,
    ),
    Recipe(
        id="builtin-install-dev",
        name="Install Dev",
        command="pip install -e '.[dev]'",
        description="Install package in development mode with dev dependencies",
        category=RecipeCategory.BUILD,
        parameters={},
        icon="📦",
        tags=("install", "development"),
        builtin=True,
    ),
    # Git status & info
    Recipe(
        id="builtin-git-status",
        name="Git Status",
        command="git status && git log --oneline -5",
        description="Show git status and recent commits",
        category=RecipeCategory.GIT,
        parameters={},
        icon="📊",
        tags=("git", "status"),
        builtin=True,
    ),
    Recipe(
        id="builtin-git-diff",
        name="Git Diff",
        command="git diff {ref}",
        description="Show diff against reference",
        category=RecipeCategory.GIT,
        parameters={"ref": "HEAD"},
        icon="📝",
        tags=("git", "diff"),
        builtin=True,
    ),
    Recipe(
        id="builtin-git-pull",
        name="Git Pull",
        command="git pull --rebase origin {branch}",
        description="Pull and rebase from remote",
        category=RecipeCategory.GIT,
        parameters={"branch": "main"},
        icon="⬇️",
        tags=("git", "pull", "sync"),
        builtin=True,
    ),
    # Testing
    Recipe(
        id="builtin-test-coverage",
        name="Test Coverage",
        command="pytest {path} --cov={package} --cov-report=term-missing",
        description="Run tests with coverage report",
        category=RecipeCategory.TEST,
        parameters={"path": "tests/", "package": "ralph_agi"},
        icon="📈",
        tags=("test", "coverage", "quality"),
        builtin=True,
    ),
    Recipe(
        id="builtin-test-quick",
        name="Quick Test",
        command="pytest {path} -x -q",
        description="Run tests, stop on first failure",
        category=RecipeCategory.TEST,
        parameters={"path": "tests/"},
        icon="⚡",
        tags=("test", "fast"),
        builtin=True,
    ),
    # Deploy
    Recipe(
        id="builtin-deploy-preview",
        name="Deploy Preview",
        command="{deploy_cmd}",
        description="Deploy to preview/staging environment",
        category=RecipeCategory.DEPLOY,
        parameters={"deploy_cmd": "echo 'Configure deploy command'"},
        icon="🚀",
        tags=("deploy", "preview", "staging"),
        builtin=True,
    ),
    # Ralph-specific
    Recipe(
        id="builtin-ralph-run",
        name="Ralph Run",
        command="ralph run --prd {prd} --config {config}",
        description="Run RALPH-AGI with specified PRD",
        category=RecipeCategory.CUSTOM,
        parameters={"prd": "PRD.json", "config": "config.yaml"},
        icon="🤖",
        pinned=True,
        pin_position=4,
        tags=("ralph", "run", "agent"),
        builtin=True,
    ),
    Recipe(
        id="builtin-ralph-tui",
        name="Ralph TUI",
        command="ralph tui --prd {prd}",
        description="Start RALPH-AGI TUI interface",
        category=RecipeCategory.CUSTOM,
        parameters={"prd": "PRD.json"},
        icon="🖥️",
        tags=("ralph", "tui", "interface"),
        builtin=True,
    ),
]


def get_builtin_recipe(recipe_id: str) -> Optional[Recipe]:
    """Get a built-in recipe by ID.

    Args:
        recipe_id: Recipe ID (e.g., "builtin-run-tests").

    Returns:
        Recipe if found, None otherwise.
    """
    for recipe in BUILTIN_RECIPES:
        if recipe.id == recipe_id:
            return recipe
    return None


def get_builtin_recipes_by_category(category: RecipeCategory) -> list[Recipe]:
    """Get built-in recipes by category.

    Args:
        category: Recipe category.

    Returns:
        List of recipes in category.
    """
    return [r for r in BUILTIN_RECIPES if r.category == category]


def get_pinned_builtins() -> list[Recipe]:
    """Get built-in recipes that are pinned by default.

    Returns:
        List of pinned built-in recipes.
    """
    return [r for r in BUILTIN_RECIPES if r.pinned]
