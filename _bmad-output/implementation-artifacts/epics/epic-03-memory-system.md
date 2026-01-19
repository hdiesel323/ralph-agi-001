# Epic 03: Multi-Layered Memory System

**PRD Reference:** FR-003
**Priority:** P1 (High)
**Roadmap:** Weeks 4-5 (Memory Layer)
**Status:** COMPLETE

---

## Epic Overview

Implement the three-tier memory system enabling context persistence across sessions using **Memvid** as the primary storage engine, with optional vector DB scaling.

**Key Technology:** [Memvid](https://github.com/memvid/memvid) - Portable, serverless AI memory in a single `.mv2` file with built-in HNSW vector search and BM25 full-text search.

## Business Value

- Enables true long-horizon autonomy (days, not hours)
- Prevents re-work on similar tasks
- Learns from past mistakes and successes
- Single-file deployment (no database servers required)

## Technical Context

"Without persistent memory, each agent session would start from scratch, wasting time rediscovering context and potentially repeating mistakes." - PRD

### Why Memvid?

| Feature          | Memvid             | Traditional Stack     |
| ---------------- | ------------------ | --------------------- |
| Storage          | Single `.mv2` file | SQLite + ChromaDB     |
| Vector Search    | Built-in HNSW      | Separate ChromaDB     |
| Full-text Search | Built-in BM25      | Manual implementation |
| Crash Safety     | Append-only frames | Manual WAL setup      |
| Temporal Queries | Native support     | Manual implementation |
| Deployment       | Zero config        | Multiple services     |

### Scaling Strategy

1. **Phase 1 (Sprint 2):** Memvid-only for all memory tiers
2. **Phase 2 (Future):** If needed, add Qdrant/Pinecone for massive scale

---

## Stories

### Story 3.1: Memvid Core Integration

**Priority:** P0 | **Points:** 3

**As a** developer
**I want** Memvid integrated as the memory backend
**So that** I have a portable, crash-safe memory system

**Acceptance Criteria:**

- [ ] Install memvid package and dependencies
- [ ] Create `MemoryStore` class wrapping Memvid
- [ ] Configure `.mv2` file path in config.yaml
- [ ] Basic append and read operations working
- [ ] Unit tests for core operations

---

### Story 3.2: Short-Term Memory (Session Context)

**Priority:** P0 | **Points:** 2

**As a** developer
**I want** session-scoped memory frames
**So that** context is preserved within a sprint

**Acceptance Criteria:**

- [ ] Store iteration results as Memvid frames
- [ ] Frame metadata: session_id, iteration, timestamp
- [ ] Query frames by current session
- [ ] Read last N frames for context loading
- [ ] Automatic frame creation in loop

---

### Story 3.3: Medium-Term Memory (Git Integration)

**Priority:** P0 | **Points:** 3

**As a** developer
**I want** git history as searchable memory
**So that** code changes are preserved and queryable

**Acceptance Criteria:**

- [ ] Auto-commit after successful task completion
- [ ] Store commit metadata in Memvid frames
- [ ] Commit message template: `feat: {description}`
- [ ] Query memory by git commit reference
- [ ] Support linking frames to commits

---

### Story 3.4: Long-Term Memory (Persistent Knowledge)

**Priority:** P1 | **Points:** 3

**As a** developer
**I want** permanent storage of learnings and observations
**So that** knowledge persists across sessions

**Acceptance Criteria:**

- [ ] Observation types: error, success, learning, preference
- [ ] Structured observation schema with metadata
- [ ] Query by observation type and date range
- [ ] Temporal queries (what did I know at time X?)
- [ ] Memory compaction for old frames

---

### Story 3.5: Vector Search Integration

**Priority:** P1 | **Points:** 3

**As a** developer
**I want** semantic search over past observations
**So that** relevant context is retrieved automatically

**Acceptance Criteria:**

- [ ] Configure embedding model (local or API)
- [ ] Auto-embed frames on creation
- [ ] `memory.search_similar(query, limit)` API
- [ ] Hybrid retrieval (semantic + BM25 keyword)
- [ ] Relevance scoring and ranking

---

### Story 3.6: Memory Query API

**Priority:** P1 | **Points:** 3

**As a** developer
**I want** a unified API for all memory queries
**So that** the loop can easily load context

**Acceptance Criteria:**

- [ ] `memory.search(query, type, limit)` unified API
- [ ] Filter by: session, type, date range, tags
- [ ] Combine vector + keyword results
- [ ] Return structured MemoryResult objects
- [ ] Context window management (token limits)

---

### Story 3.7: Lifecycle Hooks

**Priority:** P2 | **Points:** 2

**As a** developer
**I want** automatic memory capture at key points
**So that** memory is populated without manual effort

**Acceptance Criteria:**

- [ ] Hook: on_iteration_start (load context)
- [ ] Hook: on_iteration_end (store result)
- [ ] Hook: on_error (store error + context)
- [ ] Hook: on_completion (store summary)
- [ ] Configurable hook behavior in config.yaml

---

### Story 3.8: Context Compacting

**Priority:** P1 | **Points:** 3
**Source:** [Clawdbot Patterns Analysis](../../../rnd/research/2026-01-10_clawdbot-patterns-analysis.md)
**Beads:** ralph-agi-001-003

**As a** developer
**I want** automatic summarization of older context frames
**So that** context windows don't overflow during long-running tasks

**Acceptance Criteria:**

- [ ] Compaction threshold configuration in config.yaml
- [ ] LLM-based summarization of older frames (use Haiku)
- [ ] Archive original frames (don't delete)
- [ ] Preserve full detail for errors and decisions
- [ ] Integration with Story 3.6 Memory Query API
- [ ] Token usage tracking before/after compaction
- [ ] Benchmark: 50%+ token reduction on long sessions

**Technical Notes:**

- Compaction strategy:
  - Recent (last N iterations) → Full detail
  - Medium (N to 2N iterations) → Summarized
  - Old (>2N iterations) → Key points only / archived
- Importance scoring: errors > decisions > progress > chatter
- Compaction should be idempotent (safe to run multiple times)

**Config Example:**

```yaml
memory:
  compaction:
    enabled: true
    threshold_frames: 50
    summary_model: "haiku"
    preserve_errors: true
    preserve_decisions: true
```

---

## Sprint History

**Sprint 2:** Stories 3.1, 3.2, 3.5, 3.6 (11 points) - COMPLETE

| Story                 | Points | Priority | Status   |
| --------------------- | ------ | -------- | -------- |
| 3.1 Memvid Core       | 3      | P0       | Complete |
| 3.2 Short-Term Memory | 2      | P0       | Complete |
| 3.5 Vector Search     | 3      | P1       | Complete |
| 3.6 Query API         | 3      | P1       | Complete |

**Sprint 4:** Stories 3.3, 3.4, 3.7, 3.8 (11 points) - COMPLETE

| Story                  | Points | Priority | Status   |
| ---------------------- | ------ | -------- | -------- |
| 3.3 Git Integration    | 3      | P0       | Complete |
| 3.4 Long-Term Memory   | 3      | P1       | Complete |
| 3.7 Lifecycle Hooks    | 2      | P2       | Complete |
| 3.8 Context Compacting | 3      | P1       | Complete |

**Total:** 22 points delivered, 266 tests passing

---

## Dependencies

- Epic 01: Core Execution Loop (COMPLETE)
- Memvid package installation
- Embedding model selection (sentence-transformers recommended)

## Definition of Done

- [x] All 8 stories complete (Sprint 2 + Sprint 4)
- [x] Memory persists across loop restarts
- [x] Semantic search returning relevant results
- [x] Context loading integrated into RalphLoop
- [x] 90%+ test coverage on memory module (266 tests)

## Research Notes

See: `docs/research/memvid-evaluation.md`
