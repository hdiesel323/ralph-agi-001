# Epic 02: Task Management and Planning

**PRD Reference:** FR-002
**Priority:** P0 (Critical)
**Roadmap:** Weeks 2-3 (Foundation)
**Status:** Draft

---

## Epic Overview

Implement the Task Manager providing structured task definition, dependency tracking, and progress management using PRD.json as the single source of truth.

## Business Value

- Structured approach to complex project management
- Prevents premature task completion via dependency enforcement
- Enables intelligent task prioritization

## Technical Context

All tasks defined in `PRD.json` - JSON format chosen because "the model is less likely to inappropriately change or overwrite JSON files compared to Markdown files" (Anthropic).

---

## Stories

### Story 2.1: PRD.json Parser
**Priority:** P0 | **Points:** 3

**As a** developer
**I want** to parse and validate PRD.json
**So that** I can access task definitions programmatically

**Acceptance Criteria:**
- [ ] Parse PRD.json according to schema (PRD Appendix A)
- [ ] Validate required fields: id, description, passes
- [ ] Return structured Python objects
- [ ] Clear error messages for invalid JSON

---

### Story 2.2: Task Selection Algorithm
**Priority:** P0 | **Points:** 3

**As a** developer
**I want** automatic selection of the next task to work on
**So that** the loop always knows what to do next

**Acceptance Criteria:**
- [ ] Filter tasks where `passes == false`
- [ ] Filter tasks with no blocking dependencies
- [ ] Sort by priority (P0 > P1 > P2 > P3 > P4)
- [ ] Return highest priority ready task
- [ ] Return None if no tasks ready

---

### Story 2.3: Dependency Graph
**Priority:** P1 | **Points:** 5

**As a** developer
**I want** a dependency graph for task ordering
**So that** tasks are completed in correct order

**Acceptance Criteria:**
- [ ] Build graph from PRD dependencies field
- [ ] Detect circular dependencies (error)
- [ ] Query: "Is task X ready?" (all deps complete)
- [ ] Query: "What blocks task X?"
- [ ] Visualize graph (optional, for debugging)

---

### Story 2.4: Task Completion Marking
**Priority:** P0 | **Points:** 2

**As a** developer
**I want** to mark tasks as complete in PRD.json
**So that** progress is persisted

**Acceptance Criteria:**
- [ ] Update `passes: false` to `passes: true`
- [ ] Add `completed_at` timestamp
- [ ] Atomic write (no partial updates)
- [ ] NEVER modify other fields (enforced)

---

### Story 2.5: Single Feature Constraint
**Priority:** P0 | **Points:** 2

**As a** developer
**I want** enforcement of single-feature-per-iteration
**So that** context quality is maintained

**Acceptance Criteria:**
- [ ] Loop only processes one task per iteration
- [ ] Task lock during execution
- [ ] Warning if task seems too large
- [ ] Suggestion to break down large tasks

---

## Dependencies

- Epic 01: Core Execution Loop (for integration)

## Definition of Done

- [ ] PRD.json parsed and validated
- [ ] Task selection working correctly
- [ ] Dependencies respected
- [ ] Completion persisted atomically
- [ ] Unit tests for all logic
