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
from ralph_agi.scheduler.config import SchedulerConfig, load_scheduler_config
from ralph_agi.scheduler.cron import CronValidationError

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
  ralph-agi run --batch --prd PRD.json Process tasks in parallel
  ralph-agi run --batch --parallel-limit 5 Use 5 parallel workers

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

    run_parser.add_argument(
        "--show-cost",
        action="store_true",
        help="Display token usage and estimated cost after the run",
    )

    run_parser.add_argument(
        "--batch",
        action="store_true",
        help="Enable batch mode - process multiple tasks in parallel using worktrees",
    )

    run_parser.add_argument(
        "--parallel-limit",
        type=int,
        default=3,
        metavar="N",
        help="Maximum parallel workers in batch mode (default: 3)",
    )

    # Daemon command for AFK mode
    daemon_parser = subparsers.add_parser(
        "daemon",
        help="Manage the scheduler daemon for AFK mode",
        description="Control the background scheduler daemon for autonomous operation.",
    )

    daemon_subparsers = daemon_parser.add_subparsers(
        dest="daemon_command",
        help="Daemon action to perform",
    )

    # daemon start
    daemon_start = daemon_subparsers.add_parser(
        "start",
        help="Start the scheduler daemon",
    )
    daemon_start.add_argument(
        "--config",
        "-c",
        type=str,
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    daemon_start.add_argument(
        "--foreground",
        "-f",
        action="store_true",
        help="Run in foreground (don't daemonize)",
    )

    # daemon stop
    daemon_stop = daemon_subparsers.add_parser(
        "stop",
        help="Stop the scheduler daemon",
    )
    daemon_stop.add_argument(
        "--config",
        "-c",
        type=str,
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )

    # daemon status
    daemon_status = daemon_subparsers.add_parser(
        "status",
        help="Check daemon status",
    )
    daemon_status.add_argument(
        "--config",
        "-c",
        type=str,
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )

    # daemon install
    daemon_install = daemon_subparsers.add_parser(
        "install",
        help="Install system service (launchd/systemd)",
    )
    daemon_install.add_argument(
        "--config",
        "-c",
        type=str,
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    daemon_install.add_argument(
        "--mode",
        choices=["launchd", "systemd"],
        help="Service type to install (auto-detected if not specified)",
    )

    # daemon run-once (internal use by system scheduler)
    daemon_run_once = daemon_subparsers.add_parser(
        "run-once",
        help="Execute a single scheduled wake (used by system scheduler)",
    )
    daemon_run_once.add_argument(
        "--config",
        "-c",
        type=str,
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )

    # Init command for first-run setup
    init_parser = subparsers.add_parser(
        "init",
        help="Interactive setup wizard for first-run configuration",
        description="Guide through initial configuration of RALPH-AGI.",
    )
    init_parser.add_argument(
        "--quick",
        "-q",
        action="store_true",
        help="Quick mode - use defaults with minimal prompts",
    )
    init_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="config.yaml",
        metavar="PATH",
        help="Output path for config file (default: config.yaml)",
    )
    init_parser.add_argument(
        "--sample-prd",
        action="store_true",
        help="Also generate a sample PRD.json file",
    )

    # Queue command for task queue management
    queue_parser = subparsers.add_parser(
        "queue",
        help="Manage the task queue for autonomous processing",
        description="Add, list, and manage tasks in the autonomous processing queue.",
    )

    queue_subparsers = queue_parser.add_subparsers(
        dest="queue_command",
        help="Queue action to perform",
    )

    # queue add
    queue_add = queue_subparsers.add_parser(
        "add",
        help="Add a task to the queue",
    )
    queue_add.add_argument(
        "description",
        type=str,
        help="Task description (what should be accomplished)",
    )
    queue_add.add_argument(
        "--priority",
        "-p",
        type=str,
        default="P2",
        help="Task priority (P0-P4, default: P2)",
    )
    queue_add.add_argument(
        "--criteria",
        "-c",
        type=str,
        action="append",
        help="Acceptance criteria (can be repeated)",
    )
    queue_add.add_argument(
        "--depends",
        "-d",
        type=str,
        action="append",
        help="Dependency task ID (can be repeated)",
    )

    # queue list
    queue_list = queue_subparsers.add_parser(
        "list",
        help="List tasks in the queue",
    )
    queue_list.add_argument(
        "--status",
        "-s",
        type=str,
        choices=["pending", "running", "complete", "failed", "all"],
        default="pending",
        help="Filter by status (default: pending)",
    )
    queue_list.add_argument(
        "--priority",
        "-p",
        type=str,
        help="Filter by priority (P0-P4)",
    )

    # queue next
    queue_subparsers.add_parser(
        "next",
        help="Show the next task to be processed",
    )

    # queue stats
    queue_subparsers.add_parser(
        "stats",
        help="Show queue statistics",
    )

    # queue clear
    queue_clear = queue_subparsers.add_parser(
        "clear",
        help="Clear completed/failed tasks from the queue",
    )
    queue_clear.add_argument(
        "--include-running",
        action="store_true",
        help="Also clear running tasks",
    )

    # TUI command for terminal interface
    tui_parser = subparsers.add_parser(
        "tui",
        help="Launch the Terminal User Interface",
        description="Launch a rich terminal interface for monitoring RALPH-AGI execution.",
    )
    tui_parser.add_argument(
        "--prd",
        "-p",
        type=str,
        metavar="PATH",
        help="Path to PRD.json file to display tasks",
    )
    tui_parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="config.yaml",
        metavar="PATH",
        help="Path to config file (default: config.yaml)",
    )
    tui_parser.add_argument(
        "--demo",
        action="store_true",
        help="Show demo data for testing the interface",
    )

    return parser


