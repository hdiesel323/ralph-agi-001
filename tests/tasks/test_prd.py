"""Tests for PRD.json parser."""

import json
import pytest
from pathlib import Path

from ralph_agi.tasks import (
    Feature,
    PRD,
    PRDError,
    Project,
    load_prd,
    parse_prd,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def valid_prd_data():
    """A valid PRD data structure."""
    return {
        "project": {
            "name": "Test Project",
            "description": "A test project for unit tests",
            "version": "1.0.0",
        },
        "features": [
            {
                "id": "feature-1",
                "description": "First feature",
                "passes": False,
                "category": "functional",
                "priority": 0,
                "steps": ["Step 1", "Step 2"],
                "acceptance_criteria": ["AC 1", "AC 2"],
                "dependencies": [],
            },
            {
                "id": "feature-2",
                "description": "Second feature",
                "passes": True,
                "category": "ui",
                "priority": 1,
                "dependencies": ["feature-1"],
                "completed_at": "2026-01-11T10:00:00Z",
            },
        ],
    }


@pytest.fixture
def minimal_prd_data():
    """A minimal valid PRD with only required fields."""
    return {
        "project": {
            "name": "Minimal Project",
            "description": "Minimal description",
        },
        "features": [
            {
                "id": "min-feature",
                "description": "Minimal feature",
                "passes": False,
            },
        ],
    }


@pytest.fixture
def valid_prd_file(tmp_path, valid_prd_data):
    """Create a valid PRD.json file."""
    prd_file = tmp_path / "PRD.json"
    prd_file.write_text(json.dumps(valid_prd_data, indent=2))
    return prd_file


@pytest.fixture
def minimal_prd_file(tmp_path, minimal_prd_data):
    """Create a minimal PRD.json file."""
    prd_file = tmp_path / "PRD.json"
    prd_file.write_text(json.dumps(minimal_prd_data, indent=2))
    return prd_file


# =============================================================================
# Project Dataclass Tests
# =============================================================================


class TestProject:
    """Tests for the Project dataclass."""

    def test_project_required_fields(self):
        """Project requires name and description."""
        project = Project(name="Test", description="Test description")
        assert project.name == "Test"
        assert project.description == "Test description"
        assert project.version is None

    def test_project_with_version(self):
        """Project accepts optional version."""
        project = Project(name="Test", description="Test description", version="1.0.0")
        assert project.version == "1.0.0"

    def test_project_is_immutable(self):
        """Project is frozen (immutable)."""
        project = Project(name="Test", description="Test description")
        with pytest.raises(AttributeError):
            project.name = "Changed"


# =============================================================================
# Feature Dataclass Tests
# =============================================================================


class TestFeature:
    """Tests for the Feature dataclass."""

    def test_feature_required_fields(self):
        """Feature requires id, description, and passes."""
        feature = Feature(id="f1", description="Test feature", passes=False)
        assert feature.id == "f1"
        assert feature.description == "Test feature"
        assert feature.passes is False

    def test_feature_optional_fields_default(self):
        """Optional fields have sensible defaults."""
        feature = Feature(id="f1", description="Test", passes=False)
        assert feature.category is None
        assert feature.priority is None
        assert feature.steps == ()
        assert feature.acceptance_criteria == ()
        assert feature.dependencies == ()
        assert feature.completed_at is None

    def test_feature_is_ready(self):
        """is_ready returns True when passes=False."""
        incomplete = Feature(id="f1", description="Test", passes=False)
        complete = Feature(id="f2", description="Test", passes=True)
        assert incomplete.is_ready is True
        assert complete.is_ready is False

    def test_feature_priority_label(self):
        """priority_label returns correct format."""
        p0 = Feature(id="f1", description="Test", passes=False, priority=0)
        p2 = Feature(id="f2", description="Test", passes=False, priority=2)
        no_priority = Feature(id="f3", description="Test", passes=False)

        assert p0.priority_label == "P0"
        assert p2.priority_label == "P2"
        assert no_priority.priority_label == "P4"  # Default to lowest

    def test_feature_is_immutable(self):
        """Feature is frozen (immutable)."""
        feature = Feature(id="f1", description="Test", passes=False)
        with pytest.raises(AttributeError):
            feature.passes = True


# =============================================================================
# PRD Dataclass Tests
# =============================================================================


class TestPRD:
    """Tests for the PRD dataclass."""

    def test_prd_creation(self):
        """PRD holds project and features."""
        project = Project(name="Test", description="Test description")
        features = (Feature(id="f1", description="Test", passes=False),)
        prd = PRD(project=project, features=features)

        assert prd.project.name == "Test"
        assert len(prd.features) == 1

    def test_get_feature_found(self):
        """get_feature returns feature by ID."""
        project = Project(name="Test", description="Test")
        features = (
            Feature(id="f1", description="First", passes=False),
            Feature(id="f2", description="Second", passes=True),
        )
        prd = PRD(project=project, features=features)

        feature = prd.get_feature("f2")
        assert feature is not None
        assert feature.description == "Second"

    def test_get_feature_not_found(self):
        """get_feature returns None for unknown ID."""
        project = Project(name="Test", description="Test")
        features = (Feature(id="f1", description="First", passes=False),)
        prd = PRD(project=project, features=features)

        assert prd.get_feature("unknown") is None

    def test_get_incomplete_features(self):
        """get_incomplete_features returns features where passes=False."""
        project = Project(name="Test", description="Test")
        features = (
            Feature(id="f1", description="First", passes=False),
            Feature(id="f2", description="Second", passes=True),
            Feature(id="f3", description="Third", passes=False),
        )
        prd = PRD(project=project, features=features)

        incomplete = prd.get_incomplete_features()
        assert len(incomplete) == 2
        assert all(not f.passes for f in incomplete)

    def test_get_complete_features(self):
        """get_complete_features returns features where passes=True."""
        project = Project(name="Test", description="Test")
        features = (
            Feature(id="f1", description="First", passes=False),
            Feature(id="f2", description="Second", passes=True),
        )
        prd = PRD(project=project, features=features)

        complete = prd.get_complete_features()
        assert len(complete) == 1
        assert complete[0].id == "f2"

    def test_is_complete_all_done(self):
        """is_complete returns True when all features pass."""
        project = Project(name="Test", description="Test")
        features = (
            Feature(id="f1", description="First", passes=True),
            Feature(id="f2", description="Second", passes=True),
        )
        prd = PRD(project=project, features=features)

        assert prd.is_complete is True

    def test_is_complete_not_done(self):
        """is_complete returns False when any feature doesn't pass."""
        project = Project(name="Test", description="Test")
        features = (
            Feature(id="f1", description="First", passes=True),
            Feature(id="f2", description="Second", passes=False),
        )
        prd = PRD(project=project, features=features)

        assert prd.is_complete is False

    def test_completion_percentage(self):
        """completion_percentage calculates correctly."""
        project = Project(name="Test", description="Test")
        features = (
            Feature(id="f1", description="First", passes=True),
            Feature(id="f2", description="Second", passes=True),
            Feature(id="f3", description="Third", passes=False),
            Feature(id="f4", description="Fourth", passes=False),
        )
        prd = PRD(project=project, features=features)

        assert prd.completion_percentage == 50.0

    def test_completion_percentage_empty(self):
        """completion_percentage returns 100 for empty features."""
        project = Project(name="Test", description="Test")
        prd = PRD(project=project, features=())

        assert prd.completion_percentage == 100.0


# =============================================================================
# PRDError Tests
# =============================================================================


class TestPRDError:
    """Tests for the PRDError exception."""

    def test_error_message_only(self):
        """PRDError with just message."""
        error = PRDError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.path is None
        assert error.line is None

    def test_error_with_path(self):
        """PRDError with path."""
        error = PRDError("Missing field", path="features[0].id")
        assert str(error) == "Missing field at features[0].id"
        assert error.path == "features[0].id"

    def test_error_with_line(self):
        """PRDError with line number."""
        error = PRDError("Invalid JSON", line=42)
        assert str(error) == "Invalid JSON (line 42)"
        assert error.line == 42

    def test_error_with_path_and_line(self):
        """PRDError with both path and line."""
        error = PRDError("Type error", path="project.name", line=5)
        assert str(error) == "Type error at project.name (line 5)"


# =============================================================================
# parse_prd Tests
# =============================================================================


class TestParsePRD:
    """Tests for the parse_prd function."""

    def test_parse_valid_prd(self, valid_prd_data):
        """parse_prd successfully parses valid data."""
        prd = parse_prd(valid_prd_data)

        assert prd.project.name == "Test Project"
        assert prd.project.version == "1.0.0"
        assert len(prd.features) == 2
        assert prd.features[0].id == "feature-1"
        assert prd.features[0].priority == 0
        assert prd.features[0].steps == ("Step 1", "Step 2")

    def test_parse_minimal_prd(self, minimal_prd_data):
        """parse_prd handles minimal required fields."""
        prd = parse_prd(minimal_prd_data)

        assert prd.project.name == "Minimal Project"
        assert prd.project.version is None
        assert len(prd.features) == 1
        assert prd.features[0].priority is None

    def test_parse_not_dict(self):
        """parse_prd rejects non-dict input."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd([])
        assert "must be a JSON object" in str(exc_info.value)

    def test_parse_missing_project(self):
        """parse_prd rejects missing project."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({"features": []})
        assert "Missing required field 'project'" in str(exc_info.value)

    def test_parse_missing_features(self):
        """parse_prd rejects missing features."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({"project": {"name": "Test", "description": "Test"}})
        assert "Missing required field 'features'" in str(exc_info.value)

    def test_parse_features_not_array(self):
        """parse_prd rejects non-array features."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test", "description": "Test"},
                "features": "not an array",
            })
        assert "'features' must be an array" in str(exc_info.value)


