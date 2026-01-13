# Story 4.5: File System Tools

**Epic:** 04 - Tool Integration
**Sprint:** 6
**Points:** 3
**Priority:** P0
**Status:** In Progress

## User Story

**As a** RALPH agent
**I want** file system operations
**So that** I can read, write, and navigate code files to work on my own codebase

## Acceptance Criteria

- [ ] `read_file(path)` - Read file contents with encoding detection
- [ ] `write_file(path, content)` - Write/overwrite file with atomic writes
- [ ] `glob_files(pattern, root)` - Find files matching glob pattern
- [ ] `list_directory(path)` - List directory contents with metadata
- [ ] `file_exists(path)` - Check if file/directory exists
- [ ] `get_file_info(path)` - Get file metadata (size, modified, type)
- [ ] Path validation - Prevent path traversal attacks
- [ ] Configurable allowed paths (sandboxing)
- [ ] Comprehensive error handling with typed errors
- [ ] 90%+ test coverage

## Technical Design

### Module Structure

```
ralph_agi/tools/
├── __init__.py          # Updated exports
├── filesystem.py        # NEW - File system tools
└── ...
```

### Core Classes

```python
@dataclass
class FileInfo:
    """File metadata."""
    path: Path
    name: str
    is_file: bool
    is_directory: bool
    size: int  # bytes
    modified: datetime
    extension: str | None

class PathSecurityError(Exception):
    """Raised when path validation fails."""
    pass

class FileSystemTools:
    """File system operations with security constraints.

    Usage:
        fs = FileSystemTools(allowed_roots=[Path.cwd()])

        # Read file
        content = fs.read_file("src/main.py")

        # Write file
        fs.write_file("output.txt", "Hello world")

        # Find files
        files = fs.glob_files("**/*.py")

        # List directory
        entries = fs.list_directory("src/")
    """

    def __init__(
        self,
        allowed_roots: list[Path] | None = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
    ):
        """Initialize with security constraints.

        Args:
            allowed_roots: Directories that can be accessed.
                          If None, defaults to current working directory.
            max_file_size: Maximum file size to read (bytes)
        """
```

### Security Model

1. **Path Validation**: All paths resolved to absolute, checked against allowed_roots
2. **No Traversal**: `..` segments validated after resolution
3. **Size Limits**: Large files rejected (configurable max)
4. **Atomic Writes**: Write to temp file, then rename (prevents corruption)
5. **Encoding**: Auto-detect UTF-8/UTF-16/ASCII, fallback to binary

### API Reference

```python
def read_file(self, path: str | Path) -> str:
    """Read text file contents.

    Args:
        path: File path (relative or absolute)

    Returns:
        File contents as string

    Raises:
        PathSecurityError: Path outside allowed roots
        FileNotFoundError: File doesn't exist
        ValueError: File too large or binary
    """

def write_file(
    self,
    path: str | Path,
    content: str,
    create_dirs: bool = True,
) -> Path:
    """Write content to file atomically.

    Args:
        path: Target file path
        content: Content to write
        create_dirs: Create parent directories if needed

    Returns:
        Absolute path to written file

    Raises:
        PathSecurityError: Path outside allowed roots
    """

def glob_files(
    self,
    pattern: str,
    root: str | Path | None = None,
) -> list[Path]:
    """Find files matching glob pattern.

    Args:
        pattern: Glob pattern (e.g., "**/*.py")
        root: Root directory (default: first allowed root)

    Returns:
        List of matching file paths
    """

def list_directory(self, path: str | Path) -> list[FileInfo]:
    """List directory contents.

    Args:
        path: Directory path

    Returns:
        List of FileInfo for each entry
    """
```

## Test Plan

1. **Read operations**: Various encodings, large files, missing files
2. **Write operations**: New files, overwrite, atomic behavior
3. **Glob patterns**: Recursive, specific extensions, edge cases
4. **Security**: Path traversal attempts, root escaping, symlinks
5. **Edge cases**: Empty files, binary detection, permissions

## Dependencies

- Story 4.4: Tool Execution (COMPLETE)
- Python pathlib, tempfile (stdlib)

## Notes

This is the most critical tool for Meta-Ralph - enables reading and modifying its own source code.
