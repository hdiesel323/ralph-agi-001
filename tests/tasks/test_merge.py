"""Tests for confidence-based auto-merge."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ralph_agi.tasks.merge import (
    DEFAULT_AUDIT_LOG,
    AuditEntry,
    AutoMerger,
    CheckResult,
    CheckStatus,
    ConfidenceScore,
    MergeConfig,
    MergeDecision,
    MergeResult,
    MergeThreshold,
    format_confidence_score,
)


class TestMergeThreshold:
    """Tests for MergeThreshold enum."""

    def test_all_thresholds(self):
        """Test all threshold values exist."""
        assert MergeThreshold.ALWAYS_ASK.value == "always_ask"
        assert MergeThreshold.ASK_ON_WARNINGS.value == "ask_on_warnings"
        assert MergeThreshold.FULL_AUTO.value == "full_auto"


class TestCheckStatus:
    """Tests for CheckStatus enum."""

    def test_all_statuses(self):
        """Test all status values exist."""
        assert CheckStatus.PASS.value == "pass"
        assert CheckStatus.FAIL.value == "fail"
        assert CheckStatus.PENDING.value == "pending"
        assert CheckStatus.SKIPPED.value == "skipped"
        assert CheckStatus.UNKNOWN.value == "unknown"


class TestMergeDecision:
    """Tests for MergeDecision enum."""

    def test_all_decisions(self):
        """Test all decision values exist."""
        assert MergeDecision.MERGE.value == "merge"
        assert MergeDecision.ASK_HUMAN.value == "ask_human"
        assert MergeDecision.BLOCK.value == "block"


class TestMergeConfig:
    """Tests for MergeConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = MergeConfig()
        assert config.enabled is True
        assert config.threshold == MergeThreshold.ASK_ON_WARNINGS
        assert config.require_tests_pass is True
        assert config.require_ci_pass is True
        assert config.require_no_conflicts is True
        assert config.require_task_complete is True
        assert config.squash_merge is True
        assert config.delete_branch is True
        assert config.audit_log_path is None
        assert "main" in config.protected_branches
        assert "master" in config.protected_branches

    def test_custom_values(self):
        """Test custom configuration values."""
        config = MergeConfig(
            enabled=False,
            threshold=MergeThreshold.FULL_AUTO,
            require_tests_pass=False,
            squash_merge=False,
            protected_branches=("production",),
        )
        assert config.enabled is False
        assert config.threshold == MergeThreshold.FULL_AUTO
        assert config.require_tests_pass is False
        assert config.squash_merge is False
        assert config.protected_branches == ("production",)


class TestCheckResult:
    """Tests for CheckResult."""

    def test_basic_result(self):
        """Test basic check result."""
        result = CheckResult(
            name="tests",
            status=CheckStatus.PASS,
            message="All tests pass",
        )
        assert result.name == "tests"
        assert result.status == CheckStatus.PASS
        assert result.message == "All tests pass"
        assert result.required is True
        assert result.details is None

    def test_optional_result(self):
        """Test optional check result."""
        result = CheckResult(
            name="lint",
            status=CheckStatus.SKIPPED,
            message="No linter configured",
            required=False,
            details={"reason": "skipped"},
        )
        assert result.required is False
        assert result.details == {"reason": "skipped"}


