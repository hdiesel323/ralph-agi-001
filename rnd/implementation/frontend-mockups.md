# RALPH-AGI Frontend Mockups

**Date:** 2026-01-12
**Status:** Draft
**Updated:** Based on [ADR-004](../decisions/2026-01-12_solutioning_frontend-architecture-v2_approved.md)

---

## Overview

These mockups provide a visual representation of the RALPH-AGI frontend, based on the **TUI-first hybrid architecture** defined in ADR-004. The design is inspired by [Relentless](https://github.com/ArvorCo/Relentless).

---

## Phase 1: Terminal User Interface (TUI)

### Mockup 1.1: Main TUI Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RALPH-AGI v0.1.0                                    Ctrl+P: Commands  q: Quit │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Stories ────────────────────────────┐ ┌─ Metrics ─────────────────────┐ │
│ │ ● 2.1 PRD.json Parser      DONE ✓   │ │ Iterations:    15/100         │ │
│ │ ● 2.2 Task Selection       DONE ✓   │ │ Cost:          $2.34          │ │
│ │ ● 2.4 Task Completion      DONE ✓   │ │ Time:          00:45:22       │ │
│ │ ▶ 2.5 Single Feature    RUNNING     │ │ Tokens:        125,432        │ │
│ │ ○ 2.6 Docker Isolation    PENDING   │ │ Velocity:      9.2 pts/sprint │ │
│ │ ○ 3.1 Memvid Core         PENDING   │ └────────────────────────────────┘ │
│ └──────────────────────────────────────┘                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Agent Output ────────────────────────────────────────────────────────────┐│
│ │ [Iteration 15] Working on: Implement single feature constraint            ││
│ │                                                                           ││
│ │ > Reading tests/tasks/test_executor.py...                                 ││
│ │ > Found 24 test cases, 23 passing, 1 failing                              ││
│ │ > Analyzing failing test: test_feature_constraint_with_deps               ││
│ │ > The issue is in the dependency resolution when max_size is reached      ││
│ │ > Proposing fix: Add size check before adding dependent tasks             ││
│ │                                                                           ││
│ └───────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Logs ─────────────────────────────────────────────────────────────────────┐│
│ │ 23:42:15 [INFO ] Starting iteration 15...                                  ││
│ │ 23:42:16 [DEBUG] Loading context (2,450 tokens)...                         ││
│ │ 23:42:17 [INFO ] Calling Claude claude-opus-4-5-20251101...                            ││
│ │ 23:42:35 [INFO ] Response received (18s, 3,200 tokens)                     ││
│ │ 23:42:35 [INFO ] Executing tool: Read tests/tasks/test_executor.py        ││
│ │ 23:42:36 [DEBUG] Tool result: 142 lines read                               ││
│ │ 23:42:36 [INFO ] Analyzing test results...                                 ││
│ └───────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ Story 2.5 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 45%  ETA: 32m │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Mockup 1.2: Command Palette (Ctrl+P)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RALPH-AGI v0.1.0                                    Ctrl+P: Commands  q: Quit │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                    ┌─ Commands ─────────────────────────────┐               │
│                    │ > _                                    │               │
│                    ├────────────────────────────────────────┤               │
│                    │ ▶ pause     Pause current task         │               │
│                    │   resume    Resume paused task         │               │
│                    │   stop      Stop and save progress     │               │
│                    │   restart   Restart current iteration  │               │
│                    │   config    Open configuration         │               │
│                    │   logs      Toggle log view            │               │
│                    │   help      Show keyboard shortcuts    │               │
│                    └────────────────────────────────────────┘               │
│                                                                              │
│ [↑↓ Navigate]  [Enter Select]  [Esc Cancel]                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Mockup 1.3: Error State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RALPH-AGI v0.1.0                                    Ctrl+P: Commands  q: Quit │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Stories ────────────────────────────┐ ┌─ Metrics ─────────────────────┐ │
│ │ ● 2.1 PRD.json Parser      DONE ✓   │ │ Iterations:    23/100         │ │
│ │ ● 2.2 Task Selection       DONE ✓   │ │ Cost:          $4.12          │ │
│ │ ● 2.4 Task Completion      DONE ✓   │ │ Time:          01:12:45       │ │
│ │ ✗ 2.5 Single Feature      FAILED    │ │ Tokens:        245,891        │ │
│ │ ○ 2.6 Docker Isolation    PENDING   │ │ Errors:        3              │ │
│ └──────────────────────────────────────┘ └────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Error Details ──────────────────────────────────────────────────────────┐ │
│ │ ✗ FATAL: Maximum iterations (100) exceeded without completion             │ │
│ │                                                                           │ │
│ │ Last working state saved to: .ralph/checkpoints/story-2.5-iter-23.json   │ │
│ │                                                                           │ │
│ │ Suggested actions:                                                        │ │
│ │   1. Review logs for repeated patterns (possible loop)                    │ │
│ │   2. Check if task scope is too large (consider splitting)                │ │
│ │   3. Resume from checkpoint with `ralph resume story-2.5`                 │ │
│ │                                                                           │ │
│ │ [View Full Logs]  [Resume]  [Skip Task]  [Report Bug]                    │ │
│ └───────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 2: Hybrid Web UI

### Mockup 2.1: Web Dashboard with Embedded TUI

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  RALPH-AGI                                         [User] [Settings] [Docs]    │
├─────────────┬──────────────────────────────────────────────────────────────────┤
│             │                                                                  │
│  Dashboard  │  ┌─ Embedded TUI ───────────────────────────────────────────┐   │
│             │  │                                                          │   │
│  Projects   │  │  ┌─ Stories ─────────────┐ ┌─ Metrics ────────────────┐ │   │
│             │  │  │ ● 2.1 Parser   DONE ✓│ │ Iterations: 15/100       │ │   │
│  History    │  │  │ ▶ 2.2 Select RUNNING │ │ Cost: $2.34              │ │   │
│             │  │  │ ○ 2.4 Mark   PENDING │ │ Time: 00:45:22           │ │   │
│  Settings   │  │  └──────────────────────┘ └────────────────────────────┘ │   │
│             │  │                                                          │   │
│  ───────    │  │  > Analyzing task dependencies...                        │   │
│             │  │  > Found 3 ready tasks, selecting by priority            │   │
│  Status:    │  │  > Working on: Task Selection Algorithm                  │   │
│  ● Running  │  │                                                          │   │
│             │  │  [23:42:15] Starting iteration 15...                     │   │
│  Cost:      │  │  [23:42:16] Loading context (2,450 tokens)...            │   │
│  $2.34      │  │  [23:42:17] Calling Claude claude-opus-4-5-20251101...                   │   │
│             │  │                                                          │   │
│  Time:      │  └──────────────────────────────────────────────────────────┘   │
│  00:45:22   │                                                                  │
│             │  [Full Screen TUI]  [Pause]  [Stop]                              │
└─────────────┴──────────────────────────────────────────────────────────────────┘
```

### Mockup 2.2: Chat Interface (AG-UI)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  RALPH-AGI                                         [User] [Settings] [Docs]    │
├─────────────┬──────────────────────────────────────────────────────────────────┤
│             │                                                                  │
│  Dashboard  │  ┌─ Chat with Ralph ─────────────────────────────────────────┐   │
│             │  │                                                           │   │
│  Chat ◄     │  │  You: What's the status of the login feature?            │   │
│             │  │                                                           │   │
│  TUI        │  │  Ralph: The login feature is currently in progress.      │   │
│             │  │  I'm on iteration 15 of 100 (45% complete).              │   │
│  History    │  │                                                           │   │
│             │  │  So far I've:                                             │   │
│  Settings   │  │  ✓ Created the login form component                      │   │
│             │  │  ✓ Implemented password validation                       │   │
│  ───────    │  │  ✓ Added JWT token generation                            │   │
│             │  │  ⏳ Currently writing tests                               │   │
│  Status:    │  │                                                           │   │
│  ● Running  │  │  [View Code]  [View Logs]  [Stop Task]                   │   │
│             │  │                                                           │   │
│  Cost:      │  │  You: Show me the test results                           │   │
│  $2.34      │  │                                                           │   │
│             │  │  Ralph: Here are the latest test results:                │   │
│  Time:      │  │  ┌────────────────────────────────────────────────────┐  │   │
│  00:45:22   │  │  │  Test Results                     83 passed, 2 failed │  │   │
│             │  │  │  ✗ test_password_reset_email                       │  │   │
│             │  │  │  ✗ test_token_expiration                           │  │   │
│             │  │  │  [View Details]  [Rerun Failed]                     │  │   │
│             │  │  └────────────────────────────────────────────────────┘  │   │
│             │  │                                                           │   │
│             │  ├───────────────────────────────────────────────────────────┤   │
│             │  │  [Type a message...]                              [Send]  │   │
│             │  └───────────────────────────────────────────────────────────┘   │
└─────────────┴──────────────────────────────────────────────────────────────────┘
```

### Mockup 2.3: Human-in-the-Loop Approval

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  RALPH-AGI                                         [User] [Settings] [Docs]    │
├─────────────┬──────────────────────────────────────────────────────────────────┤
│             │                                                                  │
│  Dashboard  │  ┌─ Chat with Ralph ─────────────────────────────────────────┐   │
│             │  │                                                           │   │
│  Chat ◄     │  │  You: Deploy to production                               │   │
│             │  │                                                           │   │
│  TUI        │  │  Ralph: Ready to deploy. This will:                      │   │
│             │  │  • Push to main branch                                   │   │
│  History    │  │  • Trigger CI/CD pipeline                                │   │
│             │  │  • Deploy to production servers                          │   │
│  Settings   │  │                                                           │   │
│             │  │  Please confirm this action:                              │   │
│  ───────    │  │                                                           │   │
│             │  │  ┌────────────────────────────────────────────────────┐  │   │
│  Status:    │  │  │  ⚠️  Deploy to Production                           │  │   │
│  ⚠ Waiting  │  │  │                                                    │  │   │
│             │  │  │  Branch:    main                                    │  │   │
│  Approval   │  │  │  Commit:    0a6a95c "Add login feature"            │  │   │
│  Required   │  │  │  Tests:     ✓ 645 passed                           │  │   │
│             │  │  │  Coverage:  92%                                     │  │   │
│             │  │  │                                                    │  │   │
│             │  │  │  [✓ Confirm Deployment]    [✗ Cancel]              │  │   │
│             │  │  └────────────────────────────────────────────────────┘  │   │
│             │  │                                                           │   │
│             │  ├───────────────────────────────────────────────────────────┤   │
│             │  │  [Type a message...]                              [Send]  │   │
│             │  └───────────────────────────────────────────────────────────┘   │
└─────────────┴──────────────────────────────────────────────────────────────────┘
```

### Mockup 2.4: Generative UI - Dynamic Dashboard

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  RALPH-AGI                                         [User] [Settings] [Docs]    │
├─────────────┬──────────────────────────────────────────────────────────────────┤
│             │                                                                  │
│  Dashboard◄ │  Ralph generated this dashboard based on your recent activity:  │
│             │                                                                  │
│  Chat       │  ┌─ Sprint Progress ──────┐  ┌─ Cost Breakdown ──────────────┐  │
│             │  │                        │  │                               │  │
│  TUI        │  │  Sprint 5: Tool Int.   │  │  ████████░░  Claude: $18.45  │  │
│             │  │  ▓▓▓▓▓▓▓▓░░░░ 67%     │  │  ██░░░░░░░░  GPT-4: $3.20    │  │
│  History    │  │                        │  │  █░░░░░░░░░  Embedding: $0.89 │  │
│             │  │  11/16 points done     │  │                               │  │
│  Settings   │  │  ETA: 2 days           │  │  Total: $22.54                │  │
│             │  └────────────────────────┘  └───────────────────────────────┘  │
│  ───────    │                                                                  │
│             │  ┌─ Test Coverage Trend ────────────────────────────────────┐   │
│  Status:    │  │                                                          │   │
│  ● Running  │  │  100% ┤                                          ╭────   │   │
│             │  │   90% ┤                              ╭────────────╯       │   │
│  Sprint 5   │  │   80% ┤              ╭───────────────╯                    │   │
│  67%        │  │   70% ┤  ╭───────────╯                                    │   │
│             │  │   60% ┼──╯                                                │   │
│             │  │       └────────────────────────────────────────────────   │   │
│             │  │         Sprint 1   Sprint 2   Sprint 3   Sprint 4   S5   │   │
│             │  └──────────────────────────────────────────────────────────┘   │
│             │                                                                  │
│             │  [Customize Dashboard]  [Export Report]  [Share]                │
└─────────────┴──────────────────────────────────────────────────────────────────┘
```

---

## Design Principles

1. **TUI-First:** The TUI is the primary interface, optimized for developer workflows
2. **Information Density:** Show maximum relevant information without clutter
3. **Real-Time:** All views update in real-time via WebSocket/async
4. **Keyboard-First:** All actions accessible via keyboard shortcuts
5. **Consistent Status:** Status indicators (colors, icons) are consistent across all views

## Color Scheme (TUI)

- **Green:** Success, completed, passing
- **Yellow:** Warning, in-progress, pending
- **Red:** Error, failed, blocked
- **Blue:** Information, active selection
- **Gray:** Disabled, deferred, not started

---

## References

- [ADR-004: Frontend Architecture v2](../decisions/2026-01-12_solutioning_frontend-architecture-v2_approved.md)
- [Relentless TUI](https://github.com/ArvorCo/Relentless)
- [Textual Framework](https://textual.textualize.io/)
