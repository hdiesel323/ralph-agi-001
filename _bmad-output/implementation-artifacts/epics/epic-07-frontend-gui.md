# Epic 07: Workflow Control Interface

**PRD Reference:** FR-007
**Priority:** P0 (Critical - enables "sip coffee" workflow)
**Roadmap:** Weeks 9-20 (4 phases)
**Status:** Active
**Architecture:** [ADR-005](../../../rnd/decisions/2026-01-17_solutioning_frontend-architecture-v3_approved.md)

---

## Epic Overview

Build a **control-first** interface enabling the autonomous "sip coffee" workflow: drop tickets into a queue, RALPH processes them in parallel via git worktrees, auto-merges based on confidence, and notifies you when PRs are ready.

**Key Insight:** Users need to CONTROL RALPH, not just watch it. Observation (logs, metrics) is secondary to control (task creation, execution triggers, approvals).

## Business Value

- **3x Throughput:** Parallel execution via worktrees (3 tickets → 3 PRs in ~11 minutes)
- **True Autonomy:** Configurable auto-merge based on confidence scoring
- **"Sip Coffee" UX:** Human becomes ticket creator only, RALPH handles the rest
- **Immediate Notification:** Know when PRs are ready via Slack/Discord/Telegram

## Related Epics

- **ralph-agi-001-un6:** Execution Isolation & Parallelization (RalphBlaster)
- **ralph-agi-001-zow:** Visual Dev Experience (Sizzy/kitze)

---

## Phase 1: Control Foundation (Sprint 9-10)

### Story 7.1: Task Queue System
**Priority:** P0 | **Points:** 5

**As a** developer
**I want** to add tasks to a queue via CLI or files
**So that** RALPH can process them autonomously

**Acceptance Criteria:**
- [ ] Task file format: YAML in `.ralph/tasks/`
- [ ] File watcher for new task files
- [ ] Task status lifecycle: pending → running → complete/failed
- [ ] CLI: `ralph queue add "task description"`
- [ ] CLI: `ralph queue list` (show all tasks with status)
- [ ] Task validation (required fields, format checking)

**Technical Notes:**
```yaml
# .ralph/tasks/001-dark-mode.yaml
id: dark-mode-toggle
description: Add dark mode toggle to settings page
priority: P1
acceptance_criteria:
  - Toggle visible in settings
  - Persists preference to localStorage
  - System preference detection
status: pending
created_at: 2026-01-17T10:00:00Z
```

---

### Story 7.2: Git Worktree Manager
**Priority:** P0 | **Points:** 5

**As a** developer
**I want** each task to run in an isolated git worktree
**So that** multiple tasks can execute in parallel without conflicts

**Acceptance Criteria:**
- [ ] Create worktree: `git worktree add ../ralph-<task-id> -b ralph/<task-id>`
- [ ] Execute task in worktree directory
- [ ] Cleanup worktree after merge: `git worktree remove`
- [ ] Handle worktree failures gracefully
- [ ] Track active worktrees in state file
- [ ] Configurable worktree directory (default: `../ralph-worktrees/`)

**Technical Notes:**
```python
class WorktreeManager:
    def create(self, task_id: str) -> Path
    def execute_in_worktree(self, task_id: str, callback: Callable)
    def cleanup(self, task_id: str)
    def list_active(self) -> list[str]
```

---

### Story 7.3: Parallel Task Executor
**Priority:** P0 | **Points:** 5

**As a** developer
**I want** to process multiple tasks in parallel
**So that** I can complete more work in less time

**Acceptance Criteria:**
- [ ] Configurable concurrency: `ralph start --parallel=3`
- [ ] Task scheduling (respects dependencies)
- [ ] Progress tracking across all parallel tasks
- [ ] Graceful handling of individual task failures
- [ ] Resource limits (memory, CPU per worktree)
- [ ] CLI: `ralph start` (process all pending tasks)

**Technical Notes:**
- Use asyncio for concurrent execution
- Each worktree gets its own RalphLoop instance
- Shared state via file locks or SQLite

---

### Story 7.4: Confidence Scoring & Auto-Merge
**Priority:** P0 | **Points:** 5

**As a** developer
**I want** RALPH to auto-merge PRs when confidence is high
**So that** I don't have to review every change

