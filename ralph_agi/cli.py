"""Command-line interface for RALPH-AGI.

Provides the `ralph-agi` command for running the autonomous loop
with configurable options and polished terminal output.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ralph_agi import __version__
from ralph_agi.core.config import ConfigValidationError, RalphConfig, load_config
from ralph_agi.core.loop import LoopInterrupted, MaxRetriesExceeded, RalphLoop
from ralph_agi.output import OutputFormatter, Verbosity

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_MAX_ITERATIONS = 2


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for ralph-agi CLI."""
    parser = argparse.ArgumentParser(
        prog="ralph-agi",
        description="RALPH-AGI - Recursive Autonomous Long-horizon Processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ralph-agi run                        Start the loop with default config
  ralph-agi run --prd PRD.json         Run with PRD file for LLM execution
  ralph-agi run --max-iterations 10    Run with custom iteration limit
  ralph-agi run --config my-config.yaml Use custom config file
  ralph-agi run -v                     Verbose output
  ralph-agi run -q                     Quiet mode (errors only)

Exit Codes:
  0  Success (loop completed via completion signal)
  1  Error (exception raised)
  2  Max iterations reached (exited without completion)
""",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"ralph-agi {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Start the RALPH loop",
        description="Start the autonomous loop that processes tasks iteratively.",
    )

    run_parser.add_argument(
        "--max-iterations",
        type=int,
        metavar="N",
        help="Override maximum iterations from config",
    )

    run_parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="config.yaml",
        metavar="PATH",
        help="Path to config file (default: config.yaml)",
    )

    run_parser.add_argument(
        "--prd",
        "-p",
        type=str,
        metavar="PATH",
        help="Path to PRD.json file for task execution",
    )

    run_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    run_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Quiet mode - errors only",
    )

    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the next task and context without executing",
    )

    return parser


def run_loop(args: argparse.Namespace) -> int:
    """Execute the run command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0=success, 1=error, 2=max iterations).
    """
    # Determine verbosity
    if args.quiet:
        verbosity = Verbosity.QUIET
    elif args.verbose:
        verbosity = Verbosity.VERBOSE
    else:
        verbosity = Verbosity.NORMAL

    formatter = OutputFormatter(verbosity=verbosity)

    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        formatter.error(f"Config file not found: {args.config}")
        return EXIT_ERROR
    except ConfigValidationError as e:
        formatter.error(f"Invalid configuration: {e}")
        return EXIT_ERROR
    except Exception as e:
        formatter.error("Failed to load configuration", exception=e)
        return EXIT_ERROR

    # Apply CLI overrides
    if args.max_iterations is not None:
        config = RalphConfig(
            max_iterations=args.max_iterations,
            completion_promise=config.completion_promise,
            checkpoint_interval=config.checkpoint_interval,
            max_retries=config.max_retries,
            retry_delays=config.retry_delays,
            log_file=config.log_file,
            checkpoint_path=config.checkpoint_path,
            memory_enabled=config.memory_enabled,
            memory_store_path=config.memory_store_path,
            memory_embedding_model=config.memory_embedding_model,
            hooks_enabled=config.hooks_enabled,
            hooks_on_iteration_start=config.hooks_on_iteration_start,
            hooks_on_iteration_end=config.hooks_on_iteration_end,
            hooks_on_error=config.hooks_on_error,
            hooks_on_completion=config.hooks_on_completion,
            hooks_context_frames=config.hooks_context_frames,
            llm_builder_model=config.llm_builder_model,
            llm_builder_provider=config.llm_builder_provider,
            llm_critic_model=config.llm_critic_model,
            llm_critic_provider=config.llm_critic_provider,
            llm_critic_enabled=config.llm_critic_enabled,
            llm_max_tokens=config.llm_max_tokens,
            llm_max_tool_iterations=config.llm_max_tool_iterations,
            llm_temperature=config.llm_temperature,
            llm_rate_limit_retries=config.llm_rate_limit_retries,
        )

    # Dry-run logic - show next task without executing
    if args.dry_run:
        prd_path = getattr(args, "prd", None)
        if not prd_path:
            formatter.error("--dry-run requires --prd <path> to specify the PRD file")
            return EXIT_ERROR

        try:
            from ralph_agi.tasks.prd import load_prd
            from ralph_agi.tasks.selector import TaskSelector

            # Load PRD and find next task
            prd = load_prd(Path(prd_path))
            selector = TaskSelector()
            result = selector.select(prd)
            next_task = result.next_task

            formatter.message("=" * 60)
            formatter.message("DRY-RUN MODE - No LLM calls will be made")
            formatter.message("=" * 60)
            formatter.message("")

            # Project info
            formatter.message(f"Project: {prd.project.name}")
            if prd.project.description:
                formatter.message(f"Description: {prd.project.description[:200]}")
            formatter.message("")

            if next_task is None:
                formatter.message("Status: ALL TASKS COMPLETE")
                formatter.message("No pending tasks found in PRD.")
                return EXIT_SUCCESS

            # Task details
            formatter.message("NEXT TASK:")
            formatter.message(f"  ID: {next_task.id}")
            formatter.message(f"  Description: {next_task.description}")
            formatter.message(f"  Priority: {next_task.priority}")

            if next_task.steps:
                formatter.message("  Steps:")
                for i, step in enumerate(next_task.steps, 1):
                    formatter.message(f"    {i}. {step}")

            if next_task.acceptance_criteria:
                formatter.message("  Acceptance Criteria:")
                for criterion in next_task.acceptance_criteria:
                    formatter.message(f"    - {criterion}")

            if next_task.dependencies:
                formatter.message(f"  Dependencies: {', '.join(next_task.dependencies)}")

            formatter.message("")

            # Available tools (static list matching what Builder sees)
            tools = [
                ("read_file", "Read contents of a file"),
                ("write_file", "Write content to a file (creates new files)"),
                ("edit_file", "Edit existing file by replacing content (PREFERRED)"),
                ("insert_in_file", "Insert content at specific location"),
                ("append_to_file", "Append content to end of file"),
                ("list_directory", "List files in a directory"),
                ("run_command", "Execute a shell command"),
                ("git_status", "Get git repository status"),
                ("git_commit", "Create a git commit"),
            ]
            formatter.message(f"AVAILABLE TOOLS ({len(tools)}):")
            for name, desc in tools:
                formatter.message(f"  - {name}: {desc}")

            formatter.message("")
            formatter.message("=" * 60)
            formatter.message("Run without --dry-run to execute this task")
            formatter.message("=" * 60)

            return EXIT_SUCCESS

        except FileNotFoundError:
            formatter.error(f"PRD file not found: {prd_path}")
            return EXIT_ERROR
        except Exception as e:
            formatter.error(f"Error loading PRD: {e}")
            return EXIT_ERROR

    # Create and run the loop
    prd_path = getattr(args, "prd", None)
    loop = RalphLoop.from_config(config, prd_path=prd_path)

    formatter.verbose(f"Session: {loop.session_id}")
    formatter.verbose(f"Max iterations: {config.max_iterations}")
    formatter.verbose(f"Config: {args.config}")
    if prd_path:
        formatter.verbose(f"PRD: {prd_path}")
    formatter.message("")

    try:
        # Show initial header
        formatter.iteration_header(1, config.max_iterations)

        completed = loop.run(handle_signals=True)

        if completed:
            formatter.completion_banner(
                total_iterations=loop.iteration + 1,
                session_id=loop.session_id,
                reason="completed",
            )
            return EXIT_SUCCESS
        else:
            formatter.completion_banner(
                total_iterations=loop.iteration,
                session_id=loop.session_id,
                reason="max_iterations",
            )
            return EXIT_MAX_ITERATIONS

    except LoopInterrupted as e:
        formatter.message("")
        formatter.completion_banner(
            total_iterations=e.iteration + 1,
            session_id=loop.session_id,
            reason="interrupted",
        )
        if e.checkpoint_path:
            formatter.message(f"Checkpoint saved: {e.checkpoint_path}")
        return EXIT_SUCCESS  # Graceful interrupt is success

    except MaxRetriesExceeded as e:
        formatter.error(f"Max retries exceeded: {e}", exception=e.last_error)
        return EXIT_ERROR

    except KeyboardInterrupt:
        formatter.message("")
        formatter.warning("Interrupted by user")
        return EXIT_ERROR

    except Exception as e:
        formatter.error("Unexpected error", exception=e)
        return EXIT_ERROR

    finally:
        loop.close()


def main(argv: list[str] | None = None) -> int:
    """Main entry point for ralph-agi CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code.
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return EXIT_SUCCESS

    if args.command == "run":
        return run_loop(args)

    # Unknown command (shouldn't happen with subparsers)
    parser.print_help()
    return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
