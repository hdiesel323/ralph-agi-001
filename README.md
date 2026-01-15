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
  <a href="#commands">Commands</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#creating-tasks">Creating Tasks</a>
</p>

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
1. Create a Python virtual environment
2. Install all dependencies
3. Prompt for your API key (saved to `.env`)
4. Verify the installation

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

## Commands

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

# Show estimated costs
./run-ralph.sh run --prd PRD.json --show-cost

# Launch the TUI for real-time monitoring
./run-ralph.sh tui --prd PRD.json

# TUI demo mode (see what it looks like)
./run-ralph.sh tui --demo
```

### Init Command Options

```bash
./run-ralph.sh init [OPTIONS]

Options:
  --quick           Use defaults (minimal prompts)
  --output PATH     Custom output path for config.yaml
  --sample-prd      Also generate a sample PRD.json
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
  # Workflow modes:
  #   direct: Commit anywhere (solo dev, risky)
  #   branch: Create feature branches (recommended)
  #   pr: Create branches + open PRs via gh CLI
  workflow: "branch"

  # Protected branches (cannot commit directly)
  protected_branches:
    - main
    - master

  # Prefix for auto-created branches
  branch_prefix: "ralph/"

  # Auto-push after commits
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

## Creating Tasks

### PRD.json Structure

The PRD (Product Requirements Document) file tells RALPH what to build:

```json
{
  "project": {
    "name": "Project Name",
    "description": "Brief description of the project"
  },
  "features": [
    {
      "id": "unique-feature-id",
      "name": "Feature Name",
      "description": "What this feature does",
      "tasks": [
        {
          "id": "unique-task-id",
          "description": "Specific task to complete",
          "priority": "P0",
          "status": "pending",
          "dependencies": ["other-task-id"],
          "acceptance_criteria": [
            "Criterion 1 that must be true",
            "Criterion 2 that must be true"
          ]
        }
      ]
    }
  ]
}
```

### Task Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier for the task |
| `description` | Yes | What needs to be done (be specific!) |
| `priority` | Yes | P0 (critical), P1 (high), P2 (medium), P3 (low), P4 (backlog) |
| `status` | Yes | `pending`, `in_progress`, `complete`, `blocked` |
| `dependencies` | No | List of task IDs that must complete first |
| `acceptance_criteria` | Recommended | List of conditions that prove completion |
| `steps` | No | Explicit step-by-step instructions |

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
    "Accepts JSON body with email and password fields",
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

### Tips for Effective Tasks

1. **Be specific** - "Add a button" vs "Add a blue 'Submit' button in the form footer"
2. **Include acceptance criteria** - How will RALPH know it's done?
3. **Use dependencies** - Tasks that need other tasks completed first
4. **Start small** - Break large features into smaller tasks
5. **Test commands** - Include the exact test command to verify

---

## How RALPH Works

### The Loop

RALPH runs a simple, robust loop:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   1. Load Context (memory, previous work, PRD)          │
│                        ↓                                │
│   2. Select Next Task (highest priority, unblocked)     │
│                        ↓                                │
│   3. Execute with LLM (Claude generates code)           │
│                        ↓                                │
│   4. Verify Completion (run acceptance criteria)        │
│                        ↓                                │
│   5. Update State (mark complete, save memory)          │
│                        ↓                                │
│   6. Check if Done → Exit                               │
│          ↓ not done                                     │
│   Loop back to step 1                                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Completion Detection

RALPH knows a task is complete when:
1. All acceptance criteria pass (tests, file checks, etc.)
2. The LLM outputs the completion signal: `<promise>COMPLETE</promise>`

### Error Handling

- **Retries** - Failed iterations retry with exponential backoff
- **Checkpoints** - State saved regularly for crash recovery
- **Max iterations** - Safety limit prevents infinite loops

---

## Terminal UI (TUI)

RALPH includes a rich terminal interface for monitoring:

```bash
./run-ralph.sh tui --prd PRD.json
```

Features:
- Real-time task status grid
- Live metrics (iterations, cost, tokens, time)
- Agent output viewer (see what RALPH is thinking)
- Log panel with filtering
- Keyboard shortcuts (q=quit, p=pause, s=stop)

Demo mode (no PRD required):
```bash
./run-ralph.sh tui --demo
```

---

## Troubleshooting

### Common Issues

**"ANTHROPIC_API_KEY not set"**
```bash
# Add to .env file
echo "ANTHROPIC_API_KEY=your-key-here" >> .env
```

**"ModuleNotFoundError: No module named 'ralph_agi'"**
```bash
# Activate the virtual environment
source venv/bin/activate
# Or reinstall
pip install -e .
```

**"Python 3.11+ required"**
```bash
# Check your version
python3 --version
# Install Python 3.11+ from python.org
```

**"Permission denied: ./run-ralph.sh"**
```bash
chmod +x run-ralph.sh install.sh
```

### Getting Help

- Check the [Documentation](https://glittery-pasca-96b28f.netlify.app)
- Open an [Issue](https://github.com/hdiesel323/ralph-agi-001/issues)
- Follow [@hdiesel_](https://twitter.com/hdiesel_) for updates

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

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `python3 -m pytest`
5. Submit a pull request

---

## License

RALPH-AGI is licensed under the **Mozilla Public License 2.0 (MPL-2.0)**.

- Free for personal and commercial use
- Modifications to MPL files must be shared
- Can be combined with proprietary code

See [LICENSE](LICENSE) for full details.

---

## Credits

RALPH-AGI is inspired by:

- [The Ralph Wiggum Pattern](https://ghuntley.com/ralph/) by [@GeoffreyHuntley](https://twitter.com/GeoffreyHuntley)
- [Anthropic's Agent Guidance](https://www.anthropic.com/engineering/building-effective-agents)
- [Beads](https://github.com/steveyegge/beads) by @steveyegge
- [Claude-Mem](https://github.com/thedotmack/claude-mem) by @thedotmack

---

<p align="center">
  <i>Building in public, one commit at a time.</i>
  <br><br>
  <a href="https://twitter.com/hdiesel_"><b>Follow @hdiesel_ for the journey →</b></a>
</p>
