# Story 4.6: Shell Tools

**Epic:** 04 - Tool Integration
**Sprint:** 6
**Points:** 3
**Priority:** P0
**Status:** In Progress

## User Story

**As a** RALPH agent
**I want** shell command execution
**So that** I can run tests, builds, and other development commands

## Acceptance Criteria

- [ ] `execute(command)` - Execute bash command and return output
- [ ] Capture stdout and stderr separately
- [ ] Timeout handling with configurable defaults
- [ ] Working directory support
- [ ] Environment variable injection
- [ ] Exit code capture and error handling
- [ ] Command sanitization for security
- [ ] Configurable allowed/blocked commands (optional)
- [ ] 90%+ test coverage

## Technical Design

### Module Structure

```
ralph_agi/tools/
├── __init__.py          # Updated exports
├── shell.py             # NEW - Shell execution tools
└── ...
```

### Core Classes

```python
@dataclass
class CommandResult:
    """Result of shell command execution.

    Attributes:
        command: The executed command
        exit_code: Process exit code (0 = success)
        stdout: Standard output
        stderr: Standard error
        duration_ms: Execution time in milliseconds
        timed_out: Whether command timed out
    """
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False

class ShellTools:
    """Shell command execution with safety constraints.

    Usage:
        shell = ShellTools()

        # Simple command
        result = shell.execute("ls -la")
        print(result.stdout)

        # With working directory
        result = shell.execute("npm test", cwd="/path/to/project")

        # With timeout
        result = shell.execute("long_running_command", timeout=300)

        # Check success
        if result.exit_code == 0:
            print("Success!")
    """
```

### Security Considerations

1. **No shell injection**: Commands run through subprocess, not shell=True with user input
2. **Timeout protection**: Default 60s timeout prevents hangs
3. **Resource limits**: Optional memory/CPU limits
4. **Working directory validation**: Must be within allowed paths
5. **Blocked commands**: Optional blocklist for dangerous commands

### API Reference

```python
def execute(
    self,
    command: str,
    cwd: str | Path | None = None,
    timeout: float = 60.0,
    env: dict[str, str] | None = None,
    capture_output: bool = True,
) -> CommandResult:
    """Execute a shell command.

    Args:
        command: Shell command to execute
        cwd: Working directory (default: current)
        timeout: Max execution time in seconds
        env: Additional environment variables
        capture_output: Whether to capture stdout/stderr

    Returns:
        CommandResult with exit code and output
    """
```

## Test Plan

1. **Basic execution**: Simple commands, output capture
2. **Exit codes**: Success (0), failure (non-zero)
3. **Timeout**: Commands that exceed timeout
4. **Working directory**: Execute in specific directory
5. **Environment**: Custom environment variables
6. **Error handling**: Invalid commands, permission errors

## Dependencies

- Story 4.4: Tool Execution (COMPLETE)
- Story 4.5: File System Tools (COMPLETE - for cwd validation)
- Python subprocess (stdlib)

## Notes

Critical for Meta-Ralph to run tests (`pytest`), build tools (`npm`, `pip`), and verify changes work.
