---
id: ralph-agi-001-007
title: Multi-Agent LLM Architecture (Builder + Critic)
type: feature
status: planned
priority: 2
labels: [architecture, multi-agent, llm, quality, epic-05]
created: 2026-01-11
updated: 2026-01-11
epic: epic-05-evaluation-pipeline
---

# Multi-Agent LLM Architecture (Builder + Critic)

## Summary

Implement multi-agent architecture where different LLMs collaborate to improve code quality. Primary pattern: Builder LLM implements, Critic LLM reviews, with retry loop on rejection.

## Background

User asked about having different LLMs cross-checking each other's work - one builds, another QAs, they work "against" each other to catch blind spots and ensure quality.

**Research conducted:** Analyzed 4 multi-agent patterns from industry (Architect-Builder, AI Critic Systems, Consensus Panel, Parallel Builders).

## Decision: Phased Implementation

### Phase 1: Builder + Critic (Sprint 5)

- Builder (Claude Sonnet) implements code
- Critic (GPT-4.1) reviews for quality, security, correctness
- If rejected → feedback added → Builder retries
- Configurable via `config.yaml` (disabled by default)
- ~2x cost per iteration

### Phase 2: Architect + Parallel Builders (Post-MVP)

- Human + RALPH architect creates specs
- 3-4 parallel RALPH instances execute stories
- Architect reviews PRs against spec
- ~5x productivity gain (based on Kadous research)

### Phase 3: Full Adversarial Network (Future)

- Specialized agents: Security, Performance, UX
- Consensus voting on critical decisions
- Model diversity requirement

## Artifacts Created

- [x] ADR: `rnd/decisions/2026-01-11_solutioning_multi-agent-architecture_approved.md`
- [x] Q&A: `rnd/questions/2026-01-11_solutioning_multi-agent-llm-collaboration_answered.md`
- [x] Implementation Guide: `rnd/implementation/multi-agent-implementation-guide.md`

## Implementation Location

Phase 1 will be implemented in **Sprint 5** as part of **Epic 05 (Evaluation Pipeline)**:

- Add `critic` configuration to `config.yaml`
- Implement `CriticAgent` class
- Add retry loop to `RalphLoop.execute_task()`
- Quality criteria definition

## Acceptance Criteria

- [ ] Builder + Critic pattern implemented
- [ ] Configurable enable/disable via config
- [ ] Retry loop with feedback incorporation
- [ ] Different LLM providers supported (Claude, GPT, etc.)
- [ ] Cost tracking per iteration

## Related

- **Epic 05:** Evaluation Pipeline
- **Sprint 5:** Planned implementation
- **ADR-002:** Multi-Agent Architecture
