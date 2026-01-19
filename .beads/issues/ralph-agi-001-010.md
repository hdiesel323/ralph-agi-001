---
id: ralph-agi-001-010
title: Intelligent Orchestration - Stuck Detection & Context Management
type: feature
status: proposed
priority: 1
labels: [orchestration, llm, context-management, core-loop]
created: 2026-01-18
updated: 2026-01-18
epic: epic-06-intelligent-orchestration
---

# Intelligent Orchestration - Stuck Detection & Context Management

## Problem Statement

Current RALPH-AGI uses brute-force retry when agents get stuck. The `_execute_with_retry()` in `core/loop.py` uses exponential backoff (1, 2, 4 seconds) but retries with **identical context**, expecting different results. This is inefficient and often fails.

**Key insight from Alexander Conroy:**

> "If you can craft the context framework properly you can avoid the [stuck] problem entirely... reduce context bloat, including summary information passed back to the main orchestrator so it doesn't get stuck."

## Proposed Solution

Implement a three-phase intelligent orchestration system:

### Phase 1: Stuck Detection & Context Pruning

- `StuckDetector` identifies patterns: repetitive output, no progress, circular tools
- `ContextPruner` uses LLM to intelligently reduce context when stuck
- Replaces blind retry with targeted recovery

### Phase 2: Task Decomposition

- When stuck with complex tasks, automatically decompose into subtasks
- Insert subtasks into PRD and continue with smaller scope
- Enables handling tasks that exceed single-iteration capacity

### Phase 3: LLM-Based Summary Compression

- Replace char truncation in `memory/compaction.py` with semantic compression
- Use Haiku for fast, cheap summarization
- Preserve decisions, errors, and key context while compressing routine operations

## User Stories

**As a** RALPH-AGI user running long autonomous sessions
**I want** the agent to recover intelligently from stuck states
**So that** I don't need to manually intervene when the agent loops

**As a** RALPH-AGI developer
**I want** context to be automatically managed
**So that** the agent can handle complex multi-step tasks without context overflow

## Acceptance Criteria

### Stuck Detection

- [ ] Detect repetitive output pattern (same response 3+ times)
- [ ] Detect no progress pattern (no file changes across 3+ iterations)
- [ ] Detect circular tool usage (reading same files repeatedly)
- [ ] Log stuck detection with pattern and confidence
- [ ] Provide recommended action per pattern

### Context Pruning

- [ ] Implement `ContextPruner` with LLM-based pruning
- [ ] Integrate with `StuckDetector` signals
- [ ] Configurable via `config.yaml`
- [ ] Measure token reduction achieved
- [ ] Retry with pruned context before escalating

### Task Decomposition

- [ ] Implement `TaskDecomposer` agent
- [ ] Generate 2-4 subtasks with acceptance criteria
- [ ] Insert subtasks into task queue
- [ ] Track parent-child task relationships
- [ ] Handle subtask failures gracefully

### LLM Summary Compression

- [ ] Implement `create_llm_summarizer()` in `memory/compaction.py`
- [ ] Preserve errors, decisions, file paths
- [ ] Target 80% token reduction vs original
- [ ] Configurable model (default: Haiku)
- [ ] Fallback to default summarizer on LLM failure

## Technical Design

### New Files

```
ralph_agi/
├── llm/
│   ├── stuck_detector.py      # StuckDetector, StuckSignal, StuckPattern
│   └── task_decomposer.py     # TaskDecomposer agent
└── memory/
    └── context_pruner.py      # ContextPruner with LLM-based pruning
```

### Configuration

```yaml
orchestration:
  stuck_detection:
    enabled: true
    history_window: 5
    patterns: [repetitive_output, no_progress, circular_tools]

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
    summarizer: "llm"
    summarizer_model: "haiku"
    max_summary_tokens: 500
```

### Integration Points

1. **core/loop.py**: Add stuck detection after each iteration
2. **llm/orchestrator.py**: Add context pruning before retry
3. **tasks/executor.py**: Add subtask insertion capability
4. **memory/compaction.py**: Replace default summarizer

## Dependencies

- **ADR-002**: Multi-Agent Architecture (Critic pattern)
- **ADR-003**: Intelligent Orchestration (this proposal)
- **Story 1.4**: Loop Engine (provides integration point)
- **Epic 03**: Memory System (provides compaction infrastructure)

## Effort Estimate

| Phase                       | Stories | Points | Sprint   |
| --------------------------- | ------- | ------ | -------- |
| Phase 1: Stuck Detection    | 4       | 10     | Sprint 6 |
| Phase 2: Task Decomposition | 4       | 10     | Sprint 7 |
| Phase 3: LLM Summarization  | 4       | 8      | Sprint 8 |

**Total:** 28 points across 3 sprints

## Testing

- [ ] Unit tests for `StuckDetector` pattern recognition
- [ ] Unit tests for `ContextPruner` with mock LLM
- [ ] Unit tests for `TaskDecomposer` output validation
- [ ] Integration test: stuck → prune → retry → success
- [ ] Integration test: stuck → decompose → subtasks → success
- [ ] Benchmark: token reduction with LLM summarizer

## Risks & Mitigations

| Risk                                | Mitigation                                |
| ----------------------------------- | ----------------------------------------- |
| Increased LLM costs                 | Use Haiku for pruning/summarization       |
| False positive stuck detection      | Configurable thresholds, human override   |
| Decomposition creates infinite loop | Max decomposition depth limit             |
| LLM summarizer loses critical info  | Preserve error/decision frames explicitly |

## References

- [ADR-003: Intelligent Orchestration](/rnd/decisions/2026-01-18_solutioning_intelligent-orchestration_proposed.md)
- Alexander Conroy conversation (2026-01-18)
- Current retry logic: `ralph_agi/core/loop.py:_execute_with_retry()`
- Current compaction: `ralph_agi/memory/compaction.py`
