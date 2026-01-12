# Clawdbot Patterns Analysis

**Date:** 2026-01-10
**Status:** Open
**Source:** https://github.com/clawdbot/clawdbot
**Relevance:** High - Multiple patterns applicable to RALPH-AGI

---

## Executive Summary

Clawdbot is a self-hosted AI assistant framework with a WebSocket-based control plane architecture. Several patterns are directly applicable to RALPH-AGI's autonomous agent goals, particularly around scheduling, context management, and multi-agent coordination.

---

## Patterns Identified

### 1. Cron/Scheduled Triggers

**What Clawdbot Does:**
- Scheduled tasks via cron expressions
- Webhook triggers for external events
- Gmail Pub/Sub for email-triggered automation
- Gateway daemon (launchd/systemd) for background persistence

**Relevance to RALPH-AGI:**
- Currently we have SIGINT handling but no scheduled wake-ups
- AFK mode would benefit from periodic check-ins
- Enables "fire and forget" workflows that self-resume

**Implementation Considerations:**
- Add cron support to config.yaml
- Integrate with system scheduler (launchd on macOS, systemd on Linux)
- Define wake-up hooks: `on_scheduled_wake`, `on_external_trigger`

**Priority:** P1 - Directly enables AFK autonomy

---

### 2. Context Compacting

**What Clawdbot Does:**
- Summarization for context management
- Per-session state persistence
- Conversation history with optional compacting

**Relevance to RALPH-AGI:**
- Complements our Memvid hybrid search approach
- Addresses context window limits (Uday's question about prioritization)
- Reduces token costs on long-running tasks

**Implementation Considerations:**
- Integrate with Story 3.6 (Memory Query API)
- Add `compact_threshold` config option
- Use LLM to generate summaries of older chunks
- Preserve full detail only for recent/relevant content
- Store both raw and compacted versions in Memvid

**Priority:** P1 - Critical for long-horizon tasks

---

### 3. Session Isolation via Docker

**What Clawdbot Does:**
- Docker sandboxes for non-primary sessions
- Per-session configuration (thinking depth, verbosity, constraints)
- Three modes: direct chats, group isolation, activation modes

**Relevance to RALPH-AGI:**
- Multi-agent coordination (Epic 2) needs isolation
- Parallel agent execution without interference
- Safety boundary for experimental/untrusted code

**Implementation Considerations:**
- Docker Compose for agent containers
- Shared volume for coordination database
- Network isolation between agents
- Resource limits per container

**Priority:** P2 - Important for multi-agent but not blocking Sprint 2

---

### 4. Tool Streaming (Lower Priority)

**What Clawdbot Does:**
- RPC-based tool execution with block streaming
- Real-time progress for long-running tools

**Relevance to RALPH-AGI:**
- Better UX for long operations
- Not critical for core functionality

**Priority:** P3 - Nice to have

---

### 5. Agent-to-Agent Coordination

**What Clawdbot Does:**
- `sessions_*` tools for cross-session messaging
- Transcript access across sessions
- Presence/typing indicators

**Relevance to RALPH-AGI:**
- Aligns with FR-07 (multi-agent coordination via shared database)
- Could enhance our SQLite-based coordination

**Priority:** P2 - Relevant for Epic 2

---

## Recommended Actions

| Action | Target | Priority |
|--------|--------|----------|
| Add cron/scheduler support | Epic 01 enhancement | P1 |
| Implement context compacting | Epic 03 Story 3.6 | P1 |
| Research Docker isolation | New Epic or Epic 02 | P2 |

---

## References

- [Clawdbot GitHub](https://github.com/clawdbot/clawdbot)
- [RALPH-AGI Epic 01: Core Loop](../_bmad-output/implementation-artifacts/epics/epic-01-core-loop.md)
- [RALPH-AGI Epic 03: Memory System](../_bmad-output/implementation-artifacts/epics/epic-03-memory-system.md)
