# Story 4.1: MCP CLI Integration

Status: in_progress
Started: 2026-01-11

## Story

As a **developer**,
I want **to call MCP servers from Python**,
so that **I can discover and use tools programmatically**.

## Acceptance Criteria

1. **AC1:** Connect to stdio-based MCP servers
   - Launch MCP server subprocess with proper arguments
   - Communicate via stdin/stdout JSON-RPC
   - Handle server startup and initialization
   - Graceful shutdown with resource cleanup

2. **AC2:** Parse JSON-RPC messages
   - Implement MCP protocol message format
   - Parse responses with proper typing
   - Handle notifications and errors
   - Support request/response correlation via IDs

3. **AC3:** Handle errors and timeouts
   - Configurable operation timeout (default 30s)
   - Server crash detection and recovery
   - Invalid response handling
   - Clear error messages with context

4. **AC4:** Configurable server management
   - Load server configs from config.yaml
   - Support environment variable expansion
   - Track server state (connected/disconnected)
   - Lazy connection (connect on first use)

## Tasks / Subtasks

- [ ] Task 1: Create tools module structure (AC: 4)
  - [ ] Create `ralph_agi/tools/` package
  - [ ] Create `ralph_agi/tools/__init__.py`
  - [ ] Create `ralph_agi/tools/mcp.py` for MCP client

- [ ] Task 2: Implement JSON-RPC protocol (AC: 2)
  - [ ] `MCPMessage` dataclass for requests/responses
  - [ ] `MCPError` exception class with code/message
  - [ ] Request ID generation and tracking
  - [ ] Message serialization/deserialization

- [ ] Task 3: Implement stdio transport (AC: 1, 3)
  - [ ] `StdioTransport` class for subprocess communication
  - [ ] Async message reading from stdout
  - [ ] Message writing to stdin
  - [ ] Process lifecycle management

- [ ] Task 4: Implement MCPClient (AC: 1, 2, 3, 4)
  - [ ] `MCPClient` class wrapping transport
  - [ ] `connect()` method to start server
  - [ ] `send_request()` with timeout handling
  - [ ] `disconnect()` for cleanup
  - [ ] Context manager support (`async with`)

- [ ] Task 5: Write unit tests (AC: all)
  - [ ] Create `tests/tools/test_mcp.py`
  - [ ] Test: JSON-RPC message formatting
  - [ ] Test: Request/response correlation
  - [ ] Test: Timeout handling
  - [ ] Test: Error parsing
  - [ ] Test: Server lifecycle (mock subprocess)

## Dev Notes

### MCP Protocol Overview

MCP (Model Context Protocol) uses JSON-RPC 2.0 over various transports:
- **stdio**: Local processes via stdin/stdout (primary for RALPH-AGI)
- **HTTP**: Remote servers (future consideration)
- **SSE**: Deprecated, not implementing

### JSON-RPC Message Format

```json
// Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}

// Response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { "tools": [...] }
}

// Error
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": { "code": -32600, "message": "Invalid Request" }
}
```

### MCP Initialization Sequence

1. Client sends `initialize` with capabilities
2. Server responds with its capabilities
3. Client sends `initialized` notification
4. Ready for tool operations

### Config Example

```yaml
tools:
  mcp_servers:
    filesystem:
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed"]
      env:
        NODE_ENV: "production"

    github:
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-github"]
      env:
        GITHUB_TOKEN: "${GITHUB_TOKEN}"
```

### File Structure

```
ralph_agi/
├── tools/           # NEW: Create this package
│   ├── __init__.py
│   └── mcp.py       # MCP client implementation
tests/
├── tools/
│   ├── __init__.py
│   └── test_mcp.py
```

### Design Decisions

- Use asyncio for non-blocking I/O with subprocess
- Sync wrapper for compatibility with existing sync code
- Lazy connection - only start server when needed
- Environment variable expansion for secrets
- Request timeout with configurable default

### Dependencies

- **Epic 01:** Core Execution Loop (COMPLETE)
- **Epic 03:** Memory System (COMPLETE)
- **Blocks:** Stories 4.2, 4.3, 4.4 depend on this
