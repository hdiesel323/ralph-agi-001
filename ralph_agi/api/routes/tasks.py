"""Task CRUD API routes.

Provides endpoints for creating, reading, updating, and deleting tasks.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ralph_agi.api.dependencies import get_task_queue
from ralph_agi.api.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    TaskStatus,
    TaskPriority,
    task_to_response,
)
from ralph_agi.tasks.queue import (
    TaskQueue,
    TaskNotFoundError,
    TaskValidationError,
    TaskPriority as QueuePriority,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    include_terminal: bool = Query(False, description="Include completed/failed tasks"),
    queue: TaskQueue = Depends(get_task_queue),
) -> TaskListResponse:
    """List all tasks with optional filtering.

    Args:
        status: Filter by task status.
        priority: Filter by task priority.
        include_terminal: Include completed/failed/cancelled tasks.
        queue: TaskQueue dependency.

    Returns:
        List of tasks matching the filters.
    """
    # Convert API status to queue status
    status_filter = status.value if status else None
    priority_filter = None
    if priority:
        priority_filter = QueuePriority.from_string(priority.value)

    tasks = queue.list(
        status=status_filter,
        priority=priority_filter,
        include_terminal=include_terminal or (status in [TaskStatus.COMPLETE, TaskStatus.FAILED, TaskStatus.CANCELLED]),
    )

    return TaskListResponse(
        tasks=[task_to_response(t) for t in tasks],
        total=len(tasks),
    )


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    task_data: TaskCreate,
    queue: TaskQueue = Depends(get_task_queue),
) -> TaskResponse:
    """Create a new task.

    Args:
        task_data: Task creation data.
        queue: TaskQueue dependency.

    Returns:
        The created task.

    Raises:
        HTTPException: If task creation fails.
    """
    try:
        task = queue.add(
            description=task_data.description,
            priority=task_data.priority.value,
            acceptance_criteria=task_data.acceptance_criteria,
            dependencies=task_data.dependencies,
            metadata=task_data.metadata,
        )
        return task_to_response(task)

    except TaskValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {e}")


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    queue: TaskQueue = Depends(get_task_queue),
) -> TaskResponse:
    """Get a task by ID.

    Args:
        task_id: Task identifier.
        queue: TaskQueue dependency.

    Returns:
        The requested task.

    Raises:
        HTTPException: If task not found.
    """
    try:
        task = queue.get(task_id)
        return task_to_response(task)

    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task: {e}")


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    queue: TaskQueue = Depends(get_task_queue),
) -> TaskResponse:
    """Update a task.

    Only provided fields will be updated.

    Args:
        task_id: Task identifier.
        task_data: Fields to update.
        queue: TaskQueue dependency.

    Returns:
        The updated task.

    Raises:
        HTTPException: If task not found or update fails.
    """
    try:
        # First get the existing task
        task = queue.get(task_id)

        # If status is being changed, use update_status
        if task_data.status is not None:
            task = queue.update_status(
                task_id,
                task_data.status.value,
                worktree_path=task_data.worktree_path,
                branch=task_data.branch,
                pr_url=task_data.pr_url,
                pr_number=task_data.pr_number,
                confidence=task_data.confidence,
                error=task_data.error,
            )
        else:
            # For non-status updates, we need to modify the task directly
            # First update any provided fields
            if task_data.description is not None:
                task.description = task_data.description
            if task_data.priority is not None:
                task.priority = QueuePriority.from_string(task_data.priority.value)
            if task_data.acceptance_criteria is not None:
                task.acceptance_criteria = task_data.acceptance_criteria
            if task_data.dependencies is not None:
                task.dependencies = task_data.dependencies
            if task_data.worktree_path is not None:
                task.worktree_path = task_data.worktree_path
            if task_data.branch is not None:
                task.branch = task_data.branch
            if task_data.pr_url is not None:
                task.pr_url = task_data.pr_url
            if task_data.pr_number is not None:
                task.pr_number = task_data.pr_number
            if task_data.confidence is not None:
                task.confidence = task_data.confidence
            if task_data.error is not None:
                task.error = task_data.error
            if task_data.metadata is not None:
                task.metadata.update(task_data.metadata)

            # Save the updated task
            queue._save_task(task)

        return task_to_response(task)

    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    except TaskValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task: {e}")


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    queue: TaskQueue = Depends(get_task_queue),
) -> None:
    """Delete a task.

    Args:
        task_id: Task identifier.
        queue: TaskQueue dependency.

    Raises:
        HTTPException: If task not found.
    """
    if not queue.remove(task_id):
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")


@router.post("/{task_id}/approve", response_model=TaskResponse)
async def approve_task(
    task_id: str,
    queue: TaskQueue = Depends(get_task_queue),
) -> TaskResponse:
    """Approve a task for execution.

    Transitions task from pending_approval → ready.

    Args:
        task_id: Task identifier.
        queue: TaskQueue dependency.

    Returns:
        The updated task.

    Raises:
        HTTPException: If task not found or not in pending_approval status.
    """
    try:
        task = queue.get(task_id)

        # Check current status
        if task.status.value not in ("pending", "pending_approval"):
            raise HTTPException(
                status_code=400,
                detail=f"Task cannot be approved: current status is {task.status.value}",
            )

        # Transition to ready
        task = queue.update_status(task_id, "ready")
        return task_to_response(task)

    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve task: {e}")


@router.post("/{task_id}/approve-merge", response_model=TaskResponse)
async def approve_merge(
    task_id: str,
    queue: TaskQueue = Depends(get_task_queue),
) -> TaskResponse:
    """Approve a PR for merge.

    Transitions task from pending_merge → complete.

    Args:
        task_id: Task identifier.
        queue: TaskQueue dependency.

    Returns:
        The updated task.

    Raises:
        HTTPException: If task not found or not in pending_merge status.
    """
    try:
        task = queue.get(task_id)

        # Check current status
        if task.status.value != "pending_merge":
            raise HTTPException(
                status_code=400,
                detail=f"Task cannot be merged: current status is {task.status.value}",
            )

        # Transition to complete
        task = queue.update_status(task_id, "complete")
        return task_to_response(task)

    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve merge: {e}")


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: str,
    queue: TaskQueue = Depends(get_task_queue),
) -> TaskResponse:
    """Cancel a task.

    Can cancel tasks in pending, pending_approval, ready, or running status.
    Running tasks will be marked as cancelled but may continue until the
    executor detects the cancellation.

    Args:
        task_id: Task identifier.
        queue: TaskQueue dependency.

    Returns:
        The updated task.

    Raises:
        HTTPException: If task not found or cannot be cancelled.
    """
    try:
        task = queue.get(task_id)

        # Check if task can be cancelled
        cancellable_statuses = ("pending", "pending_approval", "ready", "running")
        if task.status.value not in cancellable_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Task cannot be cancelled: current status is {task.status.value}",
            )

        # Transition to cancelled
        task = queue.update_status(task_id, "cancelled", error="Cancelled by user")
        return task_to_response(task)

    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {e}")