def _display_cost_summary(formatter: OutputFormatter, loop: RalphLoop) -> None:
    """Display token usage and estimated cost summary.

    Args:
        formatter: Output formatter for display.
        loop: RalphLoop instance with token tracking.
    """
    input_tokens = loop.total_input_tokens
    output_tokens = loop.total_output_tokens
    total_tokens = input_tokens + output_tokens

    # Claude pricing: $3/1M input tokens, $15/1M output tokens
    input_cost = (input_tokens / 1_000_000) * 3.0
    output_cost = (output_tokens / 1_000_000) * 15.0
    total_cost = input_cost + output_cost

    formatter.message("")
    formatter.message("=" * 40)
    formatter.message("TOKEN USAGE SUMMARY")
    formatter.message("=" * 40)
    formatter.message(f"Input tokens: {input_tokens:,}")
    formatter.message(f"Output tokens: {output_tokens:,}")
    formatter.message(f"Total tokens: {total_tokens:,}")
    formatter.message("")
    formatter.message(f"Estimated cost: ${total_cost:.4f}")
    formatter.message("  (Based on Claude pricing: $3/1M input, $15/1M output)")
    formatter.message("=" * 40)


def run_batch(
    args: argparse.Namespace,
    config: RalphConfig,
    formatter: OutputFormatter,
) -> int:
    """Execute batch mode - parallel processing with worktrees.

    Args:
        args: Parsed command-line arguments.
        config: Loaded configuration.
        formatter: Output formatter for display.

    Returns:
        Exit code.
    """
    from ralph_agi.tasks.batch import BatchConfig, BatchExecutor, format_batch_progress

    prd_path = getattr(args, "prd", None)
    if not prd_path:
        formatter.error("--batch requires --prd <path> to specify the PRD file")
        return EXIT_ERROR

    prd_file = Path(prd_path)
    if not prd_file.exists():
        formatter.error(f"PRD file not found: {prd_path}")
        return EXIT_ERROR

    # Create batch config
    batch_config = BatchConfig(
        parallel_limit=args.parallel_limit,
        cleanup_on_complete=True,
        cleanup_on_failure=False,
    )

    formatter.message("=" * 60)
    formatter.message("BATCH MODE - Parallel Task Processing")
    formatter.message("=" * 60)
    formatter.message(f"PRD: {prd_path}")
    formatter.message(f"Parallel limit: {args.parallel_limit}")
    formatter.message("")

    # Create executor
    executor = BatchExecutor(
        prd_path=prd_file,
        config_path=Path(args.config),
        batch_config=batch_config,
    )

    # Progress callback
    last_output = [""]

    def on_progress(progress):
        output = format_batch_progress(progress)
        if output != last_output[0]:
            # Clear previous output and show new
            formatter.message("\r" + " " * 80 + "\r", end="")
            for line in output.split("\n"):
                formatter.message(line)
            last_output[0] = output

    try:
        # Get max iterations from config
        max_iterations = args.max_iterations or config.max_iterations

        # Run batch
        progress = executor.run(
            max_iterations=max_iterations,
            on_progress=on_progress,
        )

        formatter.message("")
        formatter.message("=" * 60)
        formatter.message("BATCH COMPLETE")
        formatter.message("=" * 60)
        formatter.message(f"Total: {progress.total_tasks}")
        formatter.message(f"Completed: {progress.completed_count}")
        formatter.message(f"Failed: {progress.failed_count}")

        if progress.failed_count > 0:
            formatter.message("")
            formatter.message("Failed tasks:")
            for worker_id, worker in progress.workers.items():
                if worker.status.value == "failed":
                    formatter.message(f"  - {worker.task_id}: {worker.error}")

        return EXIT_SUCCESS if progress.failed_count == 0 else EXIT_ERROR

    except KeyboardInterrupt:
        formatter.message("")
        formatter.warning("Batch interrupted by user")
        return EXIT_ERROR

    except Exception as e:
        formatter.error("Batch processing failed", exception=e)
        return EXIT_ERROR


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

    # Batch mode - parallel processing with worktrees
    if args.batch:
        return run_batch(args, config, formatter)

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
            if args.show_cost:
                _display_cost_summary(formatter, loop)
            return EXIT_SUCCESS
        else:
            formatter.completion_banner(
                total_iterations=loop.iteration,
                session_id=loop.session_id,
                reason="max_iterations",
            )
            if args.show_cost:
                _display_cost_summary(formatter, loop)
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


