# ADR-002: Multi-Agent Architecture for RALPH-AGI

**Date:** 2026-01-11
**Status:** Approved

---

## Context

The current RALPH-AGI architecture uses a single LLM for all tasks. To improve quality, catch blind spots, and increase robustness, we are considering a multi-agent architecture where different LLMs collaborate.

**Key Question:** How should we incorporate multiple LLMs into the RALPH-AGI workflow?

---

## Research & Analysis

Based on research into existing patterns (Architect-Builder, AI Critic Systems, academic papers), we identified four primary multi-agent patterns:

1.  **Builder + Critic:** One LLM builds, another reviews. Simple, effective, 2x cost.
2.  **Specialized Pipeline:** Architect → Builder → QA → Security. High expertise, complex orchestration, 4x+ cost.
3.  **Consensus Panel:** 3+ LLMs solve independently, evaluator picks best. Highest quality, 3-5x cost.
4.  **Architect + Parallel Builders:** Human + AI architect creates specs, spawns multiple builders. Massive parallelization, proven 5x productivity gain.

---

## Decision: Phased Multi-Agent Implementation

We will implement a **phased approach** to multi-agent architecture, starting with the simplest effective pattern and evolving to more complex patterns as the project matures.

### **Phase 1: Builder + Critic (Sprint 5)**

**Implementation:**

- **When:** Sprint 5, as part of Epic 05 (Evaluation Pipeline).
- **Pattern:** Builder + Critic loop.
- **Default:** Single-agent mode (for speed and cost).
- **Configurable:** Enable critic via `config.yaml` for quality-critical tasks.

**Architecture:**

```python
# In RalphLoop
def execute_task(self, task):
    # Builder implements
    code = self.builder.implement(task)

    if self.config.critic.enabled:
        # Critic reviews
        critique = self.critic.review(code, criteria=self.quality_criteria)
        if not critique.approved:
            task.add_feedback(critique)
            # Retry with feedback
            return self.execute_task(task)

    return code
```

**Configuration (`config.yaml`):**

```yaml
llm:
  builder:
    provider: "anthropic"
    model: "claude-sonnet-4"

  critic:
    enabled: false # Set to true for quality-critical tasks
    provider: "openai"
    model: "gpt-4.1"
```

**Rationale:**

- **Simplicity:** Easiest to implement within the existing `RalphLoop`.
- **Effectiveness:** Catches blind spots between different LLM providers (Anthropic vs. OpenAI).
- **Cost Control:** Disabled by default, only used when quality is paramount.
- **Alignment:** Fits perfectly into Epic 05 (Evaluation Pipeline).

---

### **Phase 2: Architect + Parallel Builders (Post-MVP)**

**Implementation:**

- **When:** Post-MVP (Week 13+), as a major new feature.
- **Pattern:** Architect + Parallel Builders.
- **Goal:** Scale development for large projects and achieve 5x productivity gains.

**Architecture:**

1.  **Architect:** The main RALPH-AGI instance, guided by a human, creates specs and plans (`_bmad-output/epics/` and `_bmad-output/stories/`).
2.  **Builders:** Multiple RALPH-AGI instances are spawned in parallel, each assigned a specific story.
3.  **Coordination:** Builders work on separate branches and create PRs upon completion.
4.  **Review:** The Architect (human + RALPH) reviews the PRs against the original spec.

**Rationale:**

- **Scalability:** The only pattern that supports massive parallelization.
- **Proven Results:** Based on Waleed Kadous's work, which showed a 5x productivity increase.
- **Human-in-the-Loop:** Keeps human oversight on critical architectural decisions.

---

## Implementation Plan

### **Sprint 5: Builder + Critic**

| Story                      | Points | Description                                     |
| :------------------------- | :----- | :---------------------------------------------- |
| **5.1: Critic Agent**      | 3      | Implement `Critic` class with `review()` method |
| **5.2: Configurable Mode** | 2      | Add `critic.enabled` to `config.yaml`           |
| **5.3: Loop Integration**  | 3      | Integrate critic review into `RalphLoop`        |
| **5.4: Quality Criteria**  | 2      | Define default quality criteria for code review |

### **Post-MVP: Architect + Builders**

| Epic                                   | Description                         |
| :------------------------------------- | :---------------------------------- |
| **Epic 06: Multi-Agent Orchestration** | Implement Architect-Builder pattern |

**Stories for Epic 06:**

- Story 6.1: Architect mode for spec/plan generation
- Story 6.2: Builder mode for spec execution
- Story 6.3: Orchestrator for spawning/monitoring builders
- Story 6.4: PR creation and review workflow

---

## Consequences

- **Positive:**
  - Increased code quality and robustness.
  - Clear path to scaling development.
  - Flexibility to trade cost for quality.
- **Negative:**
  - Increased LLM costs when critic is enabled.
  - Added complexity to the core loop.
  - Post-MVP work on Architect-Builder pattern is a significant undertaking.

---

## References

- [Architect-Builder Pattern](https://waleedk.medium.com/the-architect-builder-pattern-scaling-ai-development-with-spec-driven-teams-d3f094b8bdd0)
- [AI Critic System](https://shellypalmer.com/2025/11/how-to-build-an-ai-critic-system-that-actually-improves-your-work/)
- [Multi-Agent Adversarial Research](./multi-agent-adversarial-research.md)
