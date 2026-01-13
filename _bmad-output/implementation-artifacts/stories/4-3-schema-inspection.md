# Story 4.3: Schema Inspection

Status: not_started

## Story

As a **developer**,
I want **to get tool schemas on demand**,
so that **the LLM knows how to call tools correctly**.

## Acceptance Criteria

1. **AC1:** Fetch schema for specific tool
   - `get_schema(tool_name)` returns full input schema
   - Load from cache if available
   - Fetch from server if not cached
   - Handle tool not found gracefully

2. **AC2:** Return parameter definitions
   - Parse JSON Schema format
   - Include type, description, required fields
   - Support nested object schemas
   - Handle enum and array types

3. **AC3:** Cache schemas with longer TTL
   - Separate cache from tool list
   - Default TTL: 1 hour (schemas change rarely)
   - Configurable per-schema TTL
   - Schema versioning support (future)

4. **AC4:** Clear error if tool not found
   - `ToolNotFoundError` with helpful message
   - Suggest similar tool names
   - Include server name in error
   - List available tools on error

## Tasks / Subtasks

- [ ] Task 1: Extend ToolInfo with schema (AC: 1, 2)
  - [ ] Add `input_schema: Optional[dict]` field
  - [ ] `ToolSchema` dataclass for parsed schema
  - [ ] `Parameter` dataclass with type/desc/required
  - [ ] Schema validation helpers

- [ ] Task 2: Implement schema fetching (AC: 1, 3)
  - [ ] `get_schema(tool_name: str) -> ToolSchema`
  - [ ] Lazy schema loading (not with tools/list)
  - [ ] Cache schema after first fetch
  - [ ] `prefetch_schemas(tool_names: List[str])`

- [ ] Task 3: Implement schema parser (AC: 2)
  - [ ] Parse JSON Schema to ToolSchema
  - [ ] Handle `properties` object
  - [ ] Handle `required` array
  - [ ] Support `$ref` (basic)
  - [ ] Handle `oneOf`, `anyOf`, `allOf`

- [ ] Task 4: Implement error handling (AC: 4)
  - [ ] `ToolNotFoundError(name, server, suggestions)`
  - [ ] Fuzzy matching for suggestions
  - [ ] Available tools in error context
  - [ ] Schema validation errors

- [ ] Task 5: Write unit tests (AC: all)
  - [ ] Test: Get schema for valid tool
  - [ ] Test: Schema cache behavior
  - [ ] Test: Parameter parsing
  - [ ] Test: Nested schema handling
  - [ ] Test: Tool not found error
  - [ ] Test: Similar tool suggestions

## Dev Notes

### ToolSchema Structure

```python
@dataclass
class Parameter:
    name: str
    type: str  # "string", "number", "boolean", "object", "array"
    description: str
    required: bool
    default: Any = None
    enum: List[str] = None  # For constrained values

@dataclass
class ToolSchema:
    tool_name: str
    description: str
    parameters: List[Parameter]
    required_params: List[str]
    raw_schema: dict  # Original JSON Schema
```

### JSON Schema Example

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "File path to read"
    },
    "encoding": {
      "type": "string",
      "description": "File encoding",
      "default": "utf-8",
      "enum": ["utf-8", "ascii", "latin-1"]
    }
  },
  "required": ["path"]
}
```

### LLM Context Format

When providing schema to LLM, format as:
```
Tool: read_file
Description: Read contents of a file

Parameters:
- path (string, required): File path to read
- encoding (string, optional): File encoding. Default: utf-8. Values: utf-8, ascii, latin-1
```

### File Structure

```
ralph_agi/tools/
├── __init__.py
├── mcp.py          # Story 4.1
├── registry.py     # Story 4.2
├── cache.py        # Story 4.2
└── schema.py       # NEW: Schema parsing
```

### Design Decisions

- Lazy schema loading: Only fetch when needed (99% token savings)
- Longer cache TTL: Schemas rarely change
- Fuzzy suggestions: Help users find correct tool names
- Raw schema preserved: For direct JSON Schema validation

### Dependencies

- **Story 4.1:** MCP CLI Integration (required)
- **Story 4.2:** Tool Discovery (required)
- **Blocks:** Story 4.4 depends on this
