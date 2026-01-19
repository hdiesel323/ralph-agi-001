---
id: ralph-agi-001-005
title: First-Run Setup Wizard (ralph init)
type: feature
status: open
priority: 1
labels: [cli, ux, onboarding, developer-experience]
created: 2026-01-11
updated: 2026-01-11
epic: epic-01-core-loop
---

# First-Run Setup Wizard (ralph init)

## Problem Statement

New users need a simple, guided way to configure RALPH-AGI on first use. Currently there's no onboarding flow - users must manually create config files and set environment variables. This creates friction and increases time-to-first-loop.

## Proposed Solution

Implement an interactive CLI setup wizard using **Typer + Rich + Questionary**, with a hybrid config model (global defaults + per-project overrides).

## User Stories

**As a** new RALPH-AGI user
**I want** a guided setup wizard
**So that** I can start using Ralph quickly without reading documentation

**As a** power user
**I want** to skip interactive prompts with flags
**So that** I can automate setup in CI/scripts

## Acceptance Criteria

### Global Setup (~/.ralph/)

- [ ] Auto-detect missing global config on first run
- [ ] Prompt for Anthropic API key (or detect from env)
- [ ] Validate API key format (sk-ant-\* prefix)
- [ ] Offer model selection with recommendations
- [ ] Set max iterations with safety default (10)
- [ ] Create `~/.ralph/config.yaml` for global defaults
- [ ] Create `~/.ralph/.env` for API keys (with warning)
- [ ] Create `~/.ralph/memory/` directory

### Per-Project Setup (.ralph/)

- [ ] `ralph init` in project creates `.ralph/` directory
- [ ] Optional project-specific config overrides
- [ ] Create checkpoint directory
- [ ] Auto-add `.ralph/checkpoint.json` to .gitignore
- [ ] Detect existing config and prompt before overwriting

### CLI Flags

- [ ] `ralph init` - auto-detect, run both if needed
- [ ] `ralph init --global` - only global setup
- [ ] `ralph init --project` - only per-project
- [ ] `ralph init --reset` - wipe existing config
- [ ] `ralph init --yes` - accept all defaults (non-interactive)

## Setup Flow

```
$ ralph init

🤖 Welcome to RALPH-AGI Setup!

? Is this your first time using Ralph? (Y/n) Y
  → Running global setup...

? Anthropic API Key
  ● Detected from environment ✓
  ○ Enter manually

? Select default model:
  ❯ claude-sonnet-4-20250514 (faster, cheaper)
    claude-opus-4-20250514 (most capable)

? Max autonomous iterations before check-in? 10

✓ Global config saved to ~/.ralph/config.yaml
✓ API key saved to ~/.ralph/.env

──────────────────────────────────────────

? Initialize Ralph in this project? (Y/n) Y

? Project-specific model override? (n) n
? Enable checkpointing? (Y/n) Y

✓ Created .ralph/ directory
✓ Added .ralph/checkpoint.json to .gitignore

🚀 Run `ralph run` to start your first loop.
```

## Technical Design

### Library Stack

| Library         | Purpose                                | Version  |
| --------------- | -------------------------------------- | -------- |
| **Typer**       | CLI framework (built on Click)         | >=0.9.0  |
| **Rich**        | Terminal formatting (panels, spinners) | >=13.0.0 |
| **Questionary** | Interactive prompts                    | >=2.0.0  |

### Config Precedence (highest to lowest)

```
1. Environment variables     (always wins)
2. CLI flags                 (--model, --max-iterations)
3. Project config            (.ralph/config.yaml)
4. Global config             (~/.ralph/config.yaml)
5. Built-in defaults         (lowest)
```

### Directory Structure

```
~/.ralph/                    # Global (user home)
├── config.yaml              # Default settings
├── .env                     # API keys (never committed)
├── memory/                  # Long-term memory (Memvid)
│   └── ralph_memory.mv2
└── logs/                    # Global debug logs

project-root/                # Per-project
├── .ralph/                  # Project-specific runtime
│   ├── config.yaml          # Overrides (optional, can commit)
│   ├── checkpoint.json      # Loop state (gitignored)
│   └── logs/                # Project logs
├── prd.json                 # Task list (committed)
├── progress.txt             # Session memory (committed)
└── .gitignore               # Should include .ralph/checkpoint.json
```

### Implementation

