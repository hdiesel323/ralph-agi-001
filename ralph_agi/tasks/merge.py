"""Confidence-based auto-merge for RALPH-AGI.

This module provides automated PR merging based on confidence scoring.
PRs are merged when confidence thresholds are met based on:
- Tests passing
- No merge conflicts
- Task completion in PRD
- CI checks status

Design Principles:
- Conservative by default (ask for confirmation)
- Configurable thresholds for automation levels
- Full audit trail of merge decisions
- Human override always available
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ralph_agi.tools.git import GitTools

logger = logging.getLogger(__name__)

# Default audit log file
DEFAULT_AUDIT_LOG = ".ralph-merge-audit.jsonl"


class MergeThreshold(Enum):
    """Auto-merge threshold levels.

    Determines how much automation is applied to merge decisions.
    """

    ALWAYS_ASK = "always_ask"  # Never auto-merge, always ask human
    ASK_ON_WARNINGS = "ask_on_warnings"  # Auto-merge if high confidence, ask otherwise
    FULL_AUTO = "full_auto"  # Auto-merge unless critical failure


class CheckStatus(Enum):
    """Status of an individual check."""

    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


class MergeDecision(Enum):
    """Decision on whether to merge."""

    MERGE = "merge"  # Proceed with merge
    ASK_HUMAN = "ask_human"  # Need human approval
    BLOCK = "block"  # Do not merge


@dataclass
class MergeConfig:
    """Configuration for auto-merge behavior.

    Attributes:
        enabled: Whether auto-merge is enabled at all.
        threshold: Automation level for merge decisions.
        require_tests_pass: Require tests to pass before merging.
        require_ci_pass: Require all CI checks to pass.
        require_no_conflicts: Require no merge conflicts.
        require_task_complete: Require task marked complete in PRD.
        squash_merge: Use squash merge (recommended for clean history).
        delete_branch: Delete branch after merge.
        audit_log_path: Path for audit log file.
        protected_branches: Branches that cannot be auto-merged to.
    """

    enabled: bool = True
    threshold: MergeThreshold = MergeThreshold.ASK_ON_WARNINGS
    require_tests_pass: bool = True
    require_ci_pass: bool = True
    require_no_conflicts: bool = True
    require_task_complete: bool = True
    squash_merge: bool = True
    delete_branch: bool = True
    audit_log_path: Optional[Path] = None
    protected_branches: tuple[str, ...] = ("main", "master", "develop")


@dataclass
class CheckResult:
    """Result of a single check.

    Attributes:
        name: Name of the check.
        status: Pass/fail/pending status.
        message: Human-readable message about the result.
        required: Whether this check is required for merge.
        details: Additional details about the check.
    """

    name: str
    status: CheckStatus
    message: str
    required: bool = True
    details: Optional[dict[str, Any]] = None


@dataclass
class ConfidenceScore:
    """Confidence score for a merge decision.

    Attributes:
        score: Numeric score from 0.0 (no confidence) to 1.0 (full confidence).
        checks: Individual check results.
        warnings: List of warning messages.
        blockers: List of blocking issues (prevent merge).
        recommendation: Recommended merge decision.
    """

    score: float
    checks: list[CheckResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    recommendation: MergeDecision = MergeDecision.ASK_HUMAN

    @property
    def is_high_confidence(self) -> bool:
        """Check if confidence is high enough for auto-merge."""
        return self.score >= 0.9 and len(self.blockers) == 0

    @property
    def is_blocked(self) -> bool:
        """Check if there are blocking issues."""
        return len(self.blockers) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return len(self.warnings) > 0

    @property
    def all_checks_pass(self) -> bool:
        """Check if all required checks pass."""
        return all(
            c.status == CheckStatus.PASS
            for c in self.checks
            if c.required
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "score": self.score,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "required": c.required,
                }
                for c in self.checks
            ],
            "warnings": self.warnings,
            "blockers": self.blockers,
            "recommendation": self.recommendation.value,
        }


@dataclass
class MergeResult:
    """Result of a merge operation.

    Attributes:
        success: Whether the merge succeeded.
        pr_number: PR number that was merged.
        merge_sha: Commit SHA of the merge commit.
        method: Merge method used (squash, merge, rebase).
        branch_deleted: Whether the branch was deleted.
        error: Error message if merge failed.
    """

    success: bool
    pr_number: int
    merge_sha: Optional[str] = None
    method: str = "squash"
    branch_deleted: bool = False
    error: Optional[str] = None


@dataclass
class AuditEntry:
    """Audit log entry for a merge decision.

    Attributes:
        timestamp: When the decision was made.
        pr_number: PR number.
        pr_url: PR URL.
        branch: Source branch name.
        target_branch: Target branch name.
        task_id: Associated task ID (if any).
        confidence: Confidence score that led to decision.
        decision: The merge decision made.
        action_taken: What action was actually taken.
        merged_by: Who/what performed the merge (auto/human).
        result: Result of the merge operation.
        notes: Additional notes.
    """

    timestamp: str
    pr_number: int
    pr_url: str
    branch: str
    target_branch: str
    task_id: Optional[str]
    confidence: ConfidenceScore
    decision: MergeDecision
    action_taken: str
    merged_by: str
    result: Optional[MergeResult] = None
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "branch": self.branch,
            "target_branch": self.target_branch,
            "task_id": self.task_id,
            "confidence": self.confidence.to_dict(),
            "decision": self.decision.value,
            "action_taken": self.action_taken,
            "merged_by": self.merged_by,
            "result": {
                "success": self.result.success,
                "merge_sha": self.result.merge_sha,
                "method": self.result.method,
                "branch_deleted": self.result.branch_deleted,
                "error": self.result.error,
            } if self.result else None,
            "notes": self.notes,
        }


class AutoMerger:
    """Confidence-based automatic PR merger.

    Evaluates PRs based on configurable criteria and either
    auto-merges or requests human approval based on confidence.

    Example:
        >>> from ralph_agi.tasks.merge import AutoMerger, MergeConfig
        >>> from ralph_agi.tools.git import GitTools
        >>> git = GitTools(repo_path=Path("."))
        >>> merger = AutoMerger(git)
        >>> score = merger.evaluate_pr(pr_number=123)
        >>> if score.recommendation == MergeDecision.MERGE:
        ...     result = merger.merge_pr(123)
    """

    def __init__(
        self,
        git_tools: GitTools,
        config: Optional[MergeConfig] = None,
        prd_path: Optional[Path] = None,
    ):
        """Initialize the auto-merger.

        Args:
            git_tools: GitTools instance for git/gh operations.
            config: Merge configuration.
            prd_path: Path to PRD.json for task completion checks.
        """
        self._git = git_tools
        self._config = config or MergeConfig()
        self._prd_path = prd_path
        self._audit_log_path = self._config.audit_log_path or Path(
            self._git.repo_path / DEFAULT_AUDIT_LOG
        )

    @property
    def config(self) -> MergeConfig:
        """Get the merge configuration."""
        return self._config

    def evaluate_pr(
        self,
        pr_number: Optional[int] = None,
        task_id: Optional[str] = None,
    ) -> ConfidenceScore:
        """Evaluate a PR and calculate confidence score.

        Args:
            pr_number: PR number to evaluate. If None, uses current branch PR.
            task_id: Associated task ID for PRD completion check.

        Returns:
            ConfidenceScore with checks, warnings, and recommendation.
        """
        checks = []
        warnings = []
        blockers = []

        # Get PR status
        pr_status = self._git.get_pr_status(pr_number)
        if pr_status is None:
            return ConfidenceScore(
                score=0.0,
                blockers=["No PR found for evaluation"],
                recommendation=MergeDecision.BLOCK,
            )

        pr_number = pr_status.get("number")
        pr_state = pr_status.get("state", "unknown")

        # Check PR is open
        if pr_state not in ("OPEN", "open"):
            blockers.append(f"PR is not open (state: {pr_state})")

        # Check mergeable status
        mergeable = pr_status.get("mergeable", "UNKNOWN")
        if self._config.require_no_conflicts:
            if mergeable == "MERGEABLE":
                checks.append(CheckResult(
                    name="no_conflicts",
                    status=CheckStatus.PASS,
                    message="No merge conflicts",
                ))
            elif mergeable == "CONFLICTING":
                checks.append(CheckResult(
                    name="no_conflicts",
                    status=CheckStatus.FAIL,
                    message="Merge conflicts detected",
                ))
                blockers.append("PR has merge conflicts")
            else:
                checks.append(CheckResult(
                    name="no_conflicts",
                    status=CheckStatus.UNKNOWN,
                    message=f"Mergeable status: {mergeable}",
                ))
                warnings.append(f"Unknown mergeable status: {mergeable}")

        # Check CI status
        ci_status = self._get_ci_status(pr_number)
        if self._config.require_ci_pass:
            checks.append(ci_status)
            if ci_status.status == CheckStatus.FAIL:
                blockers.append(f"CI checks failing: {ci_status.message}")
            elif ci_status.status == CheckStatus.PENDING:
                warnings.append("CI checks still pending")

        # Check tests
        tests_status = self._get_tests_status(pr_number)
        if self._config.require_tests_pass:
            checks.append(tests_status)
            if tests_status.status == CheckStatus.FAIL:
                blockers.append(f"Tests failing: {tests_status.message}")
            elif tests_status.status == CheckStatus.PENDING:
                warnings.append("Tests still running")

        # Check task completion
        if self._config.require_task_complete and task_id:
            task_status = self._check_task_complete(task_id)
            checks.append(task_status)
            if task_status.status == CheckStatus.FAIL:
                warnings.append(f"Task not complete: {task_status.message}")

        # Calculate score
        score = self._calculate_score(checks, warnings, blockers)

        # Determine recommendation based on threshold
        recommendation = self._determine_recommendation(score, warnings, blockers)

        return ConfidenceScore(
            score=score,
            checks=checks,
            warnings=warnings,
            blockers=blockers,
            recommendation=recommendation,
        )

    def _get_ci_status(self, pr_number: int) -> CheckResult:
        """Get CI status for a PR.

        Args:
            pr_number: PR number.

        Returns:
            CheckResult with CI status.
        """
        try:
            # Use gh to get PR checks
            from ralph_agi.tools.shell import ShellTools
            shell = ShellTools(default_cwd=self._git.repo_path)

            result = shell.execute(
                f"gh pr checks {pr_number} --json name,state,conclusion"
            )

            if not result.success:
                return CheckResult(
                    name="ci_checks",
                    status=CheckStatus.UNKNOWN,
                    message="Could not retrieve CI status",
                )

            checks_data = json.loads(result.stdout)

            if not checks_data:
                return CheckResult(
                    name="ci_checks",
                    status=CheckStatus.SKIPPED,
                    message="No CI checks configured",
                    required=False,
                )

            # Analyze checks
            failed = [c for c in checks_data if c.get("conclusion") == "FAILURE"]
            pending = [c for c in checks_data if c.get("state") == "PENDING"]

            if failed:
                failed_names = [c.get("name", "unknown") for c in failed]
                return CheckResult(
                    name="ci_checks",
                    status=CheckStatus.FAIL,
                    message=f"Failed: {', '.join(failed_names[:3])}",
                    details={"failed": failed_names},
                )
            elif pending:
                pending_names = [c.get("name", "unknown") for c in pending]
                return CheckResult(
                    name="ci_checks",
                    status=CheckStatus.PENDING,
                    message=f"Pending: {', '.join(pending_names[:3])}",
                    details={"pending": pending_names},
                )
            else:
                return CheckResult(
                    name="ci_checks",
                    status=CheckStatus.PASS,
                    message="All CI checks pass",
                )

        except Exception as e:
            logger.debug(f"Error getting CI status: {e}")
            return CheckResult(
                name="ci_checks",
                status=CheckStatus.UNKNOWN,
                message=f"Error: {str(e)[:50]}",
            )

    def _get_tests_status(self, pr_number: int) -> CheckResult:
        """Get tests status for a PR.

        Looks for test-related checks in CI status.

        Args:
            pr_number: PR number.

        Returns:
            CheckResult with tests status.
        """
        try:
            from ralph_agi.tools.shell import ShellTools
            shell = ShellTools(default_cwd=self._git.repo_path)

            result = shell.execute(
                f"gh pr checks {pr_number} --json name,state,conclusion"
            )

            if not result.success:
                return CheckResult(
                    name="tests",
                    status=CheckStatus.UNKNOWN,
                    message="Could not retrieve test status",
                )

            checks_data = json.loads(result.stdout)

            # Find test-related checks
            test_checks = [
                c for c in checks_data
                if any(t in c.get("name", "").lower() for t in ["test", "pytest", "jest", "spec"])
            ]

            if not test_checks:
                return CheckResult(
                    name="tests",
                    status=CheckStatus.SKIPPED,
                    message="No test checks found",
                    required=False,
                )

            failed = [c for c in test_checks if c.get("conclusion") == "FAILURE"]
            pending = [c for c in test_checks if c.get("state") == "PENDING"]

            if failed:
                return CheckResult(
                    name="tests",
                    status=CheckStatus.FAIL,
                    message=f"Tests failing: {failed[0].get('name', 'unknown')}",
                )
            elif pending:
                return CheckResult(
                    name="tests",
                    status=CheckStatus.PENDING,
                    message="Tests running",
                )
            else:
                return CheckResult(
                    name="tests",
                    status=CheckStatus.PASS,
                    message="All tests pass",
                )

        except Exception as e:
            logger.debug(f"Error getting tests status: {e}")
            return CheckResult(
                name="tests",
                status=CheckStatus.UNKNOWN,
                message=f"Error: {str(e)[:50]}",
            )

    def _check_task_complete(self, task_id: str) -> CheckResult:
        """Check if a task is marked complete in PRD.

        Args:
            task_id: Task ID to check.

        Returns:
            CheckResult with task completion status.
        """
        if not self._prd_path or not self._prd_path.exists():
            return CheckResult(
                name="task_complete",
                status=CheckStatus.SKIPPED,
                message="No PRD path configured",
                required=False,
            )

        try:
            from ralph_agi.tasks.prd import load_prd

            prd = load_prd(self._prd_path)

            for feature in prd.features:
                if feature.id == task_id:
                    if feature.passes:
                        return CheckResult(
                            name="task_complete",
                            status=CheckStatus.PASS,
                            message=f"Task {task_id} is complete",
                        )
                    else:
                        return CheckResult(
                            name="task_complete",
                            status=CheckStatus.FAIL,
                            message=f"Task {task_id} not yet complete",
                        )

            return CheckResult(
                name="task_complete",
                status=CheckStatus.UNKNOWN,
                message=f"Task {task_id} not found in PRD",
            )

        except Exception as e:
            logger.debug(f"Error checking task completion: {e}")
            return CheckResult(
                name="task_complete",
                status=CheckStatus.UNKNOWN,
                message=f"Error: {str(e)[:50]}",
            )

    def _calculate_score(
        self,
        checks: list[CheckResult],
        warnings: list[str],
        blockers: list[str],
    ) -> float:
        """Calculate confidence score from checks.

        Args:
            checks: List of check results.
            warnings: List of warnings.
            blockers: List of blockers.

        Returns:
            Score from 0.0 to 1.0.
        """
        if blockers:
            return 0.0

        if not checks:
            return 0.5  # No checks = medium confidence

        # Calculate weighted score
        total_weight = 0
        weighted_score = 0

        for check in checks:
            weight = 2.0 if check.required else 1.0
            total_weight += weight

            if check.status == CheckStatus.PASS:
                weighted_score += weight
            elif check.status == CheckStatus.PENDING:
                weighted_score += weight * 0.5
            elif check.status == CheckStatus.SKIPPED:
                weighted_score += weight * 0.8
            # FAIL and UNKNOWN get 0

        base_score = weighted_score / total_weight if total_weight > 0 else 0.5

        # Apply warning penalty
        warning_penalty = min(len(warnings) * 0.1, 0.3)

        return max(0.0, min(1.0, base_score - warning_penalty))

    def _determine_recommendation(
        self,
        score: float,
        warnings: list[str],
        blockers: list[str],
    ) -> MergeDecision:
        """Determine merge recommendation based on threshold.

        Args:
            score: Confidence score.
            warnings: List of warnings.
            blockers: List of blockers.

        Returns:
            Recommended merge decision.
        """
        if blockers:
            return MergeDecision.BLOCK

        threshold = self._config.threshold

        if threshold == MergeThreshold.ALWAYS_ASK:
            return MergeDecision.ASK_HUMAN

        if threshold == MergeThreshold.FULL_AUTO:
            if score >= 0.5:  # Some confidence
                return MergeDecision.MERGE
            else:
                return MergeDecision.ASK_HUMAN

        # ASK_ON_WARNINGS (default)
        if warnings:
            return MergeDecision.ASK_HUMAN
        if score >= 0.9:
            return MergeDecision.MERGE
        else:
            return MergeDecision.ASK_HUMAN

    def merge_pr(
        self,
        pr_number: int,
        confidence: Optional[ConfidenceScore] = None,
        task_id: Optional[str] = None,
        force: bool = False,
    ) -> MergeResult:
        """Merge a PR via GitHub CLI.

        Args:
            pr_number: PR number to merge.
            confidence: Pre-computed confidence score (for audit).
            task_id: Associated task ID (for audit).
            force: Force merge even if confidence is low.

        Returns:
            MergeResult with outcome.
        """
        if not self._config.enabled:
            return MergeResult(
                success=False,
                pr_number=pr_number,
                error="Auto-merge is disabled in config",
            )

        # Get PR info for audit
        pr_status = self._git.get_pr_status(pr_number)
        pr_url = pr_status.get("url", f"PR #{pr_number}") if pr_status else f"PR #{pr_number}"
        branch = pr_status.get("headRefName", "unknown") if pr_status else "unknown"
        target_branch = pr_status.get("baseRefName", "main") if pr_status else "main"

        # Check protected branches
        if target_branch in self._config.protected_branches and not force:
            # Just log warning - gh will handle protection rules
            logger.warning(f"Merging to protected branch: {target_branch}")

        # Evaluate if no confidence provided
        if confidence is None:
            confidence = self.evaluate_pr(pr_number, task_id)

        # Check if we should proceed
        if not force and confidence.recommendation == MergeDecision.BLOCK:
            result = MergeResult(
                success=False,
                pr_number=pr_number,
                error=f"Blocked: {', '.join(confidence.blockers)}",
            )
            self._log_audit(
                pr_number=pr_number,
                pr_url=pr_url,
                branch=branch,
                target_branch=target_branch,
                task_id=task_id,
                confidence=confidence,
                decision=MergeDecision.BLOCK,
                action_taken="blocked",
                merged_by="auto",
                result=result,
            )
            return result

        # Build merge command
        args = ["gh", "pr", "merge", str(pr_number)]

        if self._config.squash_merge:
            args.append("--squash")
        else:
            args.append("--merge")

        if self._config.delete_branch:
            args.append("--delete-branch")

        args.append("--auto")  # Use GitHub's auto-merge

        try:
            from ralph_agi.tools.shell import ShellTools
            shell = ShellTools(default_cwd=self._git.repo_path)

            cmd = " ".join(args)
            shell_result = shell.execute(cmd)

            if shell_result.success:
                result = MergeResult(
                    success=True,
                    pr_number=pr_number,
                    method="squash" if self._config.squash_merge else "merge",
                    branch_deleted=self._config.delete_branch,
                )
                logger.info(f"Merged PR #{pr_number}")
            else:
                result = MergeResult(
                    success=False,
                    pr_number=pr_number,
                    error=shell_result.stderr or "Unknown error",
                )
                logger.error(f"Failed to merge PR #{pr_number}: {shell_result.stderr}")

        except Exception as e:
            result = MergeResult(
                success=False,
                pr_number=pr_number,
                error=str(e),
            )
            logger.error(f"Exception merging PR #{pr_number}: {e}")

        # Log audit entry
        self._log_audit(
            pr_number=pr_number,
            pr_url=pr_url,
            branch=branch,
            target_branch=target_branch,
            task_id=task_id,
            confidence=confidence,
            decision=confidence.recommendation,
            action_taken="merged" if result.success else "failed",
            merged_by="auto",
            result=result,
        )

        return result

    def _log_audit(
        self,
        pr_number: int,
        pr_url: str,
        branch: str,
        target_branch: str,
        task_id: Optional[str],
        confidence: ConfidenceScore,
        decision: MergeDecision,
        action_taken: str,
        merged_by: str,
        result: Optional[MergeResult] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Log an audit entry for a merge decision.

        Args:
            All parameters for AuditEntry.
        """
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            pr_number=pr_number,
            pr_url=pr_url,
            branch=branch,
            target_branch=target_branch,
            task_id=task_id,
            confidence=confidence,
            decision=decision,
            action_taken=action_taken,
            merged_by=merged_by,
            result=result,
            notes=notes,
        )

        # Append to JSONL audit log
        try:
            with open(self._audit_log_path, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
            logger.debug(f"Audit logged: {action_taken} PR #{pr_number}")
        except Exception as e:
            logger.warning(f"Failed to write audit log: {e}")

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        """Read recent audit log entries.

        Args:
            limit: Maximum entries to return.

        Returns:
            List of audit entry dictionaries.
        """
        if not self._audit_log_path.exists():
            return []

        entries = []
        try:
            with open(self._audit_log_path) as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
        except Exception as e:
            logger.warning(f"Failed to read audit log: {e}")
            return []

        # Return most recent entries
        return entries[-limit:]


def format_confidence_score(score: ConfidenceScore) -> str:
    """Format confidence score for display.

    Args:
        score: ConfidenceScore to format.

    Returns:
        Formatted string for terminal display.
    """
    lines = [
        f"Confidence: {score.score:.0%}",
        f"Recommendation: {score.recommendation.value}",
        "",
        "Checks:",
    ]

    for check in score.checks:
        status_symbol = {
            CheckStatus.PASS: "✅",
            CheckStatus.FAIL: "❌",
            CheckStatus.PENDING: "⏳",
            CheckStatus.SKIPPED: "⏭️",
            CheckStatus.UNKNOWN: "❓",
        }.get(check.status, "?")

        required = "*" if check.required else ""
        lines.append(f"  {status_symbol} {check.name}{required}: {check.message}")

    if score.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in score.warnings:
            lines.append(f"  ⚠️ {warning}")

    if score.blockers:
        lines.append("")
        lines.append("Blockers:")
        for blocker in score.blockers:
            lines.append(f"  🚫 {blocker}")

    return "\n".join(lines)
