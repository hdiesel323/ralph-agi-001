# Story 4.4: Tool Execution

Status: completed
Started: 2026-01-12
Completed: 2026-01-12

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

- [x] Task 1: Create ToolResult dataclass (AC: 2)
  - [x] `ToolResult` with success, content, error, duration
  - [x] `ToolError` with code, message, details
  - [x] JSON serialization for logging
  - [x] Helper methods (is_success, get_content)

- [x] Task 2: Implement ToolExecutor (AC: 1, 3, 4)
  - [x] `ToolExecutor` class managing execution
  - [x] `execute(name, args, timeout=None) -> ToolResult`
  - [x] `execute_batch(calls) -> List[ToolResult]`
  - [x] Server routing based on tool name
  - [x] Argument validation before execution

- [x] Task 3: Implement MCP tools/call (AC: 1, 2)
  - [x] Send `tools/call` request to server
  - [x] Parse tool response format
  - [x] Handle content types (text, image, etc.)
  - [x] Extract error details from response

- [x] Task 4: Implement error handling (AC: 3, 4)
  - [x] `ToolExecutionError` exception class
  - [x] Timeout detection and cancellation
  - [x] Categorize error types (ToolErrorCode enum)
  - [x] Graceful error recovery

- [x] Task 5: Implement logging (AC: 5)
  - [x] Log execution start/end with timing
  - [x] Redact sensitive arguments
  - [x] Configurable logging (log_calls flag)
  - [x] Metrics in result (duration_ms, timestamp)

- [x] Task 6: Write unit tests (AC: all)
  - [x] Test: Execute tool successfully
  - [x] Test: Handle tool errors
  - [x] Test: Timeout cancellation
  - [x] Test: Argument validation
  - [x] Test: Logging output
  - [x] Test: Batch execution

## Implementation Summary

**Delivered:**

- `ToolErrorCode` - Enum for error categories (6 types)
- `ToolError` - Structured error with code, message, details
- `ToolResult` - Complete execution result with metadata
- `ToolExecutionError` - Exception wrapping failed results
- `ToolExecutor` - High-level executor with validation, timeout, logging
- Batch execution with `execute_batch()`
- Sensitive argument redaction in logs
- Content type parsing (text, image, custom)

**Test Coverage:** 44 new tests (855 total passing)

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
result = await executor.execute("read_file", {"path": "/etc/hosts"})
if result.is_success():
    print(result.content)
else:
    print(f"Error: {result.error.message}")

# Execute with timeout
result = await executor.execute("long_operation", args, timeout=60)

# Batch execution (parallel)
results = await executor.execute_batch([
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
5. **Tool Not Found**: Tool doesn't exist
6. **Unknown Error**: Unexpected failures

### Logging Format

```
INFO TOOL_CALL tool=read_file args={'path': '/etc/hosts'}
INFO TOOL_SUCCESS tool=read_file duration=150ms content='...'
WARNING TOOL_FAILED tool=bad_tool duration=10ms error=[tool_not_found] Tool not found
```

### Design Decisions

- Validation before execution: Fail fast on bad args
- Structured results: Always return ToolResult, never throw
- Parallel batch: Execute independent calls concurrently
- Async-native: All execution methods are async
- Sensitive redaction: Passwords, keys, tokens auto-redacted from logs

### Dependencies

- **Story 4.1:** MCP CLI Integration (required)
- **Story 4.2:** Tool Discovery (required)
- **Story 4.3:** Schema Inspection (required)
- **Completes:** Epic 04 Sprint 5 scope
