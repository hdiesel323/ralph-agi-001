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
        epilog="""\
Examples:
  ralph-agi run                        Start the loop with default config
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
        )

    # Create and run the loop
    loop = RalphLoop.from_config(config)

    formatter.verbose(f"Session: {loop.session_id}")
    formatter.verbose(f"Max iterations: {config.max_iterations}")
    formatter.verbose(f"Config: {args.config}")
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
