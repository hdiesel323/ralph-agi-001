# RALPH-AGI Frontend Mockups

**Date:** 2026-01-11
**Status:** Draft

---

## Overview

These mockups provide a visual representation of the RALPH-AGI frontend, based on the phased hybrid architecture defined in [ADR-003](./../decisions/2026-01-11_solutioning_frontend-architecture_approved.md).

---

## Mockup 1: Basic Dashboard (Phase 1)

```
┌────────────────────────────────────────────────────────┐
│  RALPH-AGI                    [User] [Settings] [Docs] │
├────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │ Active   │  │ Completed│  │  Failed  │  │  Cost  ││
│  │    3     │  │    47    │  │    2     │  │ $12.45 ││
│  └──────────┘  └──────────┘  └──────────┘  └────────┘│
├────────────────────────────────────────────────────────┤
│  Current Tasks                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ ● Implement login feature            [Stop]    │   │
│  │   Iteration 15/100 | 45% | $2.34              │   │
│  │   ▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░        │   │
│  └────────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────────┐   │
│  │ ● Write tests for auth                [Stop]   │   │
│  │   Iteration 8/50 | 16% | $0.89                 │   │
│  │   ▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░        │   │
│  └────────────────────────────────────────────────┘   │
├────────────────────────────────────────────────────────┤
│  Recent Activity                                       │
│  ✓ Deployed to staging (2 min ago)                    │
│  ✓ PR #123 created (5 min ago)                        │
│  ✗ Tests failed (8 min ago) [View Logs]               │
└────────────────────────────────────────────────────────┘
```

---

## Mockup 2: Chat Interface (Phase 2)

```
┌────────────────────────────────────────────────────────┐
│  Chat with Ralph                              [Clear]  │
├────────────────────────────────────────────────────────┤
│                                                        │
│  You: What's the status of the login feature?         │
│                                                        │
│  Ralph: The login feature is currently in progress.   │
│  I'm on iteration 15 of 100 (45% complete).           │
│  So far I've:                                          │
│  ✓ Created the login form component                   │
│  ✓ Implemented password validation                    │
│  ✓ Added JWT token generation                         │
│  ⏳ Currently writing tests                            │
│                                                        │
│  [View Code] [View Logs] [Stop Task]                  │
│                                                        │
│  You: Show me the test results                        │
│                                                        │
│  Ralph: Here are the latest test results:             │
│  ┌────────────────────────────────────────────────┐   │
│  │  Test Results                                  │   │
│  │  ✓ 83 passed                                   │   │
│  │  ✗ 2 failed                                    │   │
│  │  - test_password_reset_email                   │   │
│  │  - test_token_expiration                       │   │
│  │  [View Details] [Rerun Failed]                 │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
├────────────────────────────────────────────────────────┤
│  [Type a message...]                          [Send]   │
└────────────────────────────────────────────────────────┘
```

---

## Mockup 3: Hybrid Dashboard (Phase 4)

```
┌────────────────────────────────────────────────────────────────────────┐
│  RALPH-AGI                                      [User] [Settings] [Docs] │
├─────────────┬──────────────────────────────────────────────────────────┤
│  Sidebar    │  Main View                                               │
│             │                                                          │
│  Tasks      │  ┌────────────────────────────────────────────────────┐  │
│  Logs       │  │  Chat with Ralph                                    │  │
│  Config     │  ├────────────────────────────────────────────────────┤  │
│  Docs       │  │  You: Deploy to production                          │  │
│             │  │  Ralph: Ready to deploy. Please confirm.            │  │
│  Status:    │  │  ┌──────────────────────────────────────────────┐ │  │
│  ● Running  │  │  │  Deploy to Production                        │ │  │
│             │  │  │  Branch: main                                 │ │  │
│  Current:   │  │  │  Commit: 0a6a95c                              │ │  │
│  Feature X  │  │  │  [Confirm Deployment] [Cancel]                │ │  │
│  15/100     │  │  └──────────────────────────────────────────────┘ │  │
│             │  └────────────────────────────────────────────────────┘  │
│             │                                                          │
│             │  ┌────────────────────────────────────────────────────┐  │
│             │  │  Live Logs                                          │  │
│             │  │  [INFO] Starting deployment...                      │  │
│             │  │  [DEBUG] Running pre-flight checks...               │  │
│             │  │  [INFO] All checks passed.                          │  │
│             │  └────────────────────────────────────────────────────┘  │
└─────────────┴──────────────────────────────────────────────────────────┘
```
