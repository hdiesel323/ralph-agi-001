"""Interactive CLI for RALPH-AGI.

Provides a user-friendly interactive experience when no command is specified.
Supports PRD file selection via drag & drop and template creation.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

# ANSI colors for terminal output
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner() -> None:
    """Print welcome banner."""
    print(f"""
{CYAN}{BOLD}╔═══════════════════════════════════════════════════════════════╗
║                     RALPH-AGI v0.1.0                          ║
║         Recursive Autonomous Long-horizon Processing          ║
╚═══════════════════════════════════════════════════════════════╝{RESET}
""")


def print_menu() -> None:
    """Print main menu options."""
    print(f"{BOLD}What would you like to do?{RESET}\n")
    print(f"  {GREEN}1{RESET}  Run tasks from a PRD file")
    print(f"  {GREEN}2{RESET}  Create a new PRD from template")
    print(f"  {GREEN}3{RESET}  Run setup wizard (configure API keys)")
    print(f"  {GREEN}4{RESET}  View help")
    print(f"  {GREEN}q{RESET}  Quit")
    print()


def get_choice(prompt: str, valid: list[str]) -> str:
    """Get user choice with validation.

    Args:
        prompt: Prompt to display.
        valid: List of valid choices.

    Returns:
        User's choice.
    """
    while True:
        try:
            choice = input(f"{prompt}").strip().lower()
            if choice in valid:
                return choice
            print(f"{YELLOW}Please enter one of: {', '.join(valid)}{RESET}")
        except EOFError:
            return "q"
        except KeyboardInterrupt:
            print()
            return "q"


def get_prd_path() -> Optional[str]:
    """Get PRD file path from user (supports drag & drop).

    Returns:
        Path to PRD file, or None if cancelled.
    """
    print(f"\n{BOLD}Enter path to PRD file{RESET}")
    print(f"{DIM}(Drag & drop the file here, or type the path){RESET}\n")

    try:
        path_input = input(f"{GREEN}>{RESET} ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None

    if not path_input:
        return None

    # Clean up path (drag & drop may add quotes or escape spaces)
    path = path_input.strip("'\"")
    # Handle escaped spaces from drag & drop
    path = path.replace("\\ ", " ")

    # Expand user home directory
    path = os.path.expanduser(path)

    # Check if file exists
    if not os.path.isfile(path):
        print(f"{RED}File not found: {path}{RESET}")
        retry = get_choice("Try again? (y/n): ", ["y", "n", "yes", "no"])
        if retry in ["y", "yes"]:
            return get_prd_path()
        return None

    # Verify it's a JSON file
    if not path.endswith(".json"):
        print(f"{YELLOW}Warning: File doesn't have .json extension{RESET}")
        proceed = get_choice("Continue anyway? (y/n): ", ["y", "n", "yes", "no"])
        if proceed not in ["y", "yes"]:
            return None

    return path


def create_prd_wizard() -> Optional[str]:
    """Interactive wizard to create a PRD file.

    Returns:
        Path to created PRD file, or None if cancelled.
    """
    print(f"\n{CYAN}{BOLD}PRD Creation Wizard{RESET}\n")
    print("I'll help you create a PRD (Product Requirements Document) file.")
    print("This defines the tasks RALPH will work on.\n")

    try:
        # Project name
        print(f"{BOLD}Project name:{RESET}")
        project_name = input(f"{GREEN}>{RESET} ").strip()
        if not project_name:
            project_name = "My Project"

        # Project description
        print(f"\n{BOLD}Brief description of your project:{RESET}")
        print(f"{DIM}(What are you building?){RESET}")
        project_desc = input(f"{GREEN}>{RESET} ").strip()
        if not project_desc:
            project_desc = "A software project"

        # Main goal / task
        print(f"\n{BOLD}What do you want RALPH to build or do?{RESET}")
        print(f"{DIM}(Describe the main task or feature){RESET}")
        main_task = input(f"{GREEN}>{RESET} ").strip()
        if not main_task:
            print(f"{RED}A task description is required.{RESET}")
            return None

        # Priority
        print(f"\n{BOLD}Priority level:{RESET}")
        print("  1 = Critical (do first)")
        print("  2 = High")
        print("  3 = Medium (default)")
        print("  4 = Low")
        priority_input = input(f"{GREEN}>{RESET} [3]: ").strip()
        try:
            priority = int(priority_input) if priority_input else 3
            priority = max(1, min(4, priority))
        except ValueError:
            priority = 3

        # Acceptance criteria
        print(f"\n{BOLD}Acceptance criteria:{RESET}")
        print(f"{DIM}(How will you know when the task is done? Enter each criterion on a new line.)")
        print(f"(Press Enter twice when finished){RESET}")

        criteria = []
        while True:
            criterion = input(f"{GREEN}>{RESET} ").strip()
            if not criterion:
                break
            criteria.append(criterion)

        if not criteria:
            criteria = ["Task is complete and working", "Code passes any relevant tests"]

        # Generate task ID
        task_id = f"TASK-001"

        # Build PRD structure
        prd = {
            "project": {
                "name": project_name,
                "description": project_desc,
                "version": "1.0.0"
            },
            "features": [
                {
                    "id": "F-001",
                    "name": "Main Feature",
                    "description": main_task,
                    "tasks": [
                        {
                            "id": task_id,
                            "description": main_task,
                            "priority": priority,
                            "status": "pending",
                            "acceptance_criteria": criteria,
                            "steps": [
                                "Analyze requirements and existing code",
                                "Implement the solution",
                                "Test and verify the implementation"
                            ]
                        }
                    ]
                }
            ]
        }

        # Output filename
        print(f"\n{BOLD}Save PRD as:{RESET}")
        default_name = f"{project_name.lower().replace(' ', '_')}_PRD.json"
        filename = input(f"{GREEN}>{RESET} [{default_name}]: ").strip()
        if not filename:
            filename = default_name

        # Ensure .json extension
        if not filename.endswith(".json"):
            filename += ".json"

        # Write file
        output_path = Path(filename)
        with open(output_path, "w") as f:
            json.dump(prd, f, indent=2)

        print(f"\n{GREEN}Created: {output_path.absolute()}{RESET}")
        print(f"\nYour PRD has been created with 1 task:")
        print(f"  {task_id}: {main_task[:60]}{'...' if len(main_task) > 60 else ''}")

        return str(output_path.absolute())

    except (EOFError, KeyboardInterrupt):
        print(f"\n{YELLOW}Cancelled.{RESET}")
        return None


def run_interactive() -> int:
    """Run interactive CLI mode.

    Returns:
        Exit code for the desired action.
    """
    print_banner()

    while True:
        print_menu()
        choice = get_choice(f"{GREEN}>{RESET} ", ["1", "2", "3", "4", "q"])

        if choice == "q":
            print(f"\n{DIM}Goodbye!{RESET}\n")
            return 0

        elif choice == "1":
            # Run with PRD file
            prd_path = get_prd_path()
            if prd_path:
                print(f"\n{GREEN}Starting RALPH with: {prd_path}{RESET}\n")
                # Return special code to signal "run with this PRD"
                # We'll store the path and return a code the CLI understands
                return ("run", prd_path)
            print()

        elif choice == "2":
            # Create PRD wizard
            prd_path = create_prd_wizard()
            if prd_path:
                print()
                run_now = get_choice("Run RALPH with this PRD now? (y/n): ", ["y", "n", "yes", "no"])
                if run_now in ["y", "yes"]:
                    print(f"\n{GREEN}Starting RALPH...{RESET}\n")
                    return ("run", prd_path)
            print()

        elif choice == "3":
            # Setup wizard
            print(f"\n{GREEN}Launching setup wizard...{RESET}\n")
            return ("init",)

        elif choice == "4":
            # Help
            print(f"""
{BOLD}RALPH-AGI Help{RESET}

RALPH is an autonomous AI agent that works on coding tasks.

{BOLD}Quick Start:{RESET}
  1. Create a PRD file (option 2) describing what you want to build
  2. Run RALPH with that PRD file (option 1)
  3. Watch RALPH work on your tasks

{BOLD}PRD File:{RESET}
  A PRD (Product Requirements Document) is a JSON file that describes:
  - Your project name and description
  - Features you want to build
  - Tasks with acceptance criteria

{BOLD}Command Line Usage:{RESET}
  ralph-agi run --prd myproject.json    Run with a PRD file
  ralph-agi run --dry-run --prd X.json  Preview without executing
  ralph-agi init                        Setup wizard
  ralph-agi --help                      Full help

{BOLD}More Info:{RESET}
  https://github.com/hdiesel323/ralph-agi-001
""")

    return 0
