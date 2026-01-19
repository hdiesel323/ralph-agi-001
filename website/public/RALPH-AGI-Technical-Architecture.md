# RALPH-AGI Technical Architecture

**Version:** 1.0
**Date:** January 10, 2026
**Author:** RALPH-AGI Team

---

## 1. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RALPH-AGI SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         CONTROL PLANE                                   │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │ │
│  │  │   CLI/API    │  │    Config    │  │  Scheduler   │  │  Monitor   │ │ │
│  │  │  Interface   │  │   Manager    │  │   (Cron)     │  │ Dashboard  │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      ORCHESTRATION LAYER                                │ │
│  │                                                                          │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │ │
│  │  │                      RALPH LOOP ENGINE                            │  │ │
│  │  │                                                                    │  │ │
│  │  │   while (iteration < max && !complete):                           │  │ │
│  │  │     1. Initialize/Resume Session                                  │  │ │
│  │  │     2. Load Context (Memory + Progress + Git)                     │  │ │
│  │  │     3. Select Task (PRD: highest priority, no blockers)           │  │ │
│  │  │     4. Execute Task (LLM + Tools)                                 │  │ │
│  │  │     5. Verify (Cascade Evaluation)                                │  │ │
│  │  │     6. Update State (PRD + Progress + Git Commit)                 │  │ │
│  │  │     7. Check Completion (Promise Detection)                       │  │ │
│  │  │                                                                    │  │ │
│  │  └──────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                          │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐   │ │
│  │  │  Initializer   │  │    Coding      │  │    Specialized         │   │ │
│  │  │    Agent       │  │    Agent       │  │    Agents (Future)     │   │ │
│  │  │                │  │                │  │                        │   │ │
│  │  │  • Setup env   │  │  • Implement   │  │  • Testing Agent       │   │ │
│  │  │  • Create PRD  │  │  • Test        │  │  • QA Agent            │   │ │
│  │  │  • Init git    │  │  • Commit      │  │  • Research Agent      │   │ │
│  │  └────────────────┘  └────────────────┘  └────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│           ┌─────────────────────────┼─────────────────────────┐             │
│           ▼                         ▼                         ▼             │
│  ┌─────────────────┐  ┌─────────────────────────┐  ┌─────────────────────┐ │
│  │  TASK MANAGER   │  │     MEMORY SYSTEM       │  │   TOOL REGISTRY     │ │
│  │                 │  │                         │  │                     │ │
│  │  ┌───────────┐  │  │  ┌─────────────────┐   │  │  ┌───────────────┐  │ │
│  │  │ PRD.json  │  │  │  │  Short-term     │   │  │  │ MCP Servers   │  │ │
│  │  │           │  │  │  │  (progress.txt) │   │  │  │               │  │ │
│  │  │ • passes  │  │  │  └─────────────────┘   │  │  │ • filesystem  │  │ │
│  │  │ • steps   │  │  │  ┌─────────────────┐   │  │  │ • browser     │  │ │
│  │  │ • deps    │  │  │  │  Medium-term    │   │  │  │ • github      │  │ │
│  │  │ • priority│  │  │  │  (Git History)  │   │  │  │ • database    │  │ │
│  │  └───────────┘  │  │  └─────────────────┘   │  │  └───────────────┘  │ │
│  │                 │  │  ┌─────────────────┐   │  │  ┌───────────────┐  │ │
│  │  ┌───────────┐  │  │  │  Long-term      │   │  │  │ Dynamic       │  │ │
│  │  │ Dependency│  │  │  │  (Claude-Mem)   │   │  │  │ Discovery     │  │ │
│  │  │ Graph     │  │  │  │                 │   │  │  │               │  │ │
│  │  │           │  │  │  │ • SQLite        │   │  │  │ mcp-cli       │  │ │
│  │  │ • blocks  │  │  │  │ • Chroma Vector │   │  │  │ grep/search   │  │ │
│  │  │ • ready   │  │  │  │ • Lifecycle     │   │  │  │               │  │ │
│  │  └───────────┘  │  │  └─────────────────┘   │  │  └───────────────┘  │ │
│  └─────────────────┘  └─────────────────────────┘  └─────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        EXECUTION LAYER                                  │ │
│  │                                                                          │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │ │
│  │  │                       LLM ENSEMBLE                                │  │ │
│  │  │                                                                    │  │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │  │ │
│  │  │  │  Opus 4.5    │  │  Sonnet 4    │  │  Haiku 4             │   │  │ │
│  │  │  │  (30%)       │  │  (50%)       │  │  (20%)               │   │  │ │
│  │  │  │              │  │              │  │                      │   │  │ │
│  │  │  │  Complex     │  │  Routine     │  │  Simple              │   │  │ │
│  │  │  │  Reasoning   │  │  Tasks       │  │  Queries             │   │  │ │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────────┘   │  │ │
│  │  └──────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                          │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │ │
│  │  │   Browser    │  │    File      │  │    Shell     │  │    Git    │  │ │
│  │  │  Automation  │  │   System     │  │  Execution   │  │    Ops    │  │ │
│  │  │ (Playwright) │  │ (R/W/Search) │  │   (Bash)     │  │           │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      EVALUATION PIPELINE                                │ │
│  │                                                                          │ │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────┐ │ │
│  │  │ Stage 1 │───▶│ Stage 2 │───▶│ Stage 3 │───▶│ Stage 4 │───▶│Final │ │ │
│  │  │         │    │         │    │         │    │         │    │      │ │ │
│  │  │ Syntax  │    │  Unit   │    │ Integ   │    │  E2E    │    │ LLM  │ │ │
│  │  │ Types   │    │  Tests  │    │ Tests   │    │ Visual  │    │Judge │ │ │
│  │  │         │    │         │    │         │    │         │    │      │ │ │
│  │  │  ~1s    │    │  ~10s   │    │  ~30s   │    │  ~60s   │    │ ~30s │ │ │
│  │  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └──────┘ │ │
│  │                                                                          │ │
│  │  Cascade Logic: Fail fast - only proceed if previous stage passes       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                       PERSISTENCE LAYER                                 │ │
│  │                                                                          │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │ │
│  │  │  Git Repository  │  │ SQLite Database  │  │   Vector Store     │   │ │
│  │  │                  │  │                  │  │   (Chroma)         │   │ │
│  │  │  • Source code   │  │  • Sessions      │  │                    │   │ │
│  │  │  • PRD.json      │  │  • Observations  │  │  • Embeddings      │   │ │
│  │  │  • progress.txt  │  │  • Summaries     │  │  • Semantic search │   │ │
│  │  │  • Commit history│  │  • Checkpoints   │  │  • Hybrid retrieval│   │ │
│  │  └──────────────────┘  └──────────────────┘  └────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Specifications

