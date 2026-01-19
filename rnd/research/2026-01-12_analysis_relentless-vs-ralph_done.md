# Research: Relentless vs. snarktank/ralph

**Date:** 2026-01-12
**Phase:** Analysis
**Status:** Done

---

## Overview

This document provides a comprehensive analysis of two popular open-source implementations of the Ralph Wiggum Pattern: **Relentless** by ArvorCo and **ralph** by snarktank. Both are valuable reference implementations, but they have different goals, architectures, and levels of complexity.

---

## Key Findings

### **Relentless (ArvorCo)**

**URL:** https://github.com/ArvorCo/Relentless

**Core Idea:** A universal AI agent orchestrator with a focus on structured planning, multi-agent support, and a beautiful terminal UI (TUI).

**Key Features:**

- **Beautiful TUI:** Real-time terminal interface with progress bars, story grid, and agent output.
- **Intelligent Agent Fallback:** Automatically switches agents (Claude, GPT, etc.) when rate limits are hit.
- **Hierarchical Planning:** 4-phase structure (Setup → Foundation → Stories → Polish) with dependency ordering.
- **Interactive Specification:** `/relentless.specify` and `/relentless.plan` commands for creating specs and plans from natural language.
- **Constitution Management:** Project-level principles, patterns, and constraints.
- **Dependency-Ordered Execution:** Stories with dependencies are executed in the correct order.
- **Parallel Task Markers:** Tasks marked with `[P]` can run simultaneously.
- **GitHub Issues Generation:** Convert user stories directly to GitHub issues.

**Architecture:**

- **Language:** TypeScript
- **Runtime:** Bun (recommended) or Node.js
- **Memory:** Git history, `progress.txt`, `prd.json`
- **Orchestration:** `relentless` CLI with multiple commands (`init`, `run`, `convert`, etc.)
- **Skills:** Specialized skills for Claude/Amp (`prd`, `tasks`, `checklist`, `clarify`)

**Strengths:**

- **Sophisticated Planning:** The hierarchical planning and dependency management are best-in-class.
- **Excellent UX:** The TUI provides a great user experience for monitoring progress.
- **Multi-Agent Support:** The agent fallback and auto-recovery are powerful features.
- **Extensible:** The skills system allows for adding new capabilities.

**Weaknesses:**

- **Complexity:** The multi-step workflow (`specify` → `plan` → `tasks` → `convert` → `run`) can be cumbersome.
- **Agent-Specific:** The best features are designed for Claude Code and Amp.
- **Node.js Ecosystem:** Relies on Node.js/Bun, which may not be ideal for all projects.

---

### **ralph (snarktank)**

**URL:** https://github.com/snarktank/ralph

**Core Idea:** A minimalist, bash-based implementation of the Ralph Wiggum Pattern, designed for simplicity and ease of use with Amp.

**Key Features:**

- **Simplicity:** A single `ralph.sh` script orchestrates the entire loop.
- **Bash-Based:** Easy to understand and modify for anyone familiar with shell scripting.
- **Amp-Focused:** Designed specifically for use with the Amp AI coding agent.
- **Auto-Handoff:** Recommends Amp's experimental auto-handoff for handling large tasks.
- **Flowchart Visualization:** Includes an interactive flowchart to explain the workflow.

**Architecture:**

- **Language:** Bash
- **Runtime:** Any Unix-like shell
- **Memory:** Git history, `progress.txt`, `prd.json`
- **Orchestration:** `ralph.sh` script
- **Skills:** `prd` and `ralph` skills for Amp

**Strengths:**

- **Simplicity:** The minimalist design is easy to understand and get started with.
- **Portability:** The bash script can run almost anywhere.
- **Educational:** The flowchart and simple code make it a great learning tool.

**Weaknesses:**

- **Minimalist:** Lacks many of the advanced features of Relentless (TUI, multi-agent, etc.).
- **Amp-Specific:** Tightly coupled to the Amp agent.
- **Less Robust:** The bash script is less robust than a compiled TypeScript application.

---

## Comparison Table

| Feature           | Relentless (ArvorCo)        | ralph (snarktank)           | RALPH-AGI (Ours)             |
| :---------------- | :-------------------------- | :-------------------------- | :--------------------------- |
| **Language**      | TypeScript                  | Bash                        | Python                       |
| **Runtime**       | Bun / Node.js               | Shell                       | Python                       |
| **UI**            | Beautiful TUI               | CLI only                    | CLI + Web UI (planned)       |
| **Multi-Agent**   | ✅ Yes (fallback)           | ❌ No                       | ✅ Yes (Builder + Critic)    |
| **Planning**      | Hierarchical, interactive   | Manual PRD                  | YAML-based, automated        |
| **Dependencies**  | ✅ Yes                      | ❌ No                       | ✅ Yes (Beads)               |
| **Memory**        | Git, progress.txt, prd.json | Git, progress.txt, prd.json | Memvid (planned)             |
| **Complexity**    | High                        | Low                         | Medium                       |
| **Extensibility** | Skills system               | Manual script edits         | Hooks system                 |
| **Best For**      | Complex projects, teams     | Learning, simple projects   | Production use, multi-domain |

---

## Key Insights for RALPH-AGI

### 1. **TUI is a Killer Feature**

Relentless's TUI is a major differentiator. It provides a much better user experience than a simple CLI. We should prioritize a TUI for RALPH-AGI, in addition to the web UI.

**Action Item:** Add a TUI to the RALPH-AGI roadmap (Epic 07).

### 2. **Hierarchical Planning is Powerful**

Relentless's 4-phase planning (Setup → Foundation → Stories → Polish) is a great model for organizing complex projects. We should adopt a similar structure in our planning phase.

**Action Item:** Update the `planning` templates in our R&D workspace to include this 4-phase structure.

### 3. **Constitution is a Great Idea**

Relentless's `constitution.md` file is a great way to provide project-level principles and constraints to the AI agent. This is more robust than just including them in the prompt.

**Action Item:** Add a `constitution.md` file to the RALPH-AGI project structure.

### 4. **Skills are a Good Extensibility Pattern**

Relentless's skills system is a good model for adding new capabilities. Our hooks system is similar, but we should consider if a more explicit "skill" concept would be beneficial.

**Action Item:** Review our hooks system and consider if a "skill" abstraction would be a useful addition.

### 5. **Simplicity Has Its Place**

snarktank/ralph's simplicity is its greatest strength. It's a great reminder that we should strive to keep RALPH-AGI as simple as possible, while still providing powerful features.

**Action Item:** Continuously evaluate the complexity of RALPH-AGI and look for opportunities to simplify.

---

## Conclusion

Both Relentless and snarktank/ralph are excellent implementations of the Ralph Wiggum Pattern. Relentless is a feature-rich, production-ready orchestrator, while snarktank/ralph is a minimalist, educational tool.

RALPH-AGI is well-positioned to combine the best of both worlds: the power and sophistication of Relentless with the simplicity and clarity of snarktank/ralph, all built on a robust Python foundation.

By incorporating the key insights from these projects, we can make RALPH-AGI the best autonomous AI agent orchestrator available.