class TestConfidenceScore:
    """Tests for ConfidenceScore."""

    def test_basic_score(self):
        """Test basic confidence score."""
        score = ConfidenceScore(score=0.95)
        assert score.score == 0.95
        assert score.checks == []
        assert score.warnings == []
        assert score.blockers == []
        assert score.recommendation == MergeDecision.ASK_HUMAN

    def test_is_high_confidence_true(self):
        """Test high confidence detection - true case."""
        score = ConfidenceScore(score=0.95, blockers=[])
        assert score.is_high_confidence is True

    def test_is_high_confidence_false_low_score(self):
        """Test high confidence detection - low score."""
        score = ConfidenceScore(score=0.85, blockers=[])
        assert score.is_high_confidence is False

    def test_is_high_confidence_false_has_blockers(self):
        """Test high confidence detection - has blockers."""
        score = ConfidenceScore(score=0.95, blockers=["CI failing"])
        assert score.is_high_confidence is False

    def test_is_blocked(self):
        """Test blocked detection."""
        score_blocked = ConfidenceScore(score=0.0, blockers=["Conflicts"])
        score_not_blocked = ConfidenceScore(score=0.95, blockers=[])

        assert score_blocked.is_blocked is True
        assert score_not_blocked.is_blocked is False

    def test_has_warnings(self):
        """Test warnings detection."""
        score_warnings = ConfidenceScore(score=0.8, warnings=["Tests pending"])
        score_no_warnings = ConfidenceScore(score=0.95, warnings=[])

        assert score_warnings.has_warnings is True
        assert score_no_warnings.has_warnings is False

    def test_all_checks_pass_true(self):
        """Test all checks pass - true case."""
        score = ConfidenceScore(
            score=1.0,
            checks=[
                CheckResult("tests", CheckStatus.PASS, "OK", required=True),
                CheckResult("ci", CheckStatus.PASS, "OK", required=True),
                CheckResult("lint", CheckStatus.SKIPPED, "Skipped", required=False),
            ],
        )
        assert score.all_checks_pass is True

    def test_all_checks_pass_false(self):
        """Test all checks pass - false case."""
        score = ConfidenceScore(
            score=0.5,
            checks=[
                CheckResult("tests", CheckStatus.PASS, "OK", required=True),
                CheckResult("ci", CheckStatus.FAIL, "Failed", required=True),
            ],
        )
        assert score.all_checks_pass is False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        score = ConfidenceScore(
            score=0.85,
            checks=[
                CheckResult("tests", CheckStatus.PASS, "OK"),
            ],
            warnings=["Pending review"],
            blockers=[],
            recommendation=MergeDecision.ASK_HUMAN,
        )
        data = score.to_dict()

        assert data["score"] == 0.85
        assert len(data["checks"]) == 1
        assert data["checks"][0]["name"] == "tests"
        assert data["checks"][0]["status"] == "pass"
        assert data["warnings"] == ["Pending review"]
        assert data["blockers"] == []
        assert data["recommendation"] == "ask_human"


class TestMergeResult:
    """Tests for MergeResult."""

    def test_success_result(self):
        """Test successful merge result."""
        result = MergeResult(
            success=True,
            pr_number=123,
            merge_sha="abc123",
            method="squash",
            branch_deleted=True,
        )
        assert result.success is True
        assert result.pr_number == 123
        assert result.merge_sha == "abc123"
        assert result.method == "squash"
        assert result.branch_deleted is True
        assert result.error is None

    def test_failure_result(self):
        """Test failed merge result."""
        result = MergeResult(
            success=False,
            pr_number=123,
            error="Merge conflicts",
        )
        assert result.success is False
        assert result.pr_number == 123
        assert result.error == "Merge conflicts"


