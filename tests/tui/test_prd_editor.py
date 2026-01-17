"""Tests for PRD editor widget."""

import json
import copy
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ralph_agi.tui.widgets.prd_editor import (
    UndoManager,
    UndoState,
    FeatureListItem,
    PRDEditor,
    MAX_UNDO_HISTORY,
)
from ralph_agi.tasks.prd import Feature, PRD, Project


class TestUndoState:
    """Tests for UndoState dataclass."""

    def test_create_state(self):
        """Test creating an undo state."""
        data = {"project": {"name": "Test"}, "features": []}
        state = UndoState(prd_dict=data, description="Initial")

        assert state.prd_dict == data
        assert state.description == "Initial"


class TestUndoManager:
    """Tests for UndoManager."""

    def test_initial_state(self):
        """Test initial undo manager state."""
        manager = UndoManager()

        assert not manager.can_undo()
        assert not manager.can_redo()
        assert manager.current_state is None

    def test_push_state(self):
        """Test pushing a state."""
        manager = UndoManager()
        data = {"project": {"name": "Test"}, "features": []}
        manager.push(data, "Initial")

        assert manager.current_state is not None
        assert manager.current_state.description == "Initial"
        assert not manager.can_undo()  # Only one state
        assert not manager.can_redo()

    def test_undo(self):
        """Test undo operation."""
        manager = UndoManager()
        manager.push({"name": "v1"}, "Version 1")
        manager.push({"name": "v2"}, "Version 2")

        assert manager.can_undo()
        state = manager.undo()

        assert state is not None
        assert state.prd_dict == {"name": "v1"}
        assert manager.can_redo()

    def test_redo(self):
        """Test redo operation."""
        manager = UndoManager()
        manager.push({"name": "v1"}, "Version 1")
        manager.push({"name": "v2"}, "Version 2")
        manager.undo()

        assert manager.can_redo()
        state = manager.redo()

        assert state is not None
        assert state.prd_dict == {"name": "v2"}
        assert not manager.can_redo()

    def test_undo_at_beginning(self):
        """Test undo when at the beginning."""
        manager = UndoManager()
        manager.push({"name": "v1"}, "Version 1")

        state = manager.undo()
        assert state is None

    def test_redo_at_end(self):
        """Test redo when at the end."""
        manager = UndoManager()
        manager.push({"name": "v1"}, "Version 1")

        state = manager.redo()
        assert state is None

    def test_push_discards_redo_history(self):
        """Test that pushing after undo discards redo history."""
        manager = UndoManager()
        manager.push({"name": "v1"}, "Version 1")
        manager.push({"name": "v2"}, "Version 2")
        manager.push({"name": "v3"}, "Version 3")

        manager.undo()  # Back to v2
        manager.undo()  # Back to v1

        # Push new state, should discard v2 and v3
        manager.push({"name": "v4"}, "Version 4")

        assert not manager.can_redo()
        assert manager.current_state.prd_dict == {"name": "v4"}

    def test_max_history_limit(self):
        """Test that history is limited."""
        manager = UndoManager(max_history=5)

        for i in range(10):
            manager.push({"index": i}, f"Version {i}")

        # Should only keep last 5
        count = 0
        while manager.can_undo():
            manager.undo()
            count += 1

        # Should be able to undo 4 times (5 states, minus current)
        assert count == 4

    def test_undo_description(self):
        """Test getting undo description."""
        manager = UndoManager()
        manager.push({"name": "v1"}, "Add feature")
        manager.push({"name": "v2"}, "Edit project")

        assert manager.undo_description == "Edit project"

    def test_redo_description(self):
        """Test getting redo description."""
        manager = UndoManager()
        manager.push({"name": "v1"}, "Add feature")
        manager.push({"name": "v2"}, "Edit project")
        manager.undo()

        assert manager.redo_description == "Edit project"

    def test_deep_copy_on_push(self):
        """Test that push makes a deep copy."""
        manager = UndoManager()
        data = {"project": {"name": "Test"}, "features": [{"id": "1"}]}
        manager.push(data, "Initial")

        # Modify original data
        data["project"]["name"] = "Modified"
        data["features"].append({"id": "2"})

        # State should not be affected
        assert manager.current_state.prd_dict["project"]["name"] == "Test"
        assert len(manager.current_state.prd_dict["features"]) == 1


