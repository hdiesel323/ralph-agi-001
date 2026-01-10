# RALPH-AGI

### An AI that codes while you sleep.

<p align="center">
  <img src="https://img.shields.io/badge/status-building%20in%20public-brightgreen" alt="Status">
  <img src="https://img.shields.io/badge/week-1%20of%2012-blue" alt="Week 1">
  <img src="https://img.shields.io/badge/tests-33%20passing-success" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-99%25-brightgreen" alt="Coverage">
</p>

<p align="center">
  <b>Recursive Autonomous Long-horizon Processing with Hierarchical intelligence</b>
</p>

---

## The Problem

AI coding assistants are brilliant... for about 5 minutes.

Then they forget everything. Lose context. Start hallucinating. You're back to square one.

**What if an AI could:**
- Work on tasks for hours (or days) without losing track
- Remember what it learned yesterday
- Know when it's done vs. when it's stuck
- Actually finish what it started

That's RALPH-AGI.

---

## The Idea

Most AI agent frameworks are overengineered. Complex orchestration, state machines, planning systems...

RALPH-AGI takes a different approach: **a simple loop that doesn't quit.**

```python
while not complete and under_budget:
    result = execute_task_with_retry()
    if task_complete(result):
        break
    learn_from_result(result)
```

That's it. The "Ralph Wiggum Pattern" - start simple, keep trying, get smarter.

> *"Same energy as Ralph Wiggum eating glue... but with memory that actually works and self-improves so it eventually stops eating glue and starts building real stuff."*

---

## Current Status: Week 1 of 12

Building this 100% in public. Every win. Every failure. Every 3am debugging session.

### Sprint 1 Progress: 33% Complete

| Story | Status | Description |
|-------|--------|-------------|
| 1.1 Basic Loop | ✅ Done | Core execution engine |
| 1.2 Completion Detection | 🔲 Next | Know when to stop |
| 1.3 Configuration | 🔲 Planned | YAML-driven behavior |
| 1.4 AFK Mode | 🔲 Planned | Run autonomously |

### What's Working Now

```
✅ RalphLoop engine - 33 tests, 99% coverage
✅ Exponential backoff retry (1s → 2s → 4s)
✅ Completion signal detection
✅ Clean error handling with context
✅ ISO timestamp logging
```

---

## The 12-Week Roadmap

| Phase | Weeks | Goal |
|-------|-------|------|
| **1. Core Loop** | 1-2 | Basic execution + completion detection |
| **2. Task Management** | 3-4 | Beads integration, priorities, dependencies |
| **3. Memory** | 5-6 | Persistent context, learning from history |
| **4. Tools** | 7-8 | File ops, git, testing, external APIs |
| **5. Evaluation** | 9-10 | Self-verification, quality checks |
| **6. Polish** | 11-12 | CLI, docs, real-world testing |

---

## Follow the Build

**Twitter:** [@hdiesel_](https://twitter.com/hdiesel_) - Daily updates, wins & fails

**Main Thread:** [The 12-week journey starts here](https://x.com/hdiesel_/status/2009969887356256679)

---

## Tech Stack

- **Python 3.11+** - Core engine
- **Claude** - LLM backbone
- **Beads** - Task/issue management
- **pytest** - Testing (99% coverage goal)

---

## Try It (Coming Soon)

```bash
# Not ready for public use yet - follow along!
pip install ralph-agi  # Week 6ish
```

---

## Research Foundation

RALPH-AGI is built on analysis of 9 autonomous agent systems:

- Anthropic's Official Agent Guidance (Nov 2025)
- Ralph Wiggum Pattern ($50k from $297 investment)
- AI-Long-Task (AlphaEvolve-inspired)
- Continuous-Claude-v3 (2k+ stars)
- Beads (9.4k stars) - Task management
- Claude-Mem (12.9k stars) - Memory systems
- And more in `/DOCUMENTATION`

---

## Project Structure

```
ralph-agi-001/
├── src/
│   └── core/
│       └── loop.py          # The heart of RALPH
├── tests/
│   └── core/
│       └── test_loop.py     # 33 tests, 99% coverage
├── _bmad-output/            # Sprint planning & stories
├── DOCUMENTATION/           # Research & analysis
└── client/                  # Documentation website
```

---

## Contributing

Not accepting PRs yet (still in early build phase), but:

- ⭐ **Star the repo** to follow progress
- 🐛 **Open issues** for ideas/feedback
- 💬 **Join the conversation** on Twitter

---

## License

MIT - Build cool stuff with it.

---

<p align="center">
  <i>Building in public, one commit at a time.</i>
  <br><br>
  <a href="https://twitter.com/hdiesel_">Follow the journey →</a>
</p>
