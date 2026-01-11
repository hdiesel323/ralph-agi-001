# Multi-Agent Architecture Implementation Guide

**Date:** 2026-01-11
**Status:** Approved for Sprint 5
**Related ADR:** [ADR-002: Multi-Agent Architecture](../decisions/2026-01-11_solutioning_multi-agent-architecture_approved.md)

---

## Overview

This guide provides step-by-step instructions for implementing the multi-agent architecture in RALPH-AGI, starting with the Builder + Critic pattern in Sprint 5.

---

## Phase 1: Builder + Critic (Sprint 5)

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         RalphLoop                           │
│                                                             │
│  ┌──────────────┐                                          │
│  │   Builder    │──────────┐                               │
│  │  (Claude)    │          │                               │
│  └──────────────┘          │                               │
│                            ▼                                │
│                     ┌──────────────┐                        │
│                     │     Code     │                        │
│                     └──────────────┘                        │
│                            │                                │
│                            │ if critic.enabled              │
│                            ▼                                │
│                     ┌──────────────┐                        │
│                     │    Critic    │                        │
│                     │    (GPT-4)   │                        │
│                     └──────────────┘                        │
│                            │                                │
│                     ┌──────┴──────┐                         │
│                     │             │                         │
│                 Approved      Rejected                      │
│                     │             │                         │
│                  Return      Add Feedback                   │
│                              & Retry                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Steps

### Step 1: Create `Critic` Class

**File:** `ralph_agi/core/critic.py`

```python
"""
Critic Agent for code review and quality assurance.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class CritiqueResult:
    """Result of a code review by the Critic agent.
    
    Attributes:
        approved: Whether the code passes the review.
        score: Overall quality score (1-5).
        feedback: Detailed feedback for improvement.
        issues: List of specific issues found.
    """
    approved: bool
    score: int  # 1-5
    feedback: str
    issues: list[str]


class Critic:
    """The Critic Agent - reviews code for quality and correctness.
    
    The Critic uses a different LLM than the Builder to catch blind spots
    and provide diverse perspectives on code quality.
    """
    
    def __init__(self, llm_provider: str = "openai", model: str = "gpt-4.1"):
        """Initialize the Critic agent.
        
        Args:
            llm_provider: LLM provider (e.g., "openai", "anthropic").
            model: Model name (e.g., "gpt-4.1", "claude-sonnet-4").
        """
        self.llm_provider = llm_provider
        self.model = model
        # TODO: Initialize LLM client
    
    def review(self, code: str, criteria: Optional[dict] = None) -> CritiqueResult:
        """Review code against quality criteria.
        
        Args:
            code: The code to review.
            criteria: Optional quality criteria (defaults to standard criteria).
        
        Returns:
            CritiqueResult with approval status and feedback.
        """
        if criteria is None:
            criteria = self._default_criteria()
        
        # TODO: Implement LLM-based review
        # For now, placeholder logic
        
        return CritiqueResult(
            approved=True,
            score=4,
            feedback="Code looks good overall.",
            issues=[]
        )
    
    def _default_criteria(self) -> dict:
        """Default quality criteria for code review."""
        return {
            "correctness": "Does the code solve the problem correctly?",
            "readability": "Is the code easy to understand?",
            "testing": "Are there adequate tests?",
            "security": "Are there any security vulnerabilities?",
            "performance": "Are there obvious performance issues?"
        }
```

---

### Step 2: Update `RalphConfig`

**File:** `ralph_agi/core/config.py`

Add critic configuration:

```python
@dataclass
class CriticConfig:
    """Configuration for the Critic agent."""
    enabled: bool = False
    provider: str = "openai"
    model: str = "gpt-4.1"
    min_score: int = 3  # Minimum acceptable score

@dataclass
class RalphConfig:
    """Configuration for RALPH-AGI."""
    # ... existing fields ...
    
    critic: CriticConfig = field(default_factory=CriticConfig)
```

---

### Step 3: Integrate Critic into `RalphLoop`

**File:** `ralph_agi/core/loop.py`