```python
# ralph_agi/cli/setup.py
import os
import json
from pathlib import Path
from typing import Optional

import typer
import questionary
from rich.console import Console
from rich.panel import Panel

console = Console()
GLOBAL_CONFIG_DIR = Path.home() / ".ralph"
GLOBAL_CONFIG_PATH = GLOBAL_CONFIG_DIR / "config.yaml"
GLOBAL_ENV_PATH = GLOBAL_CONFIG_DIR / ".env"
PROJECT_CONFIG_DIR = Path(".ralph")


def run_setup_wizard(global_only: bool = False, project_only: bool = False) -> dict:
    """First-run setup wizard for Ralph AGI."""

    console.print(Panel(
        "[bold blue]Welcome to Ralph AGI[/bold blue]\n"
        "Let's get you set up",
        expand=False
    ))

    config = {}

    # Global setup
    if not project_only:
        if not GLOBAL_CONFIG_PATH.exists():
            config = run_global_setup()
        else:
            console.print("[dim]Global config exists at ~/.ralph/config.yaml[/dim]")

    # Per-project setup
    if not global_only:
        if questionary.confirm(
            "Initialize Ralph in this project?",
            default=True
        ).ask():
            run_project_setup()

    # Success message
    console.print(Panel(
        "[green]✓ Ralph is ready[/green]\n\n"
        "[bold]Next steps:[/bold]\n"
        "  ralph \"your task here\"\n"
        "  ralph config\n"
        "  ralph --help",
        expand=False
    ))

    return config


def run_global_setup() -> dict:
    """Run global configuration setup."""

    # API Key
    env_key = os.environ.get("ANTHROPIC_API_KEY")

    if env_key:
        use_env = questionary.confirm(
            "Anthropic API key detected in environment. Use it?",
            default=True
        ).ask()
        api_key = None if use_env else prompt_for_key()
    else:
        api_key = prompt_for_key()

    if api_key is False:
        raise typer.Abort()

    # Model selection
    model = questionary.select(
        "Default model:",
        choices=[
            questionary.Choice("Claude Sonnet 4 (faster, cheaper)",
                             value="claude-sonnet-4-20250514"),
            questionary.Choice("Claude Opus 4 (most capable)",
                             value="claude-opus-4-20250514"),
        ],
        default="claude-sonnet-4-20250514"
    ).ask()

    # Max iterations
    max_iterations = questionary.text(
        "Max iterations before check-in:",
        default="10",
        validate=lambda x: x.isdigit() or "Must be a number"
    ).ask()

    config = {
        "model": model,
        "max_iterations": int(max_iterations),
        "completion_promise": "<promise>COMPLETE</promise>",
        "memory": {
            "store_path": str(GLOBAL_CONFIG_DIR / "memory" / "ralph_memory.mv2"),
            "enabled": True
        }
    }

    # Create directories
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (GLOBAL_CONFIG_DIR / "memory").mkdir(exist_ok=True)
    (GLOBAL_CONFIG_DIR / "logs").mkdir(exist_ok=True)

    # Save config
    import yaml
    GLOBAL_CONFIG_PATH.write_text(yaml.dump(config, default_flow_style=False))

    # Save API key to .env if provided
    if api_key:
        GLOBAL_ENV_PATH.write_text(f"ANTHROPIC_API_KEY={api_key}\n")
        console.print("[yellow]⚠ API key saved to ~/.ralph/.env[/yellow]")

    console.print(f"[green]✓ Global config saved to {GLOBAL_CONFIG_PATH}[/green]")

    return config


def run_project_setup():
    """Run per-project configuration setup."""

    PROJECT_CONFIG_DIR.mkdir(exist_ok=True)
    (PROJECT_CONFIG_DIR / "logs").mkdir(exist_ok=True)

    # Check for project overrides
    if questionary.confirm(
        "Add project-specific config overrides?",
        default=False
    ).ask():
        # Could prompt for project-specific settings here
        pass

    # Update .gitignore
    gitignore = Path(".gitignore")
    gitignore_entries = [
        ".ralph/checkpoint.json",
        ".ralph/logs/",
    ]

    if gitignore.exists():
        content = gitignore.read_text()
        additions = [e for e in gitignore_entries if e not in content]
        if additions:
            with gitignore.open("a") as f:
                f.write("\n# Ralph AGI\n")
                for entry in additions:
                    f.write(f"{entry}\n")
            console.print("[dim]Updated .gitignore[/dim]")

    console.print(f"[green]✓ Created {PROJECT_CONFIG_DIR}/ directory[/green]")


def prompt_for_key() -> Optional[str]:
    """Prompt for API key with validation."""
    return questionary.password(
        "Enter your Anthropic API key:",
        validate=lambda x: x.startswith("sk-ant-") or "Invalid key format (should start with sk-ant-)"
    ).ask()


def load_config() -> dict:
    """Load merged config from global + project sources."""
    import yaml

    config = {
        # Built-in defaults
        "model": "claude-sonnet-4-20250514",
        "max_iterations": 100,
        "completion_promise": "<promise>COMPLETE</promise>",
    }

    # Load global config
    if GLOBAL_CONFIG_PATH.exists():
        global_config = yaml.safe_load(GLOBAL_CONFIG_PATH.read_text()) or {}
        config.update(global_config)

    # Load project config (overrides global)
    project_config_path = PROJECT_CONFIG_DIR / "config.yaml"
    if project_config_path.exists():
        project_config = yaml.safe_load(project_config_path.read_text()) or {}
        config.update(project_config)

    # Environment variables always win
    if os.environ.get("ANTHROPIC_API_KEY"):
        config["api_key_source"] = "env"

    return config


def ensure_config() -> dict:
    """Load config or run setup wizard if none exists."""
    if not GLOBAL_CONFIG_PATH.exists():
        return run_setup_wizard()
    return load_config()
```

