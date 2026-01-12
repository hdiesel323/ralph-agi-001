# Story 3.6: Memory Query API

Status: completed
Completed: 2026-01-11

## Story

As a **developer**,
I want **a unified API for all memory queries**,
so that **the loop can easily load context**.

## Acceptance Criteria

1. **AC1:** `memory.search(query, type, limit)` unified API
   - Single entry point for all memory queries
   - Supports all search modes (keyword, semantic, hybrid)

2. **AC2:** Filter by: session, type, date range, tags
   - Session filtering already exists
   - Add date range filtering (start_date, end_date)
   - Add tag filtering (match any/all tags)

3. **AC3:** Combine vector + keyword results
   - Already implemented in search_hybrid
   - Expose through unified API

4. **AC4:** Return structured MemoryResult objects
   - Wrapper with query metadata
   - Include total count, timing, search mode used

5. **AC5:** Context window management (token limits)
   - Estimate token count per frame
   - Truncate results to fit token budget
   - Return whether results were truncated

## Tasks / Subtasks

- [x] Task 1: Create MemoryQueryResult class (AC: 4)
  - [x] Define result wrapper with metadata
  - [x] Include query, mode, timing, count
  - [x] Include truncation info

- [x] Task 2: Add date range filtering (AC: 2)
  - [x] Add start_date/end_date params to search
  - [x] Filter results by timestamp
  - [x] Support ISO format dates

- [x] Task 3: Add tag filtering (AC: 2)
  - [x] Add tags param to search
  - [x] Support match_all flag (AND vs OR)
  - [x] Filter results by tag overlap

- [x] Task 4: Create unified query() method (AC: 1, 3)
  - [x] Single method accepting all filters
  - [x] Auto-select search mode based on params
  - [x] Return MemoryQueryResult

- [x] Task 5: Add context window management (AC: 5)
  - [x] Add max_tokens param
  - [x] Estimate frame token counts
  - [x] Truncate results to budget
  - [x] Include truncation flag in result

- [x] Task 6: Write unit tests (AC: all)
  - [x] Test date filtering
  - [x] Test tag filtering
  - [x] Test unified query method
  - [x] Test token truncation

## Dev Notes

### API Design

```python
# Unified query method
result = store.query(
    query="error handling",
    mode="hybrid",  # "keyword" | "semantic" | "hybrid"
    limit=10,
    frame_type="error",
    session_id="sess-123",
    start_date="2026-01-10",
    end_date="2026-01-11",
    tags=["important"],
    max_tokens=4000,
)

# Result structure
print(result.frames)       # List[MemoryFrame]
print(result.total_count)  # Total matching (before limit)
print(result.truncated)    # Whether truncated for tokens
print(result.query_time)   # Seconds
```

### Token Estimation

Simple estimation: ~4 chars per token (English text average).
More accurate: use tiktoken for exact counts.

### Dependencies

- Story 3.1: Memvid Core Integration (COMPLETE)
- Story 3.2: Short-Term Memory (COMPLETE)
- Story 3.5: Vector Search Integration (COMPLETE)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- Story completed 2026-01-11
- All acceptance criteria met
- 146 tests passing (11 new tests for query API)
- Added `MemoryQueryResult` dataclass with query metadata
- Added `estimate_tokens()` method to MemoryFrame
- Added unified `query()` method with all filters
- Supports date range filtering (start_date, end_date)
- Supports tag filtering with match_all option
- Context window management via max_tokens parameter

### File List

**Modified:**
- `ralph_agi/memory/store.py` - Added MemoryQueryResult, query(), _apply_filters, _truncate_to_tokens
- `ralph_agi/memory/__init__.py` - Exported MemoryQueryResult
- `tests/memory/test_store.py` - Added 11 tests for query API

### API Summary

```python
# Unified query with all filters
result = store.query(
    query="error handling",
    mode="hybrid",           # keyword | semantic | hybrid
    limit=10,
    frame_type="error",
    session_id="sess-123",
    start_date="2026-01-10",
    end_date="2026-01-11",
    tags=["important"],
    match_all_tags=False,
    max_tokens=4000,
)

# Result metadata
result.frames        # List[MemoryFrame]
result.total_count   # Count before truncation
result.truncated     # Whether token budget exceeded
result.query_time_ms # Execution time
result.token_count   # Tokens in returned frames
```
