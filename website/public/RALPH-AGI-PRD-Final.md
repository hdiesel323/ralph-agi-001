# Product Requirements Document: RALPH-AGI

**Project Name:** RALPH-AGI (Recursive Autonomous Long-horizon Processing with Hierarchical AGI-like Intelligence)

**Version:** 1.0
**Date:** January 10, 2026
**Author:** RALPH-AGI Team

---

## 1. Introduction

### 1.1 Executive Summary

This document outlines the product requirements for RALPH-AGI, a next-generation autonomous AI agent system designed to tackle complex, long-horizon tasks that traditionally require significant human oversight. The system integrates the simple, iterative power of the "Ralph Wiggum" methodology with sophisticated memory systems, dynamic tool discovery, and robust feedback loops. The goal is to create an agent capable of AGI-like performance on software development and other knowledge-based tasks, operating autonomously for extended periods while learning from its experience and continuously improving its performance.

The name "RALPH-AGI" pays homage to the Ralph Wiggum technique, a deceptively simple approach to agent orchestration credited to Jeffrey Huntley. The core insight is that complex multi-agent architectures and elaborate orchestration systems are often unnecessary when working with sufficiently capable foundation models. Instead, a simple bash loop that iterates through a task list, combined with robust feedback mechanisms and persistent memory, can achieve remarkable results with far less complexity.

### 1.2 Problem Statement

Modern AI agents, while powerful, struggle with tasks that span multiple days or require context beyond a single session. The core challenge of long-running agents is that they must work in discrete sessions, and each new session begins with no memory of what came before. As Anthropic's engineering team noted in their research on effective harnesses for long-running agents:

> "Imagine a software project staffed by engineers working in shifts, where each new engineer arrives with no memory of what happened on the previous shift. Because context windows are limited, and because most complex projects cannot be completed within a single window, agents need a way to bridge the gap between coding sessions." [7]

The primary limitations of current systems manifest in several failure patterns. First, agents tend to attempt to "one-shot" complex tasks, running out of context mid-implementation and leaving features half-finished and undocumented. Second, agents often prematurely declare victory after seeing that some progress has been made, failing to recognize incomplete features. Third, without explicit prompting for end-to-end testing, agents mark features as complete without proper verification. These limitations prevent AI agents from being truly autonomous partners in complex projects, restricting their utility to short, well-defined tasks.

### 1.3 Target Audience

The primary users of RALPH-AGI fall into four categories. **Software Development Teams** will use the system to automate backlog tasks, accelerate feature development, and reduce the burden of routine coding and testing. **AI Researchers** will leverage the platform for experimenting with agentic architectures, long-horizon planning, and emergent autonomous behaviors. **DevOps Engineers** can employ the system to automate complex infrastructure management, deployment pipelines, and incident response. **Data Scientists** will benefit from automated data cleaning, feature engineering, and model training pipelines.

---

## 2. Product Goals and Objectives

### 2.1 Goals

The overarching vision for RALPH-AGI centers on three primary goals. The first goal is to **achieve true long-horizon autonomy** by creating an agent that can reliably work on a complex task for days at a time, surviving restarts and context loss, without requiring a human in the loop. The second goal is to **enable emergent problem-solving** by building a system that can break down high-level goals into manageable steps, discover and learn to use new tools, and adapt its strategy based on feedback. The third goal is to **maximize developer productivity** by freeing human developers from routine implementation and debugging, allowing them to focus on high-level architecture, creative problem-solving, and product innovation.

### 2.2 Objectives and Timeline

The development of RALPH-AGI will proceed through four quarterly milestones, as outlined in the table below.

| Quarter | Objective | Key Deliverables |
|---------|-----------|------------------|
| Q1 2026 | MVP Development | Core loop engine, basic PRD management, Git integration, single-tool execution |
| Q2 2026 | Memory System | Full three-tier memory implementation, 50% reduction in task re-work on similar tasks |
| Q3 2026 | Quality Assurance | Cascaded evaluation pipeline, 95% pass rate on internal quality checks |
| Q4 2026 | Advanced Features | Evolutionary research mode, SOTA Hunter integration, multi-agent collaboration preview |

