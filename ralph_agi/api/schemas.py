"""Pydantic schemas for API request/response models.

These schemas mirror the dataclasses in ralph_agi.tasks but are optimized
for JSON serialization and API validation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task lifecycle status."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class ExecutionState(str, Enum):
    """State of the parallel executor."""

    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


# Request schemas


class TaskCreate(BaseModel):
    """Request body for creating a new task."""

    description: str = Field(..., min_length=1, description="Task description")
    priority: TaskPriority = Field(TaskPriority.P2, description="Task priority")
    acceptance_criteria: list[str] = Field(
        default_factory=list, description="List of acceptance criteria"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="List of task IDs this task depends on"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class TaskUpdate(BaseModel):
    """Request body for updating a task."""

    description: Optional[str] = Field(None, min_length=1)
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    acceptance_criteria: Optional[list[str]] = None
    dependencies: Optional[list[str]] = None
    worktree_path: Optional[str] = None
    branch: Optional[str] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    error: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class ExecutionStart(BaseModel):
    """Request body for starting execution."""

    max_concurrent: int = Field(3, ge=1, le=10, description="Max concurrent tasks")
    max_tasks: Optional[int] = Field(None, ge=1, description="Max tasks to process")


# Response schemas


class TaskResponse(BaseModel):
    """Response model for a single task."""

    id: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    acceptance_criteria: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worktree_path: Optional[str] = None
    branch: Optional[str] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    confidence: Optional[float] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Response model for task list."""

    tasks: list[TaskResponse]
    total: int


class QueueStatsResponse(BaseModel):
    """Response model for queue statistics."""

    total: int
    pending: int
    ready: int
    running: int
    complete: int
    failed: int
    cancelled: int


class ExecutionProgressResponse(BaseModel):
    """Response model for execution progress."""

    total_tasks: int
    completed: int
    failed: int
    running: int
    pending: int
    success_rate: str


class ExecutionStatusResponse(BaseModel):
    """Response model for execution status."""

    state: ExecutionState
    max_concurrent: int
    progress: ExecutionProgressResponse
    running_tasks: list[str]
    queue_stats: QueueStatsResponse


class TaskResultResponse(BaseModel):
    """Response model for a task execution result."""

    task_id: str
    success: bool
    worktree_path: Optional[str] = None
    branch: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    pr_url: Optional[str] = None
    confidence: float = 0.0


class ExecutionResultsResponse(BaseModel):
    """Response model for execution results."""

    results: list[TaskResultResponse]
    total: int
    succeeded: int
    failed: int


# WebSocket event schemas


class WebSocketEvent(BaseModel):
    """WebSocket event message."""

    type: str
    timestamp: datetime = Field(default_factory=datetime.now)
    data: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str
    code: Optional[str] = None


# Conversion helpers


def task_to_response(task) -> TaskResponse:
    """Convert a QueuedTask to TaskResponse."""
    from ralph_agi.tasks.queue import QueuedTask

    if isinstance(task, QueuedTask):
        return TaskResponse(
            id=task.id,
            description=task.description,
            priority=TaskPriority(f"P{task.priority.value}"),
            status=TaskStatus(task.status.value),
            acceptance_criteria=task.acceptance_criteria,
            dependencies=task.dependencies,
            created_at=task.created_at,
            updated_at=task.updated_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            worktree_path=task.worktree_path,
            branch=task.branch,
            pr_url=task.pr_url,
            pr_number=task.pr_number,
            confidence=task.confidence,
            error=task.error,
            metadata=task.metadata,
        )
    raise ValueError(f"Cannot convert {type(task)} to TaskResponse")


def result_to_response(result) -> TaskResultResponse:
    """Convert a TaskResult to TaskResultResponse."""
    from ralph_agi.tasks.parallel import TaskResult

    if isinstance(result, TaskResult):
        return TaskResultResponse(
            task_id=result.task_id,
            success=result.success,
            worktree_path=str(result.worktree_path) if result.worktree_path else None,
            branch=result.branch,
            started_at=result.started_at,
            completed_at=result.completed_at,
            duration_seconds=result.duration_seconds,
            error=result.error,
            pr_url=result.pr_url,
            confidence=result.confidence,
        )
    raise ValueError(f"Cannot convert {type(result)} to TaskResultResponse")
