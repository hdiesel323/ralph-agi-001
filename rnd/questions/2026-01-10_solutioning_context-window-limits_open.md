# Question: How to Handle Context Window Limits?

**File Name:** `2026-01-10_solutioning_context-window-limits_open.md`

**Date:** 2026-01-10
**Author:** R&D Team
**Phase:** Solutioning
**Status:** Open

---

## Question

As the codebase grows, how do we prevent the Coding Agent from exceeding the context window limit (200K tokens for Claude 4.5)?

Specifically:

- Should we use TLDR code analysis (5-layer: AST → Call Graph → CFG → DFG → PDG)?
- Should we implement progressive disclosure (only load relevant files)?
- Should we use git logs instead of full file contents?
- How do we decide what to include in the context?

## Context

The Coding Agent needs to understand the current state of the codebase to implement new features. However, as the project grows, we can't fit the entire codebase into the context window.

**Current approach (PoC):**

- Load all files into context
- Works for small projects (<10 files)
- Will fail for larger projects

**Target:**

- Support projects with 100+ files
- Stay within 200K token limit
- Maintain agent effectiveness

## What I've Tried

- Reading Continuous-Claude-v3 documentation on TLDR analysis
- Reviewing Anthropic's guidance on context management
- Considering MCP-CLI for 99% token reduction

---

## Answer

**Date:** [To be filled]
**Author:** [To be filled]

[Answer will be provided after research and experimentation]

## Decision

[Decision will be documented after answer is provided]