class TestAuditEntry:
    """Tests for AuditEntry."""

    def test_to_dict(self):
        """Test audit entry serialization."""
        confidence = ConfidenceScore(
            score=0.95,
            recommendation=MergeDecision.MERGE,
        )
        result = MergeResult(
            success=True,
            pr_number=123,
            merge_sha="abc123",
        )
        entry = AuditEntry(
            timestamp="2025-01-16T12:00:00Z",
            pr_number=123,
            pr_url="https://github.com/test/repo/pull/123",
            branch="feature/test",
            target_branch="main",
            task_id="task-1",
            confidence=confidence,
            decision=MergeDecision.MERGE,
            action_taken="merged",
            merged_by="auto",
            result=result,
            notes="Test merge",
        )
        data = entry.to_dict()

        assert data["timestamp"] == "2025-01-16T12:00:00Z"
        assert data["pr_number"] == 123
        assert data["pr_url"] == "https://github.com/test/repo/pull/123"
        assert data["branch"] == "feature/test"
        assert data["target_branch"] == "main"
        assert data["task_id"] == "task-1"
        assert data["confidence"]["score"] == 0.95
        assert data["decision"] == "merge"
        assert data["action_taken"] == "merged"
        assert data["merged_by"] == "auto"
        assert data["result"]["success"] is True
        assert data["result"]["merge_sha"] == "abc123"
        assert data["notes"] == "Test merge"

    def test_to_dict_no_result(self):
        """Test audit entry serialization without result."""
        confidence = ConfidenceScore(score=0.0, blockers=["Blocked"])
        entry = AuditEntry(
            timestamp="2025-01-16T12:00:00Z",
            pr_number=123,
            pr_url="https://github.com/test/repo/pull/123",
            branch="feature/test",
            target_branch="main",
            task_id=None,
            confidence=confidence,
            decision=MergeDecision.BLOCK,
            action_taken="blocked",
            merged_by="auto",
            result=None,
        )
        data = entry.to_dict()

        assert data["task_id"] is None
        assert data["result"] is None


