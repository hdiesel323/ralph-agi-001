# Epic 07: Frontend GUI Architecture (TUI-First Hybrid)

**PRD Reference:** FR-007
**Priority:** P3 (Low - after core features)
**Roadmap:** Weeks 13-28 (Phase 1: TUI, Phase 2: Hybrid Web)
**Status:** Draft

---

## Epic Overview

Implement the RALPH-AGI frontend using a **TUI-first hybrid architecture**. Phase 1 delivers a rich Terminal User Interface built with Textual (Python). Phase 2 extends to a hybrid web UI that embeds the TUI via xterm.js while adding chat (AG-UI), human-in-the-loop approvals, and generative UI capabilities.

## Business Value

- **Developer-Native Experience:** TUI fits developer workflows naturally
- **Faster Time-to-Value:** TUI ships in 4 weeks vs 16 for full web UI
- **No Wasted Effort:** TUI embeds in web UI via xterm.js
- **Differentiation:** Beautiful TUI (inspired by Relentless) is a major differentiator
- **Observability:** Real-time visibility into autonomous agent execution

## Technical Context

**Architecture Decision:** [ADR-004](../../rnd/decisions/2026-01-12_solutioning_frontend-architecture-v2_approved.md)

| Phase | Duration | Tech Stack | Key Deliverables |
|-------|----------|------------|------------------|
| Phase 1 | 4 weeks | Textual (Python) | TUI with real-time streaming |
| Phase 2A | 4 weeks | FastAPI + xterm.js | Web-embedded TUI |
| Phase 2B | 4 weeks | React + Vercel AI | Chat, HITL, Generative UI |
| Phase 2C | 4 weeks | Full Integration | Hybrid Dashboard |

