"""Dependency injection for FastAPI endpoints.

Provides singletons for TaskQueue and ParallelExecutor that are
shared across all endpoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ralph_agi.tasks.queue import TaskQueue
from ralph_agi.tasks.parallel import ParallelExecutor


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


def get_executor() -> ParallelExecutor:
    """Get the singleton ParallelExecutor instance.

    Returns:
        ParallelExecutor instance for the current project.
    """
    global _executor
    if _executor is None:
        _executor = ParallelExecutor(project_root=get_project_root())
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