---

## 3. System Architecture Overview

RALPH-AGI is built on a modular, layered architecture that separates concerns and allows for independent evolution of its components. The design philosophy draws from multiple cutting-edge frameworks and research, synthesizing their best practices into a unified system.

### 3.1 Architectural Layers

The system comprises six distinct layers, each responsible for a specific aspect of the agent's operation.

**The Control Plane** serves as the entry point for users, providing CLI and API interfaces, configuration management, scheduling capabilities, and monitoring dashboards. This layer handles user authentication, task submission, and system-wide settings.

**The Orchestration Layer** contains the Ralph Loop Engine, which is the heart of the system. This engine implements the iterative cycle that drives all agent activity: loading context, selecting tasks, executing work, verifying results, updating state, and checking for completion. The layer also manages the Initializer Agent (for first-run setup) and the Coding Agent (for subsequent iterations).

**The Task Manager** implements a dependency-aware system inspired by the `beads` project, using a `PRD.json` file to define features and track progress. Each feature has a `passes` flag that indicates completion status, and the system can identify which tasks are "ready" (have no blocking dependencies).

**The Memory System** provides a three-tiered architecture for context persistence. Short-term memory uses an append-only `progress.txt` file for within-session notes. Medium-term memory leverages Git history with descriptive commit messages. Long-term memory employs a SQLite database and Chroma vector store for semantic search across all past sessions.

**The Tool Registry** implements dynamic discovery using the `mcp-cli` pattern, allowing the agent to access a vast array of tools without bloating the context window. This approach reduces tool-related token usage by approximately 99% compared to static loading.

**The Evaluation Pipeline** provides cascaded verification, proceeding from fast, cheap checks (static analysis, type checking) to slow, expensive ones (end-to-end browser testing, LLM-as-Judge review).

### 3.2 Core Data Flow

The system operates through a well-defined data flow that ensures consistent, incremental progress. When a user submits a request, the system first checks whether this is a first run. If so, the Initializer Agent creates the project scaffolding: the `PRD.json` file with all features marked as `passes: false`, the `progress.txt` file, the `init.sh` script for environment setup, and the initial Git commit.

For subsequent runs, the Coding Agent enters the Ralph Loop. Each iteration begins by loading context from the progress file, Git history, and long-term memory. The agent then selects the highest-priority task that has no blocking dependencies. It executes the task using the LLM ensemble and available tools, then runs the cascaded evaluation pipeline. If verification passes, the agent updates the PRD (marking the feature as `passes: true`), appends notes to the progress file, and creates a Git commit. Finally, it checks whether all features are complete or the maximum iteration count has been reached. If not, the loop continues.

---

## 4. Features and Requirements

### 4.1 Core Execution Loop (FR-001)

The Ralph Loop Engine is the central mechanism that drives all agent activity. The design is intentionally simple, following the principle that "a for loop" is often more effective than complex orchestration systems when working with capable foundation models.

The loop operates on a single task at a time, preventing the agent from "biting off more than it can chew." As noted in the Ralph Wiggum technique documentation, LLMs tend to produce lower-quality output as more tokens are added to the context window, so keeping each iteration focused on a single, small task is critical for maintaining code quality. [2]

The system supports two operational modes. **AFK Mode** (Away From Keyboard) runs fully autonomously, with optional notifications via webhook when complete. **Human-in-the-Loop Mode** pauses at configurable checkpoints for user approval, which is useful for difficult features or when the user wants to steer the agent's decisions.

| Requirement ID | Description | Priority |
|----------------|-------------|----------|
| FR-001.1 | Configurable maximum iteration count | P0 |
| FR-001.2 | Completion promise detection (`<promise>COMPLETE</promise>`) | P0 |
| FR-001.3 | AFK mode with webhook notifications | P0 |
| FR-001.4 | Human-in-the-Loop mode with approval gates | P1 |
| FR-001.5 | Atomic iterations leaving clean, committable state | P0 |