### 2.1 Ralph Loop Engine

The Ralph Loop Engine is the central orchestrator of the system. It implements a simple but powerful iterative pattern that processes one task at a time until all tasks are complete or the maximum iteration count is reached.

| Property                    | Specification                                  |
| --------------------------- | ---------------------------------------------- |
| **Implementation Language** | TypeScript/Node.js or Python                   |
| **Loop Type**               | Synchronous, single-threaded                   |
| **Max Iterations**          | Configurable (default: 100)                    |
| **Completion Signal**       | `<promise>COMPLETE</promise>` in LLM output    |
| **Checkpoint Frequency**    | Every iteration (configurable)                 |
| **Error Handling**          | Retry with exponential backoff, max 3 attempts |

### 2.2 Memory System

The three-tier memory system provides context persistence across sessions.

| Tier            | Storage         | Retention  | Access Pattern    |
| --------------- | --------------- | ---------- | ----------------- |
| **Short-term**  | progress.txt    | Per-sprint | Sequential append |
| **Medium-term** | Git history     | Permanent  | Log traversal     |
| **Long-term**   | SQLite + Chroma | Permanent  | Semantic search   |

**Long-term Memory Schema (SQLite):**

```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    project TEXT,
    summary TEXT
);

CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id),
    timestamp TIMESTAMP,
    type TEXT,  -- 'tool_use', 'decision', 'learning', 'error'
    content TEXT,
    embedding_id TEXT  -- Reference to Chroma
);

CREATE TABLE summaries (
    id INTEGER PRIMARY KEY,
    created_at TIMESTAMP,
    observation_ids TEXT,  -- JSON array of observation IDs
    summary TEXT
);
```

### 2.3 Tool Registry

The Tool Registry implements dynamic discovery using the MCP CLI pattern.

| Operation    | Command                            | Token Cost  |
| ------------ | ---------------------------------- | ----------- |
| List servers | `mcp-cli`                          | ~50 tokens  |
| List tools   | `mcp-cli <server>`                 | ~100 tokens |
| Get schema   | `mcp-cli <server>/<tool>`          | ~200 tokens |
| Execute      | `mcp-cli <server>/<tool> '<json>'` | Variable    |

**Comparison with Static Loading:**

