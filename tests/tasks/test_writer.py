"""Tests for PRD.json writer and completion marking."""

import json
import pytest
from pathlib import Path

from ralph_agi.tasks import (
    Feature,
    PRD,
    PRDError,
    Project,
    load_prd,
    mark_complete,
    prd_to_dict,
    validate_prd_changes,
    write_prd,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_prd_data():
    """Sample PRD data for testing."""
    return {
        "project": {
            "name": "Test Project",
            "description": "A test project",
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
                "acceptance_criteria": ["AC 1"],
                "dependencies": [],
            },
            {
                "id": "feature-2",
                "description": "Second feature",
                "passes": False,
                "category": "ui",
                "priority": 1,
                "dependencies": ["feature-1"],
            },
            {
                "id": "feature-3",
                "description": "Already complete",
                "passes": True,
                "completed_at": "2026-01-01T00:00:00+00:00",
            },
        ],
    }


@pytest.fixture
def sample_prd_file(tmp_path, sample_prd_data):
    """Create a sample PRD.json file."""
    prd_file = tmp_path / "PRD.json"
    prd_file.write_text(json.dumps(sample_prd_data, indent=2))
    return prd_file


# =============================================================================
# prd_to_dict Tests
# =============================================================================


class TestPrdToDict:
    """Tests for prd_to_dict function."""

    def test_basic_conversion(self):
        """Convert simple PRD to dict."""
        project = Project(name="Test", description="Test project")
        feature = Feature(id="f1", description="Feature", passes=False)
        prd = PRD(project=project, features=(feature,))

        data = prd_to_dict(prd)

        assert data["project"]["name"] == "Test"
        assert data["project"]["description"] == "Test project"
        assert len(data["features"]) == 1
        assert data["features"][0]["id"] == "f1"

    def test_optional_fields_excluded_when_none(self):
        """Optional fields not included when None."""
        project = Project(name="Test", description="Test")
        feature = Feature(id="f1", description="Test", passes=False)
        prd = PRD(project=project, features=(feature,))

        data = prd_to_dict(prd)

        assert "version" not in data["project"]
        assert "category" not in data["features"][0]
        assert "priority" not in data["features"][0]
        assert "steps" not in data["features"][0]

    def test_optional_fields_included_when_set(self):
        """Optional fields included when set."""
        project = Project(name="Test", description="Test", version="1.0")
        feature = Feature(
            id="f1",
            description="Test",
            passes=True,
            category="functional",
            priority=1,
            steps=("Step 1",),
            acceptance_criteria=("AC 1",),
            dependencies=("f0",),
            completed_at="2026-01-01T00:00:00Z",
        )
        prd = PRD(project=project, features=(feature,))

        data = prd_to_dict(prd)

        assert data["project"]["version"] == "1.0"
        f = data["features"][0]
        assert f["category"] == "functional"
        assert f["priority"] == 1
        assert f["steps"] == ["Step 1"]
        assert f["acceptance_criteria"] == ["AC 1"]
        assert f["dependencies"] == ["f0"]
        assert f["completed_at"] == "2026-01-01T00:00:00Z"


# =============================================================================
# write_prd Tests
# =============================================================================


class TestWritePrd:
    """Tests for write_prd function."""

    def test_write_creates_file(self, tmp_path):
        """write_prd creates a new file."""
        prd_path = tmp_path / "PRD.json"
        project = Project(name="Test", description="Test")
        feature = Feature(id="f1", description="Test", passes=False)
        prd = PRD(project=project, features=(feature,))

        write_prd(prd_path, prd)

        assert prd_path.exists()

    def test_write_content_correct(self, tmp_path):
        """write_prd writes correct JSON content."""
        prd_path = tmp_path / "PRD.json"
        project = Project(name="Test Project", description="Description")
        feature = Feature(id="f1", description="Feature", passes=False)
        prd = PRD(project=project, features=(feature,))

        write_prd(prd_path, prd)

        data = json.loads(prd_path.read_text())
        assert data["project"]["name"] == "Test Project"
        assert data["features"][0]["id"] == "f1"

    def test_write_roundtrip(self, tmp_path):
        """Write then load returns equivalent PRD."""
        prd_path = tmp_path / "PRD.json"
        project = Project(name="Test", description="Test", version="1.0")
        features = (
            Feature(id="f1", description="F1", passes=False, priority=0),
            Feature(id="f2", description="F2", passes=True, completed_at="2026-01-01T00:00:00Z"),
        )
        original = PRD(project=project, features=features)

        write_prd(prd_path, original)
        loaded = load_prd(prd_path)

        assert loaded.project.name == original.project.name
        assert len(loaded.features) == len(original.features)
        assert loaded.features[0].id == original.features[0].id
        assert loaded.features[1].completed_at == original.features[1].completed_at

    def test_write_creates_parent_directories(self, tmp_path):
        """write_prd creates parent directories if needed."""
        prd_path = tmp_path / "subdir" / "another" / "PRD.json"
        project = Project(name="Test", description="Test")
        prd = PRD(project=project, features=())

        write_prd(prd_path, prd)

        assert prd_path.exists()

    def test_write_accepts_string_path(self, tmp_path):
        """write_prd accepts string path."""
        prd_path = str(tmp_path / "PRD.json")
        project = Project(name="Test", description="Test")
        prd = PRD(project=project, features=())

        write_prd(prd_path, prd)

        assert Path(prd_path).exists()

    def test_write_overwrites_existing(self, sample_prd_file):
        """write_prd overwrites existing file."""
        project = Project(name="New Project", description="New")
        prd = PRD(project=project, features=())

        write_prd(sample_prd_file, prd)

        data = json.loads(sample_prd_file.read_text())
        assert data["project"]["name"] == "New Project"

    def test_write_utf8_content(self, tmp_path):
        """write_prd handles UTF-8 content."""
        prd_path = tmp_path / "PRD.json"
        project = Project(name="テスト", description="Description 日本語")
        feature = Feature(id="f1", description="Feature 🎉", passes=False)
        prd = PRD(project=project, features=(feature,))

        write_prd(prd_path, prd)

        loaded = load_prd(prd_path)
        assert loaded.project.name == "テスト"
        assert "🎉" in loaded.features[0].description


