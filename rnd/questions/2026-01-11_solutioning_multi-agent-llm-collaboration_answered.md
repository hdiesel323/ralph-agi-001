# Question: Multi-Agent LLM Collaboration

**Date:** 2026-01-11
**Phase:** Solutioning
**Status:** Answered
**Asked by:** User
**Answered by:** Manus AI

---

## Question

> I saw a methodology the other day about having different LLMs doing different jobs, within the same codebase. How could we include something like that here? Do one LLM builds and the other QA's pushes back etc so they build "against" each other. Or have different LLMs working in the same code base, QA'ing asking questions "talking" to each other? Effectively stop gaps in LLMs to make sure everything is done perfectly?

---

## Answer

This is an excellent idea! Multi-agent adversarial architectures are a proven pattern for improving code quality and catching blind spots. Based on extensive research, I recommend a **phased approach** that starts simple and evolves as the project matures.

### **Recommended Approach: Phased Implementation**

#### **Phase 1: Builder + Critic (Sprint 5)**

The simplest and most effective pattern for RALPH-AGI is the **Builder + Critic** loop:

1.  **Builder LLM** (e.g., Claude Sonnet 4) implements the code.
2.  **Critic LLM** (e.g., GPT-4.1) reviews the code for quality, correctness, security, and readability.
3.  If the Critic **approves**, the code proceeds.
4.  If the Critic **rejects**, feedback is added to the context, and the Builder retries.

**Why this works:**

- **Different LLMs have different blind spots.** Claude might miss what GPT catches, and vice versa.
- **Simple to implement** within the existing `RalphLoop`.
- **Cost-effective:** 2x cost per iteration is acceptable for quality-critical tasks.
- **Configurable:** Disabled by default, enabled for production code or security-sensitive tasks.

**Architecture:**

```
Builder (Claude) → Code → Critic (GPT-4) → Approved? → Proceed
                              ↓
                           Rejected
                              ↓
                        Add Feedback & Retry
```

---

#### **Phase 2: Architect + Parallel Builders (Post-MVP)**

For larger projects, the **Architect + Parallel Builders** pattern provides massive scalability:

1.  **Architect** (human + RALPH) creates specs and plans.
2.  **Builders** (3-4 parallel RALPH instances) execute separate stories concurrently.
3.  **Architect** reviews PRs against the original spec.

**Why this works:**

- **Proven 5x productivity gain** (based on Waleed Kadous's research).
- **Massive parallelization** for large projects.
- **Human-in-the-loop** for critical architectural decisions.
- **Compounding context:** More specs = better AI performance over time.

**Architecture:**

```
Architect (Human + RALPH)
    ↓
  Specs & Plans
    ↓
┌───┴───┬───┬───┐
Builder Builder Builder Builder (parallel)
│       │     │       │
PR      PR    PR      PR
└───┬───┴───┴───┘
    ↓
Architect Review → Merge
```

---

### **Implementation Plan**

#### **Sprint 5: Builder + Critic**

| Story                      | Points | Description                                     |
| :------------------------- | :----- | :---------------------------------------------- |
| **5.1: Critic Agent**      | 3      | Implement `Critic` class with `review()` method |
| **5.2: Configurable Mode** | 2      | Add `critic.enabled` to `config.yaml`           |
| **5.3: Loop Integration**  | 3      | Integrate critic review into `RalphLoop`        |
| **5.4: Quality Criteria**  | 2      | Define default quality criteria for code review |

**Configuration Example:**

```yaml
llm:
  builder:
    provider: "anthropic"
    model: "claude-sonnet-4"

  critic:
    enabled: false # Set to true for quality-critical tasks
    provider: "openai"
    model: "gpt-4.1"
    min_score: 3 # Minimum acceptable score (1-5)
```

---

#### **Post-MVP: Architect + Builders**

| Epic                                   | Description                                                  |
| :------------------------------------- | :----------------------------------------------------------- |
| **Epic 06: Multi-Agent Orchestration** | Implement Architect-Builder pattern for large-scale projects |

---

### **Cost vs. Quality Tradeoffs**

| Pattern                      | LLM Calls per Task | Relative Cost | Quality Improvement             |
| :--------------------------- | :----------------- | :------------ | :------------------------------ |
| **Single Agent**             | 1                  | 1x            | Baseline                        |
| **Builder + Critic**         | 2                  | 2x            | +20-30%                         |
| **Consensus Panel (3 LLMs)** | 3-5                | 3-5x          | +40-50%                         |
| **Architect + Builders**     | 1 + N (parallel)   | 1 + N         | +300-500% (via parallelization) |

**Recommendation:** Use Builder + Critic for quality-critical tasks, and Architect + Builders for large projects.

---

### **Why This Approach?**

1.  **Research-Backed:** Based on proven patterns from Waleed Kadous (Architect-Builder) and Shelly Palmer (AI Critic Systems).
2.  **Incremental:** Start simple (Builder + Critic), evolve to complex (Architect + Builders).
3.  **Configurable:** Trade cost for quality based on task importance.
4.  **Aligned with RALPH-AGI:** Fits naturally into Epic 05 (Evaluation Pipeline) and future Epic 06 (Multi-Agent Orchestration).

---

## Decision

**Approved:** Implement multi-agent architecture in two phases:

1.  **Sprint 5:** Builder + Critic (configurable, disabled by default).
2.  **Post-MVP:** Architect + Parallel Builders (for large-scale projects).

---

## Follow-Up Actions

- [x] Create ADR-002: Multi-Agent Architecture
- [x] Create implementation guide for Sprint 5
- [ ] Add Epic 06 to roadmap (Post-MVP)
- [ ] Update PRD with multi-agent capabilities

---

## References

- [ADR-002: Multi-Agent Architecture](../decisions/2026-01-11_solutioning_multi-agent-architecture_approved.md)
- [Multi-Agent Implementation Guide](../implementation/multi-agent-implementation-guide.md)
- [Architect-Builder Pattern](https://waleedk.medium.com/the-architect-builder-pattern-scaling-ai-development-with-spec-driven-teams-d3f094b8bdd0)
- [AI Critic System](https://shellypalmer.com/2025/11/how-to-build-an-ai-critic-system-that-actually-improves-your-work/)
