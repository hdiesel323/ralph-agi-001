# Story 3.7: Lifecycle Hooks

Status: completed
Completed: 2026-01-11

## Story

As a **developer**,
I want **automatic memory capture at key points**,
so that **memory is populated without manual effort**.

## Acceptance Criteria

1. **AC1:** Hook: on_iteration_start (load context)
   - Loads recent frames from current session
   - Optionally includes errors and decisions from other sessions
   - Returns context frame count

2. **AC2:** Hook: on_iteration_end (store result)
   - Stores iteration result with success/failure status
   - Includes output preview (truncated to 1000 chars)
   - Tags: iteration, iter-{n}, hook:iteration_end

3. **AC3:** Hook: on_error (store error + context)
   - Captures error type, message, and context
   - Includes recent activity for debugging
   - Importance: 10 (critical)

4. **AC4:** Hook: on_completion (store summary)
   - Stores session completion summary
   - Includes metrics: total iterations, error count
   - Importance: 8 (high)

5. **AC5:** Configurable hook behavior in config.yaml
   - `HookConfig` dataclass with all settings
   - Master enable/disable switch
   - Per-hook enable/disable

## Tasks / Subtasks

- [x] Task 1: Create HookConfig dataclass (AC: 5)
  - [x] enabled, on_iteration_start, on_iteration_end
  - [x] on_error, on_completion
  - [x] context_frames, include_errors_in_context

- [x] Task 2: Create HookContext and HookResult (AC: all)
  - [x] HookContext: session_id, iteration, timestamp, event, data
  - [x] HookResult: success, frame_id, context_loaded, error
  - [x] HookEvent enum: ITERATION_START, ITERATION_END, ERROR, COMPLETION

- [x] Task 3: Implement LifecycleHooks class (AC: 1-4)
  - [x] `on_iteration_start()` loads context
  - [x] `on_iteration_end()` stores result
  - [x] `on_error()` captures error with context
  - [x] `on_completion()` stores summary

- [x] Task 4: Add custom handler support (AC: all)
  - [x] `register_handler()` for custom callbacks
  - [x] `unregister_handler()` to remove handlers
  - [x] Error-tolerant handler execution

- [x] Task 5: Write unit tests (AC: all)
  - [x] Create `tests/memory/test_hooks.py`
  - [x] Test HookConfig and HookContext
  - [x] Test each hook method
  - [x] Test custom handlers
  - [x] Test disabled hooks
  - [x] 49 tests passing

## Dev Notes

### HookConfig

```python
@dataclass
class HookConfig:
    enabled: bool = True
    on_iteration_start: bool = True
    on_iteration_end: bool = True
    on_error: bool = True
    on_completion: bool = True
    context_frames: int = 10
    include_errors_in_context: bool = True
    include_decisions_in_context: bool = True
    max_error_context: int = 2000
```

### LifecycleHooks API

```python
hooks = LifecycleHooks(memory_store, config)

# At iteration start
result = hooks.on_iteration_start(session_id="sess-123", iteration=1)
print(f"Loaded {result.context_loaded} frames")

# At iteration end
hooks.on_iteration_end(
    session_id="sess-123",
    iteration=1,
    success=True,
    output="Task completed"
)

# On error
hooks.on_error(
    session_id="sess-123",
    iteration=1,
    error=ValueError("Something went wrong"),
    error_context="Processing user input"
)

# Custom handlers
def my_handler(context: HookContext):
    print(f"Hook fired: {context.event}")

hooks.register_handler(HookEvent.ITERATION_END, my_handler)
```

### File List

**Created:**

- `ralph_agi/memory/hooks.py` - LifecycleHooks, HookConfig, HookContext, etc.
- `tests/memory/test_hooks.py` - 49 unit tests

**Modified:**

- `ralph_agi/memory/__init__.py` - Export LifecycleHooks, HookConfig, etc.