def _load_scheduler_config_from_file(config_path: str) -> tuple[SchedulerConfig | None, str | None]:
    """Load scheduler config from YAML file.

    Args:
        config_path: Path to config file.

    Returns:
        Tuple of (config, error_message).
    """
    import yaml

    config_file = Path(config_path)
    if not config_file.exists():
        return None, f"Config file not found: {config_path}"

    try:
        with open(config_file) as f:
            data = yaml.safe_load(f) or {}
        return load_scheduler_config(data), None
    except CronValidationError as e:
        return None, f"Invalid cron expression: {e}"
    except Exception as e:
        return None, f"Failed to load config: {e}"


def run_daemon(args: argparse.Namespace) -> int:
    """Execute daemon commands.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from ralph_agi.scheduler.cron import CronExpression, describe_cron
    from ralph_agi.scheduler.daemon import (
        DaemonManager,
        DaemonStatus,
        generate_launchd_plist,
        generate_systemd_unit,
    )
    from ralph_agi.scheduler.hooks import WakeHookExecutor

    formatter = OutputFormatter(verbosity=Verbosity.NORMAL)

    if args.daemon_command is None:
        formatter.error("No daemon command specified. Use 'ralph-agi daemon --help'")
        return EXIT_ERROR

    # Load scheduler config
    scheduler_config, error = _load_scheduler_config_from_file(args.config)
    if error:
        formatter.error(error)
        return EXIT_ERROR

    daemon = DaemonManager(scheduler_config)

    if args.daemon_command == "status":
        state = daemon.status()
        formatter.message(f"Status: {state.status.value}")
        formatter.message(f"Message: {state.message}")
        if state.pid:
            formatter.message(f"PID: {state.pid}")
        if state.next_run:
            cron = CronExpression(scheduler_config.cron, "")
            formatter.message(f"Schedule: {scheduler_config.cron} ({describe_cron(scheduler_config.cron)})")
            formatter.message(f"Next run: {state.next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            formatter.message(f"Time until: {cron.time_until_next()}")
        return EXIT_SUCCESS

    elif args.daemon_command == "start":
        if not scheduler_config.enabled:
            formatter.warning("Scheduler is disabled in config. Set scheduler.enabled: true")
            return EXIT_ERROR

        formatter.message(f"Starting daemon with schedule: {scheduler_config.cron}")
        formatter.message(f"({describe_cron(scheduler_config.cron)})")

        state = daemon.start(background=not args.foreground)

        if state.status == DaemonStatus.RUNNING:
            formatter.message(f"Daemon started: {state.message}")
            if state.next_run:
                formatter.message(f"Next run: {state.next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            return EXIT_SUCCESS
        else:
            formatter.error(f"Failed to start: {state.message}")
            return EXIT_ERROR

    elif args.daemon_command == "stop":
        state = daemon.stop()
        if state.status == DaemonStatus.STOPPED:
            formatter.message(f"Daemon stopped: {state.message}")
            return EXIT_SUCCESS
        else:
            formatter.error(f"Failed to stop: {state.message}")
            return EXIT_ERROR

    elif args.daemon_command == "install":
        import platform

        working_dir = str(Path.cwd())

        # Auto-detect platform if not specified
        mode = args.mode
        if mode is None:
            system = platform.system()
            if system == "Darwin":
                mode = "launchd"
            elif system == "Linux":
                mode = "systemd"
            else:
                formatter.error(f"Unsupported platform: {system}. Use --mode to specify.")
                return EXIT_ERROR

        if mode == "launchd":
            plist_content = generate_launchd_plist(scheduler_config, working_dir)
            plist_path = Path("~/Library/LaunchAgents/com.ralph-agi.scheduler.plist").expanduser()
            plist_path.parent.mkdir(parents=True, exist_ok=True)
            plist_path.write_text(plist_content)
            formatter.message(f"Installed launchd plist: {plist_path}")
            formatter.message("")
            formatter.message("To enable:")
            formatter.message(f"  launchctl load {plist_path}")
            formatter.message("")
            formatter.message("To disable:")
            formatter.message(f"  launchctl unload {plist_path}")

        elif mode == "systemd":
            service_content, timer_content = generate_systemd_unit(scheduler_config, working_dir)
            service_dir = Path("~/.config/systemd/user").expanduser()
            service_dir.mkdir(parents=True, exist_ok=True)

            service_path = service_dir / "ralph-agi-scheduler.service"
            timer_path = service_dir / "ralph-agi-scheduler.timer"

            service_path.write_text(service_content)
            timer_path.write_text(timer_content)

            formatter.message(f"Installed systemd service: {service_path}")
            formatter.message(f"Installed systemd timer: {timer_path}")
            formatter.message("")
            formatter.message("To enable:")
            formatter.message("  systemctl --user daemon-reload")
            formatter.message("  systemctl --user enable --now ralph-agi-scheduler.timer")
            formatter.message("")
            formatter.message("To disable:")
            formatter.message("  systemctl --user disable --now ralph-agi-scheduler.timer")

        return EXIT_SUCCESS

    elif args.daemon_command == "run-once":
        # Single wake execution (called by system scheduler)
        formatter.message("=" * 50)
        formatter.message("RALPH-AGI Scheduled Wake")
        formatter.message("=" * 50)

        executor = WakeHookExecutor(
            prd_path=scheduler_config.prd_path,
            config_path=scheduler_config.config_path,
        )

        results = executor.execute(scheduler_config.wake_hooks)

        for result in results:
            status_symbol = "OK" if result.result.value == "success" else "FAIL" if result.result.value == "failure" else "SKIP"
            formatter.message(f"  [{status_symbol}] {result.hook}: {result.message}")

        # Run the main loop if configured
        if scheduler_config.prd_path:
            formatter.message("")
            formatter.message("Running RALPH-AGI loop...")
            # Re-use run_loop with synthetic args
            run_args = argparse.Namespace(
                config=args.config,
                prd=scheduler_config.prd_path,
                max_iterations=None,
                verbose=False,
                quiet=False,
                dry_run=False,
                show_cost=False,
            )
            return run_loop(run_args)

        return EXIT_SUCCESS

    return EXIT_ERROR


def run_init(args: argparse.Namespace) -> int:
    """Execute the init command (setup wizard).

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from ralph_agi.init_wizard import generate_sample_prd, run_wizard

    formatter = OutputFormatter(verbosity=Verbosity.NORMAL)

    try:
        success, message = run_wizard(
            quick=args.quick,
            output_path=args.output,
        )

        if not success:
            formatter.warning(message)
            return EXIT_ERROR

        # Generate sample PRD if requested
        if args.sample_prd:
            prd_success, prd_message = generate_sample_prd()
            if prd_success:
                formatter.message(f"\n{prd_message}")
            else:
                formatter.warning(prd_message)

        return EXIT_SUCCESS

    except KeyboardInterrupt:
        formatter.message("\n")
        formatter.warning("Setup cancelled by user")
        return EXIT_ERROR

    except Exception as e:
        formatter.error("Setup failed", exception=e)
        return EXIT_ERROR


