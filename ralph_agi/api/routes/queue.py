"""Queue management API routes.

Provides endpoints for queue statistics and next task selection.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from ralph_agi.api.dependencies import get_task_queue
from ralph_agi.api.schemas import (
    TaskResponse,
    QueueStatsResponse,
    task_to_response,
)
from ralph_agi.tasks.queue import TaskQueue

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("/stats", response_model=QueueStatsResponse)
async def get_queue_stats(
    queue: TaskQueue = Depends(get_task_queue),
) -> QueueStatsResponse:
    """Get queue statistics.

    Returns:
        Statistics about the task queue including counts by status.
    """
    stats = queue.stats()

    return QueueStatsResponse(
        total=stats.get("total", 0),
        pending=stats.get("pending", 0),
        pending_approval=stats.get("pending_approval", 0),
        ready=stats.get("ready", 0),
        running=stats.get("running", 0),
        pending_merge=stats.get("pending_merge", 0),
        complete=stats.get("complete", 0),
        failed=stats.get("failed", 0),
        cancelled=stats.get("cancelled", 0),
    )


@router.get("/next", response_model=Optional[TaskResponse])
async def get_next_task(
    queue: TaskQueue = Depends(get_task_queue),
) -> Optional[TaskResponse]:
    """Get the next task to process.

    Returns the highest priority pending task whose dependencies
    are all complete.

    Returns:
        The next task to process, or null if queue is empty.
    """
    task = queue.next()

    if task is None:
        return None

    return task_to_response(task)


@router.post("/clear", response_model=dict)
async def clear_queue(
    include_running: bool = False,
    queue: TaskQueue = Depends(get_task_queue),
) -> dict:
    """Clear completed/failed tasks from the queue.

    Args:
        include_running: Also clear running tasks.

    Returns:
        Number of tasks removed.
    """
    removed = queue.clear(include_running=include_running)

    return {"removed": removed}
