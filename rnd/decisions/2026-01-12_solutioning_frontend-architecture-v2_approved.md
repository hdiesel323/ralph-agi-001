# ADR-004: Frontend Architecture v2 (with TUI)

**Date:** 2026-01-12
**Status:** Approved

---

## Context

Our initial frontend architecture (ADR-003) focused on a web-based GUI. However, our analysis of **Relentless** revealed the power of a **Terminal User Interface (TUI)** for providing a rich, real-time, and developer-native experience.

**Key Question:** How should we incorporate a TUI into our frontend strategy?

---

## Decision: TUI-First, with a Hybrid Web UI

We will adopt a **TUI-first** strategy for our initial frontend, and then build a hybrid web UI that incorporates the TUI. This provides immediate value to our core developer audience and a clear path to a more accessible web UI.

### **Phase 1: Terminal User Interface (TUI) (Weeks 13-16)**

**Goal:** Provide a rich, real-time, developer-native experience.

**Architecture:**

- **Framework:** Textual (Python)
- **Real-Time:** Built-in async support

**Features (inspired by Relentless):**

- Real-time logs and progress bars
- Story grid with task status
- Agent output viewer
- Interactive commands (stop, start, pause, etc.)
- Metrics dashboard (cost, time, iterations)

### **Phase 2: Hybrid Web UI (Weeks 17-28)**

**Goal:** Combine the power of the TUI with the accessibility of a web UI.

**Architecture:**

- **Frontend:** React + TypeScript + TailwindCSS
- **Backend API:** FastAPI (Python)
- **TUI in Web:** xterm.js to embed the Textual TUI directly in the web UI
- **Real-Time:** WebSocket (Socket.io)

**Features:**

- All features from the TUI, plus:
- Chat interface (AG-UI)
- Generative UI components
- Visual configuration editor
- Multi-project management

---

## Updated Implementation Plan

| Phase                  | Duration | Complexity | Estimated Hours |
| :--------------------- | :------- | :--------- | :-------------- |
| Phase 1: TUI           | 4 weeks  | Medium     | 80-120 hours    |
| Phase 2: Hybrid Web UI | 12 weeks | Very High  | 320-440 hours   |

**Total:** 16 weeks, 400-560 hours (same total, different phases)

---

## Why TUI-First?

1.  **Developer-Native:** Our initial users are developers. A TUI is a natural fit for their workflow.
2.  **Faster to Market:** A TUI is faster to build than a full web UI, providing immediate value.
3.  **Lower Complexity:** Textual is a Python framework, so we can build the TUI in the same language as the core application.
4.  **Reusable:** The TUI can be embedded in the web UI with xterm.js, so no work is wasted.
5.  **Differentiation:** A beautiful TUI is a major differentiator, as demonstrated by Relentless.

---

## Consequences

- **Positive:**
  - Faster time-to-market for a GUI.
  - Better initial user experience for our core developer audience.
  - Reduced initial complexity.
- **Negative:**
  - The web UI is delayed.
  - Requires expertise in Textual.

---

## References

- [ADR-003: Frontend Architecture](./2026-01-11_solutioning_frontend-architecture_approved.md)
- [Relentless TUI](https://github.com/ArvorCo/Relentless)
- [Textual Framework](https://textual.textualize.io/)
- [xterm.js](https://xtermjs.org/)
