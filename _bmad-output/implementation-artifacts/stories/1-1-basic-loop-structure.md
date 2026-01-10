# Story 1.1: Basic Loop Structure

**Status:** completed

**Epic:** Epic 01 - Core Execution Loop (FR-001)
**Priority:** P0 (Critical)
**Points:** 3
**Sprint:** Sprint 1 - Week 1 PoC

---

## Story

As a **developer**,
I want **a Python script that iterates through a task list**,
so that **I can process tasks one at a time automatically**.

## Acceptance Criteria

1. **AC1:** `src/core/loop.py` implements the main Ralph Loop Engine
2. **AC2:** Configurable `max_iterations` parameter with default value of 100
3. **AC3:** Loop exits correctly on max iterations OR completion signal
4. **AC4:** Each iteration is logged with timestamp and iteration number in format: `[YYYY-MM-DDTHH:MM:SS] Iteration N/MAX: Status`
5. **AC5:** Clean error handling with retry logic (max 3 attempts per iteration with exponential backoff)

## Tasks / Subtasks

- [x] **Task 1: Project Setup** (AC: 1)
  - [x] 1.1: Create `src/` directory structure with `__init__.py` files
  - [x] 1.2: Create `src/core/` directory with `__init__.py`
  - [x] 1.3: Create empty `src/core/loop.py` file
  - [x] 1.4: Create `pyproject.toml` with Python 3.11+ requirement

- [x] **Task 2: Loop Engine Core** (AC: 1, 2, 3)
  - [x] 2.1: Implement `RalphLoop` class with `__init__` accepting `max_iterations` parameter (default=100)
  - [x] 2.2: Implement `run()` method with while loop structure (NOT for loop)
  - [x] 2.3: Add iteration counter and max iterations check
  - [x] 2.4: Add completion signal check (placeholder for Story 1.2)
  - [x] 2.5: Implement `_execute_iteration()` method stub that returns success/failure

- [x] **Task 3: Logging System** (AC: 4)
  - [x] 3.1: Configure Python logging with ISO timestamp format
  - [x] 3.2: Implement `_log_iteration_start()` with format `[YYYY-MM-DDTHH:MM:SS] Iteration N/MAX: Starting...`
  - [x] 3.3: Implement `_log_iteration_end()` with success/failure status
  - [x] 3.4: Add console and file handler support

- [x] **Task 4: Error Handling** (AC: 5)
  - [x] 4.1: Implement `_execute_with_retry()` wrapper method
  - [x] 4.2: Add exponential backoff (1s, 2s, 4s delays)
  - [x] 4.3: Max 3 retry attempts per iteration
  - [x] 4.4: Log each retry attempt with reason
  - [x] 4.5: Raise `MaxRetriesExceeded` exception after 3 failures

- [x] **Task 5: Unit Tests** (AC: 1-5)
  - [x] 5.1: Create `tests/` directory with `__init__.py`
  - [x] 5.2: Create `tests/core/test_loop.py`
  - [x] 5.3: Test loop initialization with default and custom max_iterations
  - [x] 5.4: Test loop exits at max iterations
  - [x] 5.5: Test logging format matches specification
  - [x] 5.6: Test retry logic with mock failures
  - [x] 5.7: Test exponential backoff timing

## Dev Notes

### Critical Architecture Requirements

**From PRD FR-001:**
- Loop operates on SINGLE task at a time (prevents context bloat)
- Design is intentionally simple - "a for loop is often more effective than complex orchestration"
- Must support future AFK Mode (autonomous) and Human-in-the-Loop Mode

**From PRD Non-Functional Requirements:**
- Single iteration (excluding tool execution) must complete in < 60 seconds
- 90% self-recovery rate from common errors
- All state changes must be atomic
- Comprehensive logging with timestamps and context

### Code Patterns to Follow

```python
# Loop structure (use WHILE, not FOR)
while self.iteration < self.max_iterations and not self.complete:
    try:
        self._execute_iteration()
        self.iteration += 1
    except Exception as e:
        if not self._handle_error(e):
            raise

# Logging format
import logging
from datetime import datetime

logger = logging.getLogger("ralph-agi")
timestamp = datetime.utcnow().isoformat(timespec='seconds')
logger.info(f"[{timestamp}] Iteration {self.iteration}/{self.max_iterations}: Starting...")

# Exponential backoff
import time
delays = [1, 2, 4]  # seconds
for attempt, delay in enumerate(delays):
    try:
        result = self._execute_iteration()
        break
    except Exception as e:
        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
        time.sleep(delay)
```

### File Structure (Target)

