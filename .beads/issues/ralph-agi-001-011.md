---
id: ralph-agi-001-011
title: PRD Review Workflow - Multi-Agent Validation
type: feature
status: proposed
priority: 2
labels: [prd, bmad, workflow, multi-agent, quality]
created: 2026-01-18
updated: 2026-01-18
epic: epic-07-prd-quality
---

# PRD Review Workflow - Multi-Agent Validation

## Problem Statement

Currently, PRDs go directly from creation to task generation without structured validation. This leads to:

- Implementation blockers discovered mid-development
- Ambiguous acceptance criteria causing rework
- Missing edge cases and dependencies
- Inconsistent scope across requirements

**Key insight from Alexander Conroy:**

> "measure twice, cut once" - Having dedicated review agents validate PRD quality prevents expensive rework during implementation.

## Proposed Solution

Implement a BMAD workflow with three specialized review agents that examine the PRD from different perspectives before task generation:

1. **Technical Reviewer**: Feasibility, dependencies, architecture risks
2. **Product Reviewer**: Completeness, edge cases, scope alignment
3. **QA Reviewer**: Testability, clarity, measurability
4. **Orchestrator**: Synthesizes findings, determines verdict

## User Stories

**As a** product owner creating PRDs
**I want** automated multi-perspective review
**So that** issues are caught before development starts

**As a** developer working from PRD tasks
**I want** validated, clear acceptance criteria
**So that** I can implement confidently without guesswork

## Acceptance Criteria

### Workflow Structure

- [ ] BMAD workflow with 7 step files
- [ ] Three independent review agents
- [ ] Orchestrator synthesis step
- [ ] Iteration support for NEEDS_REVISION
- [ ] Review report output artifact

### Technical Reviewer

- [ ] Evaluate implementation feasibility
- [ ] Identify external dependencies
- [ ] Assess architecture risks
- [ ] Validate effort estimates
- [ ] Output: technical-findings.md

### Product Reviewer

- [ ] Validate user story completeness
- [ ] Check acceptance criteria quality
- [ ] Identify missing edge cases
- [ ] Verify scope consistency
- [ ] Output: product-findings.md

### QA Reviewer

- [ ] Assess testability of requirements
- [ ] Identify ambiguous language
- [ ] Check for contradictions
- [ ] Validate measurability
- [ ] Output: qa-findings.md

### Orchestrator

- [ ] Cross-reference findings from all agents
- [ ] Categorize issues by severity
- [ ] Determine verdict: APPROVED | NEEDS_REVISION | BLOCKED
- [ ] Generate consolidated recommendations
- [ ] Output: prd-review-report.md

### Integration

- [ ] Pre-task generation hook in scheduler
- [ ] CLI commands: `ralph review prd.json`
- [ ] Config option to enable/disable review
- [ ] Override option for NEEDS_REVISION

## Workflow Files

```
_bmad/bmm/workflows/2-plan-workflows/prd-review/
├── workflow.md
└── steps/
    ├── step-01-init.md          # Load PRD, validate structure
    ├── step-02-technical.md     # Technical reviewer
    ├── step-03-product.md       # Product reviewer
    ├── step-04-qa.md            # QA reviewer
    ├── step-05-synthesize.md    # Orchestrator synthesis
    ├── step-06-iterate.md       # Handle revisions
    └── step-07-complete.md      # Finalize report
```

## Configuration

```yaml
prd_review:
  enabled: true

  agents:
    technical:
      model: "sonnet"
    product:
      model: "sonnet"
    qa:
      model: "sonnet"
    orchestrator:
      model: "opus"

  thresholds:
    max_passes: 3
    critical_issue_blocks: true
    auto_approve_suggestions_only: true

  output:
    report_path: "{planning_artifacts}/prd-review-report.md"
```

## CLI Integration

```bash
# Standalone review
ralph review prd.json

# Review before run (if enabled in config)
ralph run --review

# Skip review
ralph run --no-review

# Force approval despite issues
ralph run --force-approve
```

## Dependencies

- BMAD framework (`_bmad/` directory structure)
- `ralph_agi/scheduler/hooks.py` for pre-task hook
- `ralph_agi/cli.py` for CLI integration

## Effort Estimate

| Story              | Points | Description                           |
| ------------------ | ------ | ------------------------------------- |
| Workflow structure | 2      | Create workflow.md and step files     |
| Technical reviewer | 3      | Implement step-02 with prompts        |
| Product reviewer   | 3      | Implement step-03 with prompts        |
| QA reviewer        | 3      | Implement step-04 with prompts        |
| Orchestrator       | 5      | Implement synthesis and verdict logic |
| CLI integration    | 3      | Add review commands and hooks         |
| Configuration      | 2      | Add config options and validation     |

**Total:** 21 points (Sprint 9-10)

## Success Metrics

- **Issue Detection Rate**: % of implementation issues caught in review
- **Rework Reduction**: Decrease in task reopenings/revisions
- **Review Time**: Time spent in review vs time saved in implementation
- **User Satisfaction**: Rating of review feedback usefulness

## Risks & Mitigations

| Risk                              | Mitigation                                |
| --------------------------------- | ----------------------------------------- |
| Over-reviewing delays projects    | Max pass limit (3), override option       |
| False positives cause fatigue     | Tuned prompts, severity thresholds        |
| Review becomes rubber stamp       | Require engagement with critical issues   |
| Different model opinions conflict | Orchestrator synthesis resolves conflicts |

## References

- [PRD Review Workflow](/path/to/_bmad/bmm/workflows/2-plan-workflows/prd-review/workflow.md)
- Alexander Conroy: "measure twice, cut once" principle
- ADR-002: Multi-Agent Architecture
- BMAD PRD Creation Workflow
