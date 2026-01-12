"""Memory system for RALPH-AGI.

This module provides persistent memory capabilities using Memvid as the
storage backend with JSONL fallback for crash resilience. Memory is organized
into frames that can be searched semantically or by keyword.

Key Components:
- MemoryStore: Main interface for storing and retrieving memory frames
- MemoryFrame: A unit of memory with content, metadata, and timestamps
- MemoryQueryResult: Result wrapper with query metadata and token counts
- JSONLBackupStore: Crash-safe JSONL backup for memory frames
- GitMemory: Git integration for medium-term memory
- GitCommit: Structured git commit data
- KnowledgeStore: Long-term knowledge management
- Observation: Structured observation for long-term memory
- ObservationType: Categories of observations
- ContextCompactor: Automatic context compaction
- CompactionConfig: Configuration for compaction
- LifecycleHooks: Automatic memory capture at key execution points
- HookConfig: Configuration for lifecycle hooks
"""

from ralph_agi.memory.compaction import (
    CompactionConfig,
    CompactionResult,
    CompactionTier,
    ContextCompactor,
    ImportanceLevel,
    create_llm_summarizer,
)
from ralph_agi.memory.git import GitCommit, GitError, GitMemory
from ralph_agi.memory.hooks import (
    HookConfig,
    HookContext,
    HookEvent,
    HookResult,
    LifecycleHooks,
)
from ralph_agi.memory.knowledge import (
    KnowledgeStore,
    Observation,
    ObservationType,
    TemporalQuery,
)
from ralph_agi.memory.jsonl_backup import JSONLBackupStore
from ralph_agi.memory.store import MemoryFrame, MemoryQueryResult, MemoryStore

__all__ = [
    "MemoryStore",
    "MemoryFrame",
    "MemoryQueryResult",
    "JSONLBackupStore",
    "GitMemory",
    "GitCommit",
    "GitError",
    "KnowledgeStore",
    "Observation",
    "ObservationType",
    "TemporalQuery",
    "ContextCompactor",
    "CompactionConfig",
    "CompactionResult",
    "CompactionTier",
    "ImportanceLevel",
    "create_llm_summarizer",
    "LifecycleHooks",
    "HookConfig",
    "HookContext",
    "HookEvent",
    "HookResult",
]
