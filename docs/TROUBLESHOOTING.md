# Ralph AGI - Troubleshooting Guide

## WebSocket Disconnection Issues

### Symptoms
- Dashboard shows "Disconnected" status
- WebSocket constantly reconnecting and failing
- Backend crashes repeatedly

### Root Cause
Usually caused by **Python version mismatch**. The project requires Python 3.11+.

### Diagnosis
```bash
# Check Python version in your environment
python --version
# or
python3 --version

# Should be 3.11 or higher
```

### Fix
1. **Remove broken virtual environment**:
   ```bash
   cd ralph-agi-001
   rm -rf .venv venv
   poetry env remove --all  # if using Poetry
   ```

2. **Create fresh virtual environment with correct Python**:
   ```bash
   python3.12 -m venv venv
   # or
   python3.11 -m venv venv
   ```

3. **Install dependencies**:
   ```bash
   source venv/bin/activate
   pip install -e ".[api,dev]"
   ```

4. **Start backend**:
   ```bash
   uvicorn ralph_agi.api.app:create_app --factory --host 0.0.0.0 --port 8000
   ```

---

## Config Not Loading / Wrong LLM Provider

### Symptoms
- Tasks fail with "Anthropic API credit" errors despite configuring OpenAI
- Error: `type object 'RalphConfig' has no attribute 'load'`

### Root Cause
1. Config file not committed to git (worktrees don't inherit uncommitted changes)
2. Missing LLM section in config.yaml

### Fix
Ensure `config.yaml` has the LLM section and is committed:

```yaml
llm:
  builder_provider: "openai"  # or anthropic, openrouter
  builder_model: "gpt-4o-mini"
  critic_provider: "openai"
  critic_model: "gpt-4o"
  critic_enabled: true
  max_tokens: 4096
  max_tool_iterations: 10
```

Then commit:
```bash
git add config.yaml
git commit -m "Add LLM config"
git push
```

Clean old worktrees:
```bash
rm -rf ../ralph-worktrees/*
```

---

## Task Execution Fails Immediately

### Symptoms
- Tasks complete in < 1 second
- Status jumps to `failed`
- No output captured

### Diagnosis
Check the task's error field:
```bash
curl http://localhost:8000/api/tasks/TASK_ID | jq .error
```

### Common Errors

**"type object 'RalphConfig' has no attribute 'load'"**
- Fixed in commit f9bb080
- Pull latest code: `git pull origin main`

**"'str' object has no attribute 'sha'"**
- Fixed in commit 4387bac
- Pull latest code: `git pull origin main`

---

## Git Commit Tool Fails

### Symptoms
- Task generates code successfully
- Fails at commit step with: `'str' object has no attribute 'sha'`
- Uses all iterations retrying commit

### Fix
Pull latest code - this was fixed in commit 4387bac:
```bash
git pull origin main
```

---

## Environment Variables

### Required
```bash
# At least one of these depending on provider:
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...
```

### Loading
```bash
# From .env file
set -a && source .env && set +a

# Or export directly
export OPENAI_API_KEY=sk-...
```

---

## Port Conflicts

### Backend (8000)
```bash
# Find process
lsof -ti:8000

# Kill it
lsof -ti:8000 | xargs kill -9
```

### Frontend (3000/3001)
```bash
lsof -ti:3000 | xargs kill -9
lsof -ti:3001 | xargs kill -9
```

---

## System Requirements

- **Python**: 3.11+ (recommended: 3.12)
- **Node.js**: 18+
- **Package managers**: pip, pnpm
- **Git**: For worktree isolation