# =============================================================================
# Project Validation Tests
# =============================================================================


class TestProjectValidation:
    """Tests for project field validation."""

    def test_project_not_object(self):
        """project must be an object."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({"project": "string", "features": []})
        assert "'project' must be an object" in str(exc_info.value)

    def test_project_missing_name(self):
        """project.name is required."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"description": "Test"},
                "features": [],
            })
        assert "Missing required field 'name'" in str(exc_info.value)
        assert "project.name" in str(exc_info.value)

    def test_project_name_not_string(self):
        """project.name must be a string."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": 123, "description": "Test"},
                "features": [],
            })
        assert "'name' must be a string" in str(exc_info.value)

    def test_project_name_empty(self):
        """project.name cannot be empty."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "  ", "description": "Test"},
                "features": [],
            })
        assert "'name' cannot be empty" in str(exc_info.value)

    def test_project_missing_description(self):
        """project.description is required."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test"},
                "features": [],
            })
        assert "Missing required field 'description'" in str(exc_info.value)

    def test_project_version_not_string(self):
        """project.version must be a string if present."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test", "description": "Test", "version": 123},
                "features": [],
            })
        assert "'version' must be a string" in str(exc_info.value)


# =============================================================================
# Feature Validation Tests
# =============================================================================


class TestFeatureValidation:
    """Tests for feature field validation."""

    def test_feature_not_object(self):
        """feature must be an object."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test", "description": "Test"},
                "features": ["not an object"],
            })
        assert "Feature must be an object" in str(exc_info.value)
        assert "features[0]" in str(exc_info.value)

    def test_feature_missing_id(self):
        """feature.id is required."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test", "description": "Test"},
                "features": [{"description": "Test", "passes": False}],
            })
        assert "Missing required field 'id'" in str(exc_info.value)

    def test_feature_id_empty(self):
        """feature.id cannot be empty."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test", "description": "Test"},
                "features": [{"id": "", "description": "Test", "passes": False}],
            })
        assert "'id' cannot be empty" in str(exc_info.value)

    def test_feature_missing_description(self):
        """feature.description is required."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test", "description": "Test"},
                "features": [{"id": "f1", "passes": False}],
            })
        assert "Missing required field 'description'" in str(exc_info.value)

    def test_feature_missing_passes(self):
        """feature.passes is required."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test", "description": "Test"},
                "features": [{"id": "f1", "description": "Test"}],
            })
        assert "Missing required field 'passes'" in str(exc_info.value)

    def test_feature_passes_not_boolean(self):
        """feature.passes must be a boolean."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test", "description": "Test"},
                "features": [{"id": "f1", "description": "Test", "passes": "false"}],
            })
        assert "'passes' must be a boolean" in str(exc_info.value)

    def test_feature_invalid_category(self):
        """feature.category must be valid."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test", "description": "Test"},
                "features": [{
                    "id": "f1",
                    "description": "Test",
                    "passes": False,
                    "category": "invalid",
                }],
            })
        assert "Invalid category 'invalid'" in str(exc_info.value)

    def test_feature_priority_not_int(self):
        """feature.priority must be an integer."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test", "description": "Test"},
                "features": [{
                    "id": "f1",
                    "description": "Test",
                    "passes": False,
                    "priority": "high",
                }],
            })
        assert "'priority' must be an integer" in str(exc_info.value)

    def test_feature_priority_out_of_range(self):
        """feature.priority must be 0-4."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test", "description": "Test"},
                "features": [{
                    "id": "f1",
                    "description": "Test",
                    "passes": False,
                    "priority": 5,
                }],
            })
        assert "must be between 0 and 4" in str(exc_info.value)

    def test_feature_steps_not_array(self):
        """feature.steps must be an array."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test", "description": "Test"},
                "features": [{
                    "id": "f1",
                    "description": "Test",
                    "passes": False,
                    "steps": "not an array",
                }],
            })
        assert "'steps' must be an array" in str(exc_info.value)

    def test_feature_steps_item_not_string(self):
        """feature.steps items must be strings."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test", "description": "Test"},
                "features": [{
                    "id": "f1",
                    "description": "Test",
                    "passes": False,
                    "steps": ["Step 1", 123],
                }],
            })
        assert "'steps[1]' must be a string" in str(exc_info.value)

    def test_feature_dependencies_validated(self):
        """feature.dependencies is validated as string array."""
        with pytest.raises(PRDError) as exc_info:
            parse_prd({
                "project": {"name": "Test", "description": "Test"},
                "features": [{
                    "id": "f1",
                    "description": "Test",
                    "passes": False,
                    "dependencies": [123],
                }],
            })
        assert "'dependencies[0]' must be a string" in str(exc_info.value)


# =============================================================================
# load_prd Tests
# =============================================================================


class TestLoadPRD:
    """Tests for the load_prd function."""

    def test_load_valid_file(self, valid_prd_file):
        """load_prd loads valid PRD file."""
        prd = load_prd(valid_prd_file)

        assert prd.project.name == "Test Project"
        assert len(prd.features) == 2

    def test_load_minimal_file(self, minimal_prd_file):
        """load_prd loads minimal PRD file."""
        prd = load_prd(minimal_prd_file)

        assert prd.project.name == "Minimal Project"

    def test_load_accepts_path_string(self, valid_prd_file):
        """load_prd accepts string path."""
        prd = load_prd(str(valid_prd_file))
        assert prd.project.name == "Test Project"

    def test_load_file_not_found(self):
        """load_prd raises on missing file."""
        with pytest.raises(PRDError) as exc_info:
            load_prd("/nonexistent/PRD.json")
        assert "PRD file not found" in str(exc_info.value)

    def test_load_invalid_json(self, tmp_path):
        """load_prd raises on invalid JSON."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid json")

        with pytest.raises(PRDError) as exc_info:
            load_prd(bad_file)
        assert "Invalid JSON" in str(exc_info.value)
        assert exc_info.value.line is not None

    def test_load_utf8_content(self, tmp_path):
        """load_prd handles UTF-8 content."""
        prd_file = tmp_path / "PRD.json"
        prd_file.write_text(json.dumps({
            "project": {"name": "Test Project", "description": "Unicode: 日本語"},
            "features": [{"id": "f1", "description": "Feature: émoji 🎉", "passes": False}],
        }), encoding="utf-8")

        prd = load_prd(prd_file)
        assert "日本語" in prd.project.description
        assert "🎉" in prd.features[0].description


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================


