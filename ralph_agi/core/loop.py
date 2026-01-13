"""Ralph Loop Engine - The core execution loop for RALPH-AGI.

This module implements the central mechanism that drives all agent activity,
processing one task at a time until all tasks are complete or max iterations reached.

Key Design Principles (from PRD FR-001):
- Uses WHILE loop (not FOR) for cleaner exit conditions
- Single task per iteration to prevent context bloat
- Comprehensive logging with timestamps
- Retry logic with exponential backoff
- Builder → Critic multi-agent architecture (ADR-002)
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional
from uuid import uuid4

if TYPE_CHECKING:
    from ralph_agi.core.config import RalphConfig
    from ralph_agi.llm.agents import BuilderAgent, CriticAgent
    from ralph_agi.llm.orchestrator import LLMOrchestrator
    from ralph_agi.memory.store import MemoryStore
    from ralph_agi.tasks.executor import TaskExecutor


@dataclass
class IterationResult:
    """Result of a single loop iteration.

    Attributes:
        success: Whether the iteration completed successfully.
        output: Optional output string from the iteration (for completion detection).
        task_id: ID of the task that was executed.
        task_title: Title of the task that was executed.
        files_changed: List of files modified during execution.
        tokens_used: Total tokens used in this iteration.
        all_tasks_complete: Whether all tasks in PRD are complete.
        error: Error message if iteration failed.
    """

    success: bool
    output: Optional[str] = None
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    files_changed: list[str] = field(default_factory=list)
    tokens_used: int = 0
    all_tasks_complete: bool = False
    error: Optional[str] = None


class ToolExecutorAdapter:
    """Adapter that bridges LLM tool calls to RALPH tool implementations.

    Maps tool names from LLM to our FileSystemTools, ShellTools, and GitTools.
    """

    def __init__(self, work_dir: Optional[Path] = None):
        """Initialize the tool executor.

        Args:
            work_dir: Working directory for file operations.
        """
        self._work_dir = work_dir or Path.cwd()
        self._fs_tools = None
        self._shell_tools = None
        self._git_tools = None

    def _ensure_tools(self) -> None:
        """Lazily initialize tools."""
        if self._fs_tools is None:
            from ralph_agi.tools.filesystem import FileSystemTools
            self._fs_tools = FileSystemTools(allowed_roots=[self._work_dir])

        if self._shell_tools is None:
            from ralph_agi.tools.shell import ShellTools
            self._shell_tools = ShellTools(default_cwd=self._work_dir)

        if self._git_tools is None:
            from ralph_agi.tools.git import GitTools
            self._git_tools = GitTools(repo_path=self._work_dir)

    async def execute(
        self,
        tool_name: str,
        arguments: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Arguments for the tool.

        Returns:
            Tool execution result.
        """
        self._ensure_tools()
        arguments = arguments or {}

        # File system tools
        if tool_name == "read_file":
            path = arguments.get("path", "")
            return self._fs_tools.read_file(path)

        elif tool_name == "write_file":
            path = arguments.get("path", "")
            content = arguments.get("content", "")
            self._fs_tools.write_file(path, content)
            return f"File written: {path}"

        elif tool_name == "edit_file":
            path = arguments.get("path", "")
            old_content = arguments.get("old_content", "")
            new_content = arguments.get("new_content", "")
            resolved, count = self._fs_tools.edit_file(path, old_content, new_content)
            return f"Edited {resolved}: {count} replacement(s) made"

        elif tool_name == "insert_in_file":
            path = arguments.get("path", "")
            content = arguments.get("content", "")
            after = arguments.get("after")
            before = arguments.get("before")
            at_line = arguments.get("at_line")
            self._fs_tools.insert_in_file(
                path, content, after=after, before=before, at_line=at_line
            )
            return f"Content inserted into {path}"

        elif tool_name == "append_to_file":
            path = arguments.get("path", "")
            content = arguments.get("content", "")
            self._fs_tools.append_to_file(path, content)
            return f"Content appended to {path}"

        elif tool_name == "list_directory":
            path = arguments.get("path", ".")
            files = self._fs_tools.list_directory(path)
            return "\n".join(f.name for f in files)

        # Shell tools
        elif tool_name == "run_command":
            command = arguments.get("command", "")
            cwd = arguments.get("cwd")
            result = self._shell_tools.execute(command, cwd=cwd)
            if result.success:
                return result.stdout
            else:
                return f"Error (exit {result.exit_code}): {result.stderr or result.stdout}"

        # Git tools
        elif tool_name == "git_status":
            status = self._git_tools.status()
            parts = [f"Branch: {status.branch}"]
            if status.staged:
                parts.append(f"Staged: {', '.join(status.staged)}")
            if status.modified:
                parts.append(f"Modified: {', '.join(status.modified)}")
            if status.untracked:
                parts.append(f"Untracked: {', '.join(status.untracked)}")
            return "\n".join(parts)

        elif tool_name == "git_commit":
            message = arguments.get("message", "")
            self._git_tools.add(".")
            commit = self._git_tools.commit(message)
            return f"Committed: {commit.sha[:8]} - {commit.message}"

        else:
            return f"Unknown tool: {tool_name}"