| Approach | Tokens (6 servers, 60 tools) | Reduction |
| -------- | ---------------------------- | --------- |
| Static   | ~47,000                      | Baseline  |
| Dynamic  | ~400                         | **99%**   |

### 2.4 Evaluation Pipeline

The cascaded evaluation pipeline ensures quality through progressive verification.

| Stage             | Command                        | Timeout | Cost  | Blocking |
| ----------------- | ------------------------------ | ------- | ----- | -------- |
| Static Analysis   | `pnpm type-check && pnpm lint` | 60s     | $0.00 | Yes      |
| Unit Tests        | `pnpm test`                    | 300s    | $0.00 | Yes      |
| Integration Tests | `pnpm test:integration`        | 600s    | $0.01 | Optional |
| E2E Tests         | `pnpm test:e2e`                | 900s    | $0.05 | Optional |
| LLM Judge         | API call                       | 60s     | $0.10 | Optional |

---

## 3. Data Flow Diagrams

### 3.1 First Run (Initialization)

```
User Request
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    INITIALIZER AGENT                         │
│                                                              │
│  1. Parse user request                                       │
│  2. Generate comprehensive feature list                      │
│  3. Create PRD.json with all features (passes: false)        │
│  4. Create progress.txt (empty)                              │
│  5. Create init.sh script                                    │
│  6. Initialize git repository                                │
│  7. Create initial commit                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    PROJECT SCAFFOLD                          │
│                                                              │
│  project/                                                    │
│  ├── prd.json           # Feature requirements               │
│  ├── progress.txt       # Session notes (empty)              │
│  ├── init.sh            # Environment setup script           │
│  ├── src/               # Source code directory              │
│  └── .git/              # Git repository                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
  Enter Ralph Loop
```

### 3.2 Subsequent Runs (Coding Agent)

```
┌─────────────────────────────────────────────────────────────┐
│                      RALPH LOOP                              │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 1. LOAD CONTEXT                                        │  │
│  │    • Read progress.txt                                 │  │
│  │    • Query long-term memory (relevant observations)    │  │
│  │    • Check git log (last 20 commits)                   │  │
│  │    • Run init.sh (start dev server)                    │  │
│  │    • Verify basic functionality                        │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 2. SELECT TASK                                         │  │
│  │    • Parse PRD.json                                    │  │
│  │    • Filter: passes == false                           │  │
│  │    • Filter: no blocking dependencies                  │  │
│  │    • Sort by priority                                  │  │
│  │    • Select highest priority task                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 3. EXECUTE TASK                                        │  │
│  │    • LLM reasoning about implementation                │  │
│  │    • Tool invocation (file, shell, browser)            │  │
│  │    • Code generation and modification                  │  │
│  │    • Iterative refinement within task                  │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 4. VERIFY                                              │  │
│  │    • Stage 1: Static analysis ──┐                      │  │
│  │    • Stage 2: Unit tests ───────┤ Cascade              │  │
│  │    • Stage 3: Integration tests ┤ (fail fast)          │  │
│  │    • Stage 4: E2E tests ────────┤                      │  │
│  │    • Stage 5: LLM Judge ────────┘                      │  │
│  │                                                        │  │
│  │    If FAIL: Debug sub-loop (max 3 attempts)            │  │
│  │    If PASS: Continue                                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 5. UPDATE STATE                                        │  │
│  │    • Mark PRD feature: passes = true                   │  │
│  │    • Append to progress.txt                            │  │
│  │    • Store observations in long-term memory            │  │
│  │    • Git commit with descriptive message               │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 6. CHECK COMPLETION                                    │  │
│  │    • All PRD features passes == true?                  │  │
│  │    • LLM output contains <promise>COMPLETE</promise>?  │  │
│  │    • Max iterations reached?                           │  │
│  │                                                        │  │
│  │    If COMPLETE: Exit loop, notify user                 │  │
│  │    If NOT: Continue to next iteration                  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. API Specifications

### 4.1 CLI Interface

```bash
# Start a new project
ralph-agi init --name "my-project" --prompt "Build a todo app with React"

# Run in AFK mode
ralph-agi run --max-iterations 100 --notify slack

# Run in interactive mode
ralph-agi run --interactive --approve-commits

# Check status
ralph-agi status

# View progress
ralph-agi logs --tail 50