**Design References:**
- [Frontend Implementation Plan](../../rnd/implementation/frontend-implementation-plan.md)
- [Frontend Mockups](../../rnd/implementation/frontend-mockups.md)
- [Relentless TUI](https://github.com/ArvorCo/Relentless)

---

## Phase 1: Terminal User Interface (TUI)

### Story 7.1: TUI Infrastructure & Layout
**Priority:** P0 | **Points:** 5

**As a** developer
**I want** a Textual-based TUI application
**So that** I can monitor RALPH execution in my terminal

**Acceptance Criteria:**
- [ ] Textual project structure in `ralph_agi/tui/`
- [ ] Base `RalphApp` class with grid layout
- [ ] WebSocket client for RalphLoop event streaming
- [ ] `RalphLoop` adapter emitting TUI-consumable events
- [ ] pytest-textual snapshot testing setup
- [ ] Entry point: `ralph tui` command

**Technical Notes:**
- Use Textual's built-in async support for real-time updates
- Events: iteration_start, iteration_end, task_start, task_complete, error

---

### Story 7.2: Core UI Widgets
**Priority:** P0 | **Points:** 5

**As a** developer
**I want** rich UI components showing execution state
**So that** I can understand what RALPH is doing at a glance

**Acceptance Criteria:**
- [ ] `StoryGrid` widget: Task list with status indicators (inspired by Relentless)
- [ ] `MetricsBar` widget: Iterations, cost, time, tokens, velocity
- [ ] `AgentViewer` widget: Agent reasoning and output
- [ ] `LogPanel` widget: Real-time log streaming with auto-scroll
- [ ] Color-coded status: pending (gray), running (yellow), success (green), failed (red)

**Technical Notes:**
- StoryGrid should support scrolling for large task lists
- LogPanel should support log level filtering (DEBUG, INFO, WARN, ERROR)

---

### Story 7.3: Interactive Features
**Priority:** P1 | **Points:** 5

**As a** developer
**I want** keyboard-driven controls
**So that** I can interact with RALPH without leaving the terminal

**Acceptance Criteria:**
- [ ] Command palette (Ctrl+P) with fuzzy search
- [ ] Keyboard shortcuts: pause (p), stop (s), restart (r), quit (q)
- [ ] Configuration viewer/editor panel
- [ ] Progress bar with ETA for current task
- [ ] Notification system for important events (errors, completions)

**Technical Notes:**
- Command palette actions: pause, resume, stop, restart, config, logs, help
- Support vim-style navigation (j/k for up/down)

---

### Story 7.4: TUI Testing & Polish
**Priority:** P1 | **Points:** 3

**As a** developer
**I want** a polished, well-tested TUI
**So that** it works reliably across terminal environments

**Acceptance Criteria:**
- [ ] Snapshot tests for all widgets
- [ ] Integration tests for event flow
- [ ] Keyboard navigation and accessibility
- [ ] Responsive layout for different terminal sizes
- [ ] Documentation and usage guide
- [ ] 90%+ test coverage on TUI module

---

## Phase 2A: Backend API & TUI Embedding

### Story 7.5: FastAPI Backend
**Priority:** P1 | **Points:** 5

**As a** web user
**I want** a REST/WebSocket API
**So that** web clients can interact with RALPH

**Acceptance Criteria:**
- [ ] FastAPI backend in `ralph_agi/api/`
- [ ] WebSocket endpoint for TUI stream (`/ws/tui`)
- [ ] REST endpoints: `/status`, `/config`, `/tasks`, `/metrics`
- [ ] JWT authentication
- [ ] CORS and security middleware
- [ ] OpenAPI documentation

---

### Story 7.6: Web Shell (xterm.js)
**Priority:** P1 | **Points:** 5

**As a** web user
**I want** the TUI embedded in my browser
**So that** I get the same experience without a local terminal

**Acceptance Criteria:**
- [ ] React project with Vite, TypeScript, TailwindCSS
- [ ] xterm.js integration for terminal rendering
- [ ] WebSocket connection to backend TUI stream
- [ ] Terminal theme matching web UI
- [ ] Resize handling (responsive)
- [ ] Full-screen toggle

---

### Story 7.7: Chat Interface (AG-UI)
**Priority:** P2 | **Points:** 5

**As a** user
**I want** to interact with RALPH via natural language
**So that** I can control execution conversationally

**Acceptance Criteria:**
- [ ] AG-UI protocol integration in backend
- [ ] Chat sidebar component
- [ ] Natural language command parsing
- [ ] Command mapping to RalphLoop actions
- [ ] Real-time status updates in chat
- [ ] Chat history persistence

**Technical Notes:**
- Support commands: "What's the status?", "Pause", "Show me the logs", "Deploy"
- Use streaming responses for real-time feel

---

### Story 7.8: Human-in-the-Loop (HITL)
**Priority:** P2 | **Points:** 5

**As a** user
**I want** to approve critical actions
**So that** RALPH doesn't perform risky operations without my consent

**Acceptance Criteria:**
- [ ] Approval prompts in chat interface
- [ ] Configurable approval gates (deploy, git push, file delete)
- [ ] Timeout with default action (configurable)
- [ ] Feedback mechanisms for outputs
- [ ] Notification system for pending approvals
- [ ] Approval audit log

---

## Phase 2B: Advanced Features

### Story 7.9: Generative UI Framework
**Priority:** P3 | **Points:** 5

**As a** user
**I want** RALPH to generate custom UI components
**So that** I get context-aware visualizations

**Acceptance Criteria:**
- [ ] Vercel AI SDK (streamUI) integration
- [ ] React Server Components setup
- [ ] Zod schemas for UI components
- [ ] Component library: cards, buttons, charts, tables
- [ ] LLM prompt for UI generation

---

### Story 7.10: Core Generative Components
**Priority:** P3 | **Points:** 5

**As a** user
**I want** pre-built components RALPH can generate
**So that** common visualizations work out of the box

**Acceptance Criteria:**
- [ ] `TestResultsCard`: Pass/fail summary with details
- [ ] `DeploymentCard`: Deployment status and actions
- [ ] `MetricsChart`: Cost, time, token trends
- [ ] `CodeDiffViewer`: Before/after code changes
- [ ] `SprintProgressCard`: Story completion status

---

### Story 7.11: Dynamic Dashboards
**Priority:** P3 | **Points:** 5

**As a** user
**I want** RALPH to generate custom dashboards
**So that** I get insights tailored to my current context

**Acceptance Criteria:**
- [ ] Dashboard generation based on recent activity
- [ ] Cost breakdown visualization
- [ ] Test coverage trends
- [ ] Sprint velocity charts
- [ ] Customizable layout (drag-and-drop)

---

### Story 7.12: Adaptive Interfaces
**Priority:** P3 | **Points:** 3

**As a** user
**I want** the UI to adapt to my context
**So that** I see relevant information automatically

**Acceptance Criteria:**
- [ ] Context-aware widget selection
- [ ] Error state UI (show debugging info)
- [ ] Success state UI (show summary)
- [ ] Multi-project overview when applicable

---

## Phase 2C: Hybrid Dashboard

### Story 7.13: Dashboard Layout
**Priority:** P3 | **Points:** 5

**As a** user
**I want** a unified dashboard combining all features
**So that** I have a single view of RALPH's activity

**Acceptance Criteria:**
- [ ] Sidebar navigation (Dashboard, Chat, TUI, History, Settings)
- [ ] Main content area with generative UI
- [ ] Collapsible TUI pane
- [ ] Responsive design (mobile-friendly)
- [ ] Dark/light theme support

---

### Story 7.14: Feature Integration
**Priority:** P3 | **Points:** 5

**As a** user
**I want** seamless switching between views
**So that** I can use TUI, chat, and dashboard interchangeably

**Acceptance Criteria:**
- [ ] Chat sidebar embedded in dashboard
- [ ] Generative UI in main content area
- [ ] TUI pane toggle (expand/collapse)
- [ ] Mode switching (TUI-only, Chat-only, Hybrid)
- [ ] Visual configuration editor

---

### Story 7.15: User Experience Polish
**Priority:** P3 | **Points:** 3

**As a** user
**I want** a polished, professional experience
**So that** RALPH feels like a production-quality tool

**Acceptance Criteria:**
- [ ] User preferences and settings panel
- [ ] Onboarding tour for new users
- [ ] Smooth animations and transitions
- [ ] Keyboard shortcuts overlay (?)
- [ ] Multi-project management

---

### Story 7.16: Final Testing & Launch
**Priority:** P3 | **Points:** 5

**As a** developer
**I want** comprehensive testing before launch
**So that** users have a reliable experience

**Acceptance Criteria:**
- [ ] E2E testing of entire application
- [ ] Performance audit (Lighthouse)
- [ ] Security audit
- [ ] Accessibility audit (WCAG 2.1)
- [ ] Documentation and deployment guide
- [ ] Beta launch and feedback collection

---

## Dependencies

- **Epic 01:** Core Execution Loop (events to stream)
- **Epic 04:** Tool Integration (for commands)
- **Epic 05:** Evaluation Pipeline (test results to display)

## Story Point Summary

| Phase | Stories | Points |
|-------|---------|--------|
| Phase 1: TUI | 7.1-7.4 | 18 |
| Phase 2A: Backend & Embed | 7.5-7.8 | 20 |
| Phase 2B: Advanced Features | 7.9-7.12 | 18 |
| Phase 2C: Hybrid Dashboard | 7.13-7.16 | 18 |
| **Total** | **16 stories** | **74 points** |

## Definition of Done

- [ ] TUI accessible via `ralph tui` command
- [ ] Web UI accessible via `ralph serve` + browser
- [ ] Chat interface functional with natural language commands
- [ ] Human-in-the-loop approvals working
- [ ] Generative UI producing context-aware dashboards
- [ ] 90%+ test coverage on frontend modules
- [ ] Documentation complete
- [ ] Accessibility audit passed
