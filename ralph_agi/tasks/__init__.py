"""Task management for RALPH-AGI.

This module provides task management capabilities using PRD.json as the
single source of truth for project requirements, plus a file-based task
queue for autonomous "sip coffee" workflow.

Key Components:
- PRD: Project requirements document container
- Feature: A single feature/task definition
- Project: Project metadata
- load_prd: Load and validate PRD.json from file
- parse_prd: Parse PRD from dict
- TaskSelector: Algorithm for selecting next task
- BlockedReason: Why a task is blocked
- SelectionResult: Result of task selection
- mark_complete: Mark a feature as complete
- write_prd: Write PRD to file atomically
- TaskExecutor: Single-feature-per-iteration executor
- ExecutionContext: Context for task execution
- TaskAnalysis: Task size analysis results
- DependencyGraph: Graph-based dependency analysis
- DependencyNode: Node in the dependency graph

Task Queue (new in ADR-005):
- TaskQueue: File-based task queue for autonomous processing
- QueuedTask: Task definition with lifecycle management
- TaskStatus: Task lifecycle states (pending, running, complete, failed)
- TaskPriority: Priority levels (P0-P4)
- WorktreeManager: Git worktree isolation for parallel execution
- ActiveWorktree: Info about an active worktree
"""

from ralph_agi.tasks.executor import (
    ExecutionContext,
    TaskAnalysis,
    TaskExecutionError,
    TaskExecutor,
    analyze_task_size,
)
from ralph_agi.tasks.graph import (
    CircularDependencyError,
    DependencyError,
    DependencyGraph,
    DependencyNode,
    DependencyPath,
    MissingDependencyError,
)
from ralph_agi.tasks.prd import (
    Feature,
    PRD,
    PRDError,
    Project,
    load_prd,
    parse_prd,
)
from ralph_agi.tasks.selector import (
    BlockedReason,
    SelectionResult,
    TaskSelectionError,
    TaskSelector,
)
from ralph_agi.tasks.writer import (
    mark_complete,
    prd_to_dict,
    validate_prd_changes,
    write_prd,
)
from ralph_agi.tasks.queue import (
    TaskQueue,
    QueuedTask,
    TaskStatus,
    TaskPriority,
    QueueError,
    TaskNotFoundError,
    TaskValidationError,
    generate_task_id,
)
from ralph_agi.tasks.worktree import (
    WorktreeManager,
    ActiveWorktree,
    WorktreeError,
    WorktreeExistsError,
    WorktreeNotFoundError,
)
from ralph_agi.tasks.parallel import (
    ParallelExecutor,
    TaskResult,
    ExecutionProgress,
    ExecutionState,
    create_executor,
)
from ralph_agi.tasks.confidence import (
    ConfidenceScorer,
    ConfidenceFactors,
    ConfidenceResult,
    MergeDecision,
    AutoMerger,
    ReviewQueueItem,
    ConfigManager,
)

__all__ = [
    "PRD",
    "Project",
    "Feature",
    "PRDError",
    "load_prd",
    "parse_prd",
    "TaskSelector",
    "TaskSelectionError",
    "SelectionResult",
    "BlockedReason",
    "mark_complete",
    "write_prd",
    "prd_to_dict",
    "validate_prd_changes",
    "TaskExecutor",
    "TaskExecutionError",
    "ExecutionContext",
    "TaskAnalysis",
    "analyze_task_size",
    "DependencyGraph",
    "DependencyNode",
    "DependencyPath",
    "DependencyError",
    "CircularDependencyError",
    "MissingDependencyError",
    # Task Queue (ADR-005)
    "TaskQueue",
    "QueuedTask",
    "TaskStatus",
    "TaskPriority",
    "QueueError",
    "TaskNotFoundError",
    "TaskValidationError",
    "generate_task_id",
    # Worktree Manager (ADR-005)
    "WorktreeManager",
    "ActiveWorktree",
    "WorktreeError",
    "WorktreeExistsError",
    "WorktreeNotFoundError",
    # Parallel Executor (Story 7.3)
    "ParallelExecutor",
    "TaskResult",
    "ExecutionProgress",
    "ExecutionState",
    "create_executor",
    # Confidence & Auto-Merge (Story 7.4)
    "ConfidenceScorer",
    "ConfidenceFactors",
    "ConfidenceResult",
    "MergeDecision",
    "AutoMerger",
    "ReviewQueueItem",
    "ConfigManager",
]
