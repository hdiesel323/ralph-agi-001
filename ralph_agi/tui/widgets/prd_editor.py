"""PRD visual editor widget for RALPH-AGI.

Provides a form-based interface for editing PRD.json files
with validation, undo/redo support, and atomic saves.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, ClassVar, Optional

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
    ListItem,
    ListView,
    Select,
    Static,
    TextArea,
)

from ralph_agi.tasks.prd import Feature, PRD, Project, load_prd, VALID_CATEGORIES
from ralph_agi.tasks.writer import write_prd

# Maximum undo history size
MAX_UNDO_HISTORY = 50


@dataclass
class UndoState:
    """A snapshot of PRD state for undo/redo."""

    prd_dict: dict[str, Any]
    description: str


class UndoManager:
    """Manages undo/redo history for PRD editing.

    Stores snapshots of PRD state and allows navigation
    through the history stack.
    """

    def __init__(self, max_history: int = MAX_UNDO_HISTORY) -> None:
        """Initialize the undo manager.

        Args:
            max_history: Maximum number of states to keep.
        """
        self._history: list[UndoState] = []
        self._position: int = -1
        self._max_history = max_history

    def push(self, prd_dict: dict[str, Any], description: str) -> None:
        """Push a new state onto the history.

        Args:
            prd_dict: PRD data as dictionary.
            description: Description of the change.
        """
        # Remove any states after current position (discard redo history)
        if self._position < len(self._history) - 1:
            self._history = self._history[: self._position + 1]

        # Add new state
        state = UndoState(prd_dict=copy.deepcopy(prd_dict), description=description)
        self._history.append(state)
        self._position = len(self._history) - 1

        # Trim history if too large
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]
            self._position = len(self._history) - 1

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self._position > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self._position < len(self._history) - 1

    def undo(self) -> Optional[UndoState]:
        """Undo to previous state.

        Returns:
            Previous state, or None if at beginning.
        """
        if not self.can_undo():
            return None
        self._position -= 1
        return self._history[self._position]

    def redo(self) -> Optional[UndoState]:
        """Redo to next state.

        Returns:
            Next state, or None if at end.
        """
        if not self.can_redo():
            return None
        self._position += 1
        return self._history[self._position]

    @property
    def current_state(self) -> Optional[UndoState]:
        """Get current state."""
        if 0 <= self._position < len(self._history):
            return self._history[self._position]
        return None

    @property
    def undo_description(self) -> str:
        """Get description of what would be undone."""
        if self._position > 0:
            return self._history[self._position].description
        return ""

    @property
    def redo_description(self) -> str:
        """Get description of what would be redone."""
        if self._position < len(self._history) - 1:
            return self._history[self._position + 1].description
        return ""


class FeatureListItem(ListItem):
    """A feature item in the feature list."""

    def __init__(self, feature_id: str, description: str, passes: bool) -> None:
        """Initialize a feature list item.

        Args:
            feature_id: Feature ID.
            description: Feature description.
            passes: Whether feature is complete.
        """
        super().__init__()
        self.feature_id = feature_id
        self._description = description
        self._passes = passes

    def compose(self) -> ComposeResult:
        """Compose the list item."""
        icon = "✓" if self._passes else "○"
        text = f"{icon} {self.feature_id}: {self._description[:40]}"
        yield Label(text)


class FeatureList(Container):
    """List of features with selection support."""

    DEFAULT_CSS = """
    FeatureList {
        width: 30;
        height: 100%;
        border: solid $primary;
    }
    FeatureList > .list-title {
        dock: top;
        background: $primary;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    FeatureList ListView {
        height: 1fr;
    }
    FeatureList .buttons {
        dock: bottom;
        height: 3;
        padding: 1;
    }
    """

    class FeatureSelected(Message):
        """Message sent when a feature is selected."""

        def __init__(self, feature_id: str) -> None:
            super().__init__()
            self.feature_id = feature_id

    class AddFeatureRequested(Message):
        """Message sent when add feature is requested."""

        pass

    def __init__(self, **kwargs) -> None:
        """Initialize the feature list."""
        super().__init__(**kwargs)
        self._features: list[tuple[str, str, bool]] = []

    def compose(self) -> ComposeResult:
        """Compose the feature list."""
        yield Static(" Features ", classes="list-title")
        yield ListView(id="feature-listview")
        with Horizontal(classes="buttons"):
            yield Button("+ Add", id="add-feature-btn", variant="success")

    def set_features(self, features: list[Feature]) -> None:
        """Set the feature list.

        Args:
            features: List of Feature objects.
        """
        self._features = [(f.id, f.description, f.passes) for f in features]
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        """Rebuild the list view."""
        listview = self.query_one("#feature-listview", ListView)
        listview.clear()
        for fid, desc, passes in self._features:
            listview.append(FeatureListItem(fid, desc, passes))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle feature selection."""
        if isinstance(event.item, FeatureListItem):
            self.post_message(self.FeatureSelected(event.item.feature_id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "add-feature-btn":
            self.post_message(self.AddFeatureRequested())


class ProjectForm(Container):
    """Form for editing project metadata."""

    DEFAULT_CSS = """
    ProjectForm {
        height: auto;
        padding: 1;
        border: solid $secondary;
        margin-bottom: 1;
    }
    ProjectForm > .form-title {
        text-style: bold;
        margin-bottom: 1;
    }
    ProjectForm .field-label {
        margin-top: 1;
    }
    ProjectForm Input, ProjectForm TextArea {
        margin-bottom: 1;
    }
    """

    class ProjectChanged(Message):
        """Message sent when project data changes."""

        def __init__(self, name: str, description: str, version: Optional[str]) -> None:
            super().__init__()
            self.name = name
            self.description = description
            self.version = version

    def __init__(self, **kwargs) -> None:
        """Initialize the project form."""
        super().__init__(**kwargs)
        self._project: Optional[Project] = None

    def compose(self) -> ComposeResult:
        """Compose the project form."""
        yield Static("Project Details", classes="form-title")
        yield Label("Name:", classes="field-label")
        yield Input(placeholder="Project name", id="project-name")
        yield Label("Description:", classes="field-label")
        yield TextArea(id="project-description")
        yield Label("Version:", classes="field-label")
        yield Input(placeholder="Optional version", id="project-version")

    def set_project(self, project: Project) -> None:
        """Set the project data.

        Args:
            project: Project object.
        """
        self._project = project
        self.query_one("#project-name", Input).value = project.name
        self.query_one("#project-description", TextArea).text = project.description
        self.query_one("#project-version", Input).value = project.version or ""

    def get_project_data(self) -> dict[str, Any]:
        """Get current project data from form."""
        name = self.query_one("#project-name", Input).value
        description = self.query_one("#project-description", TextArea).text
        version = self.query_one("#project-version", Input).value or None
        return {"name": name, "description": description, "version": version}

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        self._emit_change()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text area changes."""
        self._emit_change()

    def _emit_change(self) -> None:
        """Emit a project changed message."""
        data = self.get_project_data()
        self.post_message(
            self.ProjectChanged(
                name=data["name"],
                description=data["description"],
                version=data["version"],
            )
        )


class FeatureForm(Container):
    """Form for editing a single feature."""

    DEFAULT_CSS = """
    FeatureForm {
        height: 100%;
        padding: 1;
        border: solid $secondary;
    }
    FeatureForm > .form-title {
        text-style: bold;
        margin-bottom: 1;
    }
    FeatureForm .field-label {
        margin-top: 1;
    }
    FeatureForm .field-row {
        height: auto;
        margin-bottom: 1;
    }
    FeatureForm Input, FeatureForm TextArea, FeatureForm Select {
        margin-bottom: 1;
    }
    FeatureForm .checkbox-row {
        height: 3;
    }
    FeatureForm .steps-area {
        height: 8;
    }
    FeatureForm .criteria-area {
        height: 6;
    }
    FeatureForm .delete-btn {
        margin-top: 1;
    }
    """

    class FeatureChanged(Message):
        """Message sent when feature data changes."""

        def __init__(self, feature_id: str, data: dict[str, Any]) -> None:
            super().__init__()
            self.feature_id = feature_id
            self.data = data

    class FeatureDeleted(Message):
        """Message sent when feature is deleted."""

        def __init__(self, feature_id: str) -> None:
            super().__init__()
            self.feature_id = feature_id

    def __init__(self, **kwargs) -> None:
        """Initialize the feature form."""
        super().__init__(**kwargs)
        self._feature_id: Optional[str] = None
        self._original_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Compose the feature form."""
        yield Static("Feature Details", classes="form-title", id="feature-title")

        with VerticalScroll():
            yield Label("ID:", classes="field-label")
            yield Input(placeholder="Feature ID (e.g., 2.1)", id="feature-id")

            yield Label("Description:", classes="field-label")
            yield TextArea(id="feature-description")

            with Horizontal(classes="field-row"):
                yield Label("Category:", classes="field-label")
                yield Select(
                    [
                        ("None", None),
                        ("Functional", "functional"),
                        ("UI", "ui"),
                        ("Performance", "performance"),
                        ("Security", "security"),
                        ("Integration", "integration"),
                    ],
                    id="feature-category",
                    allow_blank=True,
                )

            with Horizontal(classes="field-row"):
                yield Label("Priority:", classes="field-label")
                yield Select(
                    [
                        ("None", None),
                        ("P0 - Critical", 0),
                        ("P1 - High", 1),
                        ("P2 - Medium", 2),
                        ("P3 - Low", 3),
                        ("P4 - Backlog", 4),
                    ],
                    id="feature-priority",
                    allow_blank=True,
                )

            with Horizontal(classes="checkbox-row"):
                yield Checkbox("Complete", id="feature-passes")

            yield Label("Steps (one per line):", classes="field-label")
            yield TextArea(id="feature-steps", classes="steps-area")

            yield Label("Acceptance Criteria (one per line):", classes="field-label")
            yield TextArea(id="feature-criteria", classes="criteria-area")

            yield Label("Dependencies (comma-separated IDs):", classes="field-label")
            yield Input(placeholder="e.g., 1.1, 1.2", id="feature-deps")

            yield Button(
                "Delete Feature",
                id="delete-feature-btn",
                variant="error",
                classes="delete-btn",
            )

    def set_feature(self, feature: Feature) -> None:
        """Set the feature data.

        Args:
            feature: Feature object.
        """
        self._feature_id = feature.id
        self._original_id = feature.id

        self.query_one("#feature-title", Static).update(f"Feature: {feature.id}")
        self.query_one("#feature-id", Input).value = feature.id
        self.query_one("#feature-description", TextArea).text = feature.description
        self.query_one("#feature-passes", Checkbox).value = feature.passes

        # Category
        cat_select = self.query_one("#feature-category", Select)
        cat_select.value = feature.category

        # Priority
        pri_select = self.query_one("#feature-priority", Select)
        pri_select.value = feature.priority

        # Steps
        steps_text = "\n".join(feature.steps)
        self.query_one("#feature-steps", TextArea).text = steps_text

        # Criteria
        criteria_text = "\n".join(feature.acceptance_criteria)
        self.query_one("#feature-criteria", TextArea).text = criteria_text

        # Dependencies
        deps_text = ", ".join(feature.dependencies)
        self.query_one("#feature-deps", Input).value = deps_text

    def clear_form(self) -> None:
        """Clear the form."""
        self._feature_id = None
        self._original_id = None
        self.query_one("#feature-title", Static).update("Feature Details")
        self.query_one("#feature-id", Input).value = ""
        self.query_one("#feature-description", TextArea).text = ""
        self.query_one("#feature-passes", Checkbox).value = False
        self.query_one("#feature-category", Select).value = None
        self.query_one("#feature-priority", Select).value = None
        self.query_one("#feature-steps", TextArea).text = ""
        self.query_one("#feature-criteria", TextArea).text = ""
        self.query_one("#feature-deps", Input).value = ""

    def get_feature_data(self) -> dict[str, Any]:
        """Get current feature data from form."""
        feature_id = self.query_one("#feature-id", Input).value
        description = self.query_one("#feature-description", TextArea).text
        passes = self.query_one("#feature-passes", Checkbox).value

        category = self.query_one("#feature-category", Select).value
        priority = self.query_one("#feature-priority", Select).value

        steps_text = self.query_one("#feature-steps", TextArea).text
        steps = [s.strip() for s in steps_text.split("\n") if s.strip()]

        criteria_text = self.query_one("#feature-criteria", TextArea).text
        criteria = [c.strip() for c in criteria_text.split("\n") if c.strip()]

        deps_text = self.query_one("#feature-deps", Input).value
        deps = [d.strip() for d in deps_text.split(",") if d.strip()]

        return {
            "id": feature_id,
            "description": description,
            "passes": passes,
            "category": category if category else None,
            "priority": priority if priority is not None else None,
            "steps": steps,
            "acceptance_criteria": criteria,
            "dependencies": deps,
        }

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if self._original_id:
            self._emit_change()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text area changes."""
        if self._original_id:
            self._emit_change()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes."""
        if self._original_id:
            self._emit_change()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        if self._original_id:
            self._emit_change()

    def _emit_change(self) -> None:
        """Emit a feature changed message."""
        if self._original_id:
            data = self.get_feature_data()
            self.post_message(self.FeatureChanged(self._original_id, data))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "delete-feature-btn" and self._original_id:
            self.post_message(self.FeatureDeleted(self._original_id))


class PRDEditor(Container):
    """Visual PRD.json editor with undo/redo support.

    A form-based interface for editing PRD files with:
    - Project metadata editing
    - Feature list with add/edit/delete
    - Field validation with error messages
    - Undo/redo support
    - Atomic file saves

    Example:
        >>> editor = PRDEditor(prd_path="PRD.json")
        >>> # Mount in Textual app
    """

    DEFAULT_CSS = """
    PRDEditor {
        layout: horizontal;
        height: 100%;
    }
    PRDEditor .editor-main {
        width: 1fr;
        padding: 1;
    }
    PRDEditor .toolbar {
        dock: top;
        height: 3;
        padding: 0 1;
        background: $surface;
    }
    PRDEditor .toolbar Button {
        margin-right: 1;
    }
    PRDEditor .status-bar {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: $surface;
    }
    PRDEditor .validation-error {
        color: $error;
        text-style: bold;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("ctrl+z", "undo", "Undo", show=True),
        Binding("ctrl+y", "redo", "Redo", show=True),
    ]

    class PRDSaved(Message):
        """Message sent when PRD is saved."""

        def __init__(self, path: Path) -> None:
            super().__init__()
            self.path = path

    class ValidationError(Message):
        """Message sent when validation fails."""

        def __init__(self, errors: list[str]) -> None:
            super().__init__()
            self.errors = errors

    # Reactive state
    has_changes: reactive[bool] = reactive(False)
    validation_errors: reactive[list[str]] = reactive(list)

    def __init__(
        self,
        prd_path: Optional[str | Path] = None,
        on_save: Optional[Callable[[PRD], None]] = None,
        **kwargs,
    ) -> None:
        """Initialize the PRD editor.

        Args:
            prd_path: Path to PRD.json file.
            on_save: Callback when PRD is saved.
            **kwargs: Additional container arguments.
        """
        super().__init__(**kwargs)
        self._prd_path = Path(prd_path) if prd_path else None
        self._on_save = on_save
        self._prd_data: dict[str, Any] = {"project": {}, "features": []}
        self._undo_manager = UndoManager()
        self._current_feature_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Compose the editor layout."""
        yield FeatureList(id="feature-list")

        with Vertical(classes="editor-main"):
            with Horizontal(classes="toolbar"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Undo", id="undo-btn", variant="default")
                yield Button("Redo", id="redo-btn", variant="default")
                yield Button("Reload", id="reload-btn", variant="warning")

            yield ProjectForm(id="project-form")
            yield FeatureForm(id="feature-form")

            yield Static("", id="status-bar", classes="status-bar")

    def on_mount(self) -> None:
        """Handle mount - load PRD if path provided."""
        if self._prd_path and self._prd_path.exists():
            self.load_prd(self._prd_path)
        self._update_ui_state()

    def load_prd(self, path: Path | str) -> None:
        """Load a PRD from file.

        Args:
            path: Path to PRD.json file.
        """
        path = Path(path)
        self._prd_path = path

        try:
            prd = load_prd(path)
            self._prd_data = self._prd_to_dict(prd)
            self._undo_manager.push(self._prd_data, "Load PRD")
            self._refresh_ui()
            self._update_status(f"Loaded: {path.name}")
        except Exception as e:
            self._update_status(f"Error loading: {e}", error=True)

    def _prd_to_dict(self, prd: PRD) -> dict[str, Any]:
        """Convert PRD to dictionary."""
        return {
            "project": {
                "name": prd.project.name,
                "description": prd.project.description,
                "version": prd.project.version,
            },
            "features": [
                {
                    "id": f.id,
                    "description": f.description,
                    "passes": f.passes,
                    "category": f.category,
                    "priority": f.priority,
                    "steps": list(f.steps),
                    "acceptance_criteria": list(f.acceptance_criteria),
                    "dependencies": list(f.dependencies),
                    "completed_at": f.completed_at,
                }
                for f in prd.features
            ],
        }

    def _dict_to_prd(self, data: dict[str, Any]) -> PRD:
        """Convert dictionary to PRD object."""
        project = Project(
            name=data["project"]["name"],
            description=data["project"]["description"],
            version=data["project"].get("version"),
        )
        features = tuple(
            Feature(
                id=f["id"],
                description=f["description"],
                passes=f["passes"],
                category=f.get("category"),
                priority=f.get("priority"),
                steps=tuple(f.get("steps", [])),
                acceptance_criteria=tuple(f.get("acceptance_criteria", [])),
                dependencies=tuple(f.get("dependencies", [])),
                completed_at=f.get("completed_at"),
            )
            for f in data["features"]
        )
        return PRD(project=project, features=features)

    def _refresh_ui(self) -> None:
        """Refresh all UI components from current data."""
        # Update project form
        project_form = self.query_one("#project-form", ProjectForm)
        project = Project(
            name=self._prd_data["project"].get("name", ""),
            description=self._prd_data["project"].get("description", ""),
            version=self._prd_data["project"].get("version"),
        )
        project_form.set_project(project)

        # Update feature list
        feature_list = self.query_one("#feature-list", FeatureList)
        features = [
            Feature(
                id=f["id"],
                description=f["description"],
                passes=f["passes"],
                steps=tuple(f.get("steps", [])),
                acceptance_criteria=tuple(f.get("acceptance_criteria", [])),
            )
            for f in self._prd_data["features"]
        ]
        feature_list.set_features(features)

        # Clear feature form
        feature_form = self.query_one("#feature-form", FeatureForm)
        feature_form.clear_form()
        self._current_feature_id = None

    def _update_ui_state(self) -> None:
        """Update UI based on current state."""
        undo_btn = self.query_one("#undo-btn", Button)
        redo_btn = self.query_one("#redo-btn", Button)
        save_btn = self.query_one("#save-btn", Button)

        undo_btn.disabled = not self._undo_manager.can_undo()
        redo_btn.disabled = not self._undo_manager.can_redo()
        save_btn.disabled = not self.has_changes

    def _update_status(self, message: str, error: bool = False) -> None:
        """Update status bar."""
        status = self.query_one("#status-bar", Static)
        if error:
            status.update(f"[red]{message}[/red]")
        else:
            status.update(message)

    def _record_change(self, description: str) -> None:
        """Record a change for undo."""
        self._undo_manager.push(copy.deepcopy(self._prd_data), description)
        self.has_changes = True
        self._update_ui_state()

    # Event handlers
    def on_feature_list_feature_selected(
        self, event: FeatureList.FeatureSelected
    ) -> None:
        """Handle feature selection."""
        self._current_feature_id = event.feature_id

        # Find the feature
        for f in self._prd_data["features"]:
            if f["id"] == event.feature_id:
                feature = Feature(
                    id=f["id"],
                    description=f["description"],
                    passes=f["passes"],
                    category=f.get("category"),
                    priority=f.get("priority"),
                    steps=tuple(f.get("steps", [])),
                    acceptance_criteria=tuple(f.get("acceptance_criteria", [])),
                    dependencies=tuple(f.get("dependencies", [])),
                    completed_at=f.get("completed_at"),
                )
                feature_form = self.query_one("#feature-form", FeatureForm)
                feature_form.set_feature(feature)
                break

    def on_feature_list_add_feature_requested(
        self, event: FeatureList.AddFeatureRequested
    ) -> None:
        """Handle add feature request."""
        # Generate a new ID
        existing_ids = {f["id"] for f in self._prd_data["features"]}
        new_id = "new-1"
        counter = 1
        while new_id in existing_ids:
            counter += 1
            new_id = f"new-{counter}"

        # Add new feature
        new_feature = {
            "id": new_id,
            "description": "New feature",
            "passes": False,
            "steps": [],
            "acceptance_criteria": [],
            "dependencies": [],
        }
        self._prd_data["features"].append(new_feature)
        self._record_change(f"Add feature {new_id}")
        self._refresh_ui()

        # Select the new feature
        self._current_feature_id = new_id
        feature = Feature(
            id=new_id,
            description="New feature",
            passes=False,
        )
        feature_form = self.query_one("#feature-form", FeatureForm)
        feature_form.set_feature(feature)

    def on_project_form_project_changed(
        self, event: ProjectForm.ProjectChanged
    ) -> None:
        """Handle project data change."""
        self._prd_data["project"]["name"] = event.name
        self._prd_data["project"]["description"] = event.description
        self._prd_data["project"]["version"] = event.version
        self._record_change("Edit project")

    def on_feature_form_feature_changed(
        self, event: FeatureForm.FeatureChanged
    ) -> None:
        """Handle feature data change."""
        # Find and update the feature
        for i, f in enumerate(self._prd_data["features"]):
            if f["id"] == event.feature_id:
                self._prd_data["features"][i] = event.data
                self._record_change(f"Edit feature {event.feature_id}")

                # Refresh list if ID changed
                if event.data["id"] != event.feature_id:
                    self._refresh_ui()
                break

    def on_feature_form_feature_deleted(
        self, event: FeatureForm.FeatureDeleted
    ) -> None:
        """Handle feature deletion."""
        self._prd_data["features"] = [
            f for f in self._prd_data["features"] if f["id"] != event.feature_id
        ]
        self._record_change(f"Delete feature {event.feature_id}")
        self._refresh_ui()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "undo-btn":
            self.action_undo()
        elif event.button.id == "redo-btn":
            self.action_redo()
        elif event.button.id == "reload-btn":
            if self._prd_path:
                self.load_prd(self._prd_path)
                self.has_changes = False
                self._update_ui_state()

    # Actions
    def action_save(self) -> None:
        """Save the PRD to file."""
        if not self._prd_path:
            self._update_status("No file path set", error=True)
            return

        # Validate
        errors = self._validate()
        if errors:
            self._update_status(f"Validation failed: {errors[0]}", error=True)
            self.post_message(self.ValidationError(errors))
            return

        try:
            prd = self._dict_to_prd(self._prd_data)
            write_prd(self._prd_path, prd)
            self.has_changes = False
            self._update_ui_state()
            self._update_status(f"Saved: {self._prd_path.name}")
            self.post_message(self.PRDSaved(self._prd_path))
            if self._on_save:
                self._on_save(prd)
        except Exception as e:
            self._update_status(f"Save failed: {e}", error=True)

    def action_undo(self) -> None:
        """Undo the last change."""
        state = self._undo_manager.undo()
        if state:
            self._prd_data = copy.deepcopy(state.prd_dict)
            self._refresh_ui()
            self._update_status(f"Undo: {state.description}")
            self.has_changes = True
            self._update_ui_state()

    def action_redo(self) -> None:
        """Redo the last undone change."""
        state = self._undo_manager.redo()
        if state:
            self._prd_data = copy.deepcopy(state.prd_dict)
            self._refresh_ui()
            self._update_status(f"Redo: {state.description}")
            self.has_changes = True
            self._update_ui_state()

    def _validate(self) -> list[str]:
        """Validate the current PRD data.

        Returns:
            List of validation error messages.
        """
        errors = []

        # Project validation
        if not self._prd_data["project"].get("name", "").strip():
            errors.append("Project name is required")
        if not self._prd_data["project"].get("description", "").strip():
            errors.append("Project description is required")

        # Feature validation
        feature_ids = set()
        for f in self._prd_data["features"]:
            if not f.get("id", "").strip():
                errors.append("Feature ID is required")
            elif f["id"] in feature_ids:
                errors.append(f"Duplicate feature ID: {f['id']}")
            else:
                feature_ids.add(f["id"])

            if not f.get("description", "").strip():
                errors.append(f"Feature {f.get('id', '?')} description is required")

            # Validate dependencies exist
            for dep in f.get("dependencies", []):
                if dep not in feature_ids and dep not in {
                    g["id"] for g in self._prd_data["features"]
                }:
                    errors.append(f"Unknown dependency: {dep}")

        return errors
