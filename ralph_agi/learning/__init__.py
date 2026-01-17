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
]
