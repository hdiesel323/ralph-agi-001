# Sprint 3: CLI & Output Formatting - LLM-Executable Plan

**Stories:** 1.5 (CLI Entry Point) + 1.7 (Loop Output Formatting) = 4 points
**Status:** COMPLETED
**Created:** 2026-01-11
**Execution Time:** ~30 minutes

---

## Phase 0: Documentation Discovery (COMPLETED)

### Allowed APIs (Verified from Source Code)

#### CLI Module (`ralph_agi/cli.py` - 223 lines)

| API                                                                   | Source | Usage               |
| --------------------------------------------------------------------- | ------ | ------------------- |
| `argparse.ArgumentParser(prog, description, formatter_class, epilog)` | stdlib | Parser creation     |
| `parser.add_argument(--flag, type, default, help)`                    | stdlib | Flag definition     |
| `parser.add_subparsers(dest, help)`                                   | stdlib | Subcommand support  |
| `subparsers.add_parser(name, help, description)`                      | stdlib | Subcommand creation |

#### Output Module (`ralph_agi/output.py` - 260 lines)

| API                                                       | Source     | Usage             |
| --------------------------------------------------------- | ---------- | ----------------- |
| `rich.console.Console(file, force_terminal, highlight)`   | rich>=13.0 | Terminal output   |
| `rich.panel.Panel(content, title, border_style, padding)` | rich>=13.0 | Completion banner |
| `rich.text.Text(content, justify)`                        | rich>=13.0 | Text styling      |

#### Integration APIs

| API                             | Signature                        | Source       |
| ------------------------------- | -------------------------------- | ------------ |
| `load_config(path)`             | `(Optional[str]) -> RalphConfig` | config.py:84 |
| `RalphLoop.from_config(config)` | `(RalphConfig) -> RalphLoop`     | loop.py:135  |
| `loop.run(handle_signals)`      | `(bool) -> bool`                 | loop.py:465  |
| `loop.close()`                  | `() -> None`                     | loop.py:576  |

### Anti-Patterns to Avoid

- **DO NOT** use `click` library (project uses argparse)
- **DO NOT** call `Console.print()` without checking `is_tty` for color logic
- **DO NOT** forget to call `loop.close()` in finally block
- **DO NOT** use `raise SystemExit` for exit codes (use `return` from `main()`)

---

## Phase 1: Dependencies and Entry Point

### Task 1.1: Add Dependencies to pyproject.toml

**Copy from:** `pyproject.toml:23-28` (existing dependencies block)

**Add:**

```toml
dependencies = [
    "PyYAML>=6.0",
    "memvid-sdk>=0.1.0",
    "sentence-transformers>=2.2.0",
    "rich>=13.0",  # ADD THIS LINE
]

[project.scripts]
ralph-agi = "ralph_agi.cli:main"  # ADD THIS SECTION
```

**Verification:**

```bash
grep "rich" pyproject.toml  # Should show: "rich>=13.0"
grep "ralph-agi" pyproject.toml  # Should show entry point
```

---

## Phase 2: Output Formatter Module

### Task 2.1: Create `ralph_agi/output.py`

**Pattern to copy from:** Rich library examples + TTY detection pattern

**Structure (260 lines):**

```python
# Imports
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Verbosity Enum
class Verbosity(Enum):
    QUIET = 0   # Errors only
    NORMAL = 1  # Summary output
    VERBOSE = 2 # All logs

# OutputFormatter Dataclass
@dataclass
class OutputFormatter:
    verbosity: Verbosity = Verbosity.NORMAL
    file: TextIO = field(default_factory=lambda: sys.stdout)
    _console: Console = field(init=False, repr=False)

    def __post_init__(self) -> None:
        force_terminal = None
        if hasattr(self.file, "isatty"):
            force_terminal = self.file.isatty()
        self._console = Console(
            file=self.file,
            force_terminal=force_terminal,
            highlight=False,
        )
```

**Methods to implement:**
| Method | Parameters | Verbosity Gating |
|--------|-----------|------------------|
| `separator()` | none | Skip in QUIET |
| `iteration_header(current, max)` | int, int | Skip in QUIET |
| `message(text, style)` | str, str\|None | Skip in QUIET |
| `verbose(text)` | str | Only in VERBOSE |
| `summary(changes)` | list[str] | Skip in QUIET |
| `quality_status(passed, details)` | bool, str\|None | Skip in QUIET |
| `iteration_complete(iteration, continuing)` | int, bool | Skip in QUIET |
| `completion_banner(total, session_id, reason)` | int, str\|None, str | Always show |
| `error(message, exception)` | str, Exception\|None | Always show |
| `warning(message)` | str | Skip in QUIET |

**TTY vs Non-TTY Pattern:**

```python
if self.is_tty:
    self._console.print(text, style="bold cyan")  # Rich styling
else:
    self._console.print(text)  # Plain text
```

**Verification:**

```bash
python -c "from ralph_agi.output import OutputFormatter, Verbosity; print('OK')"
```

---

## Phase 3: CLI Module

### Task 3.1: Create `ralph_agi/cli.py`

**Pattern to copy from:** argparse documentation + existing codebase patterns

**Structure (223 lines):**

