"""Task management for RALPH-AGI.

This module provides task management capabilities using PRD.json as the
single source of truth for project requirements.

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
]