# =============================================================================
# mark_complete Tests
# =============================================================================


class TestMarkComplete:
    """Tests for mark_complete function."""

    def test_mark_incomplete_feature(self, sample_prd_file):
        """mark_complete updates incomplete feature."""
        result = mark_complete(sample_prd_file, "feature-1")

        assert result.get_feature("feature-1").passes is True
        assert result.get_feature("feature-1").completed_at is not None

    def test_mark_complete_persists(self, sample_prd_file):
        """mark_complete persists changes to file."""
        mark_complete(sample_prd_file, "feature-1")

        # Reload and verify
        loaded = load_prd(sample_prd_file)
        assert loaded.get_feature("feature-1").passes is True

    def test_mark_complete_adds_timestamp(self, sample_prd_file):
        """mark_complete adds completed_at timestamp."""
        result = mark_complete(sample_prd_file, "feature-1")

        timestamp = result.get_feature("feature-1").completed_at
        assert timestamp is not None
        assert "2026" in timestamp  # Year should be correct
        assert "T" in timestamp  # ISO format

    def test_mark_complete_preserves_other_fields(self, sample_prd_file):
        """mark_complete preserves other feature fields."""
        result = mark_complete(sample_prd_file, "feature-1")

        feature = result.get_feature("feature-1")
        assert feature.description == "First feature"
        assert feature.category == "functional"
        assert feature.priority == 0
        assert feature.steps == ("Step 1", "Step 2")

    def test_mark_complete_preserves_other_features(self, sample_prd_file):
        """mark_complete doesn't modify other features."""
        result = mark_complete(sample_prd_file, "feature-1")

        feature2 = result.get_feature("feature-2")
        assert feature2.passes is False
        assert feature2.description == "Second feature"

    def test_mark_complete_feature_not_found(self, sample_prd_file):
        """mark_complete raises on unknown feature."""
        with pytest.raises(PRDError) as exc_info:
            mark_complete(sample_prd_file, "nonexistent")

        assert "not found" in str(exc_info.value)

    def test_mark_complete_already_complete(self, sample_prd_file):
        """mark_complete raises on already complete feature."""
        with pytest.raises(PRDError) as exc_info:
            mark_complete(sample_prd_file, "feature-3")

        assert "already complete" in str(exc_info.value)

    def test_mark_complete_accepts_string_path(self, sample_prd_file):
        """mark_complete accepts string path."""
        result = mark_complete(str(sample_prd_file), "feature-1")

        assert result.get_feature("feature-1").passes is True


# =============================================================================
# validate_prd_changes Tests
# =============================================================================


