"""First-run setup wizard for RALPH-AGI.

Provides an interactive setup experience for new users, guiding them through
configuration options and generating a config.yaml file.

Usage:
    ralph-agi init           # Interactive setup
    ralph-agi init --quick   # Use defaults (minimal prompts)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ralph_agi.core.config import RalphConfig, save_config


@dataclass
class WizardOptions:
    """Options collected from the setup wizard."""

    # LLM Configuration
    builder_provider: str = "anthropic"
    builder_model: str = "claude-sonnet-4-20250514"
    critic_provider: str = "openai"
    critic_model: str = "gpt-4o"
    critic_enabled: bool = True

    # Git Configuration
    git_workflow: str = "branch"
    git_auto_push: bool = True

    # Execution Configuration
    max_iterations: int = 100

    # Memory Configuration
    memory_enabled: bool = True


# Provider configurations
PROVIDERS = {
    "anthropic": {
        "name": "Anthropic (Claude)",
        "env_var": "ANTHROPIC_API_KEY",
        "models": [
            ("claude-sonnet-4-20250514", "Claude Sonnet 4 (recommended)"),
            ("claude-opus-4-20250514", "Claude Opus 4 (most capable)"),
            ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet"),
        ],
    },
    "openai": {
        "name": "OpenAI",
        "env_var": "OPENAI_API_KEY",
        "models": [
            ("gpt-4o", "GPT-4o (recommended)"),
            ("gpt-4-turbo", "GPT-4 Turbo"),
            ("gpt-4o-mini", "GPT-4o Mini (faster, cheaper)"),
        ],
    },
    "openrouter": {
        "name": "OpenRouter (multi-model access)",
        "env_var": "OPENROUTER_API_KEY",
        "models": [
            ("anthropic/claude-sonnet-4", "Claude Sonnet 4 via OpenRouter"),
            ("openai/gpt-4o", "GPT-4o via OpenRouter"),
            ("google/gemini-pro-1.5", "Gemini Pro 1.5 via OpenRouter"),
        ],
    },
}

GIT_WORKFLOWS = {
    "branch": "Create feature branches (recommended for teams)",
    "pr": "Create feature branches + open PRs via gh CLI",
    "direct": "Commit directly (solo dev only, risky)",
}


def _print_header(text: str) -> None:
    """Print a section header."""
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)
    print()


def _print_step(step: int, total: int, text: str) -> None:
    """Print a step indicator."""
    print(f"\n[{step}/{total}] {text}")
    print("-" * 40)


def _prompt_choice(
    prompt: str,
    options: list[tuple[str, str]],
    default: Optional[str] = None,
) -> str:
    """Prompt user to select from a list of options.

    Args:
        prompt: The question to ask.
        options: List of (value, description) tuples.
        default: Default value if user presses enter.

    Returns:
        Selected value.
    """
    print(f"\n{prompt}")
    for i, (value, desc) in enumerate(options, 1):
        default_marker = " (default)" if value == default else ""
        print(f"  {i}. {desc}{default_marker}")

    while True:
        default_hint = f" [{default}]" if default else ""
        choice = input(f"\nEnter choice (1-{len(options)}){default_hint}: ").strip()

        if not choice and default:
            return default

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
        except ValueError:
            # Check if they typed the value directly
            for value, _ in options:
                if choice.lower() == value.lower():
                    return value

        print(f"Please enter a number between 1 and {len(options)}")


def _prompt_yes_no(prompt: str, default: bool = True) -> bool:
    """Prompt for yes/no response.

    Args:
        prompt: The question to ask.
        default: Default value if user presses enter.

    Returns:
        True for yes, False for no.
    """
    default_hint = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} [{default_hint}]: ").strip().lower()

        if not response:
            return default
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False

        print("Please enter 'y' or 'n'")


def _prompt_number(prompt: str, default: int, min_val: int = 1, max_val: int = 10000) -> int:
    """Prompt for a number.

    Args:
        prompt: The question to ask.
        default: Default value if user presses enter.
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.

    Returns:
        The number entered.
    """
    while True:
        response = input(f"{prompt} [{default}]: ").strip()

        if not response:
            return default

        try:
            value = int(response)
            if min_val <= value <= max_val:
                return value
            print(f"Please enter a number between {min_val} and {max_val}")
        except ValueError:
            print("Please enter a valid number")


def _check_api_key(provider: str) -> tuple[bool, str]:
    """Check if API key is set for provider.

    Args:
        provider: Provider name (anthropic, openai, openrouter).

    Returns:
        Tuple of (is_set, env_var_name).
    """
    env_var = PROVIDERS[provider]["env_var"]
    is_set = bool(os.environ.get(env_var))
    return is_set, env_var


def _print_api_key_status(providers_needed: list[str]) -> None:
    """Print status of required API keys."""
    print("\nAPI Key Status:")
    all_set = True
    for provider in providers_needed:
        is_set, env_var = _check_api_key(provider)
        status = "[OK]" if is_set else "[MISSING]"
        all_set = all_set and is_set
        print(f"  {status} {env_var}")

    if not all_set:
        print("\nTo set missing API keys, add them to your shell profile:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        print("  export OPENAI_API_KEY='your-key-here'")
        print("  export OPENROUTER_API_KEY='your-key-here'")


def run_wizard(quick: bool = False, output_path: str = "config.yaml") -> tuple[bool, str]:
    """Run the interactive setup wizard.

    Args:
        quick: If True, use defaults with minimal prompts.
        output_path: Path to save config file.

    Returns:
        Tuple of (success, message).
    """
    output_file = Path(output_path)
    options = WizardOptions()

    # Banner
    _print_header("RALPH-AGI Setup Wizard")
    print("Welcome! This wizard will help you configure RALPH-AGI.")
    print("Press Enter to accept defaults, or type your choice.")

    # Check if config already exists
    if output_file.exists():
        print(f"\nConfig file already exists: {output_path}")
        if not _prompt_yes_no("Overwrite existing config?", default=False):
            return False, "Setup cancelled - existing config preserved"

    if quick:
        # Quick mode: just check API keys and generate config
        print("\nQuick mode: Using default configuration...")
        providers_needed = [options.builder_provider]
        if options.critic_enabled:
            providers_needed.append(options.critic_provider)
        _print_api_key_status(list(set(providers_needed)))
    else:
        # Step 1: Builder LLM Provider
        _print_step(1, 5, "Builder Agent Configuration")
        print("The Builder agent writes code and executes tasks.")

        provider_options = [(k, v["name"]) for k, v in PROVIDERS.items()]
        options.builder_provider = _prompt_choice(
            "Select Builder provider:",
            provider_options,
            default="anthropic",
        )

        # Select model for chosen provider
        model_options = PROVIDERS[options.builder_provider]["models"]
        options.builder_model = _prompt_choice(
            "Select Builder model:",
            model_options,
            default=model_options[0][0],
        )

        # Step 2: Critic Configuration
        _print_step(2, 5, "Critic Agent Configuration")
        print("The Critic agent reviews code for bugs and hallucinations.")

        options.critic_enabled = _prompt_yes_no(
            "Enable Critic agent? (recommended for quality)",
            default=True,
        )

        if options.critic_enabled:
            # Default to different provider for diversity
            default_critic = "openai" if options.builder_provider != "openai" else "anthropic"
            options.critic_provider = _prompt_choice(
                "Select Critic provider:",
                provider_options,
                default=default_critic,
            )

            critic_models = PROVIDERS[options.critic_provider]["models"]
            options.critic_model = _prompt_choice(
                "Select Critic model:",
                critic_models,
                default=critic_models[0][0],
            )

        # Step 3: Git Workflow
        _print_step(3, 5, "Git Workflow Configuration")
        print("RALPH can manage git operations automatically.")

        workflow_options = [(k, v) for k, v in GIT_WORKFLOWS.items()]
        options.git_workflow = _prompt_choice(
            "Select git workflow mode:",
            workflow_options,
            default="branch",
        )

        if options.git_workflow != "direct":
            options.git_auto_push = _prompt_yes_no(
                "Auto-push commits to remote?",
                default=True,
            )

        # Step 4: Execution Settings
        _print_step(4, 5, "Execution Settings")

        options.max_iterations = _prompt_number(
            "Maximum iterations per task (safety limit)",
            default=100,
            min_val=10,
            max_val=1000,
        )

        options.memory_enabled = _prompt_yes_no(
            "Enable persistent memory? (recommended)",
            default=True,
        )

        # Step 5: API Key Check
        _print_step(5, 5, "API Key Verification")
        providers_needed = [options.builder_provider]
        if options.critic_enabled:
            providers_needed.append(options.critic_provider)
        _print_api_key_status(list(set(providers_needed)))

    # Generate config
    config = RalphConfig(
        max_iterations=options.max_iterations,
        memory_enabled=options.memory_enabled,
        llm_builder_model=options.builder_model,
        llm_builder_provider=options.builder_provider,
        llm_critic_model=options.critic_model,
        llm_critic_provider=options.critic_provider,
        llm_critic_enabled=options.critic_enabled,
        git_workflow=options.git_workflow,
        git_auto_push=options.git_auto_push,
    )

    # Save config
    save_config(config, output_file)

    # Success message
    _print_header("Setup Complete!")
    print(f"Configuration saved to: {output_path}")
    print()
    print("Next steps:")
    print("  1. Ensure your API keys are set in environment variables")
    print("  2. Create a PRD.json file describing your tasks")
    print("  3. Run: ralph-agi run --prd PRD.json")
    print()
    print("For help: ralph-agi --help")
    print("Documentation: https://github.com/hdiesel323/ralph-agi-001")

    return True, f"Configuration saved to {output_path}"


def generate_sample_prd(output_path: str = "PRD.json") -> tuple[bool, str]:
    """Generate a sample PRD.json file.

    Args:
        output_path: Path to save PRD file.

    Returns:
        Tuple of (success, message).
    """
    import json

    output_file = Path(output_path)

    if output_file.exists():
        print(f"PRD file already exists: {output_path}")
        return False, "PRD file already exists"

    sample_prd = {
        "project": {
            "name": "My Project",
            "description": "A sample project to demonstrate RALPH-AGI capabilities",
        },
        "features": [
            {
                "id": "feature-1",
                "name": "Hello World",
                "description": "Create a simple hello world script",
                "tasks": [
                    {
                        "id": "task-1.1",
                        "description": "Create a Python script that prints 'Hello, RALPH!'",
                        "priority": "P0",
                        "status": "pending",
                        "acceptance_criteria": [
                            "File hello.py exists",
                            "Running 'python hello.py' prints 'Hello, RALPH!'",
                        ],
                    },
                    {
                        "id": "task-1.2",
                        "description": "Add a function that greets a custom name",
                        "priority": "P1",
                        "status": "pending",
                        "dependencies": ["task-1.1"],
                        "acceptance_criteria": [
                            "Function greet(name) exists in hello.py",
                            "greet('World') returns 'Hello, World!'",
                        ],
                    },
                ],
            },
        ],
    }

    with open(output_file, "w") as f:
        json.dump(sample_prd, f, indent=2)

    return True, f"Sample PRD saved to {output_path}"