```python
# Exit codes (lines 18-21)
EXIT_SUCCESS = 0        # Completed via signal
EXIT_ERROR = 1          # Exception raised
EXIT_MAX_ITERATIONS = 2 # Max iterations reached

# Parser creation function
def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ralph-agi",
        description="RALPH-AGI - Recursive Autonomous Long-horizon Processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="..."  # Examples and exit code legend
    )
    # Add --version, subparsers, run command args

# Run command handler
def run_loop(args: argparse.Namespace) -> int:
    # 1. Determine verbosity from args.quiet/args.verbose
    # 2. Create OutputFormatter
    # 3. Load config from args.config
    # 4. Override max_iterations if args.max_iterations set
    # 5. Create loop via RalphLoop.from_config(config)
    # 6. Run loop with exception handling
    # 7. Return appropriate exit code

# Main entry point
def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return run_loop(args)
    parser.print_help()
    return EXIT_SUCCESS
```

**Exception Handling Pattern (from cli.py:148-191):**

```python
try:
    completed = loop.run(handle_signals=True)
    # Handle completion
except LoopInterrupted as e:
    # Graceful interrupt -> EXIT_SUCCESS
except MaxRetriesExceeded as e:
    # Retry exhaustion -> EXIT_ERROR
except KeyboardInterrupt:
    # User cancel -> EXIT_ERROR
except Exception as e:
    # Unexpected -> EXIT_ERROR
finally:
    loop.close()  # ALWAYS cleanup
```

**Verification:**

```bash
ralph-agi --help
ralph-agi --version
ralph-agi run --help
```

---

## Phase 4: Test Suite

### Task 4.1: Create `tests/test_output.py`

**Pattern to copy from:** Existing test patterns in tests/core/

**Test Classes (29 tests):**

- `TestVerbosity` - Enum ordering
- `TestOutputFormatterBasic` - Initialization
- `TestOutputFormatterSeparator` - separator() method
- `TestOutputFormatterIterationHeader` - iteration_header() method
- `TestOutputFormatterMessage` - message() method
- `TestOutputFormatterVerbose` - verbose() method
- `TestOutputFormatterSummary` - summary() method
- `TestOutputFormatterQualityStatus` - quality_status() method
- `TestOutputFormatterIterationComplete` - iteration_complete() method
- `TestOutputFormatterCompletionBanner` - completion_banner() method
- `TestOutputFormatterError` - error() method
- `TestOutputFormatterWarning` - warning() method
- `TestOutputFormatterTTYDetection` - is_tty property

**io.StringIO Capture Pattern:**

```python
def test_example(self):
    output = io.StringIO()
    formatter = OutputFormatter(file=output)
    formatter.method("arg")
    assert "expected" in output.getvalue()
```

### Task 4.2: Create `tests/cli/test_cli.py`

**Test Classes (27 tests):**

- `TestCreateParser` - Parser creation and flags
- `TestMainFunction` - Entry point routing
- `TestRunLoop` - Command execution
- `TestRunLoopExceptions` - Exception handling
- `TestExitCodes` - Exit code constants

**Mock Pattern:**

```python
with patch("ralph_agi.cli.RalphLoop") as mock_loop_class:
    mock_loop = MagicMock()
    mock_loop.run.return_value = True
    mock_loop.iteration = 5
    mock_loop.session_id = "test-session"
    mock_loop_class.from_config.return_value = mock_loop

    result = run_loop(args)
    mock_loop.close.assert_called_once()
```

**Verification:**

```bash
pytest tests/test_output.py tests/cli/test_cli.py -v
```

---

## Phase 5: Verification

### Verification Checklist

```bash
# 1. Dependencies installed
pip install -e ".[dev]"

# 2. CLI entry point works
ralph-agi --help                    # Shows help text
ralph-agi --version                 # Shows "ralph-agi 0.1.0"
ralph-agi run --help                # Shows run command help

# 3. Run command works
ralph-agi run --max-iterations 2    # Runs 2 iterations, exits with code 2

# 4. All tests pass
pytest tests/test_output.py tests/cli/test_cli.py -v  # 56 tests pass

# 5. Full test suite still passes
pytest tests/ -v --tb=short         # 202+ tests pass

# 6. Exit codes correct
ralph-agi run --max-iterations 1; echo "Exit: $?"  # Should show "Exit: 2"
```

### Anti-Pattern Grep Checks

```bash
# Check for invented APIs (should return nothing)
grep -r "click\." ralph_agi/         # Should be empty (we use argparse)
grep -r "Console\.style" ralph_agi/  # Should be empty (invalid API)

# Check cleanup pattern is present
grep -A2 "finally:" ralph_agi/cli.py  # Should show loop.close()
```

---

## Files Created/Modified

| File                    | Action   | Lines     |
| ----------------------- | -------- | --------- |
| `pyproject.toml`        | Modified | +4 lines  |
| `ralph_agi/output.py`   | Created  | 260 lines |
| `ralph_agi/cli.py`      | Created  | 223 lines |
| `tests/test_output.py`  | Created  | 289 lines |
| `tests/cli/__init__.py` | Created  | 1 line    |
| `tests/cli/test_cli.py` | Created  | 322 lines |

**Total:** 6 files, ~1099 lines of code + tests

---

## Summary

This plan enables an LLM to implement Sprint 3 CLI & Output Formatting by:

1. **Phase 0**: Establishing allowed APIs from actual source code
2. **Phase 1**: Adding dependencies with exact syntax
3. **Phase 2**: Creating OutputFormatter with copy-ready patterns
4. **Phase 3**: Creating CLI with verified integration patterns
5. **Phase 4**: Writing tests using documented patterns
6. **Phase 5**: Verifying with concrete commands

Each phase is self-contained and can be executed in a fresh context with the documentation references provided.
