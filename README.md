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
  <img src="https://img.shields.io/badge/version-0.1.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/tests-1478%20passing-success" alt="Tests">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-MPL%202.0-orange" alt="License">
</p>

<p align="center">
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#the-approach">The Approach</a> •
  <a href="#the-12-week-roadmap">Roadmap</a> •
  <a href="#standing-on-the-shoulders-of-giants">Credits</a>
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

## Installation

### Prerequisites

- **Python 3.11+** (check with `python3 --version`)
- **Git** (for cloning)
- **Anthropic API key** (get one at [console.anthropic.com](https://console.anthropic.com))

### One-Command Install

```bash
git clone https://github.com/hdiesel323/ralph-agi-001.git
cd ralph-agi-001
./install.sh
```

The installer will:
1. Check Python version (requires 3.11+)
2. Create a Python virtual environment
3. Install all dependencies
4. Prompt for your API key (saved to `.env`)
5. Verify the installation

### Manual Install

If you prefer manual setup:

```bash
# Clone the repository
git clone https://github.com/hdiesel323/ralph-agi-001.git
cd ralph-agi-001

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package
pip install -e ".[dev]"

# Create .env file with your API key
echo "ANTHROPIC_API_KEY=your-key-here" > .env
```

### Python Version Issues

If you have Python 3.9 but need 3.11+:

```bash
# macOS
brew install python@3.12

# Ubuntu/Debian
sudo apt install python3.12

# Then use it explicitly
python3.12 -m venv venv
source venv/bin/activate
pip install -e .
```

---

## Quick Start

### 1. Run the Setup Wizard

```bash
./run-ralph.sh init
```

This interactive wizard will:
- Configure your LLM provider (Anthropic, OpenAI, or OpenRouter)
- Set up git workflow preferences
- Generate a sample `config.yaml`
- Optionally create a sample `PRD.json` task file

### 2. Create a Task File (PRD.json)

Create a `PRD.json` file describing what you want RALPH to build:

```json
{
  "project": {
    "name": "My Project",
    "description": "What the project does"
  },
  "features": [
    {
      "id": "feature-1",
      "description": "Create a hello world script",
      "tasks": [
        {
          "id": "task-1",
          "description": "Create hello.py that prints 'Hello World'",
          "priority": "P0",
          "status": "pending",
          "acceptance_criteria": [
            "File hello.py exists",
            "Running 'python hello.py' prints 'Hello World'"
          ]
        }
      ]
    }
  ]
}
```

### 3. Run RALPH

```bash
./run-ralph.sh run --prd PRD.json
```

RALPH will:
- Parse your task file
- Select the highest priority task
- Execute it using AI
- Verify completion against acceptance criteria
- Mark as complete and move to the next task
- Repeat until all tasks are done

---

## Commands Reference

All commands can be run via `./run-ralph.sh` or by activating the venv and using `ralph-agi` directly.

### Main Commands

| Command | Description |
|---------|-------------|
| `run` | Start the autonomous loop |
| `init` | Interactive setup wizard |
| `tui` | Launch terminal UI (real-time monitoring) |
| `daemon` | Run as background service (scheduled execution) |

### Run Command Options

```bash
./run-ralph.sh run [OPTIONS]

Options:
  --prd PATH, -p PATH       Path to PRD.json task file (required for real work)
  --config PATH, -c PATH    Path to config.yaml (default: config.yaml)
  --max-iterations N        Override max iterations from config
  --verbose, -v             Show detailed output
  --quiet, -q               Show errors only
  --dry-run                 Parse and validate without executing
  --show-cost               Display token usage and cost estimates
```

### Examples

```bash
# Basic run with task file
./run-ralph.sh run --prd PRD.json

# Verbose mode to see what's happening
./run-ralph.sh run --prd PRD.json -v

# Limit to 10 iterations (for testing)
./run-ralph.sh run --prd PRD.json --max-iterations 10

# Dry run to validate PRD without executing
./run-ralph.sh run --prd PRD.json --dry-run

# Launch the TUI for real-time monitoring
./run-ralph.sh tui --prd PRD.json

# TUI demo mode (see what it looks like)
./run-ralph.sh tui --demo
```

---

## Configuration

### config.yaml

The main configuration file controls RALPH's behavior:

```yaml
# Maximum iterations before forced exit (safety limit)
max_iterations: 100

# String that signals task completion in LLM output
completion_promise: "<promise>COMPLETE</promise>"

# How often to save state (for crash recovery)
checkpoint_interval: 1

# Retry configuration for failed iterations
max_retries: 3
retry_delays: [1, 2, 4]  # Exponential backoff in seconds

# Git workflow configuration
git:
  workflow: "branch"        # direct, branch, or pr
  protected_branches: [main, master]
  branch_prefix: "ralph/"
  auto_push: true
```

### Environment Variables (.env)

API keys are stored in `.env` (never commit this file):

```bash
# Required: At least one LLM provider
ANTHROPIC_API_KEY=sk-ant-...

# Optional: Additional providers
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
```

---

## Creating Tasks (PRD.json)

### Task Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier for the task |
| `description` | Yes | What needs to be done (be specific!) |
| `priority` | Yes | P0 (critical), P1 (high), P2 (medium), P3 (low), P4 (backlog) |
| `status` | Yes | `pending`, `in_progress`, `complete`, `blocked` |
| `dependencies` | No | List of task IDs that must complete first |
| `acceptance_criteria` | Recommended | List of conditions that prove completion |

### Writing Good Tasks

**Good task:**
```json
{
  "id": "auth-1",
  "description": "Create a login endpoint at POST /api/login that accepts {email, password} and returns a JWT token",
  "priority": "P0",
  "status": "pending",
  "acceptance_criteria": [
    "POST /api/login endpoint exists",
    "Returns 200 with JWT token on valid credentials",
    "Returns 401 on invalid credentials",
    "Tests pass: pytest tests/test_auth.py -v"
  ]
}
```

**Bad task:**
```json
{
  "id": "auth",
  "description": "Add authentication",
  "priority": "P0",
  "status": "pending"
}
```

**Tips:**
1. **Be specific** - "Add a button" vs "Add a blue 'Submit' button in the form footer"
2. **Include acceptance criteria** - How will RALPH know it's done?
3. **Use dependencies** - Tasks that need other tasks completed first
4. **Start small** - Break large features into smaller tasks

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

**Big shoutout to [Geoffrey Huntley (@GeoffreyHuntley)](https://twitter.com/GeoffreyHuntley)** for creating the "Ralph Wiggum Pattern" that inspired this entire project. His original post at [ghuntley.com/ralph](https://ghuntley.com/ralph/) laid the foundation. If RALPH-AGI works, it's because Geoffrey figured out the simple truth, a while loop beats a fancy framework.

### Core Inspiration

| Project | Author | Stars | What We Learned |
|---------|--------|-------|-----------------|
| [**The Ralph Wiggum Pattern**](https://ghuntley.com/ralph/) | [@GeoffreyHuntley](https://twitter.com/GeoffreyHuntley) | - | The original! Simple loop > complex orchestration |
| [**Anthropic Agent Guidance**](https://www.anthropic.com/engineering/building-effective-agents) | Anthropic | - | Official best practices for long-running agents |
| [**Memvid**](https://github.com/memvid/memvid) | memvid | - | Portable AI memory in a single file (Sprint 2) |
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

*Interested in Enterprise?* [Join the waitlist](https://glittery-pasca-96b28f.netlify.app/enterprise) to get early access and special pricing.

---

## Follow the Build

This is a 12-week build-in-public journey. Follow along for daily updates, technical deep-dives, and all the wins and fails.

| Platform | Link | Content |
|----------|------|---------|
| **Twitter/X** | [@hdiesel_](https://twitter.com/hdiesel_) | Daily updates, hot takes |
| **Main Thread** | [The Journey](https://x.com/hdiesel_/status/2009969887356256679) | Full build story |
| **Documentation** | [View Docs](https://glittery-pasca-96b28f.netlify.app) | Technical docs |
| **Enterprise** | [Join Waitlist](https://glittery-pasca-96b28f.netlify.app/enterprise) | Early access signup |
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

## Project Structure

```
ralph-agi-001/
├── ralph_agi/              # Main Python package
│   ├── cli.py              # Command-line interface
│   ├── core/               # Core loop engine
│   │   ├── loop.py         # The main RALPH loop
│   │   └── config.py       # Configuration management
│   ├── llm/                # LLM integrations
│   │   ├── anthropic.py    # Claude integration
│   │   ├── openai.py       # OpenAI integration
│   │   └── agents.py       # Agent implementations
│   ├── tasks/              # Task management
│   │   ├── prd.py          # PRD parser
│   │   ├── selector.py     # Task selection algorithm
│   │   └── executor.py     # Task execution
│   ├── memory/             # Persistent memory system
│   ├── tools/              # Tool implementations
│   └── tui/                # Terminal UI
├── tests/                  # Test suite (1478 tests)
├── config.yaml             # Default configuration
├── install.sh              # One-command installer
├── run-ralph.sh            # Runner script
└── README.md               # You are here
```

---

## Troubleshooting

### Common Issues

**"Python 3.11 or higher is required"**
```bash
# macOS
brew install python@3.12

# Ubuntu
sudo apt install python3.12

# Then use explicitly
python3.12 -m venv venv
```

**"ANTHROPIC_API_KEY not set"**
```bash
echo "ANTHROPIC_API_KEY=your-key-here" >> .env
```

**"ModuleNotFoundError: No module named 'ralph_agi'"**
```bash
source venv/bin/activate
pip install -e .
```

**"Permission denied: ./run-ralph.sh"**
```bash
chmod +x run-ralph.sh install.sh
```

---

## Development

### Running Tests

```bash
source venv/bin/activate
python3 -m pytest                    # Run all tests
python3 -m pytest -v                 # Verbose output
python3 -m pytest tests/core/        # Run specific tests
python3 -m pytest --cov=ralph_agi    # With coverage
```

### Contributing

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
A: It's usable now! Clone the repo, run the installer, and try it. We're building in public - expect rough edges.

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
