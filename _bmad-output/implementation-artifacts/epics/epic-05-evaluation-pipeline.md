# Epic 05: Cascaded Evaluation Pipeline

**PRD Reference:** FR-005
**Priority:** P1 (High)
**Roadmap:** Week 8 (Safety & Verification)
**Status:** Draft

---

## Epic Overview

Implement the 5-stage cascaded evaluation pipeline ensuring code quality through progressive verification - from fast/cheap (syntax) to slow/expensive (LLM Judge).

## Business Value

- Prevents buggy code from being committed
- Saves resources by failing fast
- Ensures production-quality output

## Technical Context

"A failure at any stage halts the commit and triggers a debugging sub-loop." - PRD

| Stage             | Time | Cost  | Purpose                |
| ----------------- | ---- | ----- | ---------------------- |
| Static Analysis   | ~1s  | $0.00 | Syntax, linting, types |
| Unit Tests        | ~10s | $0.00 | Function-level         |
| Integration Tests | ~30s | $0.01 | Component interaction  |
| E2E Tests         | ~60s | $0.05 | User-facing            |
| LLM Judge         | ~30s | $0.10 | Qualitative review     |

---

## Stories

### Story 5.1: Pipeline Framework

**Priority:** P0 | **Points:** 3

**As a** developer
**I want** a configurable evaluation pipeline
**So that** I can define verification stages

**Acceptance Criteria:**

- [ ] Stage definition in config
- [ ] Sequential execution
- [ ] Stop on first failure (cascade)
- [ ] Configurable stage enable/disable
- [ ] Timeout per stage

---

### Story 5.2: Stage 1 - Static Analysis

**Priority:** P0 | **Points:** 2

**As a** developer
**I want** syntax and type checking
**So that** obvious errors are caught fast

**Acceptance Criteria:**

- [ ] Run configured linter (ruff, pylint)
- [ ] Run type checker (mypy, pyright)
- [ ] Parse output for errors
- [ ] Return pass/fail with details

---

### Story 5.3: Stage 2 - Unit Tests

**Priority:** P0 | **Points:** 2

**As a** developer
**I want** unit test execution
**So that** function-level correctness is verified

**Acceptance Criteria:**

- [ ] Run pytest (or configured runner)
- [ ] Parse test results
- [ ] Report failures with context
- [ ] Support test filtering

---

### Story 5.4: Stage 3 - Integration Tests

**Priority:** P1 | **Points:** 3

**As a** developer
**I want** integration test execution
**So that** component interactions are verified

**Acceptance Criteria:**

- [ ] Run integration test suite
- [ ] Longer timeout (600s)
- [ ] Environment setup/teardown
- [ ] Optional (configurable)

---

### Story 5.5: Stage 4 - E2E Tests

**Priority:** P1 | **Points:** 5

**As a** developer
**I want** end-to-end browser testing
**So that** user-facing functionality is verified

**Acceptance Criteria:**

- [ ] Playwright integration
- [ ] Test application as user would
- [ ] Screenshot on failure
- [ ] Optional (configurable)

---

### Story 5.6: Stage 5 - LLM Judge

**Priority:** P2 | **Points:** 5

**As a** developer
**I want** LLM-based code review
**So that** qualitative issues are caught

**Acceptance Criteria:**

- [ ] Send code diff to LLM
- [ ] Structured review criteria
- [ ] Score 1-10 with justification
- [ ] Configurable pass threshold
- [ ] Optional (configurable)

---

### Story 5.7: Debug Sub-Loop

**Priority:** P1 | **Points:** 5

**As a** developer
**I want** automatic debugging on failure
**So that** issues are fixed without human intervention

**Acceptance Criteria:**

- [ ] Capture failure context
- [ ] Send to LLM for diagnosis
- [ ] Apply suggested fix
- [ ] Re-run failed stage
- [ ] Max 3 retry attempts

---

## Dependencies

- Epic 01: Core Execution Loop
- Epic 04: Tool Integration (for running commands)

## Definition of Done

- [ ] All 5 stages implemented
- [ ] Cascade logic working
- [ ] Debug sub-loop functional
- [ ] 95% pass rate on internal checks
- [ ] Configurable per-project