class TestAutoMergerInit:
    """Tests for AutoMerger initialization."""

    def test_basic_init(self, tmp_path):
        """Test basic initialization."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path

        merger = AutoMerger(git_tools=mock_git)

        assert merger._git == mock_git
        assert merger.config.enabled is True
        assert merger._prd_path is None
        assert merger._audit_log_path == tmp_path / DEFAULT_AUDIT_LOG

    def test_custom_config(self, tmp_path):
        """Test initialization with custom config."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path

        config = MergeConfig(enabled=False, threshold=MergeThreshold.FULL_AUTO)
        merger = AutoMerger(git_tools=mock_git, config=config)

        assert merger.config.enabled is False
        assert merger.config.threshold == MergeThreshold.FULL_AUTO

    def test_custom_audit_log_path(self, tmp_path):
        """Test initialization with custom audit log path."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path

        audit_path = tmp_path / "custom-audit.jsonl"
        config = MergeConfig(audit_log_path=audit_path)
        merger = AutoMerger(git_tools=mock_git, config=config)

        assert merger._audit_log_path == audit_path


class TestAutoMergerEvaluatePR:
    """Tests for AutoMerger.evaluate_pr."""

    def test_no_pr_found(self, tmp_path):
        """Test evaluation when no PR found."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        mock_git.get_pr_status.return_value = None

        merger = AutoMerger(git_tools=mock_git)
        score = merger.evaluate_pr(pr_number=123)

        assert score.score == 0.0
        assert "No PR found" in score.blockers[0]
        assert score.recommendation == MergeDecision.BLOCK

    def test_pr_not_open(self, tmp_path):
        """Test evaluation when PR is not open."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        mock_git.get_pr_status.return_value = {
            "number": 123,
            "state": "MERGED",
            "mergeable": "UNKNOWN",
        }

        merger = AutoMerger(git_tools=mock_git)
        score = merger.evaluate_pr(pr_number=123)

        assert "PR is not open" in score.blockers[0]

    def test_merge_conflicts(self, tmp_path):
        """Test evaluation with merge conflicts."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        mock_git.get_pr_status.return_value = {
            "number": 123,
            "state": "OPEN",
            "mergeable": "CONFLICTING",
        }

        with patch("ralph_agi.tools.shell.ShellTools") as MockShell:
            mock_shell_instance = MagicMock()
            mock_shell_instance.execute.return_value = MagicMock(
                success=True, stdout="[]"
            )
            MockShell.return_value = mock_shell_instance

            merger = AutoMerger(git_tools=mock_git)
            score = merger.evaluate_pr(pr_number=123)

        assert any("conflicts" in b.lower() for b in score.blockers)
        assert any(
            c.name == "no_conflicts" and c.status == CheckStatus.FAIL
            for c in score.checks
        )

    def test_mergeable_pr(self, tmp_path):
        """Test evaluation with mergeable PR."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        mock_git.get_pr_status.return_value = {
            "number": 123,
            "state": "OPEN",
            "mergeable": "MERGEABLE",
        }

        with patch("ralph_agi.tools.shell.ShellTools") as MockShell:
            mock_shell_instance = MagicMock()
            # Return passing CI and tests
            mock_shell_instance.execute.return_value = MagicMock(
                success=True,
                stdout=json.dumps([
                    {"name": "tests", "state": "COMPLETED", "conclusion": "SUCCESS"},
                    {"name": "ci", "state": "COMPLETED", "conclusion": "SUCCESS"},
                ]),
            )
            MockShell.return_value = mock_shell_instance

            merger = AutoMerger(git_tools=mock_git)
            score = merger.evaluate_pr(pr_number=123)

        assert any(
            c.name == "no_conflicts" and c.status == CheckStatus.PASS
            for c in score.checks
        )
        assert score.score > 0


class TestAutoMergerCalculateScore:
    """Tests for AutoMerger._calculate_score."""

    def test_blockers_give_zero(self, tmp_path):
        """Test that blockers result in zero score."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        merger = AutoMerger(git_tools=mock_git)

        checks = [
            CheckResult("tests", CheckStatus.PASS, "OK"),
        ]
        score = merger._calculate_score(checks, [], ["Blocker!"])

        assert score == 0.0

    def test_all_pass_gives_high_score(self, tmp_path):
        """Test that all passing checks give high score."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        merger = AutoMerger(git_tools=mock_git)

        checks = [
            CheckResult("tests", CheckStatus.PASS, "OK", required=True),
            CheckResult("ci", CheckStatus.PASS, "OK", required=True),
        ]
        score = merger._calculate_score(checks, [], [])

        assert score == 1.0

    def test_pending_gives_partial_score(self, tmp_path):
        """Test that pending checks give partial score."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        merger = AutoMerger(git_tools=mock_git)

        checks = [
            CheckResult("tests", CheckStatus.PASS, "OK", required=True),
            CheckResult("ci", CheckStatus.PENDING, "Running", required=True),
        ]
        score = merger._calculate_score(checks, [], [])

        assert 0.5 < score < 1.0

    def test_warnings_reduce_score(self, tmp_path):
        """Test that warnings reduce score."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        merger = AutoMerger(git_tools=mock_git)

        checks = [
            CheckResult("tests", CheckStatus.PASS, "OK", required=True),
        ]
        score_no_warnings = merger._calculate_score(checks, [], [])
        score_with_warnings = merger._calculate_score(checks, ["Warning 1"], [])

        assert score_with_warnings < score_no_warnings

    def test_no_checks_gives_medium_score(self, tmp_path):
        """Test that no checks gives medium confidence."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        merger = AutoMerger(git_tools=mock_git)

        score = merger._calculate_score([], [], [])

        assert score == 0.5


