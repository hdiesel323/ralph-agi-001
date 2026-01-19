# ADR-005: Workflow Control Architecture (Supersedes ADR-004)

**Date:** 2026-01-17
**Status:** Approved
**Supersedes:** ADR-004 (TUI-First)

---

## Context

ADR-004 proposed a TUI-first architecture focused on **observation** - watching logs, viewing metrics, displaying status. However, this misses the core value proposition: users need to **control** RALPH-AGI, not just watch it.

**Key Insight:** The "sip coffee" workflow requires:

1. Drop tickets into a board
2. RALPH picks them up automatically
3. Parallel execution (3 tickets → 3 PRs)
4. Auto-merge based on confidence
5. Notification when done

A passive TUI viewer doesn't enable this. We need a **Workflow Control Architecture**.

---

## Decision: Control-First Architecture

We will build a **control-first** interface that enables the autonomous "sip coffee" workflow. Observation features (logs, metrics) are secondary to control features (task creation, execution triggers, approvals).

### Architecture Pillars

| Pillar                 | Description                                         | Priority |
| ---------------------- | --------------------------------------------------- | -------- |
| **Task Intake**        | Kanban board, visual PRD editor, GitHub/Linear sync | P0       |
| **Parallel Execution** | Git worktree isolation, batch processing            | P0       |
| **Autonomy Dial**      | Confidence scoring, auto-merge thresholds           | P0       |
| **Notifications**      | Slack/Discord/Telegram when PRs ready               | P1       |
| **Observation**        | Logs, metrics, status (the old TUI scope)           | P2       |

### Phase 1: Control Foundation (Weeks 9-12)

**Goal:** Enable the "sip coffee" workflow with minimal UI.

**Deliverables:**

1. **Task Queue System**
   - YAML/JSON task files in `.ralph/tasks/`
   - Watch directory for new tasks
   - Status: pending → running → complete/failed

2. **Git Worktree Manager**
   - Create isolated worktree per task
   - Parallel execution (configurable concurrency)
   - Auto-cleanup after merge

3. **Confidence & Auto-Merge**
   - Confidence scoring from Critic agent
   - Threshold-based auto-merge (e.g., >0.9 = auto-merge)
   - Manual review queue for low-confidence PRs

4. **Notification Webhooks**
   - Configurable endpoints (Slack, Discord, Telegram)
   - Events: task_started, pr_created, pr_merged, error

**CLI Interface:**

```bash
ralph queue add "Add dark mode toggle"      # Add task to queue
ralph queue list                            # Show queue status
ralph start --parallel=3                    # Process 3 tasks in parallel
ralph config set auto-merge-threshold 0.85 # Set autonomy dial
```

### Phase 2: Visual Control (Weeks 13-16)

**Goal:** Web UI for visual task management and control.

**Deliverables:**

1. **Kanban Board**
   - Columns: Backlog → Ready → Running → Review → Done
   - Drag-drop task management
   - Real-time status updates via WebSocket

2. **Visual Task Editor**
   - Form-based task creation (no JSON editing)
   - Template library for common task types
   - Acceptance criteria builder

3. **Pinned Commands / Recipes**
   - Save common workflows as 1-click buttons
   - Examples: "Run tests", "Deploy staging", "Create PR"
   - Keyboard shortcuts (Cmd+1, Cmd+2, etc.)

4. **Quick Actions Bar**
   - Pause/Resume all
   - Emergency stop
   - Merge all approved
   - Clear completed

### Phase 3: Full Dashboard (Weeks 17-20)

**Goal:** Unified dashboard combining control and observation.

**Deliverables:**

1. **Dashboard Layout**
   - Kanban board (main view)
   - Activity feed (side panel)
   - Metrics summary (header)

2. **Observation Panel** (moved from TUI)
   - Log viewer with filters
   - Agent reasoning viewer
   - Cost/time metrics

3. **Settings & Configuration**
   - Visual config editor
   - Provider management (API keys)
   - Notification preferences

---

## Key Differences from ADR-004

| Aspect            | ADR-004 (TUI-First) | ADR-005 (Control-First)                   |
| ----------------- | ------------------- | ----------------------------------------- |
| Primary Goal      | Watch RALPH work    | Control RALPH's work                      |
| First Deliverable | Terminal log viewer | Task queue + parallel execution           |
| User Action       | Observe             | Create tasks, set thresholds, approve PRs |
| Autonomy          | Manual              | Configurable auto-merge                   |
| Parallelism       | Single task         | Multiple worktrees                        |
| Time to Value     | 4 weeks (viewer)    | 4 weeks (full workflow)                   |

---

## Implementation Priority

### Sprint 9: Task Queue & Worktree Manager

- Story: Task file format and watcher
- Story: Git worktree creation/cleanup
- Story: Parallel task executor
- Story: Basic CLI (`ralph queue`, `ralph start`)

### Sprint 10: Confidence & Notifications

- Story: Confidence scoring integration
- Story: Auto-merge logic with thresholds
- Story: Webhook notification system
- Story: Telegram/Slack integration

### Sprint 11-12: Kanban Board

- Story: FastAPI backend for task management
- Story: React kanban board component
- Story: WebSocket real-time updates
- Story: Visual task editor

### Sprint 13+: Dashboard & Polish

- Story: Unified dashboard layout
- Story: Observation panel (logs, metrics)
- Story: Pinned commands/recipes
- Story: Settings UI

---

## Technical Stack

| Component     | Technology           | Rationale                            |
| ------------- | -------------------- | ------------------------------------ |
| Task Queue    | File-based YAML/JSON | Simple, git-friendly, no DB needed   |
| Worktrees     | `git worktree` CLI   | Native git, proven isolation         |
| Backend API   | FastAPI (Python)     | Same language as core, async support |
| Frontend      | React + TypeScript   | Rich ecosystem, real-time capable    |
| Real-time     | WebSocket            | Low latency status updates           |
| Notifications | Webhooks             | Universal, works with any service    |

---

## Consequences

**Positive:**

- Enables true autonomous "sip coffee" workflow
- Parallel execution dramatically increases throughput
- Users control RALPH, not just watch it
- Clear path from CLI to full web UI

**Negative:**

- More complex than passive TUI
- Requires careful worktree management
- Auto-merge needs robust confidence scoring

---

## References

- RalphBlaster demo: @saasmakermac
- Sizzy Claude Code UI: @thekitze
- Original Ralph Wiggum: @ghuntley
- [ADR-004: TUI-First Architecture](./2026-01-12_solutioning_frontend-architecture-v2_approved.md) (superseded)