### 4.2 Task Management and Planning (FR-002)

The Task Manager provides a structured way for the agent to understand its backlog, manage dependencies, and track the status of each feature. The design draws inspiration from both Anthropic's feature list approach and the `beads` project's dependency graph.

All tasks are defined in a `PRD.json` file, which serves as the single source of truth for project requirements. The choice of JSON format is deliberate; as Anthropic's research found, "the model is less likely to inappropriately change or overwrite JSON files compared to Markdown files." [7] Each feature includes a `passes` flag (boolean), a description, verification steps, and optional dependencies.

The system uses strongly-worded instructions to prevent the agent from modifying the PRD inappropriately. As Anthropic recommends: "It is unacceptable to remove or edit tests because this could lead to missing or buggy functionality." The agent may only change the `passes` field from `false` to `true` after successful verification.

| Requirement ID | Description | Priority |
|----------------|-------------|----------|
| FR-002.1 | PRD.json as single source of truth | P0 |
| FR-002.2 | Feature `passes` flag for completion tracking | P0 |
| FR-002.3 | Dependency graph for task ordering | P1 |
| FR-002.4 | Single-feature-per-iteration constraint | P0 |
| FR-002.5 | Strongly-worded constraints against PRD modification | P0 |

### 4.3 Multi-Layered Memory System (FR-003)

The Memory System is what enables RALPH-AGI to achieve true long-horizon autonomy. Without persistent memory, each agent session would start from scratch, wasting time rediscovering context and potentially repeating mistakes. The system implements a three-tiered architecture that balances recency, relevance, and efficiency.

**Short-Term Memory** uses an append-only `progress.txt` file for detailed notes within a session. The append-only constraint is critical; if the agent is allowed to "update" the file, it tends to overwrite previous content rather than adding to it. This file captures work done, decisions made, issues encountered, and notes for the next session.

**Medium-Term Memory** leverages Git history with descriptive commit messages. Each successful iteration results in a commit that documents the changes made, providing an immutable, inspectable history. This also enables recovery via `git revert` if a change introduces problems.

**Long-Term Memory** implements a persistent store based on the `claude-mem` project. This includes a SQLite database for structured data (sessions, observations, summaries) and a Chroma vector database for semantic search. The system uses lifecycle hooks to automatically capture observations at key points (session start, after tool use, session end) and employs AI-powered summarization to compress old observations while retaining key insights.

| Requirement ID | Description | Priority |
|----------------|-------------|----------|
| FR-003.1 | Append-only progress.txt file | P0 |
| FR-003.2 | Git commit per successful iteration | P0 |
| FR-003.3 | SQLite database for session/observation storage | P1 |
| FR-003.4 | Chroma vector database for semantic search | P1 |
| FR-003.5 | Lifecycle hooks for automatic observation capture | P2 |
| FR-003.6 | AI-powered memory summarization | P2 |

### 4.4 Dynamic Tool Integration (FR-004)

The Tool Registry enables the agent to discover and use a wide variety of tools without requiring their full definitions to be loaded into the context window at all times. This is critical for token efficiency; as the MCP CLI documentation notes, loading 6 MCP servers with 60 tools statically consumes approximately 47,000 tokens, while dynamic discovery reduces this to approximately 400 tokens—a 99% reduction. [6]

The agent's workflow for tool use follows a three-step pattern. First, it discovers available tools by listing servers and their capabilities. Second, it inspects the schema of a specific tool to understand its parameters. Third, it executes the tool with the correct arguments. This just-in-time approach ensures that context is only consumed when actually needed.

The system provides foundational tools for common operations: browser automation (via Playwright MCP), file system operations (read, write, search), shell command execution, and Git operations. Additional tools can be added by configuring MCP servers in the system configuration.

| Requirement ID | Description | Priority |
|----------------|-------------|----------|
| FR-004.1 | MCP CLI integration for dynamic discovery | P0 |
| FR-004.2 | Three-step tool workflow (discover, inspect, execute) | P0 |
| FR-004.3 | Browser automation via Playwright MCP | P1 |
| FR-004.4 | File system operations | P0 |
| FR-004.5 | Shell command execution | P0 |
| FR-004.6 | Git operations | P0 |

