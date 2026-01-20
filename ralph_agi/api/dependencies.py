"""Dependency injection for FastAPI endpoints.

Provides singletons for TaskQueue and ParallelExecutor that are
shared across all endpoints.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ralph_agi.tasks.queue import (
    TaskQueue,
    QueuedTask,
    TaskOutput,
    TaskArtifact,
    ExecutionLog,
)
from ralph_agi.tasks.parallel import ParallelExecutor, TaskResult

logger = logging.getLogger(__name__)

# Singleton instances
_task_queue: Optional[TaskQueue] = None
_executor: Optional[ParallelExecutor] = None
_project_root: Optional[Path] = None


def set_project_root(root: Path | str) -> None:
    """Set the project root for all dependencies.

    Must be called before get_task_queue or get_executor.

    Args:
        root: Path to the project root directory.
    """
    global _project_root, _task_queue, _executor
    _project_root = Path(root).resolve()
    # Reset singletons when root changes
    _task_queue = None
    _executor = None


def get_project_root() -> Path:
    """Get the current project root.

    Returns:
        Project root path (defaults to cwd if not set).
    """
    return _project_root or Path.cwd()


def get_task_queue() -> TaskQueue:
    """Get the singleton TaskQueue instance.

    Returns:
        TaskQueue instance for the current project.
    """
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue(project_root=get_project_root())
    return _task_queue


def _create_task_callback():
    """Create a task callback that runs the Builder agent.

    Returns:
        Callback function for task execution.
    """

    def execute_task_with_agent(task: QueuedTask, worktree_path: Path) -> TaskResult:
        """Execute a task using the Builder agent and capture output.

        Args:
            task: The task to execute
            worktree_path: Path to the worktree for this task

        Returns:
            TaskResult with execution output
        """
        started_at = datetime.now(timezone.utc)
        logs: list[ExecutionLog] = []
        artifacts: list[TaskArtifact] = []

        def log(level: str, message: str):
            logs.append(ExecutionLog(
                timestamp=datetime.now(timezone.utc).isoformat(),
                level=level,
                message=message,
            ))
            logger.info(f"[{task.id}] {level.upper()}: {message}")

        log("info", f"Starting task execution in {worktree_path}")

        try:
            # Get files before execution for change tracking
            files_before = _get_project_files(worktree_path)

            # Import here to avoid circular imports
            from ralph_agi.core.config import RalphConfig
            from ralph_agi.llm.agents import BuilderAgent
            from ralph_agi.core.loop import ToolExecutorAdapter, RalphLoop

            # Load config
            config = RalphConfig.load()

            # Create tool executor for the worktree
            tool_executor = ToolExecutorAdapter(work_dir=worktree_path)

            # Create LLM client
            client = RalphLoop._create_llm_client(
                provider=config.llm_builder_provider,
                model=config.llm_builder_model,
            )

            # Create Builder agent
            builder = BuilderAgent(
                client=client,
                tool_executor=tool_executor,
                max_iterations=config.llm_max_tool_iterations,
                max_tokens=config.llm_max_tokens,
            )

            # Build task dict for agent
            task_dict = {
                "id": task.id,
                "title": task.description[:50],
                "description": task.description,
                "acceptance_criteria": task.acceptance_criteria,
            }

            # Build tool schemas
            tools = RalphLoop._build_tool_schemas()

            log("info", "Running Builder agent...")

            # Run the agent (need to run async in sync context)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    builder.execute(task_dict, tools=tools)
                )
            finally:
                loop.close()

            log("info", f"Builder completed with status: {result.status.value}")

            # Get files after execution
            files_after = _get_project_files(worktree_path)
            new_files = files_after - files_before
            modified_files = set(result.files_changed) if result.files_changed else set()
            all_changed = new_files | modified_files

            # Track artifacts
            for file_path in all_changed:
                artifact = _create_artifact(worktree_path, file_path)
                if artifact:
                    artifacts.append(artifact)
                    log("info", f"Created/modified: {file_path}")

            # Convert tool calls to logs
            for tc in result.tool_calls:
                log(
                    "info" if tc.success else "error",
                    f"Tool {tc.tool_name}: {tc.result[:200] if tc.result else 'OK'}{'...' if tc.result and len(tc.result) > 200 else ''}"
                )

            completed_at = datetime.now(timezone.utc)

            # Build output
            output = TaskOutput(
                summary=f"Task completed with {len(artifacts)} file(s) changed. Status: {result.status.value}",
                text=result.final_response,
                markdown=result.final_response if "```" in result.final_response or "#" in result.final_response else None,
                artifacts=artifacts,
                logs=logs,
                tokens_used=result.total_tokens,
                api_calls=result.iterations,
            )

            success = result.is_complete
            error = result.error if not success else None

            if not success and not error:
                error = f"Task ended with status: {result.status.value}"

            return TaskResult(
                task_id=task.id,
                success=success,
                worktree_path=worktree_path,
                branch=None,  # Will be set by worktree manager
                started_at=started_at,
                completed_at=completed_at,
                error=error,
                confidence=0.8 if success else 0.3,
                output=output,
            )

        except Exception as e:
            log("error", f"Task execution failed: {str(e)}")
            completed_at = datetime.now(timezone.utc)

            output = TaskOutput(
                summary=f"Task failed: {str(e)}",
                text=str(e),
                artifacts=artifacts,
                logs=logs,
            )

            return TaskResult(
                task_id=task.id,
                success=False,
                worktree_path=worktree_path,
                started_at=started_at,
                completed_at=completed_at,
                error=str(e),
                confidence=0.0,
                output=output,
            )

    return execute_task_with_agent


def _get_project_files(root: Path) -> set[str]:
    """Get set of all project files (excluding common ignored dirs).

    Args:
        root: Root directory to scan

    Returns:
        Set of relative file paths
    """
    exclude_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", ".ralph", "dist", "build"}
    files = set()

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip excluded directories
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(dirpath, filename), root)
            files.add(rel_path)

    return files


def _create_artifact(root: Path, rel_path: str) -> Optional[TaskArtifact]:
    """Create a TaskArtifact from a file path.

    Args:
        root: Root directory
        rel_path: Relative path to file

    Returns:
        TaskArtifact or None if file doesn't exist
    """
    abs_path = root / rel_path
    if not abs_path.exists():
        return None

    try:
        size = abs_path.stat().st_size
        file_type = abs_path.suffix.lstrip(".") if abs_path.suffix else None

        # Read content for small text files
        content = None
        if size < 100_000:  # 100KB limit
            try:
                content = abs_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                pass  # Binary or unreadable

        return TaskArtifact(
            path=rel_path,
            absolute_path=str(abs_path),
            file_type=file_type,
            size=size,
            content=content,
        )
    except Exception:
        return None


def get_executor() -> ParallelExecutor:
    """Get the singleton ParallelExecutor instance.

    Returns:
        ParallelExecutor instance for the current project.
    """
    global _executor
    if _executor is None:
        _executor = ParallelExecutor(
            project_root=get_project_root(),
            task_callback=_create_task_callback(),
        )
    return _executor


def reset_dependencies() -> None:
    """Reset all singleton instances.

    Useful for testing or when changing project root.
    """
    global _task_queue, _executor, _project_root
    if _executor:
        try:
            _executor.stop(wait=False)
        except Exception:
            pass
    _task_queue = None
    _executor = None
    _project_root = None
