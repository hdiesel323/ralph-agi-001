# ADR-003: Frontend Architecture for RALPH-AGI

**Date:** 2026-01-11
**Status:** Approved

---

## Context

RALPH-AGI is currently a CLI-only tool. To make it accessible to non-technical users and provide a richer user experience, we need a graphical user interface (GUI).

**Key Question:** What architecture should we use for the RALPH-AGI frontend?

---

## Research & Analysis

Based on research into existing AI agent frontends (AG-UI, Generative UI, A2UI), we identified four primary patterns:

1.  **Traditional Dashboard:** Familiar, easy to implement, but not adaptive.
2.  **Chat-First Interface:** Natural language, real-time, but requires AG-UI integration.
3.  **Generative UI:** AI-generated UI components, highly adaptive, but cutting-edge and potentially unstable.
4.  **Hybrid Dashboard + Chat:** Best of both worlds, but complex to build.

---

## Decision: Phased Hybrid Architecture

We will implement a **phased hybrid architecture** that starts with a traditional dashboard and evolves to incorporate chat and generative UI features. This approach provides immediate value to technical users while building towards a more accessible and powerful experience for all users.

### **Phase 1: Basic Dashboard (Weeks 13-16)**

**Goal:** Provide visibility and control for technical users.

**Architecture:**
- **Frontend:** React + TypeScript + TailwindCSS
- **Backend API:** FastAPI (Python)
- **Real-Time:** WebSocket (Socket.io)

**Features:**
- Task list (current, completed, failed)
- Real-time logs streaming
- Configuration editor
- Stop/Start/Pause controls
- Metrics dashboard (cost, time, iterations)

---

### **Phase 2: Chat Interface (Weeks 17-20)**

**Goal:** Enable natural language interaction.

**Architecture:**
- **Protocol:** AG-UI for agent-UI communication
- **Client:** CopilotKit or custom AG-UI client
- **Real-Time:** Bi-directional WebSocket

**Features:**
- Chat with Ralph
- Natural language commands
- Real-time status updates in chat
- Human-in-the-loop approvals

---

### **Phase 3: Generative UI (Weeks 21-24)**

**Goal:** AI-generated UI components on-demand.

**Architecture:**
- **Framework:** Vercel streamUI or similar
- **Schema:** Zod schemas for component definitions
- **Rendering:** React Server Components

**Features:**
- Ralph generates UI components based on context
- Dynamic dashboards
- Bespoke visualizations
- Adaptive interface

---

### **Phase 4: Hybrid Dashboard (Weeks 25-28)**

**Goal:** Combine all patterns into a cohesive experience.

**Architecture:**
- **Layout:** Dashboard with sidebar navigation
- **Main View:** Chat interface and generative UI components
- **UX:** Seamless switching between modes

**Features:**
- All features from previous phases
- Unified experience
- Gradual learning curve

---

## Implementation Plan

| Phase | Duration | Complexity | Estimated Hours |
| :--- | :--- | :--- | :--- |
| Phase 1: Basic Dashboard | 4 weeks | Medium | 80-120 hours |
| Phase 2: Chat Interface | 4 weeks | High | 100-140 hours |
| Phase 3: Generative UI | 4 weeks | Very High | 120-160 hours |
| Phase 4: Hybrid Dashboard | 4 weeks | High | 100-140 hours |

**Total:** 16 weeks, 400-560 hours

---

## Consequences

- **Positive:**
    - Makes RALPH-AGI accessible to non-technical users.
    - Provides a richer, more interactive user experience.
    - Enables powerful features like generative UI and human-in-the-loop.
- **Negative:**
    - Significant development effort (16 weeks, 400-560 hours).
    - Adds a new frontend component to the project.
    - Requires expertise in frontend technologies (React, AG-UI, etc.).

---

## References

- [RALPH-AGI Frontend Research](./ralph-agi-frontend-research.md)
- [AG-UI Protocol](https://github.com/ag-ui-protocol/ag-ui)
- [Generative UI: The AI agent is the front end](https://www.infoworld.com/article/4110010/generative-ui-the-ai-agent-is-the-front-end.html)
- [A2UI: Agent-Driven Interfaces](https://developers.googleblog.com/introducing-a2ui-an-open-project-for-agent-driven-interfaces/)
