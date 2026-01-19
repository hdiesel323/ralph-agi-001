---
id: ralph-agi-001-003
title: Implement Context Compacting for Memory Management
type: feature
status: open
priority: 1
labels: [memory, context-management, token-efficiency, clawdbot-inspired]
created: 2026-01-10
epic: epic-03-memory-system
source: rnd/research/2026-01-10_clawdbot-patterns-analysis.md
---

# Implement Context Compacting for Memory Management

## Problem Statement

When context windows fill up during long-running tasks, we need intelligent prioritization of what to keep. Current approach relies on Memvid's hybrid search (semantic + BM25), but doesn't handle summarization/compaction of older content.

## Proposed Solution

Implement context compacting inspired by Clawdbot's approach:

1. **Compaction Strategy**

   ```
   Recent (last N iterations)  → Full detail
   Medium (N to 2N iterations) → Summarized
   Old (>2N iterations)        → Key points only / archived
   ```

2. **Compaction Pipeline**

   ```python
   def compact_context(frames, threshold):
       recent = frames[-threshold:]  # Keep full
       older = frames[:-threshold]

       # Summarize older frames
       summaries = llm.summarize(older, style="bullet_points")

       # Store both in Memvid (raw archived, summary active)
       memory.archive(older)
       memory.store(summaries, type="compacted")

       return recent + summaries
   ```

3. **Config Options**
   ```yaml
   memory:
     compaction:
       enabled: true
       threshold_frames: 50
       summary_model: "haiku" # Use cheap model for summaries
       preserve_errors: true # Always keep full error context
       preserve_decisions: true # Keep architectural decisions full
   ```

## Acceptance Criteria

- [ ] Compaction threshold configuration
- [ ] LLM-based summarization of older frames
- [ ] Archive original frames (don't delete)
- [ ] Preserve full detail for errors and decisions
- [ ] Integration with Story 3.6 Memory Query API
- [ ] Token usage tracking before/after compaction
- [ ] Unit tests for compaction logic
- [ ] Benchmark: 50%+ token reduction on long sessions

## Technical Notes

- Use Haiku/fast model for summarization (cost efficiency)
- Preserve metadata even when compacting content
- Consider importance scoring: errors > decisions > progress > chatter
- Compaction should be idempotent (safe to run multiple times)

## Dependencies

- Story 3.1: Memvid Core Integration
- Story 3.6: Memory Query API

## Effort Estimate

Points: 3

## References

- [Clawdbot Patterns Analysis](../../rnd/research/2026-01-10_clawdbot-patterns-analysis.md)
- [Memory System Epic](../../_bmad-output/implementation-artifacts/epics/epic-03-memory-system.md)