**Acceptance Criteria:**
- [ ] Confidence score from Critic agent (0.0 - 1.0)
- [ ] Configurable threshold: `ralph config set auto-merge-threshold 0.85`
- [ ] Auto-merge when confidence >= threshold
- [ ] Manual review queue for low-confidence PRs
- [ ] Confidence factors: test pass rate, code review score, file complexity
- [ ] CLI: `ralph config get auto-merge-threshold`

**Confidence Calculation:**
```python
confidence = (
    0.4 * test_pass_rate +      # All tests pass = 1.0
    0.3 * critic_score +         # Critic approval = 1.0
    0.2 * acceptance_score +     # AC evaluator = 1.0
    0.1 * (1 - complexity_score) # Simple changes = higher
)
```

---

### Story 7.5: Notification Webhooks
**Priority:** P1 | **Points:** 3

**As a** developer
**I want** notifications when PRs are ready
**So that** I can review or celebrate without watching

**Acceptance Criteria:**
- [ ] Configurable webhook endpoints in `ralph.yaml`
- [ ] Events: task_started, pr_created, pr_merged, pr_needs_review, error
- [ ] Payload includes: task_id, pr_url, confidence, summary
- [ ] Retry logic for failed webhooks
- [ ] CLI: `ralph config set webhook.slack <url>`

---

### Story 7.6: Telegram/Slack Integration
**Priority:** P1 | **Points:** 3

**As a** developer
**I want** notifications in Telegram or Slack
**So that** I get notified on my preferred platform

**Acceptance Criteria:**
- [ ] Slack incoming webhook support
- [ ] Telegram bot API support
- [ ] Discord webhook support
- [ ] Rich message formatting (PR link, confidence, summary)
- [ ] Configuration via environment variables or config file

---

## Phase 2: Visual Control (Sprint 11-12)

### Story 7.7: FastAPI Backend
**Priority:** P0 | **Points:** 5

**As a** web user
**I want** a REST API for task management
**So that** web clients can control RALPH

**Acceptance Criteria:**
- [ ] FastAPI backend in `ralph_agi/api/`
- [ ] REST endpoints: `/tasks`, `/tasks/{id}`, `/queue`, `/config`
- [ ] WebSocket endpoint for real-time updates (`/ws/events`)
- [ ] Authentication (API key or JWT)
- [ ] OpenAPI documentation
- [ ] CORS configuration

---

### Story 7.8: Kanban Board UI
**Priority:** P0 | **Points:** 8

**As a** developer
**I want** a visual kanban board for task management
**So that** I can see and control all tasks at a glance

**Acceptance Criteria:**
- [ ] React + TypeScript + TailwindCSS
- [ ] Columns: Backlog → Ready → Running → Review → Done
- [ ] Drag-drop task movement
- [ ] Real-time status updates via WebSocket
- [ ] Task cards show: title, priority, confidence, PR link
- [ ] Click card for details modal

**Mockup:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  RALPH-AGI Control Board                    [+ New Task] [⚙ Config] │
├─────────────────────────────────────────────────────────────────────┤
│ BACKLOG (3)  │ READY (2)   │ RUNNING (2)  │ REVIEW (1) │ DONE (5)   │
│──────────────│─────────────│──────────────│────────────│────────────│
│ ┌──────────┐ │ ┌─────────┐ │ ┌──────────┐ │ ┌────────┐ │ ┌────────┐ │
│ │ Add auth │ │ │ Dark    │ │ │ Fix bug  │ │ │ Update │ │ │ ✓ Init │ │
│ │ P1       │ │ │ mode    │ │ │ #234     │ │ │ deps   │ │ │ setup  │ │
│ └──────────┘ │ │ P2      │ │ │ ██░░ 45% │ │ │ 0.72   │ │ └────────┘ │
│ ┌──────────┐ │ └─────────┘ │ └──────────┘ │ │ [View] │ │ ┌────────┐ │
│ │ Add API  │ │ ┌─────────┐ │ ┌──────────┐ │ └────────┘ │ │ ✓ Add  │ │
│ │ endpoint │ │ │ Refactor│ │ │ Add      │ │            │ │ tests  │ │
│ │ P2       │ │ │ utils   │ │ │ logging  │ │            │ └────────┘ │
│ └──────────┘ │ │ P3      │ │ │ ██████░  │ │            │            │
│              │ └─────────┘ │ │ 78%      │ │            │            │
│              │             │ └──────────┘ │            │            │
└──────────────┴─────────────┴──────────────┴────────────┴────────────┘
│ Running: 2/3 │ Auto-merge: 0.85 │ Cost: $2.34 │ PRs: 3 open, 5 merged │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Story 7.9: Visual Task Editor
**Priority:** P1 | **Points:** 5

