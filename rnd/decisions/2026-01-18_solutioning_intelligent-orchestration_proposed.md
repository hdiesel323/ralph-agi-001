# ADR-003: Intelligent Orchestration and Context Management

**Date:** 2026-01-18
**Status:** Proposed

---

## Context

Current RALPH-AGI uses brute-force retry when agents get stuck:

- `_execute_with_retry()` in `core/loop.py` uses exponential backoff (1, 2, 4 seconds)
- No intelligent context adjustment or task decomposition
- Memory compaction exists but summaries are rudimentary (char truncation)
- Single Builder does all work - no sub-agent delegation

**Key insight from Alexander Conroy:**

> "If you can craft the context framework properly you can avoid the [stuck] problem entirely... reduce context bloat, including summary information passed back to the main orchestrator so it doesn't get stuck."

---

## Research & Analysis

### Current Flow (Problematic)

```
Loop → Orchestrator → Builder ←→ Critic
         ↓ stuck?
      retry (same context)
         ↓ still stuck?
      MaxRetriesExceeded
```

### Proposed Flow (Intelligent)

```
Loop → StuckDetector → ContextPruner → TaskDecomposer
                              ↓
         Orchestrator → Builder ←→ Critic
                              ↓
         SummaryAgent → CompactedContext → Next Task
```

---

## Decision: Three-Phase Intelligent Orchestration

### Phase 1: Stuck Detection & Context Pruning (Sprint 6)

**Problem:** Ralph retries with identical context, expecting different results.

**Solution:** Implement `StuckDetector` that identifies stuck patterns and `ContextPruner` that intelligently reduces context.

```python
# ralph_agi/llm/stuck_detector.py
@dataclass
class StuckSignal:
    """Detected stuck pattern."""
    pattern: StuckPattern  # REPETITIVE_OUTPUT, NO_PROGRESS, CIRCULAR_TOOLS
    confidence: float
    context_diagnosis: str  # "context too large", "missing info", "wrong tools"
    recommended_action: StuckAction  # PRUNE_CONTEXT, DECOMPOSE_TASK, ESCALATE


class StuckDetector:
    """Detects when Builder is stuck and diagnoses the cause."""

    def __init__(self, history_window: int = 5):
        self._history: deque[BuilderResult] = deque(maxlen=history_window)

    def analyze(self, result: BuilderResult) -> Optional[StuckSignal]:
        """Analyze result for stuck patterns."""
        self._history.append(result)

        # Pattern 1: Repetitive outputs
        if self._detect_repetition():
            return StuckSignal(
                pattern=StuckPattern.REPETITIVE_OUTPUT,
                confidence=0.9,
                context_diagnosis="LLM cycling through same responses",
                recommended_action=StuckAction.PRUNE_CONTEXT,
            )

        # Pattern 2: No file changes across iterations
        if self._detect_no_progress():
            return StuckSignal(
                pattern=StuckPattern.NO_PROGRESS,
                confidence=0.8,
                context_diagnosis="No meaningful work being done",
                recommended_action=StuckAction.DECOMPOSE_TASK,
            )

        # Pattern 3: Circular tool usage
        if self._detect_circular_tools():
            return StuckSignal(
                pattern=StuckPattern.CIRCULAR_TOOLS,
                confidence=0.85,
                context_diagnosis="Reading same files repeatedly",
                recommended_action=StuckAction.PRUNE_CONTEXT,
            )

        return None
```

**Context Pruner:**

```python
# ralph_agi/memory/context_pruner.py
class ContextPruner:
    """Intelligently prune context when stuck detected."""

    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    async def prune(
        self,
        current_context: str,
        stuck_signal: StuckSignal,
        task: dict,
    ) -> str:
        """Prune context based on stuck diagnosis."""

        # Use small/fast model for pruning decisions
        prompt = f"""The agent is stuck with pattern: {stuck_signal.pattern.value}
Diagnosis: {stuck_signal.context_diagnosis}

Current task: {task.get('title')}

Current context ({len(current_context)} chars):
{current_context[:2000]}...

Extract ONLY the information essential to complete this specific task.
Remove: conversation history, completed steps, tangential information.
Keep: file contents being edited, error messages, acceptance criteria.

Return the pruned context:"""

        response = await self._llm.complete(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )

        return response.content
```