class MaxRetriesExceeded(Exception):
    """Raised when maximum retry attempts are exhausted."""

    def __init__(self, message: str, attempts: int, last_error: Optional[Exception] = None):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


class LoopInterrupted(Exception):
    """Raised when the loop is interrupted by a signal (SIGINT/SIGTERM)."""

    def __init__(self, message: str, iteration: int, checkpoint_path: Optional[str] = None):
        super().__init__(message)
        self.iteration = iteration
        self.checkpoint_path = checkpoint_path


class RalphLoop:
    """The Ralph Loop Engine - core execution loop for RALPH-AGI.

    Implements the iterative cycle that processes tasks one at a time:
    1. Load Context
    2. Select Task
    3. Execute Task
    4. Verify
    5. Update State
    6. Check Completion

    Attributes:
        max_iterations: Maximum number of iterations before forced exit (default: 100)
        iteration: Current iteration number (0-indexed)
        complete: Whether the loop has received a completion signal
    """

    # Default retry configuration
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds

    def __init__(
        self,
        max_iterations: int = 100,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delays: Optional[list[int]] = None,
        log_file: Optional[str] = None,
        completion_promise: str = "<promise>COMPLETE</promise>",
        checkpoint_path: Optional[str] = None,
        memory_store: Optional[MemoryStore] = None,
        session_id: Optional[str] = None,
        prd_path: Optional[str] = None,
        task_executor: Optional[TaskExecutor] = None,
        orchestrator: Optional[LLMOrchestrator] = None,
    ):
        """Initialize the Ralph Loop Engine.

        Args:
            max_iterations: Maximum iterations before forced exit. Default: 100
            max_retries: Maximum retry attempts per iteration. Default: 3
            retry_delays: List of delays (seconds) for exponential backoff.
                         Default: [1, 2, 4]
            log_file: Optional path to log file. If provided, logs to both
                     console and file.
            completion_promise: String to detect for task completion.
                         Default: "<promise>COMPLETE</promise>"
            checkpoint_path: Optional path for saving checkpoints on interrupt.
                         Default: None (no checkpointing)
            memory_store: Optional MemoryStore for persistent memory.
                         Default: None (no memory)
            session_id: Optional session identifier. If not provided, a new
                       UUID will be generated. Default: None
            prd_path: Path to PRD.json file for task management.
                     Required for LLM execution mode.
            task_executor: Optional TaskExecutor for task lifecycle.
                          Created automatically if prd_path provided.
            orchestrator: Optional LLMOrchestrator for Builder → Critic flow.
                         Created from config if not provided.
        """
        if max_iterations < 0:
            raise ValueError("max_iterations must be non-negative")

        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.retry_delays = retry_delays or self.DEFAULT_RETRY_DELAYS.copy()

        self.iteration = 0
        self.complete = False
        self._completion_signal = completion_promise
        self._checkpoint_path = checkpoint_path
        self._interrupted = False
        self._original_sigint_handler = None
        self._original_sigterm_handler = None

        # Session management
        self.session_id = session_id or str(uuid4())

        # Memory store (optional)
        self._memory_store = memory_store

        # Task management (for LLM execution)
        self._prd_path = Path(prd_path) if prd_path else None
        self._task_executor = task_executor
        self._orchestrator = orchestrator
        self._tools: list[Any] = []  # LLM Tool schemas

        # Set up logging
        self._setup_logging(log_file)

    @classmethod
    def from_config(
        cls,
        config: RalphConfig,
        prd_path: Optional[str] = None,
    ) -> RalphLoop:
        """Create a RalphLoop instance from a RalphConfig.

        Args:
            config: RalphConfig instance with configuration values.
            prd_path: Path to PRD.json file for task management.

        Returns:
            Configured RalphLoop instance.
        """
        # Create memory store if enabled
        memory_store = None
        if config.memory_enabled:
            from ralph_agi.memory.store import MemoryStore
            memory_store = MemoryStore(config.memory_store_path)

        # Create LLM components
        orchestrator = None
        task_executor = None

        if prd_path:
            prd_file = Path(prd_path)
            work_dir = prd_file.parent if prd_file.exists() else Path.cwd()
            orchestrator = cls._create_orchestrator(config, work_dir=work_dir)
            from ralph_agi.tasks.executor import TaskExecutor
            task_executor = TaskExecutor()

        loop = cls(
            max_iterations=config.max_iterations,
            max_retries=config.max_retries,
            retry_delays=config.retry_delays,
            log_file=config.log_file,
            completion_promise=config.completion_promise,
            checkpoint_path=config.checkpoint_path,
            memory_store=memory_store,
            prd_path=prd_path,
            task_executor=task_executor,
            orchestrator=orchestrator,
        )

        # Build tool schemas for LLM
        if orchestrator:
            loop._tools = cls._build_tool_schemas()

        return loop

    @staticmethod
    def _create_orchestrator(
        config: RalphConfig,
        work_dir: Optional[Path] = None,
    ) -> LLMOrchestrator:
        """Create LLM orchestrator from config.

        Args:
            config: RalphConfig with LLM settings.
            work_dir: Working directory for tool execution.

        Returns:
            Configured LLMOrchestrator.
        """
        from ralph_agi.llm.agents import BuilderAgent, CriticAgent
        from ralph_agi.llm.orchestrator import LLMOrchestrator

        # Create tool executor
        tool_executor = ToolExecutorAdapter(work_dir=work_dir)

        # Create Builder client based on provider
        builder_client = RalphLoop._create_llm_client(
            provider=config.llm_builder_provider,
            model=config.llm_builder_model,
        )

        builder = BuilderAgent(
            client=builder_client,
            tool_executor=tool_executor,
            max_iterations=config.llm_max_tool_iterations,
            max_tokens=config.llm_max_tokens,
        )

        # Create Critic if enabled
        critic = None
        if config.llm_critic_enabled:
            critic_client = RalphLoop._create_llm_client(
                provider=config.llm_critic_provider,
                model=config.llm_critic_model,
            )
            critic = CriticAgent(
                client=critic_client,
                max_tokens=config.llm_max_tokens,
            )

        return LLMOrchestrator(
            builder=builder,
            critic=critic,
            critic_enabled=config.llm_critic_enabled,
            max_rate_limit_retries=config.llm_rate_limit_retries,
        )

    @staticmethod
    def _create_llm_client(provider: str, model: str) -> Any:
        """Create an LLM client for the given provider.

        Args:
            provider: Provider name (anthropic, openai, openrouter).
            model: Model name.

        Returns:
            LLM client instance.

        Raises:
            ValueError: If provider is unknown.
        """
        if provider == "anthropic":
            from ralph_agi.llm.anthropic import AnthropicClient
            return AnthropicClient(model=model)
        elif provider == "openai":
            from ralph_agi.llm.openai import OpenAIClient
            return OpenAIClient(model=model)
        elif provider == "openrouter":
            from ralph_agi.llm.openrouter import OpenRouterClient
            return OpenRouterClient(model=model)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    @staticmethod
    def _build_tool_schemas() -> list[Any]:
        """Build Tool schemas for LLM from available tools.

        Returns:
            List of Tool dataclasses for LLM.
        """
        from ralph_agi.llm.client import Tool

        # Core file system tools
        tools = [
            Tool(
                name="read_file",
                description="Read the contents of a file at the specified path.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absolute or relative path to the file to read.",
                        },
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="write_file",
                description="Write content to a file, creating it if it doesn't exist. WARNING: This overwrites the entire file. For existing files, prefer edit_file or insert_in_file.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to write.",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file.",
                        },
                    },
                    "required": ["path", "content"],
                },
            ),
            Tool(
                name="edit_file",
                description="Edit an existing file by finding and replacing specific content. PREFERRED for modifying existing files - preserves content you don't change.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to edit.",
                        },
                        "old_content": {
                            "type": "string",
                            "description": "The exact content to find and replace. Must exist in the file.",
                        },
                        "new_content": {
                            "type": "string",
                            "description": "The content to replace it with.",
                        },
                    },
                    "required": ["path", "old_content", "new_content"],
                },
            ),
            Tool(
                name="insert_in_file",
                description="Insert content into a file at a specific location. Use for adding new code without modifying existing content.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to modify.",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to insert.",
                        },
                        "after": {
                            "type": "string",
                            "description": "Insert after the line containing this string.",
                        },
                        "before": {
                            "type": "string",
                            "description": "Insert before the line containing this string.",
                        },
                        "at_line": {
                            "type": "integer",
                            "description": "Insert at this line number (1-indexed).",
                        },
                    },
                    "required": ["path", "content"],
                },
            ),
            Tool(
                name="append_to_file",
                description="Append content to the end of a file. Use for adding new functions, classes, or tests to existing files.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file.",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to append at the end.",
                        },
                    },
                    "required": ["path", "content"],
                },
            ),
            Tool(
                name="list_directory",
                description="List files and directories at the specified path.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the directory to list.",
                        },
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="run_command",
                description="Execute a shell command and return its output.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute.",
                        },
                        "cwd": {
                            "type": "string",
                            "description": "Working directory for the command (optional).",
                        },
                    },
                    "required": ["command"],
                },
            ),
            Tool(
                name="git_status",
                description="Get the current git status of the repository.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the git repository (optional, defaults to cwd).",
                        },
                    },
                },
            ),
            Tool(
                name="git_commit",
                description="Create a git commit with the specified message.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Commit message.",
                        },
                        "path": {
                            "type": "string",
                            "description": "Path to the git repository (optional).",
                        },
                    },
                    "required": ["message"],
                },
            ),
        ]

        return tools

    def _setup_logging(self, log_file: Optional[str] = None) -> None:
        """Configure logging with ISO timestamp format.

        Args:
            log_file: Optional path to log file for dual output.
        """
        # Use instance-specific logger name to avoid conflicts with multiple RalphLoop instances
        self._logger_name = f"ralph-agi.{id(self)}"
        self.logger = logging.getLogger(self._logger_name)
        self.logger.setLevel(logging.DEBUG)
        # Note: propagate=True (default) allows pytest caplog to capture logs

        # Track handlers for cleanup
        self._handlers: list[logging.Handler] = []

        # Custom formatter with ISO timestamp in brackets
        class BracketedTimestampFormatter(logging.Formatter):
            def format(self, record):
                timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
                record.bracketed_time = f"[{timestamp}]"
                return super().format(record)

        formatter = BracketedTimestampFormatter(
            "%(bracketed_time)s %(message)s"
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        self._handlers.append(console_handler)

        # File handler (if specified)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            self._handlers.append(file_handler)

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful interrupt handling."""
        self._original_sigint_handler = signal.signal(signal.SIGINT, self._handle_interrupt)
        self._original_sigterm_handler = signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        if self._original_sigint_handler is not None:
            signal.signal(signal.SIGINT, self._original_sigint_handler)
        if self._original_sigterm_handler is not None:
            signal.signal(signal.SIGTERM, self._original_sigterm_handler)

    def _handle_interrupt(self, signum: int, frame: Any) -> None:
        """Handle interrupt signals (SIGINT/SIGTERM).

        Sets the interrupted flag to allow graceful shutdown.
        """
        signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        self.logger.warning(f"Received {signal_name}, initiating graceful shutdown...")
        self._interrupted = True

    def get_state(self) -> dict[str, Any]:
        """Get current loop state for checkpointing.

        Returns:
            Dictionary containing current loop state.
        """
        return {
            "iteration": self.iteration,
            "complete": self.complete,
            "max_iterations": self.max_iterations,
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def save_checkpoint(self, path: Optional[str] = None) -> str:
        """Save current state to a checkpoint file.

        Args:
            path: Path to save checkpoint. Uses _checkpoint_path if not provided.

        Returns:
            Path where checkpoint was saved.

        Raises:
            ValueError: If no checkpoint path is available.
        """
        checkpoint_path = path or self._checkpoint_path
        if not checkpoint_path:
            raise ValueError("No checkpoint path specified")

        state = self.get_state()
        checkpoint_file = Path(checkpoint_path)
        checkpoint_file.write_text(json.dumps(state, indent=2))

        self.logger.info(f"Checkpoint saved to {checkpoint_path}")
        return str(checkpoint_path)

    def load_checkpoint(self, path: Optional[str] = None) -> dict[str, Any]:
        """Load state from a checkpoint file.

        Args:
            path: Path to load checkpoint from. Uses _checkpoint_path if not provided.

        Returns:
            Dictionary containing loaded state.

        Raises:
            ValueError: If no checkpoint path is available.
            FileNotFoundError: If checkpoint file doesn't exist.
        """
        checkpoint_path = path or self._checkpoint_path
        if not checkpoint_path:
            raise ValueError("No checkpoint path specified")

        checkpoint_file = Path(checkpoint_path)
        if not checkpoint_file.exists():
            raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_path}")

        state = json.loads(checkpoint_file.read_text())
        self.logger.info(f"Checkpoint loaded from {checkpoint_path}")
        return state

    def resume_from_checkpoint(self, path: Optional[str] = None) -> None:
        """Resume loop state from a checkpoint file.

        Args:
            path: Path to load checkpoint from. Uses _checkpoint_path if not provided.
        """
        state = self.load_checkpoint(path)
        self.iteration = state.get("iteration", 0)
        self.complete = state.get("complete", False)
        # Restore session_id if available, otherwise keep the current one
        if "session_id" in state:
            self.session_id = state["session_id"]
        self.logger.info(f"Resumed from iteration {self.iteration} (session: {self.session_id[:8]}...)")

    def _log_iteration_start(self) -> None:
        """Log the start of an iteration with timestamp and iteration number."""
        self.logger.info(
            f"Iteration {self.iteration + 1}/{self.max_iterations}: Starting..."
        )

    def _log_iteration_end(self, success: bool, message: str = "") -> None:
        """Log the end of an iteration with status.

        Args:
            success: Whether the iteration completed successfully.
            message: Optional additional message.
        """
        status = "Success" if success else "Failed"
        msg = f"Iteration {self.iteration + 1}/{self.max_iterations}: {status}"
        if message:
            msg += f" - {message}"

        if success:
            self.logger.info(msg)
        else:
            self.logger.error(msg)

    def _execute_iteration(self) -> IterationResult:
        """Execute a single iteration of the loop.

        If LLM execution is configured (PRD path and orchestrator), runs
        the Builder → Critic flow for the next task. Otherwise, returns
        a basic success result.

        Returns:
            IterationResult with execution details.
        """
        # Check if LLM execution is configured
        if not self._prd_path or not self._task_executor or not self._orchestrator:
            # Fallback to stub mode (for tests or non-LLM usage)
            return IterationResult(success=True, output=None)

        # Run async execution in sync context
        return asyncio.get_event_loop().run_until_complete(
            self._execute_iteration_async()
        )

    async def _execute_iteration_async(self) -> IterationResult:
        """Async implementation of iteration execution.

        Implements the full Builder → Critic flow:
        1. Get next task from TaskExecutor
        2. Build context (task + memory + tools)
        3. Run LLMOrchestrator.execute_iteration()
        4. Complete task if successful
        5. Return IterationResult

        Returns:
            IterationResult with execution details.
        """
        from ralph_agi.llm.orchestrator import OrchestratorStatus

        # Step 1: Get next task
        try:
            ctx = self._task_executor.begin_task(self._prd_path)
        except Exception as e:
            self.logger.error(f"Failed to get next task: {e}")
            return IterationResult(
                success=False,
                error=str(e),
            )

        # Check if all tasks are complete
        if ctx is None:
            self.logger.info("All tasks complete - no more work to do")
            return IterationResult(
                success=True,
                output=self._completion_signal,
                all_tasks_complete=True,
            )

        task = ctx.feature
        # Feature uses description as the main content (no title field)
        task_title = task.description[:50] + "..." if len(task.description) > 50 else task.description
        task_dict = {
            "id": task.id,
            "title": task_title,
            "description": task.description,
            "priority": task.priority,
            "steps": task.steps,
            "acceptance_criteria": task.acceptance_criteria,
            "dependencies": task.dependencies,
        }

        self.logger.info(f"Working on task: {task.id} - {task_title}")

        # Step 2: Build context
        project_context = self._build_project_context()
        memory_context = self._build_memory_context()

        # Step 3: Execute via orchestrator
        try:
            result = await self._orchestrator.execute_iteration(
                task=task_dict,
                tools=self._tools,
                context=project_context,
                memory_context=memory_context,
            )
        except Exception as e:
            self.logger.error(f"LLM execution failed: {e}")
            self._task_executor.abort_task(reason=str(e))
            return IterationResult(
                success=False,
                task_id=task.id,
                task_title=task.title,
                error=str(e),
            )

        # Step 4: Handle result
        if result.is_success:
            # Complete the task
            try:
                self._task_executor.complete_task(ctx)
                self.logger.info(f"Task {task.id} completed successfully")
            except Exception as e:
                self.logger.error(f"Failed to mark task complete: {e}")
                return IterationResult(
                    success=False,
                    task_id=task.id,
                    task_title=task.title,
                    files_changed=result.files_changed,
                    tokens_used=result.token_usage.total,
                    error=f"Failed to mark complete: {e}",
                )

            return IterationResult(
                success=True,
                output=f"Task completed: {task_title}",
                task_id=task.id,
                task_title=task_title,
                files_changed=result.files_changed,
                tokens_used=result.token_usage.total,
            )
        else:
            # Task failed or blocked
            reason = result.error or f"Status: {result.status.value}"
            self._task_executor.abort_task(reason=reason)

            # Check if blocked vs needs revision
            if result.status == OrchestratorStatus.BLOCKED:
                self.logger.warning(f"Task {task.id} blocked: {reason}")
            elif result.status == OrchestratorStatus.NEEDS_REVISION:
                self.logger.info(f"Task {task.id} needs revision")
            else:
                self.logger.error(f"Task {task.id} failed: {reason}")

            return IterationResult(
                success=False,
                task_id=task.id,
                task_title=task_title,
                files_changed=result.files_changed,
                tokens_used=result.token_usage.total,
                error=reason,
            )

    def _build_project_context(self) -> str:
        """Build project context string for LLM.

        Returns:
            Context string with project information.
        """
        parts = []

        # Add project info if PRD available
        if self._prd_path and self._prd_path.exists():
            parts.append(f"## Project\nWorking on PRD: {self._prd_path.name}")

            # Try to load PRD for project name
            try:
                from ralph_agi.tasks.prd import load_prd
                prd = load_prd(self._prd_path)
                # PRD has project.name field for project name
                parts.append(f"Project: {prd.project.name}")
                if prd.project.description:
                    parts.append(f"\n{prd.project.description[:500]}")
            except Exception:
                pass

        # Add working directory
        import os
        parts.append(f"\n## Working Directory\n{os.getcwd()}")

        return "\n".join(parts) if parts else ""

    def _build_memory_context(self) -> str:
        """Build memory context string from recent frames.

        Returns:
            Context string with relevant memories.
        """
        if not self._memory_store:
            return ""

        try:
            frames = self.get_context(n=5)
            if not frames:
                return ""

            parts = ["## Recent Context"]
            for frame in frames:
                content = frame.content
                if len(content) > 200:
                    content = content[:200] + "..."
                parts.append(f"- {content}")

            return "\n".join(parts)
        except Exception as e:
            self.logger.debug(f"Failed to build memory context: {e}")
            return ""

    def _check_completion(self, output: Optional[str] = None) -> bool:
        """Check if the completion signal has been received.

        Args:
            output: Optional output string to check for completion signal.

        Returns:
            True if completion signal detected, False otherwise.
        """
        if output and self._completion_signal in output:
            return True
        return False

    def _store_iteration_result(self, result: IterationResult) -> Optional[str]:
        """Store an iteration result in memory.

        Args:
            result: The IterationResult from the completed iteration.

        Returns:
            Frame ID if stored successfully, None otherwise.
        """
        if self._memory_store is None:
            return None

        try:
            content = f"Iteration {self.iteration + 1} {'completed successfully' if result.success else 'failed'}"
            if result.output:
                content += f": {result.output[:500]}"  # Truncate long outputs

            frame_id = self._memory_store.append(
                content=content,
                frame_type="iteration_result",
                metadata={
                    "iteration": self.iteration + 1,
                    "success": result.success,
                    "has_output": result.output is not None,
                },
                session_id=self.session_id,
                tags=["iteration", f"iter-{self.iteration + 1}"],
            )
            self.logger.debug(f"Stored iteration result as frame {frame_id[:8]}")
            return frame_id

        except Exception as e:
            self.logger.warning(f"Failed to store iteration result in memory: {e}")
            return None

    def get_context(self, n: int = 10) -> list[Any]:
        """Get recent context from memory for the current session.

        Args:
            n: Maximum number of frames to retrieve. Default: 10

        Returns:
            List of MemoryFrame objects, most recent first.
        """
        if self._memory_store is None:
            return []

        try:
            return self._memory_store.get_by_session(self.session_id, limit=n)
        except Exception as e:
            self.logger.warning(f"Failed to load context from memory: {e}")
            return []

    def get_recent_context(self, n: int = 10) -> list[Any]:
        """Get recent context from memory across all sessions.

        Args:
            n: Maximum number of frames to retrieve. Default: 10

        Returns:
            List of MemoryFrame objects, most recent first.
        """
        if self._memory_store is None:
            return []

        try:
            return self._memory_store.get_recent(n)
        except Exception as e:
            self.logger.warning(f"Failed to load recent context from memory: {e}")
            return []

    def _execute_with_retry(
        self,
        func: Callable[[], IterationResult],
    ) -> IterationResult:
        """Execute a function with retry logic and exponential backoff.

        Args:
            func: The function to execute. Should return IterationResult.

        Returns:
            IterationResult if function succeeded (possibly after retries).

        Raises:
            MaxRetriesExceeded: If all retry attempts are exhausted.
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                result = func()
                if result.success:
                    return result
                # Function returned failure status - treat as failure
                raise RuntimeError("Iteration returned failure status")
            except Exception as e:
                last_error = e

                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    self.logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                        f"No more retries."
                    )

        raise MaxRetriesExceeded(
            f"Failed after {self.max_retries} attempts",
            attempts=self.max_retries,
            last_error=last_error,
        )

    def run(self, handle_signals: bool = True) -> bool:
        """Run the Ralph Loop until completion or max iterations.

        The loop continues while:
        - iteration < max_iterations AND
        - complete flag is False AND
        - not interrupted

        Args:
            handle_signals: Whether to set up signal handlers for graceful
                          interrupt handling. Default: True

        Returns:
            True if completed successfully (via completion signal),
            False if exited due to max iterations.

        Raises:
            MaxRetriesExceeded: If an iteration fails after all retries.
            LoopInterrupted: If interrupted by SIGINT/SIGTERM (with checkpoint saved).
        """
        self.logger.info(
            f"Ralph Loop starting (session: {self.session_id[:8]}..., max_iterations={self.max_iterations})"
        )

        # Set up signal handlers for AFK mode
        if handle_signals:
            self._setup_signal_handlers()

        try:
            # Handle edge case of 0 max iterations
            if self.max_iterations == 0:
                self.logger.info("Max iterations is 0, exiting immediately")
                return False

            # Main loop - use WHILE (not FOR) for cleaner exit conditions
            while self.iteration < self.max_iterations and not self.complete:
                # Check for interrupt before starting iteration
                if self._interrupted:
                    self._handle_graceful_shutdown()

                self._log_iteration_start()

                try:
                    # Execute with retry logic
                    result = self._execute_with_retry(self._execute_iteration)
                    self._log_iteration_end(result.success)

                    # Store iteration result in memory (non-blocking)
                    self._store_iteration_result(result)

                    # Check for completion signal in the iteration output
                    if self._check_completion(result.output):
                        self.complete = True
                        self.logger.info(
                            f"Completion signal detected after {self.iteration + 1} iterations"
                        )
                        break

                    self.iteration += 1

                    # Check for interrupt after completing iteration
                    if self._interrupted:
                        self._handle_graceful_shutdown()

                except MaxRetriesExceeded as e:
                    self._log_iteration_end(False, str(e))
                    raise

            # Log final status
            if self.complete:
                self.logger.info(
                    f"Ralph Loop completed successfully after {self.iteration + 1} iterations"
                )
                return True
            else:
                self.logger.info(
                    f"Ralph Loop reached max iterations ({self.max_iterations})"
                )
                return False

        finally:
            # Always restore signal handlers
            if handle_signals:
                self._restore_signal_handlers()

    def _handle_graceful_shutdown(self) -> None:
        """Handle graceful shutdown on interrupt.

        Saves checkpoint if path is configured, then raises LoopInterrupted.
        """
        checkpoint_path = None
        if self._checkpoint_path:
            checkpoint_path = self.save_checkpoint()

        self.logger.info(
            f"Graceful shutdown complete at iteration {self.iteration + 1}"
        )

        raise LoopInterrupted(
            f"Loop interrupted at iteration {self.iteration + 1}",
            iteration=self.iteration,
            checkpoint_path=checkpoint_path,
        )

    def set_complete(self) -> None:
        """Manually set the completion flag.

        This can be used to signal completion from external code.
        """
        self.complete = True

    def close(self) -> None:
        """Clean up resources (logging handlers, file handles, memory store).

        Should be called when the RalphLoop instance is no longer needed,
        especially if log_file was specified.
        """
        # Close memory store
        if self._memory_store is not None:
            try:
                self._memory_store.close()
            except Exception as e:
                self.logger.warning(f"Error closing memory store: {e}")
            self._memory_store = None

        # Close logging handlers
        for handler in self._handlers:
            handler.close()
            self.logger.removeHandler(handler)
        self._handlers.clear()