```
ralph-agi/
├── src/
│   ├── __init__.py
│   └── core/
│       ├── __init__.py
│       └── loop.py          # THIS STORY
├── tests/
│   ├── __init__.py
│   └── core/
│       ├── __init__.py
│       └── test_loop.py     # THIS STORY
├── pyproject.toml           # THIS STORY
└── README.md
```

### Testing Standards

- Use `pytest` as test framework
- Aim for >80% code coverage on new code
- Use `unittest.mock` for mocking external dependencies
- Test both success and failure paths
- Test edge cases: 0 iterations, 1 iteration, max iterations

### Dependencies

**Required (add to pyproject.toml):**
- Python >= 3.11
- pytest >= 7.0 (dev dependency)
- pytest-cov >= 4.0 (dev dependency)

**DO NOT add unnecessary dependencies** - keep it minimal for PoC

### Project Structure Notes

- This is a NEW Python project - no existing code to maintain compatibility with
- The `client/` folder contains a React documentation website (IGNORE for this story)
- Create clean Python project structure from scratch in project root

### Anti-Patterns to Avoid

1. **DO NOT** use `for` loop - use `while` for cleaner exit conditions
2. **DO NOT** add complex orchestration - keep it simple
3. **DO NOT** implement task selection yet (Story 1.2+)
4. **DO NOT** implement configuration loading (Story 1.3)
5. **DO NOT** implement checkpoint/state persistence (Story 1.4)

### References

- [Source: client/public/RALPH-AGI-PRD-Final.md#4.1 Core Execution Loop]
- [Source: client/public/RALPH-AGI-Technical-Architecture.md#2.1 Ralph Loop Engine]
- [Source: _bmad-output/planning-artifacts/project-context.md#Critical Rules]
- [Source: _bmad-output/implementation-artifacts/epics/epic-01-core-loop.md#Story 1.1]

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Implementation Plan

1. Created Python project structure with src/ and tests/ directories
2. Implemented RalphLoop class with:
   - Configurable max_iterations (default 100)
   - While loop structure (not for loop) for clean exit conditions
   - Completion signal detection via `_check_completion()`
   - Iteration tracking and logging
3. Implemented logging system with:
   - Custom BracketedTimestampFormatter for `[YYYY-MM-DDTHH:MM:SS]` format
   - Console and optional file handler support
   - Separate methods for start/end logging
4. Implemented error handling with:
   - `_execute_with_retry()` wrapper with exponential backoff
   - MaxRetriesExceeded custom exception
   - Configurable retry delays [1, 2, 4] seconds
5. Created comprehensive test suite with 26 tests covering all ACs

### Debug Log References

No debugging issues encountered. All tests passed on first run.

### Completion Notes

- All 5 acceptance criteria satisfied
- 33 unit tests written and passing (after code review fixes)
- 99% code coverage achieved (target was >80%)
- Used WHILE loop as specified (not FOR loop)
- Logging format matches specification exactly
- Exponential backoff implemented with configurable delays
- MaxRetriesExceeded exception properly propagates error context
- Code is minimal and follows "keep it simple" principle from PRD

### Code Review Fixes Applied

1. **Issue 1 (HIGH):** Fixed completion check to properly receive iteration output
   - Added `IterationResult` dataclass to return both success and output
   - Modified `_execute_iteration()` to return `IterationResult`
   - Updated `run()` to pass output to `_check_completion()`

2. **Issue 2 (HIGH):** Fixed shared logger state
   - Logger names now include instance ID: `ralph-agi.{id(self)}`
   - Multiple RalphLoop instances no longer interfere with each other

3. **Issue 3 (MEDIUM):** Added `close()` method
   - Properly closes and removes logging handlers
   - Prevents resource leaks (file handles)

4. **Issue 4 (MEDIUM):** Added file logging tests
   - New test verifies log file creation and content
   - New test verifies multiple instances have independent loggers

### File List

**Created:**
- `src/__init__.py` - Package init with version
- `src/core/__init__.py` - Core module init with RalphLoop, IterationResult, MaxRetriesExceeded exports
- `src/core/loop.py` - Main Ralph Loop Engine implementation (111 statements)
- `tests/__init__.py` - Test package init
- `tests/core/__init__.py` - Core tests init
- `tests/core/test_loop.py` - Comprehensive test suite (33 tests)
- `pyproject.toml` - Project configuration with pytest setup

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-10 | Story created with comprehensive context | BMM create-story |
| 2026-01-10 | Implementation complete - all 5 tasks done, 26 tests passing, 94% coverage | Claude Opus 4.5 |
| 2026-01-10 | Code review fixes applied - 4 issues resolved, 33 tests passing, 99% coverage | Claude Opus 4.5 |
