"""Main TUI application for RALPH-AGI."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, ProgressBar, Static

from ralph_agi import __version__
from ralph_agi.tui.widgets import AgentViewer, LogPanel, MetricsBar, StoryGrid
from ralph_agi.tui.widgets.story_grid import TaskInfo, TaskStatus
from ralph_agi.tui.events import Event, EventBus, EventType


class ProgressFooter(Horizontal):
    """Footer with progress bar and status."""

    DEFAULT_CSS = """
    ProgressFooter {
        dock: bottom;
        height: 1;
        background: $surface;
        padding: 0 1;
    }
    ProgressFooter > .task-label {
        width: auto;
        padding-right: 1;
    }
    ProgressFooter > ProgressBar {
        width: 1fr;
        padding: 0;
    }
    ProgressFooter > .eta {
        width: auto;
        padding-left: 1;
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        """Initialize the progress footer."""
        super().__init__()
        self._task_name = ""
        self._progress = 0.0
        self._eta = ""

    def compose(self) -> ComposeResult:
        """Compose the footer layout."""
        yield Static("", classes="task-label", id="task-label")
        yield ProgressBar(total=100, show_eta=False, id="progress-bar")
        yield Static("", classes="eta", id="eta-label")

    def update_progress(self, task_name: str, progress: float, eta: str = "") -> None:
        """Update progress display.

        Args:
            task_name: Current task name.
            progress: Progress percentage (0-100).
            eta: Estimated time remaining.
        """
        self._task_name = task_name
        self._progress = progress
        self._eta = eta

        task_label = self.query_one("#task-label", Static)
        task_label.update(task_name)

        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.update(progress=progress)

        eta_label = self.query_one("#eta-label", Static)
        eta_label.update(f"ETA: {eta}" if eta else "")


class RalphTUI(App[None]):
    """RALPH-AGI Terminal User Interface.

    A rich, real-time TUI for monitoring RALPH-AGI execution.
    Built with Textual for a developer-native experience.
    """

    TITLE = f"RALPH-AGI v{__version__}"
    SUB_TITLE = "Autonomous Agent Monitor"

    CSS_PATH: ClassVar[str | Path | None] = Path(__file__).parent / "styles.tcss"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+p", "command_palette", "Commands", show=True),
        Binding("p", "pause", "Pause", show=True),
        Binding("r", "resume", "Resume", show=False),
        Binding("s", "stop", "Stop", show=True),
        Binding("l", "toggle_logs", "Toggle Logs", show=False),
        Binding("a", "toggle_auto_scroll", "Auto-scroll", show=False),
        Binding("ctrl+l", "clear_logs", "Clear Logs", show=False),
    ]

    def __init__(
        self,
        prd_path: str | None = None,
        config_path: str | None = None,
        demo_mode: bool = False,
    ) -> None:
        """Initialize the TUI application.

        Args:
            prd_path: Path to PRD.json file.
            config_path: Path to config.yaml file.
            demo_mode: If True, show demo data.
        """
        super().__init__()
        self.prd_path = prd_path
        self.config_path = config_path
        self.demo_mode = demo_mode

        self._paused = False
        self._running = False

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header(show_clock=True)

        with Container(id="main-container"):
            # Top row: Stories + Metrics
            with Horizontal(id="top-row"):
                yield StoryGrid(title="Stories", id="story-grid")
                yield MetricsBar(title="Metrics", id="metrics-bar")

            # Middle: Agent output
            yield AgentViewer(title="Agent Output", id="agent-viewer")

            # Bottom: Logs
            yield LogPanel(title="Logs", id="log-panel")

        yield ProgressFooter()
        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount - initialize display."""
        if self.demo_mode:
            self._load_demo_data()
        else:
            self._initialize_from_prd()

        # Subscribe to events from RalphLoop
        self._subscribe_to_events()

        # Start time refresh timer
        self.set_interval(1.0, self._refresh_time)

    def _subscribe_to_events(self) -> None:
        """Subscribe to RalphLoop events for live updates."""
        bus = EventBus.get_instance()

        # Loop lifecycle
        bus.subscribe(EventType.LOOP_STARTED, self._on_loop_started)
        bus.subscribe(EventType.LOOP_STOPPED, self._on_loop_stopped)

        # Iteration events
        bus.subscribe(EventType.ITERATION_STARTED, self._on_iteration_started)
        bus.subscribe(EventType.ITERATION_COMPLETED, self._on_iteration_completed)

        # Task events
        bus.subscribe(EventType.TASK_SELECTED, self._on_task_selected)
        bus.subscribe(EventType.TASK_COMPLETED, self._on_task_completed)

        # Agent events
        bus.subscribe(EventType.AGENT_THINKING, self._on_agent_thinking)
        bus.subscribe(EventType.AGENT_ACTION, self._on_agent_action)
        bus.subscribe(EventType.TOOL_CALLED, self._on_tool_called)
        bus.subscribe(EventType.TOOL_RESULT, self._on_tool_result)

        # Metrics events
        bus.subscribe(EventType.TOKENS_USED, self._on_tokens_used)
        bus.subscribe(EventType.COST_UPDATED, self._on_cost_updated)

        # Log events
        bus.subscribe(EventType.LOG_MESSAGE, self._on_log_message)
        bus.subscribe(EventType.LOG_ERROR, self._on_log_error)

        # Progress events
        bus.subscribe(EventType.PROGRESS_UPDATED, self._on_progress_updated)

    def _on_loop_started(self, event: Event) -> None:
        """Handle loop started event."""
        total = event.data.get("total_iterations", 0)
        self._running = True
        self.log_info(f"RALPH-AGI loop started (max {total} iterations)")
        self.notify("Loop started", severity="information")

    def _on_loop_stopped(self, event: Event) -> None:
        """Handle loop stopped event."""
        reason = event.data.get("reason", "unknown")
        self._running = False
        self.log_info(f"Loop stopped: {reason}")
        self.notify(f"Loop stopped: {reason}", severity="warning")

    def _on_iteration_started(self, event: Event) -> None:
        """Handle iteration started event."""
        iteration = event.data.get("iteration", 0)
        task_id = event.data.get("task_id", "")
        self.log_info(f"Starting iteration {iteration}...")

        # Update story grid if task is specified
        if task_id:
            story_grid = self.query_one("#story-grid", StoryGrid)
            story_grid.update_task(task_id, TaskStatus.RUNNING)

    def _on_iteration_completed(self, event: Event) -> None:
        """Handle iteration completed event."""
        iteration = event.data.get("iteration", 0)
        success = event.data.get("success", False)
        duration = event.data.get("duration_seconds", 0)
        tokens = event.data.get("tokens_used", 0)

        # Update metrics
        metrics_bar = self.query_one("#metrics-bar", MetricsBar)
        metrics_bar.update_iteration(iteration, iteration)  # TODO: get max from config

        status = "✓" if success else "✗"
        self.log_info(f"Iteration {iteration} {status} ({duration:.1f}s, {tokens} tokens)")

    def _on_task_selected(self, event: Event) -> None:
        """Handle task selected event."""
        task_id = event.data.get("task_id", "")
        task_name = event.data.get("task_name", "")
        self.log_info(f"Selected task: {task_id} - {task_name}")

        # Update agent viewer
        agent_viewer = self.query_one("#agent-viewer", AgentViewer)
        agent_viewer.show_iteration(0, task_name)

    def _on_task_completed(self, event: Event) -> None:
        """Handle task completed event."""
        task_id = event.data.get("task_id", "")
        success = event.data.get("success", False)

        story_grid = self.query_one("#story-grid", StoryGrid)
        status = TaskStatus.DONE if success else TaskStatus.FAILED
        story_grid.update_task(task_id, status)

        emoji = "✅" if success else "❌"
        self.log_info(f"Task {task_id} {emoji}")

    def _on_agent_thinking(self, event: Event) -> None:
        """Handle agent thinking event."""
        thought = event.data.get("thought", "")
        agent_viewer = self.query_one("#agent-viewer", AgentViewer)
        agent_viewer.show_thought(thought)

    def _on_agent_action(self, event: Event) -> None:
        """Handle agent action event."""
        action = event.data.get("action", "")
        agent_viewer = self.query_one("#agent-viewer", AgentViewer)
        agent_viewer.show_action(action)

    def _on_tool_called(self, event: Event) -> None:
        """Handle tool called event."""
        tool_name = event.data.get("tool_name", "")
        self.log_debug(f"Tool: {tool_name}")

    def _on_tool_result(self, event: Event) -> None:
        """Handle tool result event."""
        tool_name = event.data.get("tool_name", "")
        success = event.data.get("success", False)
        result = event.data.get("result", "")[:100]

        agent_viewer = self.query_one("#agent-viewer", AgentViewer)
        agent_viewer.show_result(f"{tool_name}: {result}")

    def _on_tokens_used(self, event: Event) -> None:
        """Handle tokens used event."""
        prompt = event.data.get("prompt_tokens", 0)
        completion = event.data.get("completion_tokens", 0)

        metrics_bar = self.query_one("#metrics-bar", MetricsBar)
        metrics_bar.update_tokens(prompt, completion)

    def _on_cost_updated(self, event: Event) -> None:
        """Handle cost updated event."""
        cost = event.data.get("total_cost", 0.0)

        metrics_bar = self.query_one("#metrics-bar", MetricsBar)
        metrics_bar.update_cost(cost)

    def _on_log_message(self, event: Event) -> None:
        """Handle log message event."""
        level = event.data.get("level", "info")
        message = event.data.get("message", "")

        if level == "debug":
            self.log_debug(message)
        elif level == "warning":
            self.log_warning(message)
        else:
            self.log_info(message)

    def _on_log_error(self, event: Event) -> None:
        """Handle log error event."""
        message = event.data.get("message", "")
        self.log_error(message)

    def _on_progress_updated(self, event: Event) -> None:
        """Handle progress updated event."""
        task_name = event.data.get("task_name", "")
        progress = event.data.get("progress", 0.0)
        eta = event.data.get("eta", "")

        progress_footer = self.query_one(ProgressFooter)
        progress_footer.update_progress(task_name, progress, eta)

    def _initialize_from_prd(self) -> None:
        """Initialize display from PRD file."""
        if not self.prd_path:
            self.log_info("No PRD file specified. Use --prd to load tasks.")
            return

        try:
            import json

            with open(self.prd_path) as f:
                prd_data = json.load(f)

            # Load tasks
            tasks = []
            for task in prd_data.get("tasks", []):
                status_map = {
                    "pending": TaskStatus.PENDING,
                    "in_progress": TaskStatus.RUNNING,
                    "complete": TaskStatus.DONE,
                    "blocked": TaskStatus.BLOCKED,
                }
                status = status_map.get(task.get("status", "pending"), TaskStatus.PENDING)
                tasks.append(
                    TaskInfo(
                        id=task.get("id", "?"),
                        name=task.get("description", "Unknown")[:40],
                        status=status,
                    )
                )

            story_grid = self.query_one("#story-grid", StoryGrid)
            story_grid.set_tasks(tasks)

            self.log_info(f"Loaded {len(tasks)} tasks from {self.prd_path}")

        except FileNotFoundError:
            self.log_error(f"PRD file not found: {self.prd_path}")
        except json.JSONDecodeError as e:
            self.log_error(f"Invalid JSON in PRD: {e}")
        except Exception as e:
            self.log_error(f"Error loading PRD: {e}")

    def _load_demo_data(self) -> None:
        """Load demo data for demonstration."""
        # Demo tasks
        demo_tasks = [
            TaskInfo("2.1", "PRD.json Parser", TaskStatus.DONE),
            TaskInfo("2.2", "Task Selection", TaskStatus.DONE),
            TaskInfo("2.4", "Task Completion", TaskStatus.DONE),
            TaskInfo("2.5", "Single Feature", TaskStatus.RUNNING, progress=45),
            TaskInfo("2.6", "Docker Isolation", TaskStatus.PENDING),
            TaskInfo("3.1", "Memvid Core", TaskStatus.PENDING),
        ]

        story_grid = self.query_one("#story-grid", StoryGrid)
        story_grid.set_tasks(demo_tasks)

        # Demo metrics
        metrics_bar = self.query_one("#metrics-bar", MetricsBar)
        metrics_bar.update_iteration(15, 100)
        metrics_bar.update_cost(2.34)
        metrics_bar.update_tokens(85000, 40432)

        # Demo agent output
        agent_viewer = self.query_one("#agent-viewer", AgentViewer)
        agent_viewer.show_iteration(15, "Implement single feature constraint")
        agent_viewer.show_action("Reading tests/tasks/test_executor.py...")
        agent_viewer.show_result("Found 24 test cases, 23 passing, 1 failing")
        agent_viewer.show_action("Analyzing failing test: test_feature_constraint_with_deps")
        agent_viewer.show_thought("The issue is in the dependency resolution when max_size is reached")
        agent_viewer.show_action("Proposing fix: Add size check before adding dependent tasks")

        # Demo logs
        self.log_info("Starting iteration 15...")
        self.log_debug("Loading context (2,450 tokens)...")
        self.log_info("Calling Claude claude-opus-4-5-20251101...")
        self.log_info("Response received (18s, 3,200 tokens)")
        self.log_info("Executing tool: Read tests/tasks/test_executor.py")
        self.log_debug("Tool result: 142 lines read")
        self.log_info("Analyzing test results...")

        # Demo progress
        progress_footer = self.query_one(ProgressFooter)
        progress_footer.update_progress("Story 2.5", 45, "32m")

    def _refresh_time(self) -> None:
        """Refresh time display periodically."""
        metrics_bar = self.query_one("#metrics-bar", MetricsBar)
        metrics_bar.refresh_time()

    # Logging methods
    def log_info(self, message: str) -> None:
        """Log an info message."""
        log_panel = self.query_one("#log-panel", LogPanel)
        log_panel.log_info(message)

    def log_debug(self, message: str) -> None:
        """Log a debug message."""
        log_panel = self.query_one("#log-panel", LogPanel)
        log_panel.log_debug(message)

    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        log_panel = self.query_one("#log-panel", LogPanel)
        log_panel.log_warning(message)

    def log_error(self, message: str) -> None:
        """Log an error message."""
        log_panel = self.query_one("#log-panel", LogPanel)
        log_panel.log_error(message)

    # Actions
    def action_pause(self) -> None:
        """Pause execution."""
        if self._running and not self._paused:
            self._paused = True
            self.log_warning("Execution paused")
            self.notify("Paused", severity="warning")

    def action_resume(self) -> None:
        """Resume execution."""
        if self._paused:
            self._paused = False
            self.log_info("Execution resumed")
            self.notify("Resumed", severity="information")

    def action_stop(self) -> None:
        """Stop execution."""
        self.log_warning("Stop requested...")
        self.notify("Stopping...", severity="warning")
        # In real implementation, this would signal the loop to stop

    def action_toggle_logs(self) -> None:
        """Toggle log panel visibility."""
        log_panel = self.query_one("#log-panel", LogPanel)
        log_panel.display = not log_panel.display

    def action_toggle_auto_scroll(self) -> None:
        """Toggle auto-scroll in log panel."""
        log_panel = self.query_one("#log-panel", LogPanel)
        enabled = log_panel.toggle_auto_scroll()
        self.notify(f"Auto-scroll: {'ON' if enabled else 'OFF'}")

    def action_clear_logs(self) -> None:
        """Clear log panel."""
        log_panel = self.query_one("#log-panel", LogPanel)
        log_panel.clear_logs()
        self.notify("Logs cleared")

    def action_command_palette(self) -> None:
        """Show command palette."""
        # Textual has built-in command palette, but we can customize
        self.notify("Command palette: Press Ctrl+\\ for built-in palette", timeout=3)


def run_tui(
    prd_path: str | None = None,
    config_path: str | None = None,
    demo: bool = False,
) -> None:
    """Run the RALPH-AGI TUI.

    Args:
        prd_path: Path to PRD.json file.
        config_path: Path to config.yaml file.
        demo: If True, show demo data.
    """
    app = RalphTUI(prd_path=prd_path, config_path=config_path, demo_mode=demo)
    app.run()