class TestValidatePrdChanges:
    """Tests for validate_prd_changes function."""

    def test_valid_completion_change(self):
        """Valid completion change passes validation."""
        project = Project(name="Test", description="Test")
        old_feature = Feature(id="f1", description="Test", passes=False)
        new_feature = Feature(
            id="f1",
            description="Test",
            passes=True,
            completed_at="2026-01-01T00:00:00Z",
        )
        old_prd = PRD(project=project, features=(old_feature,))
        new_prd = PRD(project=project, features=(new_feature,))

        # Should not raise
        validate_prd_changes(old_prd, new_prd, "f1")

    def test_project_changed_raises(self):
        """Changing project raises error."""
        old_project = Project(name="Test", description="Test")
        new_project = Project(name="Changed", description="Test")
        feature = Feature(id="f1", description="Test", passes=False)
        old_prd = PRD(project=old_project, features=(feature,))
        new_prd = PRD(project=new_project, features=(feature,))

        with pytest.raises(PRDError) as exc_info:
            validate_prd_changes(old_prd, new_prd, "f1")

        assert "Project metadata" in str(exc_info.value)

    def test_feature_count_changed_raises(self):
        """Changing feature count raises error."""
        project = Project(name="Test", description="Test")
        feature1 = Feature(id="f1", description="Test", passes=False)
        feature2 = Feature(id="f2", description="Test", passes=False)
        old_prd = PRD(project=project, features=(feature1,))
        new_prd = PRD(project=project, features=(feature1, feature2))

        with pytest.raises(PRDError) as exc_info:
            validate_prd_changes(old_prd, new_prd, "f1")

        assert "Number of features" in str(exc_info.value)

    def test_other_feature_changed_raises(self):
        """Changing non-target feature raises error."""
        project = Project(name="Test", description="Test")
        old_f1 = Feature(id="f1", description="Test", passes=False)
        old_f2 = Feature(id="f2", description="Original", passes=False)
        new_f1 = Feature(id="f1", description="Test", passes=True, completed_at="2026-01-01")
        new_f2 = Feature(id="f2", description="Changed", passes=False)
        old_prd = PRD(project=project, features=(old_f1, old_f2))
        new_prd = PRD(project=project, features=(new_f1, new_f2))

        with pytest.raises(PRDError) as exc_info:
            validate_prd_changes(old_prd, new_prd, "f1")

        assert "Unexpected changes" in str(exc_info.value)
        assert "f2" in str(exc_info.value)

    def test_feature_description_changed_raises(self):
        """Changing target feature description raises error."""
        project = Project(name="Test", description="Test")
        old_f = Feature(id="f1", description="Original", passes=False)
        new_f = Feature(id="f1", description="Changed", passes=True, completed_at="2026-01-01")
        old_prd = PRD(project=project, features=(old_f,))
        new_prd = PRD(project=project, features=(new_f,))

        with pytest.raises(PRDError) as exc_info:
            validate_prd_changes(old_prd, new_prd, "f1")

        assert "description was modified" in str(exc_info.value)

    def test_feature_priority_changed_raises(self):
        """Changing target feature priority raises error."""
        project = Project(name="Test", description="Test")
        old_f = Feature(id="f1", description="Test", passes=False, priority=0)
        new_f = Feature(id="f1", description="Test", passes=True, priority=1, completed_at="2026-01-01")
        old_prd = PRD(project=project, features=(old_f,))
        new_prd = PRD(project=project, features=(new_f,))

        with pytest.raises(PRDError) as exc_info:
            validate_prd_changes(old_prd, new_prd, "f1")

        assert "priority was modified" in str(exc_info.value)


# =============================================================================
# Atomic Write Tests
# =============================================================================


class TestAtomicWrite:
    """Tests for atomic write behavior."""

    def test_no_temp_file_on_success(self, tmp_path):
        """No temp file left after successful write."""
        prd_path = tmp_path / "PRD.json"
        project = Project(name="Test", description="Test")
        prd = PRD(project=project, features=())

        write_prd(prd_path, prd)

        # Check no .tmp files remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_original_preserved_on_second_write(self, sample_prd_file):
        """Second write overwrites cleanly."""
        # First, modify
        project = Project(name="First", description="First")
        prd1 = PRD(project=project, features=())
        write_prd(sample_prd_file, prd1)

        # Second write
        project2 = Project(name="Second", description="Second")
        prd2 = PRD(project=project2, features=())
        write_prd(sample_prd_file, prd2)

        # Verify final content
        data = json.loads(sample_prd_file.read_text())
        assert data["project"]["name"] == "Second"


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge cases and integration tests."""

    def test_mark_multiple_features_sequentially(self, sample_prd_file):
        """Can mark multiple features complete sequentially."""
        mark_complete(sample_prd_file, "feature-1")
        result = mark_complete(sample_prd_file, "feature-2")

        assert result.get_feature("feature-1").passes is True
        assert result.get_feature("feature-2").passes is True

    def test_write_empty_features(self, tmp_path):
        """Can write PRD with no features."""
        prd_path = tmp_path / "PRD.json"
        project = Project(name="Test", description="Test")
        prd = PRD(project=project, features=())

        write_prd(prd_path, prd)

        loaded = load_prd(prd_path)
        assert len(loaded.features) == 0

    def test_mark_complete_minimal_feature(self, tmp_path):
        """mark_complete works with minimal feature."""
        prd_path = tmp_path / "PRD.json"
        data = {
            "project": {"name": "Test", "description": "Test"},
            "features": [{"id": "f1", "description": "Test", "passes": False}],
        }
        prd_path.write_text(json.dumps(data))

        result = mark_complete(prd_path, "f1")

        assert result.get_feature("f1").passes is True
        assert result.get_feature("f1").completed_at is not None
