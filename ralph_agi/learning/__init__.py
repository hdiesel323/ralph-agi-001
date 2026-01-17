"""Learning system for RALPH-AGI.

Implements the four-layer contextual learning framework:
- Layer 1: Codebase patterns (patterns.py)
- Layer 2: Progress entries (progress.py)
- Layer 3: Git history (history.py)
- Layer 4: Conversation logs (logs.py)
"""

from ralph_agi.learning.patterns import (
    CodebasePattern,
    CodebasePatterns,
    PatternCategory,
    load_patterns,
    save_patterns,
    get_patterns_path,
    analyze_codebase,
    inject_patterns,
)

from ralph_agi.learning.progress import (
    Outcome,
    ProgressEntry,
    ProgressStore,
    load_progress,
    save_progress,
    get_progress_path,
    generate_session_id,
    inject_progress,
)

from ralph_agi.learning.history import (
    CommitInfo,
    CommitDiff,
    FileDiff,
    GitHistory,
    inject_git_history,
)

from ralph_agi.learning.logs import (
    MessageRole,
    ToolCall,
    ConversationMessage,
    ConversationLog,
    get_logs_path,
    save_message,
    load_log,
    load_recent_logs,
    compress_old_logs,
    extract_patterns,
    inject_conversation_context,
)

__all__ = [
    # Layer 1: Patterns
    "CodebasePattern",
    "CodebasePatterns",
    "PatternCategory",
    "load_patterns",
    "save_patterns",
    "get_patterns_path",
    "analyze_codebase",
    "inject_patterns",
    # Layer 2: Progress
    "Outcome",
    "ProgressEntry",
    "ProgressStore",
    "load_progress",
    "save_progress",
    "get_progress_path",
    "generate_session_id",
    "inject_progress",
    # Layer 3: Git History
    "CommitInfo",
    "CommitDiff",
    "FileDiff",
    "GitHistory",
    "inject_git_history",
    # Layer 4: Conversation Logs
    "MessageRole",
    "ToolCall",
    "ConversationMessage",
    "ConversationLog",
    "get_logs_path",
    "save_message",
    "load_log",
    "load_recent_logs",
    "compress_old_logs",
    "extract_patterns",
    "inject_conversation_context",
]
