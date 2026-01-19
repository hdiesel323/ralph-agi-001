# RALPH-AGI Frontend Implementation Plan

**Date:** 2026-01-12
**Status:** Ready for Implementation
**Updated:** Based on [ADR-004](../decisions/2026-01-12_solutioning_frontend-architecture-v2_approved.md)

---

## Overview

This document outlines the implementation plan for the RALPH-AGI frontend, based on the **TUI-first hybrid architecture** defined in ADR-004.

**Strategy:** TUI-First, then Hybrid Web UI
**Total Estimated Duration:** 16 weeks
**Total Estimated Hours:** 400-560 hours

---

## Phase 1: Terminal User Interface (TUI) (Weeks 13-16)

**Goal:** Provide a rich, real-time, developer-native experience.

**Architecture:**

- **Framework:** Textual (Python)
- **Real-Time:** Built-in async support
- **Language:** Python (same as core application)

**Key Benefits:**

- Developer-native experience for our core audience
- Faster to build than web UI
- Same language as core application (no context switching)
- Reusable via xterm.js in Phase 2

### **Week 13: Project Setup & Core Infrastructure**

- [ ] **Task 1.1:** Set up Textual project structure within `ralph_agi/tui/`
- [ ] **Task 1.2:** Create base `App` class with layout grid (logs, status, metrics)
- [ ] **Task 1.3:** Implement WebSocket client for RalphLoop event streaming
- [ ] **Task 1.4:** Create `RalphLoop` adapter to emit events for TUI consumption
- [ ] **Task 1.5:** Set up pytest-textual for snapshot testing

### **Week 14: Core UI Components**

- [ ] **Task 2.1:** Build `LogPanel` widget for real-time log streaming with auto-scroll
- [ ] **Task 2.2:** Build `StoryGrid` widget displaying task status (inspired by Relentless)
- [ ] **Task 2.3:** Build `AgentViewer` widget for agent output and thoughts
- [ ] **Task 2.4:** Build `MetricsBar` widget showing cost, time, iterations
- [ ] **Task 2.5:** Implement color-coded status indicators (pending/running/success/failed)

### **Week 15: Interactive Features**

- [ ] **Task 3.1:** Implement command palette with fuzzy search (Ctrl+P)
- [ ] **Task 3.2:** Add stop/start/pause keyboard shortcuts
- [ ] **Task 3.3:** Create configuration viewer/editor panel
- [ ] **Task 3.4:** Implement progress bars for long-running operations
- [ ] **Task 3.5:** Add notification system for important events

### **Week 16: Polish & Testing**

- [ ] **Task 4.1:** Write snapshot tests for all components
- [ ] **Task 4.2:** Write integration tests for event flow
- [ ] **Task 4.3:** Implement keyboard navigation and accessibility
- [ ] **Task 4.4:** Create `ralph tui` CLI command entry point
- [ ] **Task 4.5:** Documentation and usage guide

**Deliverable:** Fully functional TUI accessible via `ralph tui` command

---

## Phase 2: Hybrid Web UI (Weeks 17-28)

**Goal:** Combine the power of the TUI with the accessibility of a web UI.

**Architecture:**

- **Frontend:** React + TypeScript + TailwindCSS
- **Backend API:** FastAPI (Python)
- **TUI in Web:** xterm.js to embed the Textual TUI directly in the web UI
- **Real-Time:** WebSocket (Socket.io)

### Sub-Phase 2A: Backend API & TUI Embedding (Weeks 17-20)

#### **Week 17: Backend API Foundation**

- [ ] **Task 5.1:** Set up FastAPI backend in `ralph_agi/api/`
- [ ] **Task 5.2:** Implement WebSocket endpoint for TUI stream
- [ ] **Task 5.3:** Create REST endpoints for configuration and status
- [ ] **Task 5.4:** Implement JWT authentication
- [ ] **Task 5.5:** Set up CORS and security middleware

#### **Week 18: Web Shell & TUI Embedding**

- [ ] **Task 6.1:** Set up React project with Vite, TypeScript, TailwindCSS
- [ ] **Task 6.2:** Integrate xterm.js for terminal rendering
- [ ] **Task 6.3:** Connect xterm.js to backend TUI WebSocket
- [ ] **Task 6.4:** Style terminal to match web UI theme
- [ ] **Task 6.5:** Implement terminal resize handling

#### **Week 19: Chat Interface (AG-UI)**

- [ ] **Task 7.1:** Integrate AG-UI protocol into FastAPI backend
- [ ] **Task 7.2:** Create chat sidebar component
- [ ] **Task 7.3:** Implement natural language command parsing
- [ ] **Task 7.4:** Map chat commands to RalphLoop actions
- [ ] **Task 7.5:** Display real-time status updates in chat

#### **Week 20: Human-in-the-Loop**

