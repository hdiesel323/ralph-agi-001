# RALPH-AGI Demo

## What is RALPH?

**RALPH** = **R**ecursive **A**utonomous **L**ong-horizon **P**rocessing **H**andler

RALPH is an autonomous AI agent that can execute software engineering tasks without human intervention. You give it a list of tasks, and it works through them one by one until complete.

### Key Capabilities

| Capability | Description |
|------------|-------------|
| **Task Selection** | Automatically picks the next task based on priority and dependencies |
| **Code Generation** | Writes code using LLM (Claude/GPT) with tool access |
| **File Operations** | Reads, writes, and modifies files in the project |
| **Shell Execution** | Runs commands, tests, build scripts |
| **Self-Verification** | Marks tasks complete only when acceptance criteria are met |
| **Memory** | Remembers context across iterations for coherent multi-step work |

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      RALPH Loop                             │
│                                                             │
│   PRD.json ──► Task Selector ──► Builder Agent ──► Tools    │
│       │              │               │              │       │
│       │              │               │              ▼       │
│       │              │               │      ┌─────────────┐ │
│       │              │               │      │ read_file   │ │
│       │              │               │      │ write_file  │ │
│       │              │               └─────►│ run_command │ │
│       │              │                      │ git_status  │ │
│       │              │                      │ list_dir    │ │
│       │              │                      └─────────────┘ │
│       │              │                                      │
│       ▼              ▼                                      │
│   ┌──────────────────────────────────────────────┐          │
│   │  Task Complete? ──► Update PRD ──► Next Task │          │
│   └──────────────────────────────────────────────┘          │
│                           │                                 │
│                           ▼                                 │
│                  All Tasks Done? ──► EXIT                   │
└─────────────────────────────────────────────────────────────┘
```

## Demo Scenarios

We have 3 test scenarios of increasing complexity:

### Scenario 1: Hello World (Simple)
- **Task**: Create a Python script that prints a message
- **Complexity**: Single file, no dependencies
- **Expected**: ~1 iteration, ~5 seconds

### Scenario 2: Calculator Module (Medium)
- **Task**: Create a calculator module with add/subtract/multiply/divide
- **Complexity**: Multiple functions, basic logic
- **Expected**: ~1-2 iterations, ~15 seconds

### Scenario 3: Multi-Task Project (Complex)
- **Tasks**:
  1. Create a utility module
  2. Add tests for the module
  3. Create a CLI wrapper
- **Complexity**: 3 dependent tasks, multiple files
- **Expected**: ~3-4 iterations, ~45 seconds

## Running the Demo

### Prerequisites
```bash
# Set your API key (OpenAI or Anthropic)
export OPENAI_API_KEY=sk-...
# or
export ANTHROPIC_API_KEY=sk-ant-...
```

### Quick Demo
```bash
cd demo
./run_demo.sh
```

### Individual Scenarios
```bash
# Scenario 1: Hello World
cd demo/scenario-1-hello
ralph-agi run --prd PRD.json --config config.yaml -v

# Scenario 2: Calculator
cd demo/scenario-2-calculator
ralph-agi run --prd PRD.json --config config.yaml -v

# Scenario 3: Multi-Task
cd demo/scenario-3-multitask
ralph-agi run --prd PRD.json --config config.yaml -v
```

## What to Watch For

During the demo, observe:

1. **Task Selection** - RALPH picks tasks in priority order
2. **Tool Calls** - LLM decides which tools to use
3. **Code Quality** - Generated code should be clean and working
4. **Completion Detection** - Tasks marked complete when done
5. **Multi-Task Flow** - Dependencies respected, tasks run in order

## Success Criteria

| Metric | Target |
|--------|--------|
| Task Completion Rate | 100% |
| Generated Code Runs | Yes |
| Tests Pass (if applicable) | Yes |
| PRD Updated | `passes: true` for all tasks |

## Technical Details

- **LLM Provider**: OpenAI GPT-4o (configurable to Claude)
- **Max Iterations**: 5 per scenario
- **Tools Available**: read_file, write_file, list_directory, run_command, git_status
- **Memory**: Enabled (stores context between iterations)
