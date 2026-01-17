"""Frontmatter YAML editor widget for RALPH-AGI.

Provides a visual form-based interface for editing YAML frontmatter
in markdown files with validation and undo/redo support.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, ClassVar, Optional

import yaml

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    Static,
    TextArea,
)


# Regex to match YAML frontmatter
FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n",
    re.MULTILINE | re.DOTALL,
)


@dataclass
class FrontmatterField:
    """Definition of a frontmatter field for the form."""

    name: str
    label: str
    field_type: str  # "text", "textarea", "checkbox", "number"
    required: bool = False
    default: Any = None
    help_text: Optional[str] = None


# Common frontmatter schemas for different file types
SCHEMAS: dict[str, list[FrontmatterField]] = {
    "story": [
        FrontmatterField("id", "Story ID", "text", required=True),
        FrontmatterField("title", "Title", "text", required=True),
        FrontmatterField("status", "Status", "text", default="draft"),
        FrontmatterField("priority", "Priority", "number", default=2),
        FrontmatterField("assignee", "Assignee", "text"),
        FrontmatterField("epic", "Epic", "text"),
        FrontmatterField("estimate", "Estimate (hours)", "number"),
        FrontmatterField("description", "Description", "textarea"),
    ],
    "epic": [
        FrontmatterField("id", "Epic ID", "text", required=True),
        FrontmatterField("title", "Title", "text", required=True),
        FrontmatterField("status", "Status", "text", default="planning"),
        FrontmatterField("priority", "Priority", "number", default=1),
        FrontmatterField("owner", "Owner", "text"),
        FrontmatterField("description", "Description", "textarea"),
    ],
    "task": [
        FrontmatterField("id", "Task ID", "text", required=True),
        FrontmatterField("title", "Title", "text", required=True),
        FrontmatterField("status", "Status", "text", default="pending"),
        FrontmatterField("priority", "Priority", "number", default=2),
        FrontmatterField("blocked", "Blocked", "checkbox", default=False),
        FrontmatterField("notes", "Notes", "textarea"),
    ],
    "generic": [
        FrontmatterField("title", "Title", "text"),
        FrontmatterField("date", "Date", "text"),
        FrontmatterField("author", "Author", "text"),
        FrontmatterField("tags", "Tags (comma-separated)", "text"),
        FrontmatterField("description", "Description", "textarea"),
    ],
}


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Full markdown file content.

    Returns:
        Tuple of (frontmatter dict, body content).
    """
    match = FRONTMATTER_PATTERN.match(content)
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            frontmatter = {}
        body = content[match.end() :]
        return frontmatter, body
    return {}, content


def serialize_frontmatter(data: dict[str, Any], body: str) -> str:
    """Serialize frontmatter and body back to markdown.

    Args:
        data: Frontmatter dictionary.
        body: Body content.

    Returns:
        Full markdown content with frontmatter.
    """
    # Filter out None/empty values
    clean_data = {k: v for k, v in data.items() if v is not None and v != ""}

    if clean_data:
        frontmatter = yaml.dump(clean_data, default_flow_style=False, allow_unicode=True)
        return f"---\n{frontmatter}---\n{body}"
    return body


class DynamicField(Container):
    """A dynamic form field that adapts to field type."""

    DEFAULT_CSS = """
    DynamicField {
        height: auto;
        margin-bottom: 1;
    }
    DynamicField .field-label {
        height: 1;
    }
    DynamicField .field-help {
        color: $text-muted;
        height: 1;
    }
    DynamicField .required-marker {
        color: $error;
    }
    DynamicField Input, DynamicField TextArea {
        width: 100%;
    }
    DynamicField TextArea {
        height: 4;
    }
    """

    class FieldChanged(Message):
        """Message sent when field value changes."""

        def __init__(self, name: str, value: Any) -> None:
            super().__init__()
            self.name = name
            self.value = value

    def __init__(self, field: FrontmatterField, value: Any = None, **kwargs) -> None:
        """Initialize a dynamic field.

        Args:
            field: Field definition.
            value: Initial value.
            **kwargs: Container arguments.
        """
        super().__init__(**kwargs)
        self._field = field
        self._value = value if value is not None else field.default

    def compose(self) -> ComposeResult:
        """Compose the field widget."""
        # Label with required marker
        required = " *" if self._field.required else ""
        yield Label(
            f"{self._field.label}{required}",
            classes="field-label",
        )

        # Help text
        if self._field.help_text:
            yield Static(self._field.help_text, classes="field-help")

        # Field widget based on type
        if self._field.field_type == "textarea":
            yield TextArea(
                str(self._value) if self._value else "",
                id=f"field-{self._field.name}",
            )
        elif self._field.field_type == "checkbox":
            yield Checkbox(
                "",
                value=bool(self._value),
                id=f"field-{self._field.name}",
            )
        elif self._field.field_type == "number":
            yield Input(
                str(self._value) if self._value is not None else "",
                placeholder="Enter number",
                id=f"field-{self._field.name}",
            )
        else:  # text
            yield Input(
                str(self._value) if self._value else "",
                placeholder=f"Enter {self._field.label.lower()}",
                id=f"field-{self._field.name}",
            )

    @property
    def field_name(self) -> str:
        """Get the field name."""
        return self._field.name

    def get_value(self) -> Any:
        """Get the current field value."""
        widget_id = f"field-{self._field.name}"

        if self._field.field_type == "textarea":
            widget = self.query_one(f"#{widget_id}", TextArea)
            return widget.text
        elif self._field.field_type == "checkbox":
            widget = self.query_one(f"#{widget_id}", Checkbox)
            return widget.value
        elif self._field.field_type == "number":
            widget = self.query_one(f"#{widget_id}", Input)
            try:
                return int(widget.value) if widget.value else None
            except ValueError:
                return None
        else:
            widget = self.query_one(f"#{widget_id}", Input)
            return widget.value or None

    def set_value(self, value: Any) -> None:
        """Set the field value."""
        widget_id = f"field-{self._field.name}"
        self._value = value

        if self._field.field_type == "textarea":
            widget = self.query_one(f"#{widget_id}", TextArea)
            widget.text = str(value) if value else ""
        elif self._field.field_type == "checkbox":
            widget = self.query_one(f"#{widget_id}", Checkbox)
            widget.value = bool(value)
        elif self._field.field_type == "number":
            widget = self.query_one(f"#{widget_id}", Input)
            widget.value = str(value) if value is not None else ""
        else:
            widget = self.query_one(f"#{widget_id}", Input)
            widget.value = str(value) if value else ""

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        self.post_message(self.FieldChanged(self._field.name, self.get_value()))

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text area changes."""
        self.post_message(self.FieldChanged(self._field.name, self.get_value()))

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes."""
        self.post_message(self.FieldChanged(self._field.name, self.get_value()))