**As a** developer
**I want** to create tasks via a form
**So that** I don't have to write YAML manually

**Acceptance Criteria:**
- [ ] Modal/drawer form for new task
- [ ] Fields: title, description, priority, acceptance criteria
- [ ] Template dropdown for common task types
- [ ] Acceptance criteria builder (add/remove items)
- [ ] Preview of generated task file
- [ ] Direct submit to queue

---

### Story 7.10: Pinned Commands / Recipes
**Priority:** P1 | **Points:** 5

**As a** developer
**I want** saved shortcuts for common workflows
**So that** I can execute them with one click

**Acceptance Criteria:**
- [ ] Recipe format in `ralph.yaml` or `.ralph/recipes/`
- [ ] Quick action buttons in UI header
- [ ] Keyboard shortcuts (Cmd+1, Cmd+2, etc.)
- [ ] Built-in recipes: "Run tests", "Deploy staging", "Merge all approved"
- [ ] Custom recipe creation via UI

---

### Story 7.11: Quick Actions Bar
**Priority:** P1 | **Points:** 3

**As a** developer
**I want** global control buttons
**So that** I can quickly pause, stop, or approve all

**Acceptance Criteria:**
- [ ] Pause/Resume all tasks
- [ ] Emergency stop (kill all worktrees)
- [ ] Merge all approved (confidence >= threshold)
- [ ] Clear completed tasks
- [ ] Refresh status

---

## Phase 3: Dashboard & Polish (Sprint 13-14)

### Story 7.12: Unified Dashboard Layout
**Priority:** P2 | **Points:** 5

**As a** developer
**I want** a dashboard combining control and observation
**So that** I have a single view of RALPH's activity

**Acceptance Criteria:**
- [ ] Kanban board (main area)
- [ ] Activity feed (right sidebar)
- [ ] Metrics bar (header)
- [ ] Collapsible panels
- [ ] Responsive design

---

### Story 7.13: Observation Panel
**Priority:** P2 | **Points:** 5

**As a** developer
**I want** to see logs and agent output
**So that** I can debug issues when needed

**Acceptance Criteria:**
- [ ] Log viewer with level filters (DEBUG, INFO, WARN, ERROR)
- [ ] Agent reasoning viewer (Builder/Critic output)
- [ ] Task timeline (events for selected task)
- [ ] Auto-scroll with pause on hover

---

### Story 7.14: Settings UI
**Priority:** P2 | **Points:** 3

**As a** developer
**I want** to configure RALPH via UI
**So that** I don't have to edit YAML files

**Acceptance Criteria:**
- [ ] Auto-merge threshold slider
- [ ] Parallel execution limit
- [ ] Notification preferences
- [ ] API key management
- [ ] Theme (dark/light)

---

### Story 7.15: Testing & Launch
**Priority:** P2 | **Points:** 5

**As a** developer
**I want** a polished, well-tested interface
**So that** it works reliably

**Acceptance Criteria:**
- [ ] E2E tests for critical workflows
- [ ] Integration tests for API
- [ ] Performance audit
- [ ] Accessibility audit
- [ ] Documentation

---

## Dependencies

- **Epic 01:** Core Execution Loop (task execution)
- **Epic 04:** Tool Integration (git operations)
- **Epic 05:** Evaluation Pipeline (confidence scoring)

## Story Point Summary

| Phase | Stories | Points |
|-------|---------|--------|
| Phase 1: Control Foundation | 7.1-7.6 | 26 |
| Phase 2: Visual Control | 7.7-7.11 | 26 |
| Phase 3: Dashboard & Polish | 7.12-7.15 | 18 |
| **Total** | **15 stories** | **70 points** |

## Definition of Done

- [ ] `ralph queue add` and `ralph start --parallel=3` working
- [ ] Tasks execute in isolated worktrees
- [ ] Auto-merge works based on confidence threshold
- [ ] Notifications sent to configured webhooks
- [ ] Kanban board shows real-time task status
- [ ] Visual task editor creates valid task files
- [ ] 90%+ test coverage on new modules
