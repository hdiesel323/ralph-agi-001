# Epic 01: Core Execution Loop (Ralph Loop Engine)

**PRD Reference:** FR-001
**Priority:** P0 (Critical)
**Roadmap:** Week 1 (PoC)
**Status:** Ready for Sprint

---

## Epic Overview

Implement the Ralph Loop Engine - the central mechanism that drives all agent activity. This is the heart of RALPH-AGI, implementing the iterative cycle that processes one task at a time until all tasks are complete.

## Business Value

- Enables autonomous task execution without human intervention
- Foundation for all other system capabilities
- Validates the core "Ralph Wiggum Pattern" hypothesis

## Technical Context

The loop operates on a single task at a time, preventing context bloat. Key insight from PRD: "LLMs produce lower-quality output as more tokens are added to the context window."

```
while (iteration < max && !complete):
    1. Load Context (Memory + Progress + Git)
    2. Select Task (PRD: highest priority, no blockers)
    3. Execute Task (LLM + Tools)
    4. Verify (Cascade Evaluation - basic for PoC)
    5. Update State (PRD + Progress + Git Commit)
    6. Check Completion (Promise Detection)
```

---

## Stories

### Story 1.1: Basic Loop Structure
**Priority:** P0 | **Points:** 3

**As a** developer
**I want** a Python script that iterates through a task list
**So that** I can process tasks one at a time automatically

**Acceptance Criteria:**
- [ ] `src/core/loop.py` implements main loop
- [ ] Configurable `max_iterations` parameter
- [ ] Loop exits on max iterations or completion signal
- [ ] Each iteration is logged with timestamp and iteration number
- [ ] Clean error handling with retry logic (max 3 attempts)

**Technical Notes:**
- Use `while` loop, not `for` loop (cleaner exit conditions)
- Log format: `[2026-01-10T14:30:00] Iteration 1/100: Starting...`

---

### Story 1.2: Completion Promise Detection
**Priority:** P0 | **Points:** 2

**As a** developer
**I want** the loop to detect when all tasks are complete
**So that** it exits gracefully instead of running unnecessarily

**Acceptance Criteria:**
- [ ] Detect `<promise>COMPLETE</promise>` in LLM output
- [ ] Exit loop immediately when detected
- [ ] Log completion message with total iterations
- [ ] Return success status to caller

**Technical Notes:**
- Simple string search is sufficient
- Configurable promise string via config

---

### Story 1.3: Configuration Management
**Priority:** P0 | **Points:** 2

**As a** developer
**I want** a YAML configuration file for system settings
**So that** I can customize behavior without code changes

**Acceptance Criteria:**
- [ ] `config.yaml` in project root
- [ ] Load config at startup
- [ ] Support for: max_iterations, completion_promise, checkpoint_interval
- [ ] Validation of required fields
- [ ] Sensible defaults if config missing

**Technical Notes:**
- Use PyYAML for parsing
- Schema from PRD Appendix C

---

### Story 1.4: AFK Mode (Basic)
**Priority:** P0 | **Points:** 2

**As a** developer
**I want** the loop to run fully autonomously
**So that** I can start it and walk away

**Acceptance Criteria:**
- [ ] No user input required during execution
- [ ] All progress logged to file and console
- [ ] Graceful handling of interrupts (Ctrl+C)
- [ ] State saved on interrupt for resume

**Technical Notes:**
- Signal handling for SIGINT/SIGTERM
- Write checkpoint before exit

---

### Story 1.5: CLI Entry Point
**Priority:** P1 | **Points:** 2

**As a** developer
**I want** a CLI command to start the loop
**So that** I can easily run RALPH-AGI from terminal

**Acceptance Criteria:**
- [ ] `ralph-agi run` command starts loop
- [ ] `--max-iterations` flag overrides config
- [ ] `--config` flag specifies config file
- [ ] Help text with usage examples
- [ ] Exit codes: 0=success, 1=error, 2=max iterations

**Technical Notes:**
- Use `argparse` or `click`
- Entry point in `setup.py` or `pyproject.toml`

---

## Dependencies

- None (this is the foundation)

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Loop runs forever | Medium | High | Hard max_iterations limit |
| LLM API failures | High | Medium | Retry with exponential backoff |
| State corruption on crash | Medium | High | Atomic checkpoints |

## Definition of Done

- [ ] All stories complete and tested
- [ ] Basic loop executes 3-5 simple tasks successfully
- [ ] Unit tests for loop logic
- [ ] Integration test: full loop with mock LLM
- [ ] Documentation updated

## Sprint 1 Scope (Week 1 PoC)

For the PoC, implement Stories 1.1, 1.2, 1.3, and 1.4. Story 1.5 (CLI) can be deferred.

**PoC Success Criteria:**
- Loop runs with mock task list
- Detects completion correctly
- Handles errors gracefully
- Logs all activity