class FrontmatterEditor(Container):
    """Visual YAML frontmatter editor for markdown files.

    A form-based interface for editing YAML frontmatter with:
    - Schema-driven form generation
    - Field validation
    - Undo/redo support
    - Preserves markdown body content

    Example:
        >>> editor = FrontmatterEditor(
        ...     file_path="story.md",
        ...     schema="story",
        ... )
    """

    DEFAULT_CSS = """
    FrontmatterEditor {
        height: 100%;
        padding: 1;
        border: solid $primary;
    }
    FrontmatterEditor .editor-title {
        dock: top;
        background: $primary;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    FrontmatterEditor .toolbar {
        dock: top;
        height: 3;
        padding: 0 1;
        margin-top: 1;
    }
    FrontmatterEditor .toolbar Button {
        margin-right: 1;
    }
    FrontmatterEditor .form-scroll {
        height: 1fr;
    }
    FrontmatterEditor .status-bar {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: $surface;
    }
    FrontmatterEditor .raw-yaml {
        height: 10;
        border: solid $secondary;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("ctrl+z", "undo", "Undo", show=True),
        Binding("ctrl+y", "redo", "Redo", show=True),
    ]

    class FrontmatterSaved(Message):
        """Message sent when frontmatter is saved."""

        def __init__(self, path: Path) -> None:
            super().__init__()
            self.path = path

    # Reactive state
    has_changes: reactive[bool] = reactive(False)

    def __init__(
        self,
        file_path: Optional[str | Path] = None,
        schema: str = "generic",
        custom_fields: Optional[list[FrontmatterField]] = None,
        on_save: Optional[Callable[[dict[str, Any]], None]] = None,
        **kwargs,
    ) -> None:
        """Initialize the frontmatter editor.

        Args:
            file_path: Path to markdown file.
            schema: Schema name from SCHEMAS or "generic".
            custom_fields: Custom field definitions (overrides schema).
            on_save: Callback when frontmatter is saved.
            **kwargs: Container arguments.
        """
        super().__init__(**kwargs)
        self._file_path = Path(file_path) if file_path else None
        self._schema_name = schema
        self._custom_fields = custom_fields
        self._on_save = on_save

        self._fields = custom_fields or SCHEMAS.get(schema, SCHEMAS["generic"])
        self._data: dict[str, Any] = {}
        self._body: str = ""
        self._history: list[dict[str, Any]] = []
        self._history_pos: int = -1

    def compose(self) -> ComposeResult:
        """Compose the editor layout."""
        title = f"Frontmatter: {self._file_path.name if self._file_path else 'New'}"
        yield Static(f" {title} ", classes="editor-title")

        with Horizontal(classes="toolbar"):
            yield Button("Save", id="save-btn", variant="primary")
            yield Button("Undo", id="undo-btn", variant="default")
            yield Button("Redo", id="redo-btn", variant="default")
            yield Button("Raw YAML", id="raw-btn", variant="default")

        with VerticalScroll(classes="form-scroll", id="form-scroll"):
            for field in self._fields:
                yield DynamicField(field, id=f"dynamic-{field.name}")

            # Raw YAML view (hidden by default)
            yield TextArea(id="raw-yaml", classes="raw-yaml")

        yield Static("", id="status-bar", classes="status-bar")

    def on_mount(self) -> None:
        """Handle mount - load file if path provided."""
        # Hide raw YAML by default
        raw_yaml = self.query_one("#raw-yaml", TextArea)
        raw_yaml.display = False

        if self._file_path and self._file_path.exists():
            self.load_file(self._file_path)
        self._update_ui_state()

    def load_file(self, path: Path | str) -> None:
        """Load a markdown file with frontmatter.

        Args:
            path: Path to markdown file.
        """
        path = Path(path)
        self._file_path = path

        try:
            content = path.read_text(encoding="utf-8")
            self._data, self._body = parse_frontmatter(content)
            self._push_history("Load file")
            self._refresh_form()
            self._update_status(f"Loaded: {path.name}")
        except Exception as e:
            self._update_status(f"Error loading: {e}", error=True)

    def _refresh_form(self) -> None:
        """Refresh form fields from current data."""
        for field in self._fields:
            try:
                widget = self.query_one(f"#dynamic-{field.name}", DynamicField)
                widget.set_value(self._data.get(field.name))
            except Exception:
                pass  # Field might not exist

        # Update raw YAML
        raw_yaml = self.query_one("#raw-yaml", TextArea)
        yaml_text = yaml.dump(self._data, default_flow_style=False, allow_unicode=True)
        raw_yaml.text = yaml_text

    def _push_history(self, description: str) -> None:
        """Push current state to history."""
        # Trim future history
        if self._history_pos < len(self._history) - 1:
            self._history = self._history[: self._history_pos + 1]

        self._history.append(copy.deepcopy(self._data))
        self._history_pos = len(self._history) - 1

        # Limit history size
        if len(self._history) > 50:
            self._history = self._history[-50:]
            self._history_pos = len(self._history) - 1

    def _update_ui_state(self) -> None:
        """Update UI based on current state."""
        undo_btn = self.query_one("#undo-btn", Button)
        redo_btn = self.query_one("#redo-btn", Button)
        save_btn = self.query_one("#save-btn", Button)

        undo_btn.disabled = self._history_pos <= 0
        redo_btn.disabled = self._history_pos >= len(self._history) - 1
        save_btn.disabled = not self.has_changes

    def _update_status(self, message: str, error: bool = False) -> None:
        """Update status bar."""
        status = self.query_one("#status-bar", Static)
        if error:
            status.update(f"[red]{message}[/red]")
        else:
            status.update(message)

    def on_dynamic_field_field_changed(self, event: DynamicField.FieldChanged) -> None:
        """Handle field value changes."""
        self._data[event.name] = event.value
        self.has_changes = True
        self._push_history(f"Edit {event.name}")
        self._update_ui_state()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "undo-btn":
            self.action_undo()
        elif event.button.id == "redo-btn":
            self.action_redo()
        elif event.button.id == "raw-btn":
            self._toggle_raw_yaml()

    def _toggle_raw_yaml(self) -> None:
        """Toggle raw YAML view."""
        raw_yaml = self.query_one("#raw-yaml", TextArea)
        raw_yaml.display = not raw_yaml.display

    def action_save(self) -> None:
        """Save the frontmatter to file."""
        if not self._file_path:
            self._update_status("No file path set", error=True)
            return

        # Validate required fields
        errors = self._validate()
        if errors:
            self._update_status(f"Validation: {errors[0]}", error=True)
            return

        try:
            content = serialize_frontmatter(self._data, self._body)
            self._file_path.write_text(content, encoding="utf-8")
            self.has_changes = False
            self._update_ui_state()
            self._update_status(f"Saved: {self._file_path.name}")
            self.post_message(self.FrontmatterSaved(self._file_path))
            if self._on_save:
                self._on_save(self._data)
        except Exception as e:
            self._update_status(f"Save failed: {e}", error=True)

    def action_undo(self) -> None:
        """Undo the last change."""
        if self._history_pos > 0:
            self._history_pos -= 1
            self._data = copy.deepcopy(self._history[self._history_pos])
            self._refresh_form()
            self.has_changes = True
            self._update_ui_state()
            self._update_status("Undo")

    def action_redo(self) -> None:
        """Redo the last undone change."""
        if self._history_pos < len(self._history) - 1:
            self._history_pos += 1
            self._data = copy.deepcopy(self._history[self._history_pos])
            self._refresh_form()
            self.has_changes = True
            self._update_ui_state()
            self._update_status("Redo")

    def _validate(self) -> list[str]:
        """Validate the current frontmatter.

        Returns:
            List of validation error messages.
        """
        errors = []
        for field in self._fields:
            if field.required:
                value = self._data.get(field.name)
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors.append(f"{field.label} is required")
        return errors

    def get_data(self) -> dict[str, Any]:
        """Get the current frontmatter data."""
        return copy.deepcopy(self._data)

    def set_data(self, data: dict[str, Any]) -> None:
        """Set the frontmatter data.

        Args:
            data: Frontmatter dictionary.
        """
        self._data = copy.deepcopy(data)
        self._push_history("Set data")
        self._refresh_form()
        self.has_changes = True
        self._update_ui_state()