class TestAutoMergerDetermineRecommendation:
    """Tests for AutoMerger._determine_recommendation."""

    def test_blockers_always_block(self, tmp_path):
        """Test that blockers always result in BLOCK."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        merger = AutoMerger(git_tools=mock_git)

        decision = merger._determine_recommendation(0.95, [], ["Blocker"])
        assert decision == MergeDecision.BLOCK

    def test_always_ask_threshold(self, tmp_path):
        """Test ALWAYS_ASK threshold always asks."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        config = MergeConfig(threshold=MergeThreshold.ALWAYS_ASK)
        merger = AutoMerger(git_tools=mock_git, config=config)

        decision = merger._determine_recommendation(1.0, [], [])
        assert decision == MergeDecision.ASK_HUMAN

    def test_full_auto_high_score(self, tmp_path):
        """Test FULL_AUTO merges with decent score."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        config = MergeConfig(threshold=MergeThreshold.FULL_AUTO)
        merger = AutoMerger(git_tools=mock_git, config=config)

        decision = merger._determine_recommendation(0.6, [], [])
        assert decision == MergeDecision.MERGE

    def test_full_auto_low_score(self, tmp_path):
        """Test FULL_AUTO asks for low score."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        config = MergeConfig(threshold=MergeThreshold.FULL_AUTO)
        merger = AutoMerger(git_tools=mock_git, config=config)

        decision = merger._determine_recommendation(0.3, [], [])
        assert decision == MergeDecision.ASK_HUMAN

    def test_ask_on_warnings_with_warnings(self, tmp_path):
        """Test ASK_ON_WARNINGS asks when warnings present."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        config = MergeConfig(threshold=MergeThreshold.ASK_ON_WARNINGS)
        merger = AutoMerger(git_tools=mock_git, config=config)

        decision = merger._determine_recommendation(0.95, ["Warning"], [])
        assert decision == MergeDecision.ASK_HUMAN

    def test_ask_on_warnings_high_score_no_warnings(self, tmp_path):
        """Test ASK_ON_WARNINGS merges with high score and no warnings."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        config = MergeConfig(threshold=MergeThreshold.ASK_ON_WARNINGS)
        merger = AutoMerger(git_tools=mock_git, config=config)

        decision = merger._determine_recommendation(0.95, [], [])
        assert decision == MergeDecision.MERGE


