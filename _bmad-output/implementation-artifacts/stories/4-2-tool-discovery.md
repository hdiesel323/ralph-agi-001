# Story 4.2: Tool Discovery

Status: not_started

## Story

As a **developer**,
I want **to list available tools dynamically**,
so that **the agent knows what tools are available without static loading**.

## Acceptance Criteria

1. **AC1:** List all configured MCP servers
   - Load server definitions from config
   - Return server metadata (name, command, status)
   - Support lazy enumeration (don't connect until needed)
   - Handle missing/invalid server configs

2. **AC2:** List tools per server
   - Call `tools/list` on connected server
   - Parse tool definitions with name/description/schema
   - Handle servers with no tools
   - Return unified ToolInfo objects

3. **AC3:** Cache tool list with configurable TTL
   - In-memory cache of discovered tools
   - Configurable cache TTL (default 5 minutes)
   - Cache invalidation on refresh
   - Per-server cache timestamps

4. **AC4:** Refresh on demand
   - `refresh_tools(server_name)` for single server
   - `refresh_all_tools()` for full refresh
   - Force refresh bypassing cache
   - Return delta of added/removed tools

## Tasks / Subtasks

- [ ] Task 1: Create ToolInfo dataclass (AC: 2)
  - [ ] `ToolInfo` with name, description, server, input_schema
  - [ ] `ServerInfo` with name, command, status, tools
  - [ ] JSON serialization support
  - [ ] Type hints throughout

- [ ] Task 2: Implement ToolRegistry (AC: 1, 2, 3, 4)
  - [ ] `ToolRegistry` class managing all servers
  - [ ] `list_servers() -> List[ServerInfo]`
  - [ ] `list_tools(server: str = None) -> List[ToolInfo]`
  - [ ] `get_tool(name: str) -> ToolInfo`
  - [ ] `refresh(server: str = None, force: bool = False)`

- [ ] Task 3: Implement caching layer (AC: 3)
  - [ ] `ToolCache` class with TTL support
  - [ ] `get(key) -> Optional[T]`
  - [ ] `set(key, value, ttl: int = None)`
  - [ ] `invalidate(key)` and `clear()`
  - [ ] Automatic TTL expiration

- [ ] Task 4: Integrate with MCPClient (AC: 1, 2)
  - [ ] `_discover_tools(server: str) -> List[ToolInfo]`
  - [ ] Parse `tools/list` response
  - [ ] Extract input schema from tool definitions
  - [ ] Handle discovery errors gracefully

- [ ] Task 5: Write unit tests (AC: all)
  - [ ] Test: List servers from config
  - [ ] Test: Discover tools from server
  - [ ] Test: Cache hit/miss behavior
  - [ ] Test: TTL expiration
  - [ ] Test: Refresh invalidates cache
  - [ ] Test: Handle server errors

## Dev Notes

### MCP tools/list Response

```json
{
  "tools": [
    {
      "name": "read_file",
      "description": "Read contents of a file",
      "inputSchema": {
        "type": "object",
        "properties": {
          "path": { "type": "string", "description": "File path to read" }
        },
        "required": ["path"]
      }
    }
  ]
}
```

### Token Reduction Strategy

Static loading: ~47,000 tokens (60 tools with full schemas)
Dynamic discovery: ~400 tokens (just tool names/descriptions)
On-demand schema: Load full schema only when needed

### ToolRegistry API

```python
registry = ToolRegistry(config)

# List available servers
servers = registry.list_servers()

# Discover all tools (cached)
tools = registry.list_tools()

# Filter by server
fs_tools = registry.list_tools(server="filesystem")

# Get specific tool
tool = registry.get_tool("read_file")

# Force refresh
registry.refresh(force=True)
```

### File Structure

```
ralph_agi/tools/
├── __init__.py
├── mcp.py          # Story 4.1 (MCP client)
├── registry.py     # NEW: Tool discovery
└── cache.py        # NEW: Caching layer
```

### Design Decisions

- Lazy loading: Don't connect servers until tools requested
- Unified interface: Same API regardless of server
- Cache by default: Reduce MCP round trips
- Server isolation: One server failure doesn't break others

### Dependencies

- **Story 4.1:** MCP CLI Integration (required)
- **Blocks:** Stories 4.3, 4.4 depend on this