### CLI Entry Point

```python
# ralph_agi/cli/main.py
import typer
from ralph_agi.cli.setup import ensure_config, run_setup_wizard, load_config

app = typer.Typer(help="Ralph AGI - Autonomous agent system")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    task: str = typer.Argument(None, help="Task to execute")
):
    """Run Ralph with a task, or show help if no task provided."""
    if ctx.invoked_subcommand is None:
        config = ensure_config()

        if task:
            from ralph_agi.core import execute_task
            execute_task(task, config)
        else:
            ctx.get_help()


@app.command()
def init(
    reset: bool = typer.Option(False, "--reset", help="Wipe existing config"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Accept all defaults"),
    global_only: bool = typer.Option(False, "--global", help="Only global setup"),
    project_only: bool = typer.Option(False, "--project", help="Only project setup"),
):
    """Run setup wizard."""
    if reset:
        # Handle reset logic
        pass
    run_setup_wizard(global_only=global_only, project_only=project_only)


@app.command()
def config(
    key: str = typer.Argument(None),
    value: str = typer.Argument(None),
):
    """View or modify configuration."""
    import json
    cfg = load_config()

    if key is None:
        typer.echo(json.dumps(cfg, indent=2))
    elif value is None:
        typer.echo(cfg.get(key, "Key not found"))
    else:
        # Set key logic
        typer.echo(f"Set {key} = {value}")


@app.command()
def run(
    max_iterations: int = typer.Option(None, "--max-iterations", "-n"),
):
    """Run the Ralph Loop."""
    config = ensure_config()
    if max_iterations:
        config["max_iterations"] = max_iterations

    from ralph_agi.core.loop import RalphLoop
    loop = RalphLoop.from_config(config)
    loop.run()


if __name__ == "__main__":
    app()
```

## Dependencies

```toml
# pyproject.toml additions
[project.dependencies]
typer = ">=0.9.0"
rich = ">=13.0.0"
questionary = ">=2.0.0"
python-dotenv = ">=1.0.0"

[project.scripts]
ralph = "ralph_agi.cli.main:app"
```

## Dependencies (Stories)

- **Story 1.3:** Configuration Management (existing config loading)
- **Story 1.5:** CLI Entry Point (provides base CLI structure)

## Effort Estimate

Points: 5

## Testing

- [ ] Test global setup creates ~/.ralph/ structure
- [ ] Test project setup creates .ralph/ structure
- [ ] Test config precedence (env > project > global > defaults)
- [ ] Test --yes flag skips all prompts
- [ ] Test --reset flag clears config
- [ ] Test API key validation
- [ ] Test .gitignore updates

## References

- [Typer docs](https://typer.tiangolo.com/)
- [Rich docs](https://rich.readthedocs.io/)
- [Questionary docs](https://questionary.readthedocs.io/)
- [create-next-app](https://nextjs.org/docs/api-reference/create-next-app) - UX reference