class TestAutoMergerMergePR:
    """Tests for AutoMerger.merge_pr."""

    def test_disabled_config(self, tmp_path):
        """Test merge fails when disabled."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        config = MergeConfig(enabled=False)
        merger = AutoMerger(git_tools=mock_git, config=config)

        result = merger.merge_pr(123)

        assert result.success is False
        assert "disabled" in result.error.lower()

    def test_blocked_pr_no_merge(self, tmp_path):
        """Test blocked PR is not merged."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        mock_git.get_pr_status.return_value = {
            "number": 123,
            "url": "https://github.com/test/pr/123",
            "headRefName": "feature",
            "baseRefName": "main",
        }

        merger = AutoMerger(git_tools=mock_git)
        confidence = ConfidenceScore(
            score=0.0,
            blockers=["Conflicts"],
            recommendation=MergeDecision.BLOCK,
        )
        result = merger.merge_pr(123, confidence=confidence)

        assert result.success is False
        assert "Blocked" in result.error

    def test_successful_merge(self, tmp_path):
        """Test successful merge execution."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        mock_git.get_pr_status.return_value = {
            "number": 123,
            "url": "https://github.com/test/pr/123",
            "headRefName": "feature",
            "baseRefName": "main",
        }

        with patch("ralph_agi.tools.shell.ShellTools") as MockShell:
            mock_shell_instance = MagicMock()
            mock_shell_instance.execute.return_value = MagicMock(
                success=True, stdout="", stderr=""
            )
            MockShell.return_value = mock_shell_instance

            merger = AutoMerger(git_tools=mock_git)
            confidence = ConfidenceScore(
                score=0.95,
                recommendation=MergeDecision.MERGE,
            )
            result = merger.merge_pr(123, confidence=confidence)

        assert result.success is True
        assert result.method == "squash"
        assert result.branch_deleted is True

    def test_merge_failure(self, tmp_path):
        """Test merge command failure."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        mock_git.get_pr_status.return_value = {
            "number": 123,
            "url": "https://github.com/test/pr/123",
            "headRefName": "feature",
            "baseRefName": "main",
        }

        with patch("ralph_agi.tools.shell.ShellTools") as MockShell:
            mock_shell_instance = MagicMock()
            mock_shell_instance.execute.return_value = MagicMock(
                success=False, stdout="", stderr="Permission denied"
            )
            MockShell.return_value = mock_shell_instance

            merger = AutoMerger(git_tools=mock_git)
            confidence = ConfidenceScore(
                score=0.95,
                recommendation=MergeDecision.MERGE,
            )
            result = merger.merge_pr(123, confidence=confidence)

        assert result.success is False
        assert "Permission denied" in result.error

    def test_force_merge_blocked(self, tmp_path):
        """Test force merge overrides block."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        mock_git.get_pr_status.return_value = {
            "number": 123,
            "url": "https://github.com/test/pr/123",
            "headRefName": "feature",
            "baseRefName": "main",
        }

        with patch("ralph_agi.tools.shell.ShellTools") as MockShell:
            mock_shell_instance = MagicMock()
            mock_shell_instance.execute.return_value = MagicMock(
                success=True, stdout="", stderr=""
            )
            MockShell.return_value = mock_shell_instance

            merger = AutoMerger(git_tools=mock_git)
            confidence = ConfidenceScore(
                score=0.0,
                blockers=["Blocked"],
                recommendation=MergeDecision.BLOCK,
            )
            result = merger.merge_pr(123, confidence=confidence, force=True)

        # Force should proceed with merge
        assert result.success is True


class TestAutoMergerAuditLog:
    """Tests for AutoMerger audit logging."""

    def test_audit_log_written(self, tmp_path):
        """Test audit log is written on merge."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        mock_git.get_pr_status.return_value = {
            "number": 123,
            "url": "https://github.com/test/pr/123",
            "headRefName": "feature",
            "baseRefName": "main",
        }

        with patch("ralph_agi.tools.shell.ShellTools") as MockShell:
            mock_shell_instance = MagicMock()
            mock_shell_instance.execute.return_value = MagicMock(
                success=True, stdout="", stderr=""
            )
            MockShell.return_value = mock_shell_instance

            merger = AutoMerger(git_tools=mock_git)
            confidence = ConfidenceScore(
                score=0.95,
                recommendation=MergeDecision.MERGE,
            )
            merger.merge_pr(123, confidence=confidence, task_id="task-1")

        # Check audit log was written
        audit_log_path = tmp_path / DEFAULT_AUDIT_LOG
        assert audit_log_path.exists()

        with open(audit_log_path) as f:
            entries = [json.loads(line) for line in f if line.strip()]

        assert len(entries) == 1
        assert entries[0]["pr_number"] == 123
        assert entries[0]["task_id"] == "task-1"
        assert entries[0]["action_taken"] == "merged"

    def test_get_audit_log_empty(self, tmp_path):
        """Test reading empty audit log."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        merger = AutoMerger(git_tools=mock_git)

        entries = merger.get_audit_log()
        assert entries == []

    def test_get_audit_log_with_entries(self, tmp_path):
        """Test reading audit log with entries."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path

        # Write some audit entries
        audit_path = tmp_path / DEFAULT_AUDIT_LOG
        with open(audit_path, "w") as f:
            for i in range(5):
                entry = {
                    "pr_number": i,
                    "timestamp": f"2025-01-0{i+1}T12:00:00Z",
                    "action_taken": "merged",
                }
                f.write(json.dumps(entry) + "\n")

        merger = AutoMerger(git_tools=mock_git)
        entries = merger.get_audit_log(limit=3)

        assert len(entries) == 3
        # Should return most recent
        assert entries[-1]["pr_number"] == 4


