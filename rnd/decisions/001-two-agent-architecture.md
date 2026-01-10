# [001] - Two-Agent Architecture (Initializer + Coding Agent)

**Date:** 2026-01-10
**Status:** Accepted

---

## Context

Based on Anthropic's official guidance for long-running agents, we need to decide whether to use a single-agent or multi-agent architecture for RALPH-AGI.

**Options considered:**

1. **Single Agent:** One agent handles both initialization and coding
2. **Two-Agent Architecture:** Separate Initializer Agent and Coding Agent
3. **Multi-Agent Swarm:** Multiple specialized agents working in parallel

**Key considerations:**

- Context confusion: A single agent can get confused about whether it's setting up or implementing
- Separation of concerns: Different tasks require different prompts and behaviors
- Simplicity: More agents = more complexity
- Proven patterns: Anthropic recommends two-agent architecture in their official guidance

---

## Decision

We will implement a **two-agent architecture** with:

1. **Initializer Agent:** Runs once at the beginning to:
   - Expand the user prompt into a detailed `feature_list.json`
   - Create the `progress.txt` file
   - Initialize the git repository
   - Set up the `init.sh` script

2. **Coding Agent:** Runs in a loop to:
   - Read `progress.txt` and git logs to understand the current state
   - Select the next feature to work on
   - Write and modify code
   - Run tests and debug errors
   - Commit completed features to git

**Why two agents, not more?**

- Simplicity: Two agents are easier to manage than a swarm
- Proven pattern: Anthropic's official guidance validates this approach
- Clear separation: Initialization vs. implementation are distinct phases
- Future extensibility: We can add specialized agents later (Testing, QA, etc.) without changing the core architecture

---

## Consequences

**Positive:**

- Clear separation of concerns prevents context confusion
- Each agent can have a specialized prompt optimized for its task
- Easier to debug and maintain
- Follows official Anthropic best practices
- Enables future addition of specialized agents

**Negative:**

- Slightly more complex than a single-agent approach
- Requires coordination between agents (via shared artifacts)
- Two separate prompts to maintain

**Neutral:**

- We'll need to design the handoff mechanism between agents (via `feature_list.json` and `progress.txt`)
- We'll need to decide when to invoke each agent (Initializer once, Coding Agent in a loop)

---

## Implementation Notes

- Initializer Agent will use a prompt focused on planning and decomposition
- Coding Agent will use a prompt focused on implementation and debugging
- Both agents will share access to the file system, git repository, and memory system
- The Coding Agent will check `feature_list.json` to determine if all features are complete (exit condition)

---

## References

- [Anthropic Official Guidance on Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Ralph Wiggum Pattern (uses a single agent but recommends separation for complex tasks)
- Continuous-Claude-v3 (uses multiple specialized agents)
