<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,14,25,27&height=200&section=header&text=RALPH-AGI&fontSize=70&fontAlignY=35&desc=An%20AI%20that%20codes%20while%20you%20sleep&descSize=25&descAlignY=55&fontColor=ffffff&animation=fadeIn" alt="RALPH-AGI Banner">
</p>

<h3 align="center">
  <b>RALPH-AGI</b> — Recursive Autonomous Long-horizon Processing with Hierarchical intelligence
</h3>

<p align="center">
  <i>An autonomous AI agent that works on complex coding tasks for hours, remembers everything, and knows when it's done.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-building%20in%20public-brightgreen" alt="Status">
  <img src="https://img.shields.io/badge/week-1%20of%2012-blue" alt="Week 1">
  <img src="https://img.shields.io/badge/tests-83%20passing-success" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-97%25-brightgreen" alt="Coverage">
  <img src="https://img.shields.io/badge/license-MPL%202.0-orange" alt="License">
</p>

<p align="center">
  <a href="https://twitter.com/hdiesel_">Follow the Build</a> •
  <a href="#standing-on-the-shoulders-of-giants">Credits & Inspiration</a> •
  <a href="#the-12-week-roadmap">Roadmap</a> •
  <a href="https://ralph-agi.netlify.app">Documentation</a>
</p>

---

## The Problem

AI coding assistants are brilliant... for about 5 minutes.

Then they forget everything. Lose context. Start hallucinating. You're back to square one.

**Current AI limitations:**
- 🧠 **No persistent memory** - Every conversation starts from zero
- ⏱️ **Context window limits** - Long tasks get truncated
- 🎯 **No task completion awareness** - Doesn't know when it's actually done
- 🔄 **No learning** - Makes the same mistakes repeatedly
- 👀 **Requires constant supervision** - Can't run autonomously

**What if an AI could:**
- Work on complex tasks for hours (or days) without losing track
- Remember what it learned yesterday, last week, last month
- Know when it's genuinely done vs. when it's stuck
- Learn from mistakes and improve over time
- Run autonomously while you sleep (AFK Mode)

That's RALPH-AGI.

---

## The Approach

Most AI agent frameworks are overengineered. Complex orchestration, state machines, planning systems, agent hierarchies...

RALPH-AGI takes a radically simple approach inspired by the best open-source agent systems:

**The "Ralph Wiggum Pattern"** - Start simple, keep trying, get smarter.

```python
while not complete and under_budget:
    context = load_memory()
    result = execute_task_with_retry(context)

    if task_complete(result):
        celebrate()
        break

    save_to_memory(result)
    learn_from_result(result)
```

> *"Same energy as Ralph Wiggum eating glue... but with memory that actually works and self-improves so it eventually stops eating glue and starts building real stuff."*

### Core Principles

| Principle | Why It Matters |
|-----------|----------------|
| **Simple Loop > Complex Orchestration** | A while loop beats fancy agent frameworks |
| **Persistent Memory** | Context survives across sessions |
| **Completion Detection** | Knows when to stop (and when to keep going) |
| **Graceful Failure** | Retries with exponential backoff, learns from errors |
| **Human-in-the-Loop Option** | AFK mode OR supervised mode |

---

## Current Status: Week 1 of 12

**Building this 100% in public.** Every win. Every failure. Every 3am debugging session.

### Sprint 1 Progress: 100% Complete ✅

| Story | Points | Status | Description |
|-------|--------|--------|-------------|
| 1.1 Basic Loop | 3 | ✅ Done | Core RalphLoop execution engine |
| 1.2 Completion Detection | 2 | ✅ Done | Promise-based completion signals |
| 1.3 Configuration | 2 | ✅ Done | YAML-driven behavior |
| 1.4 AFK Mode | 2 | ✅ Done | Autonomous operation mode |

### What's Working Now

```
✅ RalphLoop engine with configurable iterations
✅ IterationResult dataclass for rich output
✅ Exponential backoff retry logic (1s → 2s → 4s)
✅ Completion signal detection (<promise>COMPLETE</promise>)
✅ MaxRetriesExceeded with full error context
✅ ISO timestamp logging [YYYY-MM-DDTHH:MM:SS]
✅ Resource cleanup via close() method
✅ YAML configuration management (RalphConfig)
✅ Signal handling (SIGINT/SIGTERM)
✅ Checkpoint save/load for state persistence
✅ Resume from checkpoint (AFK mode)
✅ Graceful shutdown with state preservation
✅ 83 unit tests passing
✅ 97% code coverage
```

