# RALPH-AGI Quick Start Guide

## Installation (One Command)

```bash
./install.sh
```

This will:

- Create a Python virtual environment
- Install all dependencies (including anthropic)
- Prompt for your API key
- Set up everything automatically

## Running RALPH-AGI

### Basic Usage

```bash
# See all options
./run-ralph.sh --help

# Run basic loop (demo mode)
./run-ralph.sh run

# Run with a PRD file (real LLM execution)
./run-ralph.sh run --prd your_prd.json

# Run with more iterations
./run-ralph.sh run --prd your_prd.json --max-iterations 50

# Verbose output
./run-ralph.sh run -v

# Quiet mode (errors only)
./run-ralph.sh run -q
```

### Manual Activation

If you prefer to activate the environment manually:

```bash
source venv/bin/activate
ralph-agi run --help
```

## Configuration

### API Key

Your Anthropic API key should be in `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

The installer creates this automatically, or edit manually.

### Config File

Main configuration is in `config.yaml`:

```yaml
max_iterations: 10
retry_attempts: 3
completion_signal: "<promise>COMPLETE</promise>"
```

---

# Beads - Issue Tracking System

Beads is a lightweight, git-friendly issue tracker built into this project. It stores issues in `.beads/` and syncs with git.

## Quick Commands

```bash
# Initialize (already done for this project)
bd init

# List all open issues
bd list

# List ready-to-work tasks (no blockers)
bd ready

# Create a new issue
bd create --title="Fix login bug" --type=bug --priority=2

# View issue details
bd show beads-123

# Update status
bd update beads-123 --status=in_progress

# Close an issue
bd close beads-123

# Sync with git
bd sync
```

## Issue Types

| Type      | Use For            |
| --------- | ------------------ |
| `task`    | General work items |
| `bug`     | Bug fixes          |
| `feature` | New features       |

## Priority Levels

| Priority | Meaning                    |
| -------- | -------------------------- |
| 0 (P0)   | Critical - drop everything |
| 1 (P1)   | High - do soon             |
| 2 (P2)   | Medium - normal priority   |
| 3 (P3)   | Low - when time permits    |
| 4 (P4)   | Backlog - someday          |

## Dependencies

```bash
# Add dependency (issue-B depends on issue-A)
bd dep add beads-B beads-A

# View blocked issues
bd blocked
```

## Workflow

```bash
# 1. Find work
bd ready

# 2. Claim it
bd update beads-123 --status=in_progress

# 3. Do the work...

# 4. Close it
bd close beads-123

# 5. Sync to git
bd sync
```

---

# BMAD - Method for AI Development

BMAD (BMad Method for Agile Development) is a framework for structuring AI-assisted development workflows. The `_bmad/` folder contains agents and workflows.

## Structure

```
_bmad/
├── core/           # Core agents and workflows
│   ├── agents/     # AI agent definitions
│   └── workflows/  # Step-by-step workflows
├── bmm/            # Main method workflows
└── bmb/            # Builder workflows
```

## Key Concepts

### Agents

Pre-defined AI personas with specific expertise:

- `bmad-master` - Main orchestrator
- `dev` - Developer agent
- `architect` - System design
- `pm` - Product management

### Workflows

Step-by-step processes for common tasks:

- `create-prd` - Create product requirements
- `create-architecture` - Design system architecture
- `dev-story` - Implement a user story
- `code-review` - Review code changes

## Using BMAD Workflows

In Claude Code, invoke workflows with:

```
/bmad:bmm:workflows:create-prd
/bmad:bmm:workflows:dev-story
```

Or reference agents:

```
/bmad:bmm:agents:dev
```

---

# Troubleshooting

## "anthropic package not installed"

```bash
source venv/bin/activate
pip install anthropic
```

## "ANTHROPIC_API_KEY not set"

Make sure `.env` has your key:

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

Then run with `./run-ralph.sh` (it auto-loads .env).

## Virtual environment issues

Recreate it:

```bash
rm -rf venv
./install.sh
```

## Permission denied on scripts

```bash
chmod +x install.sh run-ralph.sh
```
