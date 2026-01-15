"""Log panel widget for real-time log streaming."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static


class LogEntry(Static):
    """A single log entry with timestamp and level coloring."""

    DEFAULT_CSS = """
    LogEntry {
        height: auto;
        padding: 0 1;
    }
    LogEntry.info {
        color: $text;
    }
    LogEntry.debug {
        color: $text-muted;
    }
    LogEntry.warning {
        color: $warning;
    }
    LogEntry.error {
        color: $error;
        text-style: bold;
    }
    """

    def __init__(
        self,
        message: str,
        level: str = "info",
        timestamp: datetime | None = None,
    ) -> None:
        """Initialize a log entry.

        Args:
            message: The log message.
            level: Log level (debug, info, warning, error).
            timestamp: Optional timestamp, defaults to now.
        """
        self.timestamp = timestamp or datetime.now()
        self.level = level.lower()
        self.message = message

        time_str = self.timestamp.strftime("%H:%M:%S")
        level_str = level.upper()[:5].ljust(5)
        formatted = f"[dim]{time_str}[/] [{self._level_color}]{level_str}[/] {message}"

        super().__init__(formatted, classes=self.level)

    @property
    def _level_color(self) -> str:
        """Get color for log level."""
        colors = {
            "debug": "dim",
            "info": "cyan",
            "warning": "yellow",
            "error": "red bold",
        }
        return colors.get(self.level, "white")


class LogPanel(VerticalScroll):
    """Panel for displaying real-time logs with auto-scroll."""

    DEFAULT_CSS = """
    LogPanel {
        border: solid $primary;
        height: 100%;
        scrollbar-gutter: stable;
    }
    LogPanel > .log-title {
        dock: top;
        background: $primary;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    """

    TITLE: ClassVar[str] = "Logs"
    MAX_ENTRIES: ClassVar[int] = 500

    def __init__(self, title: str = "Logs", **kwargs) -> None:
        """Initialize the log panel.

        Args:
            title: Panel title.
            **kwargs: Additional arguments for VerticalScroll.
        """
        super().__init__(**kwargs)
        self._title = title
        self._entries: list[LogEntry] = []
        self._auto_scroll = True

    def compose(self) -> ComposeResult:
        """Compose the panel layout."""
        yield Static(f" {self._title} ", classes="log-title")

    def add_log(
        self,
        message: str,
        level: str = "info",
        timestamp: datetime | None = None,
    ) -> None:
        """Add a log entry to the panel.

        Args:
            message: The log message.
            level: Log level (debug, info, warning, error).
            timestamp: Optional timestamp.
        """
        entry = LogEntry(message, level, timestamp)
        self._entries.append(entry)

        # Prune old entries if over limit
        if len(self._entries) > self.MAX_ENTRIES:
            oldest = self._entries.pop(0)
            oldest.remove()

        self.mount(entry)

        if self._auto_scroll:
            self.scroll_end(animate=False)

    def log_info(self, message: str) -> None:
        """Add an info log entry."""
        self.add_log(message, "info")

    def log_debug(self, message: str) -> None:
        """Add a debug log entry."""
        self.add_log(message, "debug")

    def log_warning(self, message: str) -> None:
        """Add a warning log entry."""
        self.add_log(message, "warning")

    def log_error(self, message: str) -> None:
        """Add an error log entry."""
        self.add_log(message, "error")

    def clear_logs(self) -> None:
        """Clear all log entries."""
        for entry in self._entries:
            entry.remove()
        self._entries.clear()

    def toggle_auto_scroll(self) -> bool:
        """Toggle auto-scroll behavior.

        Returns:
            New auto-scroll state.
        """
        self._auto_scroll = not self._auto_scroll
        return self._auto_scroll
