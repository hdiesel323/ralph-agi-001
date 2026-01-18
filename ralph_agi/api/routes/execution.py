"""Execution control API routes.

Provides endpoints for starting, stopping, and monitoring parallel execution.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from ralph_agi.api.dependencies import get_executor, get_task_queue
from ralph_agi.api.schemas import (
    ExecutionStart,
    ExecutionState,
    ExecutionStatusResponse,
    ExecutionProgressResponse,
    ExecutionResultsResponse,
    QueueStatsResponse,
    TaskResultResponse,
    result_to_response,
)
from ralph_agi.tasks.parallel import (
    ParallelExecutor,
    ExecutionState as ExecState,
)
from ralph_agi.tasks.queue import TaskQueue

router = APIRouter(prefix="/execution", tags=["execution"])

# Store for execution results (in memory, cleared on restart)
_execution_results: list = []


@router.get("/status", response_model=ExecutionStatusResponse)
async def get_execution_status(
    executor: ParallelExecutor = Depends(get_executor),
) -> ExecutionStatusResponse:
    """Get current execution status.

    Returns:
        Current state of the parallel executor.
    """
    status = executor.get_status()
    progress = status["progress"]
    queue_stats = status["queue_stats"]

    return ExecutionStatusResponse(
        state=ExecutionState(status["state"]),
        max_concurrent=status["max_concurrent"],
        progress=ExecutionProgressResponse(
            total_tasks=progress["total_tasks"],
            completed=progress["completed"],
            failed=progress["failed"],
            running=progress["running"],
            pending=progress["pending"],
            success_rate=progress["success_rate"],
        ),
        running_tasks=status["running_tasks"],
        queue_stats=QueueStatsResponse(
            total=queue_stats.get("total", 0),
            pending=queue_stats.get("pending", 0),
            ready=queue_stats.get("ready", 0),
            running=queue_stats.get("running", 0),
            complete=queue_stats.get("complete", 0),
            failed=queue_stats.get("failed", 0),
            cancelled=queue_stats.get("cancelled", 0),
        ),
    )


@router.post("/start", response_model=dict)
async def start_execution(
    request: ExecutionStart,
    background_tasks: BackgroundTasks,
    executor: ParallelExecutor = Depends(get_executor),
) -> dict:
    """Start parallel task execution.

    Args:
        request: Execution configuration.
        background_tasks: FastAPI background tasks.
        executor: ParallelExecutor dependency.

    Returns:
        Status message.

    Raises:
        HTTPException: If executor is already running.
    """
    global _execution_results

    if executor.state == ExecState.RUNNING:
        raise HTTPException(
            status_code=409,
            detail="Executor is already running",
        )

    # Update max concurrent
    executor.max_concurrent = request.max_concurrent

    # Clear previous results
    _execution_results = []

    # Store results callback
    def on_complete(result):
        _execution_results.append(result)

    # Set callback
    executor._on_task_complete = on_complete

    # Start execution in background
    async def run_executor():
        try:
            await executor.run(max_tasks=request.max_tasks)
        except Exception as e:
            # Log error but don't crash
            import logging
            logging.getLogger(__name__).error(f"Execution error: {e}", exc_info=True)

    # Schedule the async task - using create_task to run it in the event loop
    asyncio.create_task(run_executor())

    return {
        "status": "started",
        "max_concurrent": request.max_concurrent,
        "max_tasks": request.max_tasks,
    }


@router.post("/stop", response_model=dict)
async def stop_execution(
    wait: bool = True,
    executor: ParallelExecutor = Depends(get_executor),
) -> dict:
    """Stop parallel task execution.

    Args:
        wait: Wait for running tasks to complete.
        executor: ParallelExecutor dependency.

    Returns:
        Status message.
    """
    if executor.state != ExecState.RUNNING:
        return {"status": "not_running"}

    executor.stop(wait=wait)

    return {"status": "stopped"}


@router.get("/results", response_model=ExecutionResultsResponse)
async def get_execution_results() -> ExecutionResultsResponse:
    """Get results from the last execution.

    Returns:
        List of task results from the last execution run.
    """
    global _execution_results

    results = [result_to_response(r) for r in _execution_results]
    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    return ExecutionResultsResponse(
        results=results,
        total=len(results),
        succeeded=succeeded,
        failed=failed,
    )


@router.post("/cleanup", response_model=dict)
async def cleanup_worktrees(
    force: bool = False,
    executor: ParallelExecutor = Depends(get_executor),
) -> dict:
    """Clean up all worktrees.

    Args:
        force: Force cleanup even with uncommitted changes.
        executor: ParallelExecutor dependency.

    Returns:
        Number of worktrees cleaned up.
    """
    cleaned = executor.cleanup(force=force)

    return {"cleaned": cleaned}