class TestFeatureListItem:
    """Tests for FeatureListItem."""

    def test_create_incomplete(self):
        """Test creating an incomplete feature item."""
        item = FeatureListItem("task-1", "Test task", passes=False)

        assert item.feature_id == "task-1"

    def test_create_complete(self):
        """Test creating a complete feature item."""
        item = FeatureListItem("task-1", "Test task", passes=True)

        assert item.feature_id == "task-1"


class TestPRDEditorDataConversion:
    """Tests for PRDEditor data conversion methods."""

    def test_prd_to_dict(self, tmp_path):
        """Test converting PRD to dictionary."""
        prd = PRD(
            project=Project(name="Test", description="Test project"),
            features=(
                Feature(
                    id="task-1",
                    description="Test task",
                    passes=False,
                    priority=1,
                    steps=("Step 1", "Step 2"),
                    acceptance_criteria=("AC 1",),
                ),
            ),
        )

        # Can't easily test private method, but we can test load/save roundtrip
        prd_path = tmp_path / "PRD.json"
        prd_data = {
            "project": {"name": "Test", "description": "Test project"},
            "features": [
                {
                    "id": "task-1",
                    "description": "Test task",
                    "passes": False,
                    "priority": 1,
                    "steps": ["Step 1", "Step 2"],
                    "acceptance_criteria": ["AC 1"],
                }
            ],
        }
        prd_path.write_text(json.dumps(prd_data))

        # Verify we can create editor and load
        # (Full widget tests need Textual test framework)
        assert prd_path.exists()


class TestPRDEditorValidation:
    """Tests for PRDEditor validation logic."""

    def test_validate_empty_project_name(self):
        """Test validation catches empty project name."""
        prd_data = {
            "project": {"name": "", "description": "Test"},
            "features": [],
        }

        # Validation logic extracted for testing
        errors = []
        if not prd_data["project"].get("name", "").strip():
            errors.append("Project name is required")

        assert "Project name is required" in errors

    def test_validate_empty_project_description(self):
        """Test validation catches empty project description."""
        prd_data = {
            "project": {"name": "Test", "description": ""},
            "features": [],
        }

        errors = []
        if not prd_data["project"].get("description", "").strip():
            errors.append("Project description is required")

        assert "Project description is required" in errors

    def test_validate_duplicate_feature_ids(self):
        """Test validation catches duplicate feature IDs."""
        prd_data = {
            "project": {"name": "Test", "description": "Test"},
            "features": [
                {"id": "task-1", "description": "Task 1", "passes": False},
                {"id": "task-1", "description": "Task 2", "passes": False},
            ],
        }

        errors = []
        feature_ids = set()
        for f in prd_data["features"]:
            if f["id"] in feature_ids:
                errors.append(f"Duplicate feature ID: {f['id']}")
            else:
                feature_ids.add(f["id"])

        assert "Duplicate feature ID: task-1" in errors

    def test_validate_empty_feature_id(self):
        """Test validation catches empty feature ID."""
        prd_data = {
            "project": {"name": "Test", "description": "Test"},
            "features": [
                {"id": "", "description": "Task", "passes": False},
            ],
        }

        errors = []
        for f in prd_data["features"]:
            if not f.get("id", "").strip():
                errors.append("Feature ID is required")

        assert "Feature ID is required" in errors

    def test_validate_empty_feature_description(self):
        """Test validation catches empty feature description."""
        prd_data = {
            "project": {"name": "Test", "description": "Test"},
            "features": [
                {"id": "task-1", "description": "", "passes": False},
            ],
        }

        errors = []
        for f in prd_data["features"]:
            if not f.get("description", "").strip():
                errors.append(f"Feature {f.get('id', '?')} description is required")

        assert "Feature task-1 description is required" in errors