class TestEdgeCases:
    """Edge cases and integration tests."""

    def test_many_features(self):
        """PRD can handle many features."""
        data = {
            "project": {"name": "Test", "description": "Test"},
            "features": [
                {"id": f"feature-{i}", "description": f"Feature {i}", "passes": i % 2 == 0}
                for i in range(100)
            ],
        }
        prd = parse_prd(data)

        assert len(prd.features) == 100
        assert prd.completion_percentage == 50.0

    def test_deep_dependencies(self):
        """Features can have multiple dependencies."""
        data = {
            "project": {"name": "Test", "description": "Test"},
            "features": [
                {"id": "f1", "description": "F1", "passes": True},
                {"id": "f2", "description": "F2", "passes": True, "dependencies": ["f1"]},
                {"id": "f3", "description": "F3", "passes": False, "dependencies": ["f1", "f2"]},
            ],
        }
        prd = parse_prd(data)

        assert prd.features[2].dependencies == ("f1", "f2")

    def test_all_categories(self):
        """All valid categories are accepted."""
        categories = ["functional", "ui", "performance", "security", "integration"]
        features = [
            {"id": f"f{i}", "description": f"F{i}", "passes": False, "category": cat}
            for i, cat in enumerate(categories)
        ]
        data = {
            "project": {"name": "Test", "description": "Test"},
            "features": features,
        }
        prd = parse_prd(data)

        assert len(prd.features) == 5
        for i, cat in enumerate(categories):
            assert prd.features[i].category == cat

    def test_feature_error_index_in_message(self):
        """Error messages include feature index."""
        data = {
            "project": {"name": "Test", "description": "Test"},
            "features": [
                {"id": "f1", "description": "F1", "passes": False},
                {"id": "f2", "description": "F2", "passes": False},
                {"description": "F3 missing id", "passes": False},
            ],
        }
        with pytest.raises(PRDError) as exc_info:
            parse_prd(data)
        assert "features[2]" in str(exc_info.value)