### 4.5 Cascaded Evaluation Pipeline (FR-005)

The Evaluation Pipeline ensures that every code change is rigorously tested before being accepted. The design follows a cascaded approach, proceeding from fastest/cheapest to slowest/most expensive checks. This "fail fast" strategy saves resources by catching simple errors early before investing in expensive end-to-end testing.

The pipeline consists of five stages. **Stage 1 (Static Analysis)** runs syntax checking, linting, and type checking in approximately 1 second at negligible cost. **Stage 2 (Unit Tests)** executes the project's unit test suite in approximately 10 seconds. **Stage 3 (Integration Tests)** runs tests that verify component interactions in approximately 30 seconds. **Stage 4 (End-to-End Tests)** uses browser automation to test the application as a human user would, taking approximately 60 seconds and incurring modest costs. **Stage 5 (LLM-as-Judge)** performs a qualitative review of the code, taking approximately 30 seconds and incurring the highest per-check cost.

A stage only runs if the preceding stage passes. A failure at any stage halts the commit and triggers a debugging sub-loop, where the agent attempts to diagnose and fix the issue before retrying.

| Stage | Time | Cost | Purpose |
|-------|------|------|---------|
| Static Analysis | ~1s | $0.00 | Syntax, linting, type checking |
| Unit Tests | ~10s | $0.00 | Function-level verification |
| Integration Tests | ~30s | $0.01 | Component interaction verification |
| End-to-End Tests | ~60s | $0.05 | User-facing functionality |
| LLM-as-Judge | ~30s | $0.10 | Qualitative code review |

---

## 5. User Stories

The following user stories illustrate the primary use cases for RALPH-AGI.

**Story 1: Overnight Feature Development.** As a software developer, I want to assign a high-level feature request to RALPH-AGI before leaving work so that I can return the next morning to a working, tested, and documented implementation. This allows me to focus my time on architectural decisions and creative problem-solving rather than routine implementation.

**Story 2: Project Progress Monitoring.** As a project manager, I want to view a real-time dashboard of RALPH-AGI's progress, including completed tasks, current work, and any encountered blockers. This enables me to accurately track project velocity and identify potential issues early.

**Story 3: Research Mode Experimentation.** As an AI researcher, I want to configure and run RALPH-AGI in evolutionary mode on a competitive coding problem. This allows me to study its emergent problem-solving strategies and benchmark its performance against baseline approaches.

**Story 4: Human-in-the-Loop Steering.** As a senior developer, I want to run RALPH-AGI in interactive mode for a complex feature that requires careful architectural decisions. This allows me to guide the agent's approach while still benefiting from its implementation speed.

---

## 6. Non-Functional Requirements

### 6.1 Performance

The system must maintain responsive performance even on large projects. A single loop iteration, excluding external tool execution time, should complete in under 60 seconds. The system must be able to manage projects with over 1,000 features in the PRD without significant performance degradation. Memory queries should return results within 2 seconds, even with millions of stored observations.

### 6.2 Reliability

The agent must demonstrate robust self-recovery capabilities. The target self-recovery rate is 90% from common errors (failed tests, tool errors, network issues) without human intervention. The system must checkpoint its state after every successful iteration, enabling recovery from crashes or restarts. All state changes must be atomic, ensuring the system is never left in an inconsistent state.

### 6.3 Security

All code and tool commands must execute within a sandboxed environment with no direct access to host system resources. Secrets and API keys must be managed through environment variables, never stored in code or logs. The system must implement rate limiting to prevent runaway resource consumption. All external communications must use encrypted channels (HTTPS, SSH).

### 6.4 Observability

The system must provide comprehensive logging and monitoring capabilities. All agent actions must be logged with timestamps and context. A real-time dashboard must display current status, progress, and resource consumption. Alerts must be configurable for error conditions, stuck states, and completion events.

---

## 7. Success Metrics

The effectiveness of RALPH-AGI will be measured across four dimensions.

