# Epic 04: Dynamic Tool Integration

**PRD Reference:** FR-004
**Priority:** P0 (Critical)
**Roadmap:** Weeks 2-3 (Foundation)
**Status:** Draft

---

## Epic Overview

Implement the Tool Registry enabling dynamic tool discovery and execution using the MCP CLI pattern for 99% token reduction compared to static loading.

## Business Value

- Massively reduced token consumption (47K → 400 tokens)
- Extensible tool ecosystem without code changes
- Just-in-time context loading

## Technical Context

"Loading 6 MCP servers with 60 tools statically consumes approximately 47,000 tokens, while dynamic discovery reduces this to approximately 400 tokens." - PRD

Three-step pattern: Discover → Inspect → Execute

---

## Stories

### Story 4.1: MCP CLI Integration
**Priority:** P0 | **Points:** 3

**As a** developer
**I want** to call MCP CLI from Python
**So that** I can discover and use tools

**Acceptance Criteria:**
- [ ] Subprocess wrapper for `mcp-cli`
- [ ] Parse JSON output
- [ ] Handle errors and timeouts
- [ ] Configurable CLI path

---

### Story 4.2: Tool Discovery
**Priority:** P0 | **Points:** 3

**As a** developer
**I want** to list available tools dynamically
**So that** the agent knows what's possible

**Acceptance Criteria:**
- [ ] List all MCP servers
- [ ] List tools per server
- [ ] Cache tool list (configurable TTL)
- [ ] Refresh on demand

---

### Story 4.3: Schema Inspection
**Priority:** P0 | **Points:** 2

**As a** developer
**I want** to get tool schemas on demand
**So that** the LLM knows how to call tools

**Acceptance Criteria:**
- [ ] Fetch schema for specific tool
- [ ] Return parameter definitions
- [ ] Cache schemas (longer TTL)
- [ ] Clear error if tool not found

---

### Story 4.4: Tool Execution
**Priority:** P0 | **Points:** 3

**As a** developer
**I want** to execute tools with parameters
**So that** the agent can take actions

**Acceptance Criteria:**
- [ ] Execute tool with JSON arguments
- [ ] Return structured result
- [ ] Handle errors gracefully
- [ ] Timeout handling
- [ ] Log all tool calls

---

### Story 4.5: Core Tools (File System)
**Priority:** P0 | **Points:** 3

**As a** developer
**I want** file system operations
**So that** the agent can read/write code

**Acceptance Criteria:**
- [ ] Read file
- [ ] Write file
- [ ] Search files (glob)
- [ ] List directory
- [ ] Path validation (security)

---

### Story 4.6: Core Tools (Shell)
**Priority:** P0 | **Points:** 3

**As a** developer
**I want** shell command execution
**So that** the agent can run tests/builds

**Acceptance Criteria:**
- [ ] Execute bash command
- [ ] Capture stdout/stderr
- [ ] Timeout handling
- [ ] Working directory support
- [ ] Security restrictions

---

### Story 4.7: Core Tools (Git)
**Priority:** P0 | **Points:** 2

**As a** developer
**I want** git operations
**So that** the agent can commit changes

**Acceptance Criteria:**
- [ ] git status
- [ ] git add
- [ ] git commit
- [ ] git log
- [ ] git revert

---

## Dependencies

- Epic 01: Core Execution Loop (for integration)

## Definition of Done

- [ ] MCP CLI integration working
- [ ] Dynamic discovery operational
- [ ] All core tools functional
- [ ] 99% token reduction verified
- [ ] Security constraints enforced
