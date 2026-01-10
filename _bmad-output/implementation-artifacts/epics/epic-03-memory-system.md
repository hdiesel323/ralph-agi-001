# Epic 03: Multi-Layered Memory System

**PRD Reference:** FR-003
**Priority:** P1 (High)
**Roadmap:** Weeks 4-5 (Memory Layer)
**Status:** Draft

---

## Epic Overview

Implement the three-tier memory system enabling context persistence across sessions: Short-term (progress.txt), Medium-term (Git), Long-term (SQLite + ChromaDB).

## Business Value

- Enables true long-horizon autonomy (days, not hours)
- Prevents re-work on similar tasks
- Learns from past mistakes and successes

## Technical Context

"Without persistent memory, each agent session would start from scratch, wasting time rediscovering context and potentially repeating mistakes." - PRD

---

## Stories

### Story 3.1: Short-Term Memory (progress.txt)
**Priority:** P0 | **Points:** 2

**As a** developer
**I want** append-only session notes
**So that** context is preserved within a sprint

**Acceptance Criteria:**
- [ ] Append-only file operations (NEVER overwrite)
- [ ] Structured format: timestamp, iteration, content
- [ ] Read last N lines for context loading
- [ ] Max file size handling (rotate if needed)

---

### Story 3.2: Medium-Term Memory (Git)
**Priority:** P0 | **Points:** 3

**As a** developer
**I want** descriptive git commits after each feature
**So that** history is preserved and recoverable

**Acceptance Criteria:**
- [ ] Auto-commit after successful task completion
- [ ] Commit message template: `feat: {description}`
- [ ] Read git log for context
- [ ] Support `git revert` for recovery

---

### Story 3.3: Long-Term Memory Schema (SQLite)
**Priority:** P1 | **Points:** 3

**As a** developer
**I want** structured storage for observations
**So that** learnings persist permanently

**Acceptance Criteria:**
- [ ] SQLite database at configurable path
- [ ] Tables: sessions, observations, summaries
- [ ] Schema from PRD Section 2.2
- [ ] Query by session, type, date range

---

### Story 3.4: Vector Search (ChromaDB)
**Priority:** P1 | **Points:** 5

**As a** developer
**I want** semantic search over past observations
**So that** relevant context is retrieved automatically

**Acceptance Criteria:**
- [ ] ChromaDB integration
- [ ] Embed observations on creation
- [ ] Query: "Find similar past work"
- [ ] Hybrid retrieval (semantic + keyword)

---

### Story 3.5: Memory Query API
**Priority:** P1 | **Points:** 3

**As a** developer
**I want** a unified API for memory queries
**So that** the loop can easily load context

**Acceptance Criteria:**
- [ ] `memory.search(query, type, limit)`
- [ ] Combine results from all tiers
- [ ] Rank by relevance
- [ ] Return structured results

---

### Story 3.6: Lifecycle Hooks
**Priority:** P2 | **Points:** 3

**As a** developer
**I want** automatic observation capture at key points
**So that** memory is populated without manual effort

**Acceptance Criteria:**
- [ ] Hook: session_start
- [ ] Hook: after_tool_use
- [ ] Hook: after_task_complete
- [ ] Hook: session_end
- [ ] Configurable hook behavior

---

## Dependencies

- Epic 01: Core Execution Loop
- Epic 02: Task Management (for task context)

## Definition of Done

- [ ] All three memory tiers operational
- [ ] Context loading from all tiers
- [ ] Observations stored automatically
- [ ] Semantic search working
- [ ] 50% reduction in task re-work (measurable)
