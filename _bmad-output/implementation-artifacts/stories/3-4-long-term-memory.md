# Story 3.4: Long-Term Memory (Persistent Knowledge)

Status: completed
Completed: 2026-01-11

## Story

As a **developer**,
I want **permanent storage of learnings and observations**,
so that **knowledge persists across sessions**.

## Acceptance Criteria

1. **AC1:** Observation types: error, success, learning, preference, decision, context, summary
   - `ObservationType` enum with all types
   - Each type has importance score (1-10)
   - Importance: error=10, decision=9, learning=8, preference=7, success=5

2. **AC2:** Structured observation schema with metadata
   - `Observation` dataclass with content, type, source, confidence
   - Support for related_ids and tags
   - `to_dict()` conversion for storage

3. **AC3:** Query by observation type and date range
   - `get_by_type()` returns frames of specific type
   - `query_by_date_range()` with start/end date filters
   - Convenience methods: `get_errors()`, `get_learnings()`, etc.

4. **AC4:** Temporal queries (what did I know at time X?)
   - `get_knowledge_at()` returns observations before point in time
   - `TemporalQuery` dataclass with query, point_in_time, observations
   - Filter by observation types

5. **AC5:** Memory compaction for old frames
   - Importance-based retention
   - High-importance observations preserved longer
   - Integration with ContextCompactor (Story 3.8)

## Tasks / Subtasks

- [x] Task 1: Create ObservationType enum (AC: 1)
  - [x] Define ERROR, SUCCESS, LEARNING, PREFERENCE, DECISION, CONTEXT, SUMMARY
  - [x] Add importance property with scores
  - [x] Document importance rationale

- [x] Task 2: Create Observation dataclass (AC: 2)
  - [x] Fields: content, observation_type, source, confidence
  - [x] Optional: related_ids, tags, metadata
  - [x] Computed importance from type \* confidence

- [x] Task 3: Create KnowledgeStore class (AC: 3, 4, 5)
  - [x] `record()` stores observation with tags
  - [x] Convenience methods: record_error, record_success, etc.
  - [x] `get_by_type()` and `query_by_date_range()`
  - [x] `get_knowledge_at()` for temporal queries

- [x] Task 4: Implement search and filtering (AC: 3, 4)
  - [x] `search_knowledge()` with type and importance filters
  - [x] `get_related()` finds related observations
  - [x] `get_high_importance()` for critical knowledge

- [x] Task 5: Write unit tests (AC: all)
  - [x] Create `tests/memory/test_knowledge.py`
  - [x] Test ObservationType and importance scores
  - [x] Test Observation dataclass
  - [x] Test KnowledgeStore operations
  - [x] Test temporal queries
  - [x] 38 tests passing

## Dev Notes

### ObservationType Importance

```python
ERROR = 10      # Always keep errors
DECISION = 9    # Decisions are critical
LEARNING = 8    # Learnings inform future work
PREFERENCE = 7  # Preferences guide behavior
SUCCESS = 5     # Success is good but less critical
SUMMARY = 4     # Summaries are derived
CONTEXT = 3     # Context is transient
```

### KnowledgeStore API

```python
ks = KnowledgeStore(memory_store)

# Record observations
ks.record_error("API timeout", source="task-123")
ks.record_learning("Use exponential backoff", confidence=0.9)
ks.record_decision("Switch to async API", related_ids=["obs-1"])

# Query knowledge
errors = ks.get_errors(limit=10)
knowledge = ks.get_knowledge_at("2026-01-10T12:00:00Z")
critical = ks.get_high_importance(min_importance=7)
```

### File List

**Created:**

- `ralph_agi/memory/knowledge.py` - KnowledgeStore, Observation, ObservationType
- `tests/memory/test_knowledge.py` - 38 unit tests

**Modified:**

- `ralph_agi/memory/__init__.py` - Export KnowledgeStore, Observation, etc.
