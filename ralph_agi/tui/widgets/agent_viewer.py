"""Agent viewer widget for displaying agent output and thoughts."""

from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static


class AgentMessage(Static):
    """A single agent message with styling."""

    DEFAULT_CSS = """
    AgentMessage {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }
    AgentMessage.thought {
        color: $text-muted;
        border-left: thick $surface-lighten-2;
        padding-left: 2;
    }
    AgentMessage.action {
        color: $success;
    }
    AgentMessage.tool {
        color: $primary-lighten-2;
    }
    AgentMessage.result {
        color: $text;
    }
    AgentMessage.error {
        color: $error;
        text-style: bold;
    }
    AgentMessage.header {
        color: $warning;
        text-style: bold;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        content: str,
        message_type: str = "result",
    ) -> None:
        """Initialize an agent message.

        Args:
            content: Message content.
            message_type: Message type (thought, action, tool, result, error, header).
        """
        self.message_type = message_type

        # Add prefix based on type
        prefixes = {
            "thought": "💭",
            "action": ">",
            "tool": "🔧",
            "result": "→",
            "error": "✗",
            "header": "●",
        }
        prefix = prefixes.get(message_type, "")
        formatted = f"{prefix} {content}" if prefix else content

        super().__init__(formatted, classes=message_type)


class AgentViewer(VerticalScroll):
    """Panel for displaying agent output and reasoning."""

    DEFAULT_CSS = """
    AgentViewer {
        border: solid $primary;
        height: 100%;
        scrollbar-gutter: stable;
    }
    AgentViewer > .viewer-title {
        dock: top;
        background: $primary;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    """

    TITLE: ClassVar[str] = "Agent Output"
    MAX_MESSAGES: ClassVar[int] = 200

    def __init__(self, title: str = "Agent Output", **kwargs) -> None:
        """Initialize the agent viewer.

        Args:
            title: Panel title.
            **kwargs: Additional arguments for VerticalScroll.
        """
        super().__init__(**kwargs)
        self._title = title
        self._messages: list[AgentMessage] = []
        self._auto_scroll = True

    def compose(self) -> ComposeResult:
        """Compose the viewer layout."""
        yield Static(f" {self._title} ", classes="viewer-title")

    def _add_message(self, content: str, message_type: str) -> None:
        """Add a message to the viewer.

        Args:
            content: Message content.
            message_type: Message type.
        """
        msg = AgentMessage(content, message_type)
        self._messages.append(msg)

        # Prune old messages if over limit
        if len(self._messages) > self.MAX_MESSAGES:
            oldest = self._messages.pop(0)
            oldest.remove()

        self.mount(msg)

        if self._auto_scroll:
            self.scroll_end(animate=False)

    def show_iteration(self, iteration: int, task_name: str) -> None:
        """Show iteration header.

        Args:
            iteration: Iteration number.
            task_name: Name of the current task.
        """
        self._add_message(f"[Iteration {iteration}] Working on: {task_name}", "header")

    def show_thought(self, thought: str) -> None:
        """Show agent thinking/reasoning.

        Args:
            thought: The agent's thought.
        """
        self._add_message(thought, "thought")

    def show_action(self, action: str) -> None:
        """Show an action being taken.

        Args:
            action: Description of the action.
        """
        self._add_message(action, "action")

    def show_tool_call(self, tool_name: str, description: str = "") -> None:
        """Show a tool being called.

        Args:
            tool_name: Name of the tool.
            description: Optional description.
        """
        text = f"Calling {tool_name}" + (f": {description}" if description else "")
        self._add_message(text, "tool")

    def show_result(self, result: str) -> None:
        """Show a result.

        Args:
            result: The result text.
        """
        self._add_message(result, "result")

    def show_error(self, error: str) -> None:
        """Show an error.

        Args:
            error: Error message.
        """
        self._add_message(error, "error")

    def clear(self) -> None:
        """Clear all messages."""
        for msg in self._messages:
            msg.remove()
        self._messages.clear()

    def toggle_auto_scroll(self) -> bool:
        """Toggle auto-scroll behavior.

        Returns:
            New auto-scroll state.
        """
        self._auto_scroll = not self._auto_scroll
        return self._auto_scroll