**Task Completion Rate** measures the percentage of assigned tasks completed autonomously to specification. The target is 85% for the MVP, increasing to 95% by the end of Q4 2026.

**Human Intervention Rate** measures the number of human interventions required per 10 hours of agent operation. The target is fewer than 2 interventions for routine tasks, with complex tasks allowing up to 5 interventions.

**Code Quality Score** aggregates the results from the LLM-as-Judge and static analysis tools. The target is an average score of 8/10 or higher on the LLM-as-Judge assessment, with zero critical issues from static analysis.

**Context Efficiency** measures the ratio of useful work done to total tokens consumed. The target is a 50% improvement over baseline approaches that use static tool loading and lack memory systems.

---

## 8. Future Work

Several areas are identified for future development beyond the initial release.

**Multi-Agent Collaboration** will allow multiple RALPH-AGI instances to work on the same project simultaneously, dividing the backlog and resolving merge conflicts automatically. This will require sophisticated coordination mechanisms and conflict resolution strategies.

**GUI for Task Management** will provide a web-based interface for creating, editing, and prioritizing tasks in the PRD.json. This will make the system more accessible to non-technical users and enable real-time collaboration on requirements.

**Advanced Self-Healing** will move beyond simple git revert to enable the agent to perform root cause analysis and write its own bug fixes. This will require deeper integration with debugging tools and more sophisticated reasoning about code behavior.

**Evolutionary Optimization** will implement the full LongHorizon-style evolutionary system, with multiple populations evolving in parallel, cross-pollination via migration, and automatic research to incorporate state-of-the-art knowledge.

---

## 9. References

[1] FareedKhan-dev/ai-long-task. GitHub Repository. https://github.com/FareedKhan-dev/ai-long-task

[2] AwesomeClaude - Ralph Wiggum. https://awesomeclaude.ai/ralph-wiggum

[3] YouTube - Ralph Wiggum Technique Video. https://www.youtube.com/watch?v=_IK18goX4X8

[4] thedotmack/claude-mem. GitHub Repository. https://github.com/thedotmack/claude-mem

[5] steveyegge/beads. GitHub Repository. https://github.com/steveyegge/beads

[6] Phil Schmid - MCP CLI: Dynamic Tool Discovery for AI Agents. https://www.philschmid.de/mcp-cli

[7] Anthropic Engineering - Effective harnesses for long-running agents. https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

---

## 10. Glossary

| Term | Definition |
|------|------------|
| **AGI** | Artificial General Intelligence; a hypothetical type of intelligent agent that can understand or learn any intellectual task that a human being can. |
| **Agentic System** | An AI system that can perceive its environment, make decisions, and take actions to achieve specific goals. |
| **Long-Horizon Task** | A complex task that requires multiple steps and context persistence over an extended period (hours or days). |
| **Ralph Wiggum Technique** | A simple, iterative loop-based approach to agent orchestration, where the agent works on one small task at a time until a larger goal is complete. |
| **MCP** | Model Context Protocol; a standard for dynamically discovering and using tools (APIs, functions) with AI models. |
| **Harness** | The infrastructure and prompting framework that guides and constrains an AI agent, providing it with memory, tools, and feedback loops. |
| **Cascaded Evaluation** | A multi-stage testing pipeline that proceeds from fast, cheap checks to slow, expensive ones, failing fast to save resources. |
| **PRD** | Product Requirements Document; a structured file defining all features and their completion status. |
| **Context Window** | The maximum amount of text (measured in tokens) that an LLM can process in a single session. |
| **Compaction** | A technique for summarizing and compressing context to fit within the context window while retaining essential information. |

---

