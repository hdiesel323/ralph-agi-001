# RALPH-AGI Project Context

> Critical rules and patterns for AI agents working on this codebase.
> Last updated: 2026-01-10

## Project Identity

- **Name:** RALPH-AGI (Recursive Autonomous Long-horizon Processing with Hierarchical AGI-like Intelligence)
- **Type:** Autonomous AI Agent System
- **Language:** Python 3.11+
- **Stage:** Phase 1 - Proof of Concept

## Core Concept: The Ralph Wiggum Pattern

The system is built on a deceptively simple principle: **a for loop is often more effective than complex orchestration systems** when working with capable foundation models.

```
while (iteration < max && !complete):
    1. Load Context
    2. Select Task (highest priority, no blockers)
    3. Execute Task (one feature only)
    4. Verify (cascaded evaluation)
    5. Update State (PRD + progress + git commit)
    6. Check Completion
```

**Key Insight:** LLMs produce lower-quality output as more tokens are added. Keep each iteration focused on a SINGLE, SMALL task.

## Architecture Overview

```
RALPH-AGI
├── Control Plane (CLI/API, Config, Scheduler, Monitor)
├── Orchestration Layer (Ralph Loop Engine, Agents)
├── Task Manager (PRD.json, Dependency Graph)
├── Memory System (Short/Medium/Long-term)
├── Tool Registry (MCP dynamic discovery)
├── Evaluation Pipeline (5-stage cascade)
└── Persistence Layer (Git, SQLite, Chroma)
```

## Critical Rules

### 1. Single Feature Per Iteration

- NEVER work on multiple features in one loop iteration
- Complete one feature fully before moving to next
- This prevents context bloat and maintains quality

### 2. PRD.json is Sacred

- ONLY change the `passes` field from `false` to `true`
- NEVER delete or modify feature descriptions
- NEVER remove tests or acceptance criteria

### 3. Append-Only Progress

- `progress.txt` is APPEND-ONLY
- Never overwrite, only add new entries
- Each entry should note: work done, decisions, issues, next steps

### 4. Git Commit After Each Feature

- Every successful feature = one commit
- Descriptive commit messages following: `feat: {description}`
- Enables recovery via `git revert` if needed

### 5. Fail Fast Evaluation

- Run cheap checks first (syntax, types)
- Only proceed to expensive checks (E2E, LLM Judge) if cheap ones pass
- If any stage fails, fix before retrying

## File Structure (Target)

```
ralph-agi/
├── src/
│   ├── core/
│   │   ├── loop.py           # Ralph Loop Engine
│   │   ├── agents/
│   │   │   ├── initializer.py
│   │   │   └── coding.py
│   │   └── config.py
│   ├── task/
│   │   ├── prd.py            # PRD.json management
│   │   └── dependency.py     # Dependency graph
│   ├── memory/
│   │   ├── short_term.py     # progress.txt
│   │   ├── medium_term.py    # Git integration
│   │   └── long_term.py      # SQLite + Chroma
│   ├── tools/
│   │   ├── registry.py       # MCP CLI integration
│   │   └── discovery.py
│   └── evaluation/
│       ├── pipeline.py       # Cascaded evaluation
│       └── stages/
├── tests/
├── prd.json                  # Feature requirements
├── progress.txt              # Session notes
└── config.yaml               # System configuration
```

## Technology Decisions

| Component      | Choice          | Rationale                     |
| -------------- | --------------- | ----------------------------- |
| Language       | Python 3.11+    | Rich AI/ML ecosystem          |
| LLM Primary    | Claude Sonnet 4 | Balance of capability/cost    |
| LLM Complex    | Claude Opus 4.5 | For architecture, debugging   |
| Database       | SQLite          | Simple, file-based, no server |
| Vector DB      | ChromaDB        | Local, Python-native          |
| Tool Discovery | MCP CLI         | 99% token reduction           |

## Key Patterns

### Completion Detection

```python
if "<promise>COMPLETE</promise>" in llm_output:
    # All tasks done, exit loop
```

### Task Selection

```python
# Filter: passes == false AND no blocking dependencies
# Sort by: priority (P0 > P1 > P2)
# Select: first matching task
```

### Memory Query

```python
# Short-term: Read progress.txt (last 50 lines)
# Medium-term: git log --oneline -20
# Long-term: Semantic search in Chroma
```

## Anti-Patterns to Avoid

1. **Over-engineering** - Simple bash loop > complex orchestration
2. **Multi-tasking** - One feature per iteration, always
3. **Context bloat** - Dynamic tool loading, not static
4. **Silent failures** - Always verify before marking complete
5. **Memory overwrites** - Append-only for progress tracking

## Reference Documents

- PRD: `client/public/RALPH-AGI-PRD-Final.md`
- Architecture: `client/public/RALPH-AGI-Technical-Architecture.md`
- Sample Loop: PRD Appendix B

## Success Metrics (from PRD)

| Metric               | Target                      |
| -------------------- | --------------------------- |
| Task Completion Rate | >85% (MVP), >95% (Q4)       |
| Human Interventions  | <2 per 10 hours             |
| Code Quality Score   | 8/10+ (LLM Judge)           |
| Context Efficiency   | 50% improvement over static |
