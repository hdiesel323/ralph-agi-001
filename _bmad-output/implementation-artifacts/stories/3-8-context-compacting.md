# Story 3.8: Context Compacting

Status: completed
Completed: 2026-01-11

## Story

As a **developer**,
I want **automatic summarization of older context frames**,
so that **context windows don't overflow during long-running tasks**.

## Acceptance Criteria

1. **AC1:** Compaction threshold configuration in config.yaml
   - `CompactionConfig` dataclass with all settings
   - threshold_frames: trigger compaction at N frames
   - recent_count: frames to keep at full detail

2. **AC2:** LLM-based summarization of older frames (use Haiku)
   - `Summarizer` protocol for custom summarizers
   - `create_llm_summarizer()` factory function
   - Default fallback summarizer for testing

3. **AC3:** Archive original frames (don't delete)
   - Summary frames include original_ids metadata
   - Compacted frames marked with `compacted: true`
   - Original token count preserved

4. **AC4:** Preserve full detail for errors and decisions
   - `PRESERVE_TYPES`: error, decision, git_commit
   - `should_preserve()` checks type and importance
   - Config options: preserve_errors, preserve_decisions

5. **AC5:** Integration with Story 3.6 Memory Query API
   - Summary frames returned in queries
   - Token estimation for compaction decisions
   - Dry-run mode for estimation

6. **AC6:** Token usage tracking before/after compaction
   - `CompactionResult` with tokens_before, tokens_after
   - `reduction_percentage` computed property
   - Benchmark: 50%+ token reduction on long sessions

## Tasks / Subtasks

- [x] Task 1: Create CompactionConfig (AC: 1)
  - [x] enabled, threshold_frames, recent_count, medium_count
  - [x] preserve_errors, preserve_decisions
  - [x] summary_model, max_summary_tokens

- [x] Task 2: Create tier and importance system (AC: 4)
  - [x] CompactionTier: RECENT, MEDIUM, OLD
  - [x] ImportanceLevel: CRITICAL, HIGH, MEDIUM, LOW
  - [x] PRESERVE_TYPES and COMPACTABLE_TYPES sets

- [x] Task 3: Implement ContextCompactor (AC: 2, 3, 5)
  - [x] `get_importance()` and `should_preserve()`
  - [x] `get_tier()` based on frame position
  - [x] `group_frames()` by compaction tier
  - [x] `compact_group()` with summarization

- [x] Task 4: Implement compaction operations (AC: 5, 6)
  - [x] `needs_compaction()` checks threshold
  - [x] `compact()` runs full compaction
  - [x] `estimate_compaction()` dry-run mode
  - [x] Token tracking and reduction calculation

- [x] Task 5: Write unit tests (AC: all)
  - [x] Create `tests/memory/test_compaction.py`
  - [x] Test CompactionConfig and tiers
  - [x] Test importance and preservation
  - [x] Test grouping and compaction
  - [x] Test token reduction
  - [x] 52 tests passing

## Dev Notes

### CompactionConfig

```python
@dataclass
class CompactionConfig:
    enabled: bool = True
    threshold_frames: int = 50
    recent_count: int = 10
    medium_count: int = 20
    preserve_errors: bool = True
    preserve_decisions: bool = True
    summary_model: str = "haiku"
    max_summary_tokens: int = 500
```

### Compaction Tiers

```
Frames:     [old...][medium...][recent...]
Position:   0       medium_start recent_start
Compaction: Heavy   Moderate    None
```

### ContextCompactor API

```python
compactor = ContextCompactor(memory_store, config)

# Check if needed
if compactor.needs_compaction():
    # Run compaction
    result = compactor.compact()
    print(f"Reduced tokens by {result.reduction_percentage:.1f}%")

# Dry-run estimation
estimate = compactor.estimate_compaction()
print(f"Would reduce {estimate.tokens_before} to {estimate.tokens_after}")
```

### Preservation Rules

- **CRITICAL (never compact):** error, decision, git_commit
- **HIGH (minimal compaction):** learning, preference
- **MEDIUM (normal compaction):** success
- **LOW (aggressive compaction):** iteration_result, context

### File List

**Created:**
- `ralph_agi/memory/compaction.py` - ContextCompactor, CompactionConfig, etc.
- `tests/memory/test_compaction.py` - 52 unit tests

**Modified:**
- `ralph_agi/memory/__init__.py` - Export ContextCompactor, CompactionConfig, etc.