class TestFormatConfidenceScore:
    """Tests for format_confidence_score function."""

    def test_format_basic(self):
        """Test basic formatting."""
        score = ConfidenceScore(
            score=0.95,
            recommendation=MergeDecision.MERGE,
        )
        output = format_confidence_score(score)

        assert "95%" in output
        assert "merge" in output.lower()

    def test_format_with_checks(self):
        """Test formatting with checks."""
        score = ConfidenceScore(
            score=0.85,
            checks=[
                CheckResult("tests", CheckStatus.PASS, "All pass"),
                CheckResult("ci", CheckStatus.FAIL, "1 failure"),
                CheckResult("lint", CheckStatus.PENDING, "Running"),
            ],
            recommendation=MergeDecision.ASK_HUMAN,
        )
        output = format_confidence_score(score)

        assert "85%" in output
        assert "tests" in output
        assert "All pass" in output
        assert "1 failure" in output
        assert "✅" in output  # Pass symbol
        assert "❌" in output  # Fail symbol
        assert "⏳" in output  # Pending symbol

    def test_format_with_warnings(self):
        """Test formatting with warnings."""
        score = ConfidenceScore(
            score=0.75,
            warnings=["Tests are slow", "No code review"],
            recommendation=MergeDecision.ASK_HUMAN,
        )
        output = format_confidence_score(score)

        assert "Warnings:" in output
        assert "Tests are slow" in output
        assert "No code review" in output
        assert "⚠️" in output

    def test_format_with_blockers(self):
        """Test formatting with blockers."""
        score = ConfidenceScore(
            score=0.0,
            blockers=["Merge conflicts", "CI failing"],
            recommendation=MergeDecision.BLOCK,
        )
        output = format_confidence_score(score)

        assert "Blockers:" in output
        assert "Merge conflicts" in output
        assert "CI failing" in output
        assert "🚫" in output


class TestAutoMergerTaskCompletion:
    """Tests for task completion checking."""

    def test_no_prd_path_skips(self, tmp_path):
        """Test that missing PRD path skips check."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path

        merger = AutoMerger(git_tools=mock_git, prd_path=None)
        result = merger._check_task_complete("task-1")

        assert result.status == CheckStatus.SKIPPED
        assert result.required is False

    def test_prd_not_exists_skips(self, tmp_path):
        """Test that non-existent PRD skips check."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path
        prd_path = tmp_path / "nonexistent.json"

        merger = AutoMerger(git_tools=mock_git, prd_path=prd_path)
        result = merger._check_task_complete("task-1")

        assert result.status == CheckStatus.SKIPPED

    def test_task_complete_passes(self, tmp_path):
        """Test completed task passes check."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path

        prd_path = tmp_path / "PRD.json"
        prd_data = {
            "project": {"name": "Test", "description": "Test project"},
            "features": [
                {
                    "id": "task-1",
                    "description": "Test task",
                    "priority": 1,
                    "status": "complete",
                    "passes": True,
                    "steps": ["Step 1"],
                    "acceptance_criteria": ["Criterion 1"],
                }
            ],
        }
        prd_path.write_text(json.dumps(prd_data))

        merger = AutoMerger(git_tools=mock_git, prd_path=prd_path)
        result = merger._check_task_complete("task-1")

        assert result.status == CheckStatus.PASS

    def test_task_incomplete_fails(self, tmp_path):
        """Test incomplete task fails check."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path

        prd_path = tmp_path / "PRD.json"
        prd_data = {
            "project": {"name": "Test", "description": "Test project"},
            "features": [
                {
                    "id": "task-1",
                    "description": "Test task",
                    "priority": 1,
                    "status": "in_progress",
                    "passes": False,
                    "steps": ["Step 1"],
                    "acceptance_criteria": ["Criterion 1"],
                }
            ],
        }
        prd_path.write_text(json.dumps(prd_data))

        merger = AutoMerger(git_tools=mock_git, prd_path=prd_path)
        result = merger._check_task_complete("task-1")

        assert result.status == CheckStatus.FAIL

    def test_task_not_found_unknown(self, tmp_path):
        """Test unknown task returns unknown status."""
        mock_git = MagicMock()
        mock_git.repo_path = tmp_path

        prd_path = tmp_path / "PRD.json"
        prd_data = {
            "project": {"name": "Test", "description": "Test project"},
            "features": [],
        }
        prd_path.write_text(json.dumps(prd_data))

        merger = AutoMerger(git_tools=mock_git, prd_path=prd_path)
        result = merger._check_task_complete("nonexistent-task")

        assert result.status == CheckStatus.UNKNOWN