## Appendix A: PRD.json Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "project": {
      "type": "object",
      "properties": {
        "name": { "type": "string" },
        "description": { "type": "string" },
        "version": { "type": "string" }
      },
      "required": ["name", "description"]
    },
    "features": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "category": { 
            "type": "string",
            "enum": ["functional", "ui", "performance", "security", "integration"]
          },
          "description": { "type": "string" },
          "priority": { 
            "type": "integer",
            "minimum": 0,
            "maximum": 4
          },
          "steps": {
            "type": "array",
            "items": { "type": "string" }
          },
          "acceptance_criteria": {
            "type": "array",
            "items": { "type": "string" }
          },
          "dependencies": {
            "type": "array",
            "items": { "type": "string" }
          },
          "passes": { "type": "boolean" },
          "completed_at": { "type": "string", "format": "date-time" }
        },
        "required": ["id", "description", "passes"]
      }
    }
  },
  "required": ["project", "features"]
}
```

---

## Appendix B: Sample Ralph Loop Implementation

```bash
#!/bin/bash
set -e

# Check for max iterations argument
if [ -z "$1" ]; then
    echo "Usage: ralph.sh <max_iterations>"
    exit 1
fi

MAX_ITERATIONS=$1

for ((i=1; i<=MAX_ITERATIONS; i++)); do
    echo "=========================================="
    echo "RALPH ITERATION $i of $MAX_ITERATIONS"
    echo "=========================================="
    
    OUTPUT=$(claude-code \
        --file plans/prd.json \
        --file progress.txt \
        --prompt "
        You are working through a product backlog. Follow these steps:
        
        1. Find the highest priority feature to work on (not necessarily first in list)
        2. Check that the types check via 'pnpm type-check' and tests pass via 'pnpm test'
        3. Update the PRD with the work done (mark passes: true)
        4. APPEND your progress to progress.txt (leave notes for next iteration)
        5. Make a git commit of that feature
        6. Only work on a SINGLE feature per iteration
        
        If the PRD is complete, output: <promise>COMPLETE</promise>
        ")
    
    echo "$OUTPUT"
    
    if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
        echo "=========================================="
        echo "PRD COMPLETE! Exiting after $i iterations."
        echo "=========================================="
        exit 0
    fi
done

echo "=========================================="
echo "Max iterations ($MAX_ITERATIONS) reached."
echo "=========================================="
```

---

## Appendix C: System Configuration Schema

```yaml
system:
  name: "RALPH-AGI"
  version: "1.0.0"

orchestration:
  loop_type: "ralph"
  max_iterations: 100
  completion_promise: "<promise>COMPLETE</promise>"
  human_in_loop: false
  checkpoint_interval: 1

task_management:
  prd_path: "prd.json"
  prd_format: "json"
  git_backed: true
  auto_commit: true
  commit_message_template: "feat: {feature_description}"

memory:
  short_term:
    type: "progress_file"
    path: "progress.txt"
    mode: "append"
  medium_term:
    type: "git"
    branch: "main"
  long_term:
    enabled: true
    sqlite_path: "~/.ralph-agi/memory.db"
    vector_db: "chroma"
    embedding_model: "text-embedding-3-small"
    
tools:
  discovery: "mcp_cli"
  config_path: "~/.config/mcp/mcp_servers.json"
  dynamic_loading: true
  
evaluation:
  cascade: true
  stages:
    - name: "static_analysis"
      command: "pnpm type-check && pnpm lint"
      timeout: 60
    - name: "unit_tests"
      command: "pnpm test"
      timeout: 300
    - name: "integration_tests"
      command: "pnpm test:integration"
      timeout: 600
      optional: true
    - name: "e2e_tests"
      command: "pnpm test:e2e"
      timeout: 900
      optional: true
    - name: "llm_judge"
      enabled: true
      model: "claude-sonnet-4"

llm:
  default_model: "claude-sonnet-4"
  ensemble:
    - model: "claude-opus-4.5"
      weight: 0.3
      use_for: ["complex_reasoning", "architecture", "debugging"]
    - model: "claude-sonnet-4"
      weight: 0.5
      use_for: ["implementation", "testing", "documentation"]
    - model: "claude-haiku-4"
      weight: 0.2
      use_for: ["simple_queries", "formatting", "git_operations"]

notifications:
  enabled: true
  channels:
    - type: "webhook"
      url: "${SLACK_WEBHOOK_URL}"
      events: ["complete", "error", "stuck"]
```