```python
from ralph_agi.core.critic import Critic, CritiqueResult

class RalphLoop:
    def __init__(self, config: RalphConfig, ...):
        # ... existing initialization ...
        
        # Initialize critic if enabled
        if config.critic.enabled:
            self.critic = Critic(
                llm_provider=config.critic.provider,
                model=config.critic.model
            )
        else:
            self.critic = None
    
    def _execute_task_with_review(self, task: Task) -> IterationResult:
        """Execute a task with optional critic review."""
        
        # Builder implements the task
        code = self._builder_implement(task)
        
        # If critic is enabled, review the code
        if self.critic:
            critique = self.critic.review(code)
            
            if not critique.approved or critique.score < self.config.critic.min_score:
                # Add feedback and retry
                task.add_feedback(critique.feedback)
                self.logger.warning(f"Critic rejected code (score: {critique.score}). Retrying...")
                return self._execute_task_with_review(task)
            
            self.logger.info(f"Critic approved code (score: {critique.score})")
        
        return IterationResult(success=True, output=code)
```

---

### Step 4: Update `config.yaml`

**File:** `config.yaml`

```yaml
llm:
  builder:
    provider: "anthropic"
    model: "claude-sonnet-4"

  critic:
    enabled: false  # Set to true for quality-critical tasks
    provider: "openai"
    model: "gpt-4.1"
    min_score: 3  # Minimum acceptable score (1-5)
```

---

### Step 5: Write Tests

**File:** `tests/core/test_critic.py`

```python
import pytest
from ralph_agi.core.critic import Critic, CritiqueResult

def test_critic_initialization():
    """Test that Critic initializes correctly."""
    critic = Critic(llm_provider="openai", model="gpt-4.1")
    assert critic.llm_provider == "openai"
    assert critic.model == "gpt-4.1"

def test_critic_review_approval():
    """Test that Critic can approve code."""
    critic = Critic()
    code = "def add(a, b): return a + b"
    result = critic.review(code)
    assert isinstance(result, CritiqueResult)
    assert result.approved is True
    assert 1 <= result.score <= 5

def test_critic_review_rejection():
    """Test that Critic can reject code."""
    # TODO: Implement with actual LLM integration
    pass
```

---

## Testing Strategy

### Unit Tests
- Test `Critic` class initialization
- Test `review()` method with mock LLM
- Test `CritiqueResult` dataclass

### Integration Tests
- Test `RalphLoop` with critic enabled
- Test retry logic when critic rejects code
- Test that critic is skipped when disabled

### End-to-End Tests
- Run a full task with critic enabled
- Verify that code quality improves with critic
- Measure cost increase (should be ~2x)

---

## Cost Analysis

| Configuration | LLM Calls per Task | Estimated Cost per Task |
| :--- | :--- | :--- |
| Single Agent (Builder only) | 1 | $0.10 |
| Builder + Critic (1 retry) | 2 | $0.20 |
| Builder + Critic (2 retries) | 3 | $0.30 |

**Recommendation:** Enable critic only for quality-critical tasks (e.g., production code, security-sensitive code).

---

## Configuration Examples

### Example 1: Default (No Critic)
```yaml
llm:
  critic:
    enabled: false
```

### Example 2: Quality-Critical Task
```yaml
llm:
  critic:
    enabled: true
    provider: "openai"
    model: "gpt-4.1"
    min_score: 4  # Higher bar for quality
```

### Example 3: Security Audit
```yaml
llm:
  critic:
    enabled: true
    provider: "anthropic"
    model: "claude-opus-4"  # Use most capable model
    min_score: 5  # Highest bar
```

---

## Success Metrics

| Metric | Target | How to Measure |
| :--- | :--- | :--- |
| **Code Quality Improvement** | +20% | Compare test coverage, bug density |
| **Blind Spot Detection** | 80%+ | Track issues caught by critic |
| **Cost Increase** | <2.5x | Monitor LLM API costs |
| **Retry Rate** | <30% | Track how often critic rejects code |

---

## Next Steps

1. **Sprint 5:** Implement Builder + Critic pattern
2. **Sprint 6:** Collect metrics on quality improvement and cost
3. **Sprint 7-12:** Refine critic criteria based on real-world usage
4. **Post-MVP:** Design and implement Architect + Builders pattern

---

## References

- [ADR-002: Multi-Agent Architecture](../decisions/2026-01-11_solutioning_multi-agent-architecture_approved.md)
- [Multi-Agent Adversarial Research](./multi-agent-adversarial-research.md)
- [Architect-Builder Pattern](https://waleedk.medium.com/the-architect-builder-pattern-scaling-ai-development-with-spec-driven-teams-d3f094b8bdd0)
- [AI Critic System](https://shellypalmer.com/2025/11/how-to-build-an-ai-critic-system-that-actually-improves-your-work/)
