# Story 4.4: Tool Execution

Status: not_started

## Story

As a **developer**,
I want **to execute tools with parameters**,
so that **the agent can take actions in the environment**.

## Acceptance Criteria

1. **AC1:** Execute tool with JSON arguments
   - `execute(tool_name, arguments)` main API
   - Validate arguments against schema
   - Route to correct MCP server
   - Return structured ToolResult

2. **AC2:** Return structured result
   - `ToolResult` dataclass with success/error
   - Include raw output and parsed content
   - Capture execution duration
   - Include tool metadata (name, server, args)

3. **AC3:** Handle errors gracefully
   - Distinguish tool errors from transport errors
   - Parse MCP error responses
   - Include stack trace when available
   - Retry logic for transient failures

4. **AC4:** Timeout handling
   - Per-tool timeout configuration
   - Default timeout from config (30s)
   - Cancel long-running operations
   - Partial result recovery (if possible)

5. **AC5:** Log all tool calls
   - Log tool name, arguments, result
   - Integration with memory system
   - Execution timing metrics
   - Configurable log level

## Tasks / Subtasks

- [ ] Task 1: Create ToolResult dataclass (AC: 2)
  - [ ] `ToolResult` with success, content, error, duration
  - [ ] `ToolError` with code, message, details
  - [ ] JSON serialization for logging
  - [ ] Helper methods (is_success, get_content)

- [ ] Task 2: Implement ToolExecutor (AC: 1, 3, 4)
  - [ ] `ToolExecutor` class managing execution
  - [ ] `execute(name, args, timeout=None) -> ToolResult`
  - [ ] `execute_batch(calls) -> List[ToolResult]`
  - [ ] Server routing based on tool name
  - [ ] Argument validation before execution

- [ ] Task 3: Implement MCP tools/call (AC: 1, 2)
  - [ ] Send `tools/call` request to server
  - [ ] Parse tool response format
  - [ ] Handle content types (text, image, etc.)
  - [ ] Extract error details from response

- [ ] Task 4: Implement error handling (AC: 3, 4)
  - [ ] `ToolExecutionError` exception class
  - [ ] Timeout detection and cancellation
  - [ ] Retry logic with exponential backoff
  - [ ] Categorize error types

- [ ] Task 5: Implement logging (AC: 5)
  - [ ] Log execution start/end with timing
  - [ ] Redact sensitive arguments
  - [ ] Memory integration for tool history
  - [ ] Metrics collection

- [ ] Task 6: Write unit tests (AC: all)
  - [ ] Test: Execute tool successfully
  - [ ] Test: Handle tool errors
  - [ ] Test: Timeout cancellation
  - [ ] Test: Argument validation
  - [ ] Test: Logging output
  - [ ] Test: Retry on transient failure

## Dev Notes

### MCP tools/call Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "read_file",
    "arguments": {
      "path": "/path/to/file.txt"
    }
  }
}
```

### MCP tools/call Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "File contents here..."
      }
    ]
  }
}
```

### ToolResult Structure

```python
@dataclass
class ToolResult:
    tool_name: str
    server: str
    arguments: dict
    success: bool
    content: Optional[str] = None
    content_type: str = "text"
    error: Optional[ToolError] = None
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def is_success(self) -> bool:
        return self.success and self.error is None

    def get_text(self) -> str:
        """Get content as text, handle different types."""
        if self.content_type == "text":
            return self.content
        return str(self.content)
```

### ToolExecutor API

```python
executor = ToolExecutor(registry)

# Execute single tool
result = executor.execute("read_file", {"path": "/etc/hosts"})
if result.is_success():
    print(result.content)
else:
    print(f"Error: {result.error.message}")

# Execute with timeout
result = executor.execute("long_operation", args, timeout=60)

# Batch execution (parallel where possible)
results = executor.execute_batch([
    ("read_file", {"path": "a.txt"}),
    ("read_file", {"path": "b.txt"}),
])
```

### File Structure

```
ralph_agi/tools/
├── __init__.py
├── mcp.py          # Story 4.1
├── registry.py     # Story 4.2
├── cache.py        # Story 4.2
├── schema.py       # Story 4.3
└── executor.py     # NEW: Tool execution
```

### Error Categories

1. **Validation Error**: Invalid arguments before execution
2. **Transport Error**: Network/subprocess failures
3. **Tool Error**: Tool returned error response
4. **Timeout Error**: Operation exceeded time limit
5. **Unknown Error**: Unexpected failures

### Logging Format

```
[2026-01-11 12:00:00] TOOL_CALL tool=read_file server=filesystem
[2026-01-11 12:00:00] TOOL_ARGS {"path": "/etc/hosts"}
[2026-01-11 12:00:01] TOOL_SUCCESS duration=150ms bytes=1234
```

### Design Decisions

- Validation before execution: Fail fast on bad args
- Structured results: Always return ToolResult, never throw
- Parallel batch: Execute independent calls concurrently
- Memory integration: Log all calls for learning

### Dependencies

- **Story 4.1:** MCP CLI Integration (required)
- **Story 4.2:** Tool Discovery (required)
- **Story 4.3:** Schema Inspection (required)
- **Completes:** Epic 04 Sprint 5 scope