def run_queue(args: argparse.Namespace) -> int:
    """Execute queue commands.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from ralph_agi.tasks.queue import TaskQueue, TaskStatus

    formatter = OutputFormatter(verbosity=Verbosity.NORMAL)

    if args.queue_command is None:
        formatter.error("No queue command specified. Use 'ralph-agi queue --help'")
        return EXIT_ERROR

    # Initialize queue
    queue = TaskQueue()

    if args.queue_command == "add":
        try:
            task = queue.add(
                description=args.description,
                priority=args.priority,
                acceptance_criteria=args.criteria or [],
                dependencies=args.depends or [],
            )

            formatter.message(f"Task created: {task.id}")
            formatter.message(f"  Description: {task.description}")
            formatter.message(f"  Priority: P{task.priority.value}")
            formatter.message(f"  Status: {task.status.value}")

            if task.acceptance_criteria:
                formatter.message("  Criteria:")
                for criterion in task.acceptance_criteria:
                    formatter.message(f"    - {criterion}")

            if task.dependencies:
                formatter.message(f"  Dependencies: {', '.join(task.dependencies)}")

            return EXIT_SUCCESS

        except Exception as e:
            formatter.error(f"Failed to add task: {e}")
            return EXIT_ERROR

    elif args.queue_command == "list":
        # Determine status filter
        if args.status == "all":
            tasks = queue.list(include_terminal=True)
        else:
            tasks = queue.list(status=args.status, include_terminal=(args.status in ["complete", "failed"]))

        # Apply priority filter
        if args.priority:
            from ralph_agi.tasks.queue import TaskPriority
            priority = TaskPriority.from_string(args.priority)
            tasks = [t for t in tasks if t.priority == priority]

        if not tasks:
            formatter.message("No tasks found")
            return EXIT_SUCCESS

        # Display tasks
        formatter.message(f"Tasks ({len(tasks)}):")
        formatter.message("")

        for task in tasks:
            # Status indicator
            status_icons = {
                TaskStatus.PENDING: " ",
                TaskStatus.READY: "*",
                TaskStatus.RUNNING: ">",
                TaskStatus.COMPLETE: "✓",
                TaskStatus.FAILED: "✗",
                TaskStatus.CANCELLED: "-",
            }
            icon = status_icons.get(task.status, "?")

            # Format line
            line = f"[{icon}] [{task.priority.name}] {task.id}"
            formatter.message(line)
            formatter.message(f"    {task.description[:60]}{'...' if len(task.description) > 60 else ''}")

            if task.pr_url:
                formatter.message(f"    PR: {task.pr_url}")
            if task.confidence is not None:
                formatter.message(f"    Confidence: {task.confidence:.2f}")
            if task.error:
                formatter.message(f"    Error: {task.error}")

            formatter.message("")

        return EXIT_SUCCESS

    elif args.queue_command == "next":
        next_task = queue.next()

        if next_task is None:
            formatter.message("No tasks ready to process")
            formatter.message("(All tasks may be blocked by dependencies)")
            return EXIT_SUCCESS

        formatter.message("Next task to process:")
        formatter.message("")
        formatter.message(f"  ID: {next_task.id}")
        formatter.message(f"  Description: {next_task.description}")
        formatter.message(f"  Priority: P{next_task.priority.value}")

        if next_task.acceptance_criteria:
            formatter.message("  Acceptance Criteria:")
            for criterion in next_task.acceptance_criteria:
                formatter.message(f"    - {criterion}")

        if next_task.dependencies:
            formatter.message(f"  Dependencies: {', '.join(next_task.dependencies)}")

        return EXIT_SUCCESS

    elif args.queue_command == "stats":
        stats = queue.stats()

        formatter.message("Queue Statistics:")
        formatter.message("")
        formatter.message(f"  Total:     {stats['total']}")
        formatter.message(f"  Pending:   {stats.get('pending', 0)}")
        formatter.message(f"  Ready:     {stats.get('ready', 0)}")
        formatter.message(f"  Running:   {stats.get('running', 0)}")
        formatter.message(f"  Complete:  {stats.get('complete', 0)}")
        formatter.message(f"  Failed:    {stats.get('failed', 0)}")
        formatter.message(f"  Cancelled: {stats.get('cancelled', 0)}")

        return EXIT_SUCCESS

    elif args.queue_command == "clear":
        removed = queue.clear(include_running=args.include_running)
        formatter.message(f"Cleared {removed} tasks from queue")
        return EXIT_SUCCESS

    return EXIT_ERROR


def run_tui(args: argparse.Namespace) -> int:
    """Execute the tui command (terminal interface).

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from ralph_agi.tui.app import run_tui as launch_tui

    try:
        launch_tui(
            prd_path=args.prd,
            config_path=args.config,
            demo=args.demo,
        )
        return EXIT_SUCCESS

    except KeyboardInterrupt:
        return EXIT_SUCCESS

    except Exception as e:
        formatter = OutputFormatter(verbosity=Verbosity.NORMAL)
        formatter.error("TUI error", exception=e)
        return EXIT_ERROR


def main(argv: list[str] | None = None) -> int:
    """Main entry point for ralph-agi CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code.
    """
    # Auto-load .env file for API keys
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv is optional

    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        # No command specified - launch interactive mode
        from ralph_agi.interactive import run_interactive

        result = run_interactive()

        # Handle interactive mode results
        if isinstance(result, tuple):
            if result[0] == "run":
                # User selected a PRD to run
                prd_path = result[1]
                args = parser.parse_args(["run", "--prd", prd_path])
                return run_loop(args)
            elif result[0] == "init":
                # User wants to run setup wizard
                args = parser.parse_args(["init"])
                return run_init(args)

        return EXIT_SUCCESS

    if args.command == "run":
        return run_loop(args)

    if args.command == "daemon":
        return run_daemon(args)

    if args.command == "init":
        return run_init(args)

    if args.command == "queue":
        return run_queue(args)

    if args.command == "tui":
        return run_tui(args)

    # Unknown command (shouldn't happen with subparsers)
    parser.print_help()
    return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
