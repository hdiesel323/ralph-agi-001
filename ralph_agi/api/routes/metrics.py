"""Metrics API routes.

Provides endpoints for real-time execution metrics including
token usage, cost estimates, and timing information.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends

from ralph_agi.api.dependencies import get_executor, get_task_queue
from ralph_agi.api.schemas import MetricsResponse
from ralph_agi.tasks.parallel import ParallelExecutor, ExecutionState
from ralph_agi.tasks.queue import TaskQueue
from ralph_agi.tui.events import emit_metrics_updated, emit_tokens_used, emit_cost_updated

router = APIRouter(prefix="/metrics", tags=["metrics"])

# In-memory metrics store (reset on server restart)
_metrics_store = {
    "iteration": 0,
    "max_iterations": 100,
    "cost": 0.0,
    "input_tokens": 0,
    "output_tokens": 0,
    "errors": 0,
    "start_time": None,
    "current_task": None,
}


def get_metrics_store() -> dict:
    """Get the metrics store singleton."""
    return _metrics_store


def reset_metrics() -> None:
    """Reset all metrics (called on execution start)."""
    global _metrics_store
    _metrics_store = {
        "iteration": 0,
        "max_iterations": 100,
        "cost": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "errors": 0,
        "start_time": datetime.now(),
        "current_task": None,
    }


def update_tokens(input_tokens: int, output_tokens: int) -> None:
    """Add token usage to metrics.

    Args:
        input_tokens: Number of input tokens used.
        output_tokens: Number of output tokens used.
    """
    _metrics_store["input_tokens"] += input_tokens
    _metrics_store["output_tokens"] += output_tokens
    # Calculate cost using Claude pricing: $3/1M input, $15/1M output
    input_cost = (input_tokens / 1_000_000) * 3.0
    output_cost = (output_tokens / 1_000_000) * 15.0
    _metrics_store["cost"] += input_cost + output_cost

    # Emit events for real-time updates
    emit_tokens_used(input_tokens, output_tokens)
    emit_cost_updated(_metrics_store["cost"])
    _emit_metrics_event()


def update_iteration(iteration: int, max_iterations: Optional[int] = None) -> None:
    """Update iteration count.

    Args:
        iteration: Current iteration number.
        max_iterations: Optional new max iterations.
    """
    _metrics_store["iteration"] = iteration
    if max_iterations is not None:
        _metrics_store["max_iterations"] = max_iterations
    _emit_metrics_event()


def update_current_task(description: Optional[str]) -> None:
    """Update the current task being worked on.

    Args:
        description: Task description or None if idle.
    """
    _metrics_store["current_task"] = description
    _emit_metrics_event()


def increment_errors() -> None:
    """Increment the error count."""
    _metrics_store["errors"] += 1
    _emit_metrics_event()


def _emit_metrics_event() -> None:
    """Emit a metrics updated event with current metrics."""
    elapsed_seconds = 0.0
    if _metrics_store["start_time"]:
        elapsed_seconds = (datetime.now() - _metrics_store["start_time"]).total_seconds()

    total_tokens = _metrics_store["input_tokens"] + _metrics_store["output_tokens"]

    emit_metrics_updated({
        "iteration": _metrics_store["iteration"],
        "max_iterations": _metrics_store["max_iterations"],
        "cost": round(_metrics_store["cost"], 4),
        "input_tokens": _metrics_store["input_tokens"],
        "output_tokens": _metrics_store["output_tokens"],
        "total_tokens": total_tokens,
        "elapsed_seconds": round(elapsed_seconds, 1),
        "elapsed_formatted": _format_elapsed(elapsed_seconds),
        "errors": _metrics_store["errors"],
        "current_task": _metrics_store["current_task"],
    })


def _format_elapsed(seconds: float) -> str:
    """Format seconds as HH:MM:SS.

    Args:
        seconds: Number of seconds.

    Returns:
        Formatted time string.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@router.get("", response_model=MetricsResponse)
async def get_metrics(
    executor: ParallelExecutor = Depends(get_executor),
    queue: TaskQueue = Depends(get_task_queue),
) -> MetricsResponse:
    """Get current execution metrics.

    Returns real-time metrics including token usage, estimated cost,
    elapsed time, and task progress.

    Returns:
        Current execution metrics.
    """
    # Calculate elapsed time
    elapsed_seconds = 0.0
    if _metrics_store["start_time"]:
        elapsed_seconds = (datetime.now() - _metrics_store["start_time"]).total_seconds()

    # Get queue stats for task counts
    stats = queue.stats()

    # Get running task info from executor
    status = executor.get_status()
    running_tasks = status.get("running_tasks", [])

    # Determine current task description
    current_task = _metrics_store["current_task"]
    if not current_task and running_tasks:
        # Try to get description of first running task
        for task in queue.list():
            if task.id in running_tasks:
                current_task = task.description[:50] + "..." if len(task.description) > 50 else task.description
                break

    total_tokens = _metrics_store["input_tokens"] + _metrics_store["output_tokens"]

    return MetricsResponse(
        iteration=_metrics_store["iteration"],
        max_iterations=_metrics_store["max_iterations"],
        cost=round(_metrics_store["cost"], 4),
        input_tokens=_metrics_store["input_tokens"],
        output_tokens=_metrics_store["output_tokens"],
        total_tokens=total_tokens,
        elapsed_seconds=round(elapsed_seconds, 1),
        elapsed_formatted=_format_elapsed(elapsed_seconds),
        errors=_metrics_store["errors"],
        tasks_completed=stats.get("complete", 0),
        tasks_running=stats.get("running", 0),
        current_task=current_task,
    )


@router.post("/reset", response_model=dict)
async def reset_metrics_endpoint() -> dict:
    """Reset all metrics to zero.

    Typically called when starting a new execution session.

    Returns:
        Status confirmation.
    """
    reset_metrics()
    return {"status": "reset", "message": "Metrics have been reset"}


@router.post("/tokens", response_model=MetricsResponse)
async def add_tokens(
    input_tokens: int = 0,
    output_tokens: int = 0,
    executor: ParallelExecutor = Depends(get_executor),
    queue: TaskQueue = Depends(get_task_queue),
) -> MetricsResponse:
    """Add token usage to metrics.

    This endpoint is called by the execution system to report
    token usage after each LLM call.

    Args:
        input_tokens: Number of input tokens to add.
        output_tokens: Number of output tokens to add.

    Returns:
        Updated metrics.
    """
    update_tokens(input_tokens, output_tokens)
    return await get_metrics(executor, queue)