---

## The 12-Week Roadmap

| Phase | Weeks | Epic | Goal |
|-------|-------|------|------|
| **1. Core Loop** | 1-2 | `epic-01` | Basic execution engine + completion detection |
| **2. Task Management** | 3-4 | `epic-02` | Beads integration, priorities, dependencies |
| **3. Memory System** | 5-6 | `epic-03` | Persistent context, semantic search, learning |
| **4. Tool Integration** | 7-8 | `epic-04` | File ops, git, testing, external APIs |
| **5. Evaluation Pipeline** | 9-10 | `epic-05` | Self-verification, quality gates, metrics |
| **6. Polish & Ship** | 11-12 | - | CLI, documentation, real-world testing |

### Success Metrics

- **Autonomous Task Completion:** 80%+ success rate on SWE-bench-lite
- **Context Retention:** Maintain coherent context over 100+ iterations
- **Self-Recovery:** 90%+ recovery from common errors without human intervention
- **Cost Efficiency:** <$5 average cost per completed task

---

## Standing on the Shoulders of Giants

**RALPH-AGI wouldn't exist without these incredible open-source projects and research.**

This project synthesizes ideas and patterns from the following (all credit to the original authors):

### 🎉 Special Thanks

**Massive shoutout to [Geoffrey Huntley (@GeoffreyHuntley)](https://twitter.com/GeoffreyHuntley)** for creating the "Ralph Wiggum Pattern" that inspired this entire project. His original post at [ghuntley.com/ralph](https://ghuntley.com/ralph/) laid the foundation for everything you see here. If RALPH-AGI works, it's because Geoffrey figured out the simple truth: a while loop beats a fancy framework.

### Core Inspiration

| Project | Author | Stars | What We Learned |
|---------|--------|-------|-----------------|
| [**The Ralph Wiggum Pattern**](https://ghuntley.com/ralph/) | [@GeoffreyHuntley](https://twitter.com/GeoffreyHuntley) | - | The original! Simple loop > complex orchestration |
| [**Anthropic Agent Guidance**](https://www.anthropic.com/engineering/building-effective-agents) | Anthropic | - | Official best practices for long-running agents |
| [**Beads**](https://github.com/steveyegge/beads) | @steveyegge | 9.4k⭐ | Dependency-aware task management |
| [**Claude-Mem**](https://github.com/thedotmack/claude-mem) | @thedotmack | 12.9k⭐ | Persistent memory architecture |

### Additional Research

| Project | What We Learned |
|---------|-----------------|
| [**AI-Long-Task**](https://github.com/FareedKhan-dev/ai-long-task) | AlphaEvolve-inspired autonomous execution |
| [**Continuous-Claude-v3**](https://github.com/zckly/continuous-claude-v3) | Hooks system for automatic behaviors |
| [**MCP-CLI**](https://github.com/anthropics/anthropic-tools) | Tool integration patterns |

### Research Papers & Posts

- [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) - Anthropic Engineering
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) - Anthropic Engineering

**We're not claiming to have invented any of these patterns.** We're combining the best ideas into a cohesive, well-tested system and building it in public so others can learn and contribute.

---

## License: Open Core Model

RALPH-AGI uses an **open core** licensing model (similar to GitLab, Grafana, and Mozilla):

### Community Edition (This Repo) - MPL 2.0

```
✅ Free forever for personal use
✅ Free for open source projects
✅ Free for commercial use (self-hosted)
✅ Modify and distribute freely
✅ Contribute improvements back to the community
```

**Mozilla Public License 2.0** - You can use, modify, and distribute this code. Modifications to MPL-licensed files must be shared, but you can combine with proprietary code.

### Enterprise Edition (Coming Soon)

For teams that want managed infrastructure and enterprise features:

```
🏢 Hosted cloud version (no setup required)
🔐 SSO/SAML authentication
📊 Team dashboards & analytics
🛡️ Priority support & SLAs
🔧 Custom integrations
💰 Subscription pricing
```

*Interested in Enterprise?* [Join the waitlist](https://ralph-agi.netlify.app/enterprise) to get early access and special pricing.

---

## Follow the Build

This is a 12-week build-in-public journey. Follow along for daily updates, technical deep-dives, and all the wins and fails.

| Platform | Link | Content |
|----------|------|---------|
| **Twitter/X** | [@hdiesel_](https://twitter.com/hdiesel_) | Daily updates, hot takes |
| **Main Thread** | [The Journey](https://x.com/hdiesel_/status/2009969887356256679) | Full build story |
| **Documentation** | [ralph-agi.netlify.app](https://ralph-agi.netlify.app) | Technical docs |
| **This Repo** | Star ⭐ for updates | Code, issues, discussions |

---

## Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| **Language** | Python 3.11+ | Type hints, async support, ecosystem |
| **LLM** | Claude (Anthropic) | Best-in-class reasoning, long context |
| **Task Management** | Beads | Dependency-aware, SQLite-backed |
| **Memory** | Claude-Mem patterns | Semantic search, compaction |
| **Testing** | pytest | 99% coverage target |
| **CI/CD** | GitHub Actions | Automated testing & deployment |

---

## Quick Start (Coming Week 6)

```bash
# Not ready for public use yet - follow along for updates!

# Eventually:
pip install ralph-agi

# Configure
ralph init
ralph config set llm.provider anthropic
ralph config set llm.model claude-sonnet-4

# Run a task
ralph run "Implement user authentication for my Flask app"

# AFK Mode (autonomous)
ralph run --afk "Complete all tasks in TODO.md"
```

---

## Project Structure

```
ralph-agi-001/
│
├── 🔧 ralph_agi/                # The RALPH-AGI Python package
│   ├── __init__.py
│   └── core/
│       ├── loop.py              # 🔥 The heart of RALPH
│       └── config.py            # YAML configuration management
│
├── 🧪 tests/                    # Test suite (83 tests, 97% coverage)
│   └── core/
│       ├── test_loop.py
│       ├── test_config.py
│       └── test_afk_mode.py
│
├── 🌐 website/                  # Project website (Netlify)
│   ├── src/                     # React components
│   └── public/                  # Static assets
│
├── 📚 docs/                     # Official documentation
│   ├── RALPH-AGI-PRD.md
│   ├── RALPH-AGI-ARCHITECTURE.md
│   └── ...
│
├── 📋 _bmad-output/             # Sprint planning & stories
│   ├── epics/
│   ├── stories/
│   └── sprint-status.yaml
│
├── pyproject.toml               # Python package config
├── LICENSE                      # MPL 2.0
└── README.md                    # You are here
```

---

## Contributing

**Not accepting PRs yet** (still in early build phase), but here's how to get involved:

| Action | How |
|--------|-----|
| ⭐ **Star the repo** | Get notified of updates |
| 🐛 **Open issues** | Bug reports, feature ideas, questions |
| 💬 **Join Twitter** | Daily discussions, polls, feedback |
| 📧 **Enterprise interest** | DM [@hdiesel_](https://twitter.com/hdiesel_) |

Once we hit Week 8, we'll open up for community contributions with clear guidelines.

---

## FAQ

**Q: Why "Ralph Wiggum"?**
A: The pattern is named after the Simpsons character who famously eats paste. The idea is that the agent starts simple (even dumb), but unlike Ralph, it actually learns and improves over time.

**Q: How is this different from AutoGPT, BabyAGI, etc.?**
A: Those projects focus on complex planning and agent hierarchies. RALPH-AGI focuses on a simple, robust execution loop with persistent memory. Less magic, more reliability.

**Q: When will it be ready to use?**
A: Follow the 12-week build. MVP targeting Week 6 (basic CLI), production-ready by Week 12.

**Q: Can I use this for my company?**
A: Yes! The MPL 2.0 license allows commercial use. For managed hosting and enterprise features, stay tuned for the Enterprise Edition.

---

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,14,25,27&height=100&section=footer">
    <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,14,25,27&height=100&section=footer" alt="Footer">
  </picture>
</p>

<p align="center">
  <i>Building in public, one commit at a time.</i>
  <br><br>
  <a href="https://twitter.com/hdiesel_"><b>Follow @hdiesel_ for the journey →</b></a>
</p>
