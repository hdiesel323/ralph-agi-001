# Story 4.1: MCP CLI Integration

Status: completed
Started: 2026-01-11
Completed: 2026-01-12

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

- [x] Task 1: Create tools module structure (AC: 4)
  - [x] Create `ralph_agi/tools/` package
  - [x] Create `ralph_agi/tools/__init__.py`
  - [x] Create `ralph_agi/tools/mcp.py` for MCP client

- [x] Task 2: Implement JSON-RPC protocol (AC: 2)
  - [x] `MCPMessage` dataclass for requests/responses
  - [x] `MCPError` exception class with code/message
  - [x] Request ID generation and tracking
  - [x] Message serialization/deserialization

- [x] Task 3: Implement stdio transport (AC: 1, 3)
  - [x] `StdioTransport` class for subprocess communication
  - [x] Async message reading from stdout
  - [x] Message writing to stdin
  - [x] Process lifecycle management

- [x] Task 4: Implement MCPClient (AC: 1, 2, 3, 4)
  - [x] `MCPClient` class wrapping transport
  - [x] `connect()` method to start server
  - [x] `send_request()` with timeout handling
  - [x] `disconnect()` for cleanup
  - [x] Context manager support (`async with`)

- [x] Task 5: Write unit tests (AC: all)
  - [x] Create `tests/tools/test_mcp.py`
  - [x] Test: JSON-RPC message formatting
  - [x] Test: Request/response correlation
  - [x] Test: Timeout handling
  - [x] Test: Error parsing
  - [x] Test: Server lifecycle (mock subprocess)

## Implementation Summary

**Delivered:**
- `StdioTransport` - async subprocess management with stdin/stdout JSON-RPC
- `MCPClient` - full async MCP protocol client with handshake
- `SyncMCPClient` - synchronous wrapper using background event loop
- `MCPRequest`, `MCPResponse`, `MCPNotification` - message types
- `MCPError`, `MCPTimeoutError`, `MCPConnectionError` - error hierarchy
- `ServerInfo`, `ServerCapabilities` - server metadata parsing

**Test Coverage:** 41 tests passing (1 integration test skipped)

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