# Resume from checkpoint
ralph-agi resume --checkpoint latest
```

### 4.2 Configuration API

```typescript
interface RalphConfig {
  system: {
    name: string;
    version: string;
  };
  orchestration: {
    loopType: "ralph";
    maxIterations: number;
    completionPromise: string;
    humanInLoop: boolean;
    checkpointInterval: number;
  };
  taskManagement: {
    prdPath: string;
    prdFormat: "json";
    gitBacked: boolean;
    autoCommit: boolean;
  };
  memory: {
    shortTerm: {
      type: "progress_file";
      path: string;
      mode: "append";
    };
    longTerm: {
      enabled: boolean;
      sqlitePath: string;
      vectorDb: "chroma";
    };
  };
  tools: {
    discovery: "mcp_cli";
    configPath: string;
  };
  evaluation: {
    cascade: boolean;
    stages: EvaluationStage[];
  };
  llm: {
    defaultModel: string;
    ensemble: LLMConfig[];
  };
}
```

### 4.3 Memory Query API

```typescript
interface MemoryQuery {
  query: string;
  type?: "bugfix" | "feature" | "decision" | "learning";
  dateRange?: { start: Date; end: Date };
  project?: string;
  limit?: number;
}

interface MemoryResult {
  id: number;
  summary: string;
  type: string;
  timestamp: Date;
  relevanceScore: number;
  fullContent?: string;
}

// Usage
const results = await memory.search({
  query: "authentication implementation",
  type: "feature",
  limit: 5,
});
```

---

## 5. Deployment Architecture

### 5.1 Single-Node Deployment

```
┌─────────────────────────────────────────────────────────────┐
│                      HOST MACHINE                            │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                   DOCKER CONTAINER                     │  │
│  │                                                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │  │
│  │  │ RALPH-AGI   │  │   SQLite    │  │    Chroma    │  │  │
│  │  │   Process   │  │   Database  │  │  Vector DB   │  │  │
│  │  └─────────────┘  └─────────────┘  └──────────────┘  │  │
│  │                                                        │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │              SANDBOXED WORKSPACE                 │  │  │
│  │  │                                                  │  │  │
│  │  │  • Project files                                 │  │  │
│  │  │  • Git repository                                │  │  │
│  │  │  • Node.js / Python runtime                      │  │  │
│  │  │  • Browser (Chromium)                            │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    VOLUMES                             │  │
│  │  • /data/projects     (project files)                 │  │
│  │  • /data/memory       (SQLite + Chroma)               │  │
│  │  • /data/config       (configuration)                 │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Resource Requirements

| Component           | CPU         | Memory      | Storage   |
| ------------------- | ----------- | ----------- | --------- |
| RALPH-AGI Process   | 2 cores     | 4 GB        | -         |
| SQLite Database     | -           | 512 MB      | 1 GB      |
| Chroma Vector DB    | 1 core      | 2 GB        | 10 GB     |
| Sandboxed Workspace | 2 cores     | 4 GB        | 50 GB     |
| Browser (Chromium)  | 1 core      | 2 GB        | -         |
| **Total**           | **6 cores** | **12.5 GB** | **61 GB** |

---

## 6. Security Considerations

### 6.1 Sandboxing

All code execution occurs within an isolated container with limited capabilities. The sandbox has no access to the host filesystem outside of designated volumes, no network access except to whitelisted endpoints (LLM APIs, configured MCP servers), and no ability to escalate privileges.

### 6.2 Secret Management

Secrets are managed through environment variables, never stored in code or logs. The system supports integration with secret management services (AWS Secrets Manager, HashiCorp Vault) for production deployments.

### 6.3 Rate Limiting

The system implements rate limiting at multiple levels to prevent runaway resource consumption. API calls to LLM providers are rate-limited according to provider quotas. Tool executions are limited to prevent infinite loops. Git commits are limited to prevent repository bloat.

---

## 7. Monitoring and Observability

### 7.1 Metrics

| Metric                       | Description                  | Alert Threshold |
| ---------------------------- | ---------------------------- | --------------- |
| `ralph_iterations_total`     | Total loop iterations        | -               |
| `ralph_tasks_completed`      | Tasks marked as passes: true | -               |
| `ralph_errors_total`         | Total errors encountered     | > 5/hour        |
| `ralph_stuck_duration`       | Time without progress        | > 30 minutes    |
| `ralph_tokens_used`          | Total tokens consumed        | > 1M/day        |
| `ralph_evaluation_pass_rate` | % of evaluations passing     | < 80%           |

### 7.2 Logging

All agent actions are logged with structured JSON format, including timestamp, iteration number, action type, tool used, result, and token count. Logs are rotated daily and retained for 30 days by default.

### 7.3 Alerting

Configurable alerts can be sent via webhook (Slack, Discord), email, or PagerDuty for critical events such as task completion, errors, stuck states, and resource exhaustion.