- [ ] **Task 8.1:** Implement approval prompts in chat interface
- [ ] **Task 8.2:** Add feedback mechanisms for Ralph outputs
- [ ] **Task 8.3:** Integrate with multi-agent Critic for reviews
- [ ] **Task 8.4:** Create notification system for pending approvals
- [ ] **Task 8.5:** Testing and refinement

### Sub-Phase 2B: Advanced Features (Weeks 21-24)

#### **Week 21: Generative UI Setup**

- [ ] **Task 9.1:** Integrate Vercel streamUI or similar
- [ ] **Task 9.2:** Set up React Server Components
- [ ] **Task 9.3:** Create Zod schemas for UI components
- [ ] **Task 9.4:** Define component library (cards, buttons, charts)

#### **Week 22: Core Generative Components**

- [ ] **Task 10.1:** Implement `generate` function for Ralph
- [ ] **Task 10.2:** Create `TestResultsCard` component
- [ ] **Task 10.3:** Create `DeploymentCard` component
- [ ] **Task 10.4:** Create `MetricsChart` component
- [ ] **Task 10.5:** Create `CodeDiffViewer` component

#### **Week 23: Advanced Generative UI**

- [ ] **Task 11.1:** Implement dynamic dashboards generated by Ralph
- [ ] **Task 11.2:** Create bespoke visualizations (cost breakdown, timeline)
- [ ] **Task 11.3:** Implement adaptive interfaces based on context
- [ ] **Task 11.4:** Create multi-project overview dashboard

#### **Week 24: Testing & Optimization**

- [ ] **Task 12.1:** Test generative UI performance and accuracy
- [ ] **Task 12.2:** Optimize LLM prompts for UI generation
- [ ] **Task 12.3:** User testing for usability
- [ ] **Task 12.4:** Performance profiling and optimization

### Sub-Phase 2C: Hybrid Dashboard (Weeks 25-28)

#### **Week 25: UI/UX Redesign**

- [ ] **Task 13.1:** Design hybrid dashboard layout (sidebar, main view, TUI pane)
- [ ] **Task 13.2:** Create Figma mockups
- [ ] **Task 13.3:** Implement new layout components
- [ ] **Task 13.4:** Add responsive design for different screen sizes

#### **Week 26: Integration**

- [ ] **Task 14.1:** Embed chat interface into dashboard sidebar
- [ ] **Task 14.2:** Integrate generative UI components into main view
- [ ] **Task 14.3:** Create TUI pane toggle (expand/collapse)
- [ ] **Task 14.4:** Implement seamless mode switching
- [ ] **Task 14.5:** Add visual configuration editor

#### **Week 27: Final Touches**

- [ ] **Task 15.1:** Add user preferences and settings panel
- [ ] **Task 15.2:** Implement onboarding tour
- [ ] **Task 15.3:** Polish UI animations and transitions
- [ ] **Task 15.4:** Add keyboard shortcuts overlay
- [ ] **Task 15.5:** Implement multi-project management

#### **Week 28: Final Testing & Launch**

- [ ] **Task 16.1:** Final E2E testing of entire application
- [ ] **Task 16.2:** Performance and security audit
- [ ] **Task 16.3:** Accessibility audit (WCAG 2.1)
- [ ] **Task 16.4:** Documentation and deployment guide
- [ ] **Task 16.5:** Public beta launch and feedback collection

---

## Implementation Summary

| Phase                         | Duration | Complexity | Estimated Hours |
| :---------------------------- | :------- | :--------- | :-------------- |
| Phase 1: TUI                  | 4 weeks  | Medium     | 80-120 hours    |
| Phase 2A: Backend & TUI Embed | 4 weeks  | High       | 80-100 hours    |
| Phase 2B: Advanced Features   | 4 weeks  | Very High  | 120-160 hours   |
| Phase 2C: Hybrid Dashboard    | 4 weeks  | High       | 120-180 hours   |

**Total:** 16 weeks, 400-560 hours

---

## Why TUI-First?

1. **Developer-Native:** Our initial users are developers. A TUI is a natural fit for their workflow.
2. **Faster to Market:** A TUI is faster to build than a full web UI, providing immediate value.
3. **Lower Complexity:** Textual is a Python framework, so we can build in the same language as the core application.
4. **Reusable:** The TUI can be embedded in the web UI with xterm.js, so no work is wasted.
5. **Differentiation:** A beautiful TUI is a major differentiator, as demonstrated by Relentless.

---

## References

- [ADR-004: Frontend Architecture v2](../decisions/2026-01-12_solutioning_frontend-architecture-v2_approved.md)
- [ADR-003: Language Choice - Python](../decisions/2026-01-12_solutioning_language-choice-python_approved.md)
- [Relentless TUI](https://github.com/ArvorCo/Relentless)
- [Textual Framework](https://textual.textualize.io/)
- [xterm.js](https://xtermjs.org/)
- [AG-UI Protocol](https://github.com/ag-ui-protocol/ag-ui)
