"""Output formatting for RALPH-AGI CLI.

Provides polished terminal output using Rich library, based on
Ryan Carson's production-validated patterns.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

if TYPE_CHECKING:
    from typing import TextIO


class Verbosity(Enum):
    """Output verbosity levels."""

    QUIET = 0  # Errors only
    NORMAL = 1  # Summary output
    VERBOSE = 2  # All logs


@dataclass
class OutputFormatter:
    """Formats RALPH-AGI output for terminal display.

    Supports TTY detection for colored vs plain output,
    and configurable verbosity levels.
    """

    verbosity: Verbosity = Verbosity.NORMAL
    file: TextIO = field(default_factory=lambda: sys.stdout)
    _console: Console = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize Rich console with TTY detection."""
        force_terminal = None
        if hasattr(self.file, "isatty"):
            force_terminal = self.file.isatty()
        self._console = Console(
            file=self.file,
            force_terminal=force_terminal,
            highlight=False,
        )

    @property
    def is_tty(self) -> bool:
        """Check if output is to a terminal."""
        return self._console.is_terminal

    def separator(self) -> None:
        """Print a visual separator bar."""
        if self.verbosity == Verbosity.QUIET:
            return
        bar = "\u2550" * 64  # ═
        if self.is_tty:
            self._console.print(bar, style="cyan")
        else:
            self._console.print(bar)

    def iteration_header(self, current: int, max_iterations: int) -> None:
        """Print iteration header with count.

        Args:
            current: Current iteration number (1-based)
            max_iterations: Maximum iterations configured
        """
        if self.verbosity == Verbosity.QUIET:
            return

        self.separator()
        header = f"    Ralph Iteration {current} of {max_iterations}"
        if self.is_tty:
            self._console.print(header, style="bold cyan")
        else:
            self._console.print(header)
        self.separator()
        self._console.print()

    def message(self, text: str, style: str | None = None) -> None:
        """Print a general message.

        Args:
            text: Message text
            style: Optional Rich style (ignored in non-TTY mode)
        """
        if self.verbosity == Verbosity.QUIET:
            return
        if self.is_tty and style:
            self._console.print(text, style=style)
        else:
            self._console.print(text)

    def verbose(self, text: str) -> None:
        """Print verbose-only message.

        Args:
            text: Message text (only shown in verbose mode)
        """
        if self.verbosity != Verbosity.VERBOSE:
            return
        if self.is_tty:
            self._console.print(text, style="dim")
        else:
            self._console.print(text)

    def summary(self, changes: list[str]) -> None:
        """Print a bullet-point summary of changes.

        Args:
            changes: List of change descriptions
        """
        if self.verbosity == Verbosity.QUIET:
            return
        if not changes:
            return

        self._console.print()
        if self.is_tty:
            self._console.print("Summary:", style="bold")
        else:
            self._console.print("Summary:")

        for change in changes:
            bullet = "\u2022" if self.is_tty else "-"
            self._console.print(f"  {bullet} {change}")
        self._console.print()

    def quality_status(self, passed: bool, details: str | None = None) -> None:
        """Print quality gate status.

        Args:
            passed: Whether quality checks passed
            details: Optional details about the check
        """
        if self.verbosity == Verbosity.QUIET:
            return

        if passed:
            icon = "\u2714" if self.is_tty else "[PASS]"  # ✔
            text = f"{icon} All quality checks pass"
            style = "green"
        else:
            icon = "\u2718" if self.is_tty else "[FAIL]"  # ✘
            text = f"{icon} Quality checks failed"
            style = "red"

        if details:
            text = f"{text}: {details}"

        if self.is_tty:
            self._console.print(text, style=style)
        else:
            self._console.print(text)

    def iteration_complete(self, iteration: int, continuing: bool = True) -> None:
        """Print iteration completion message.

        Args:
            iteration: Completed iteration number
            continuing: Whether loop will continue
        """
        if self.verbosity == Verbosity.QUIET:
            return

        if continuing:
            msg = f"Iteration {iteration} complete. Continuing..."
        else:
            msg = f"Iteration {iteration} complete."

        if self.is_tty:
            self._console.print(msg, style="dim")
        else:
            self._console.print(msg)
        self._console.print()

    def completion_banner(
        self,
        total_iterations: int,
        session_id: str | None = None,
        reason: str = "completed",
    ) -> None:
        """Print final completion banner with stats.

        Args:
            total_iterations: Total iterations executed
            session_id: Optional session identifier
            reason: Completion reason (completed, interrupted, max_iterations)
        """
        lines = []
        if reason == "completed":
            title = "RALPH Complete"
            style = "green"
            lines.append(f"Successfully finished in {total_iterations} iteration(s)")
        elif reason == "interrupted":
            title = "RALPH Interrupted"
            style = "yellow"
            lines.append(f"Stopped after {total_iterations} iteration(s)")
        else:  # max_iterations
            title = "RALPH Stopped"
            style = "yellow"
            lines.append(f"Reached max iterations ({total_iterations})")

        if session_id:
            lines.append(f"Session: {session_id}")

        content = "\n".join(lines)

        if self.is_tty:
            panel = Panel(
                Text(content, justify="center"),
                title=title,
                border_style=style,
                padding=(1, 2),
            )
            self._console.print()
            self._console.print(panel)
        else:
            self._console.print()
            self._console.print(f"=== {title} ===")
            for line in lines:
                self._console.print(line)
            self._console.print("=" * (len(title) + 8))

    def error(self, message: str, exception: Exception | None = None) -> None:
        """Print error message (always shown, even in quiet mode).

        Args:
            message: Error description
            exception: Optional exception for details
        """
        if self.is_tty:
            self._console.print(f"Error: {message}", style="bold red")
            if exception and self.verbosity == Verbosity.VERBOSE:
                self._console.print(f"  {type(exception).__name__}: {exception}", style="red")
        else:
            self._console.print(f"Error: {message}")
            if exception and self.verbosity == Verbosity.VERBOSE:
                self._console.print(f"  {type(exception).__name__}: {exception}")

    def warning(self, message: str) -> None:
        """Print warning message.

        Args:
            message: Warning description
        """
        if self.verbosity == Verbosity.QUIET:
            return
        if self.is_tty:
            self._console.print(f"Warning: {message}", style="yellow")
        else:
            self._console.print(f"Warning: {message}")