---

### Phase 2: Task Decomposition Agent (Sprint 7)

**Problem:** Complex tasks overwhelm single Builder iterations.

**Solution:** When stuck with `DECOMPOSE_TASK` signal, invoke `TaskDecomposer` to break task into subtasks.

```python
# ralph_agi/llm/task_decomposer.py
class TaskDecomposer:
    """Decomposes stuck tasks into manageable subtasks."""

    DECOMPOSITION_PROMPT = """You are a task decomposition specialist.

The following task is too complex for a single agent iteration:

TASK: {title}
DESCRIPTION: {description}
ACCEPTANCE CRITERIA:
{acceptance_criteria}

STUCK REASON: {stuck_diagnosis}

Break this into 2-4 smaller, independent subtasks that:
1. Can be completed in a single iteration each
2. Have clear, testable acceptance criteria
3. Build on each other sequentially
4. Together fully satisfy the original task

Return as JSON array:
[
  {{"id": "subtask-1", "title": "...", "description": "...", "acceptance_criteria": [...]}},
  ...
]"""

    async def decompose(
        self,
        task: dict,
        stuck_signal: StuckSignal,
    ) -> list[dict]:
        """Decompose task into subtasks."""

        prompt = self.DECOMPOSITION_PROMPT.format(
            title=task.get("title"),
            description=task.get("description"),
            acceptance_criteria="\n".join(f"- {ac}" for ac in task.get("acceptance_criteria", [])),
            stuck_diagnosis=stuck_signal.context_diagnosis,
        )

        response = await self._llm.complete(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )

        subtasks = json.loads(response.content)

        # Link subtasks to parent
        for st in subtasks:
            st["parent_task_id"] = task.get("id")
            st["is_subtask"] = True

        return subtasks
```

**Integration with Loop:**

```python
# In core/loop.py
async def _execute_iteration(self) -> IterationResult:
    # ... existing code ...

    result = await self._orchestrator.execute_iteration(...)

    # Check for stuck patterns
    stuck_signal = self._stuck_detector.analyze(result)

    if stuck_signal:
        if stuck_signal.recommended_action == StuckAction.PRUNE_CONTEXT:
            # Prune and retry
            pruned_context = await self._context_pruner.prune(
                current_context=project_context,
                stuck_signal=stuck_signal,
                task=task_dict,
            )
            # Retry with pruned context
            result = await self._orchestrator.execute_iteration(
                task=task_dict,
                context=pruned_context,  # Use pruned context
                ...
            )

        elif stuck_signal.recommended_action == StuckAction.DECOMPOSE_TASK:
            # Decompose into subtasks
            subtasks = await self._task_decomposer.decompose(task_dict, stuck_signal)

            # Insert subtasks before current task
            for subtask in reversed(subtasks):
                self._task_executor.insert_task(subtask, before=task.id)

            # Mark original task as "decomposed" (skip)
            self._task_executor.mark_decomposed(task.id)

            return IterationResult(
                success=True,
                output=f"Decomposed into {len(subtasks)} subtasks",
                task_id=task.id,
            )
```

---

### Phase 3: LLM-Based Summary Compression (Sprint 8)

**Problem:** `_default_summarizer()` in `memory/compaction.py` uses char truncation, not semantic compression.

**Solution:** Enable `create_llm_summarizer()` with proper implementation.

```python
# ralph_agi/memory/compaction.py

def create_llm_summarizer(
    llm_client: LLMClient,
    model: str = "haiku",
    max_tokens: int = 500,
) -> Summarizer:
    """Create an LLM-based summarizer for context compaction."""

    async def llm_summarizer(frames: list[MemoryFrame]) -> str:
        """Summarize frames using LLM with semantic compression."""
        if not frames:
            return ""

        # Build frame digest
        frame_digest = []
        for frame in frames:
            frame_digest.append(f"[{frame.frame_type}] {frame.content[:500]}")

        prompt = f"""You are a context compaction agent. Your job is to create
a HIGHLY COMPRESSED summary that preserves essential information for future tasks.

FRAMES TO SUMMARIZE ({len(frames)} total):
{chr(10).join(frame_digest)}

RULES:
1. Preserve ALL error messages and their solutions
2. Preserve ALL decisions made and their rationale
3. Preserve file paths and key code patterns
4. REMOVE conversational fluff, status updates, routine operations
5. Use bullet points, not paragraphs
6. Target: 20% of original size

OUTPUT FORMAT:
## Key Decisions
- ...

## Errors & Solutions
- ...

## Modified Files
- ...

## Critical Context
- ..."""

        response = await llm_client.complete(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )

        return response.content

    return llm_summarizer
```

---

## Implementation Plan

### Sprint 6: Stuck Detection & Context Pruning

| Story | Points | Description                                        |
| ----- | ------ | -------------------------------------------------- |
| 6.1   | 3      | Implement `StuckDetector` with pattern recognition |
| 6.2   | 3      | Implement `ContextPruner` with LLM-based pruning   |
| 6.3   | 2      | Integrate into `RalphLoop` with retry logic        |
| 6.4   | 2      | Add metrics/logging for stuck detection            |

### Sprint 7: Task Decomposition

| Story | Points | Description                             |
| ----- | ------ | --------------------------------------- |
| 7.1   | 3      | Implement `TaskDecomposer` agent        |
| 7.2   | 3      | Add subtask insertion to `TaskExecutor` |
| 7.3   | 2      | Handle decomposed task state in PRD     |
| 7.4   | 2      | Add tests for decomposition flow        |

### Sprint 8: LLM Summary Compression

| Story | Points | Description                         |
| ----- | ------ | ----------------------------------- |
| 8.1   | 2      | Implement `create_llm_summarizer()` |
| 8.2   | 2      | Integrate with `ContextCompactor`   |
| 8.3   | 2      | Add compaction metrics and config   |
| 8.4   | 2      | Test token reduction effectiveness  |

---

## Consequences

### Positive

- **Eliminates brute-force retry** - intelligent recovery from stuck states
- **Reduces context bloat** - semantic compression vs char truncation
- **Handles complex tasks** - automatic decomposition when overwhelmed
- **Aligns with Alexander's insight** - proper context framework design

### Negative

- **Increased LLM calls** - pruning/decomposition use additional API calls
- **Added complexity** - more moving parts in orchestration
- **Latency** - stuck detection adds overhead per iteration

### Mitigation

- Use fast/cheap models (Haiku) for pruning and summarization
- Cache stuck patterns to avoid redundant detection
- Make all features configurable via `config.yaml`

---

## Configuration

```yaml
# config.yaml additions
orchestration:
  stuck_detection:
    enabled: true
    history_window: 5
    patterns:
      - repetitive_output
      - no_progress
      - circular_tools

  context_pruning:
    enabled: true
    model: "haiku"
    max_pruned_tokens: 2000

  task_decomposition:
    enabled: true
    max_subtasks: 4
    model: "sonnet"

memory:
  compaction:
    enabled: true
    summarizer: "llm" # or "default" for char truncation
    summarizer_model: "haiku"
    max_summary_tokens: 500
```

---

## References

- Alexander Conroy conversation (2026-01-18)
- ADR-002: Multi-Agent Architecture
- `ralph_agi/memory/compaction.py` - existing compaction implementation
- `ralph_agi/core/loop.py` - current retry logic
