"""Tests for notification base classes."""

from __future__ import annotations

import pytest
from datetime import datetime

from ralph_agi.notifications.base import (
    Notification,
    NotificationPriority,
    NotificationResult,
)


class TestNotificationPriority:
    """Tests for NotificationPriority enum."""

    def test_all_priorities_exist(self):
        """Test all expected priorities exist."""
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.URGENT.value == "urgent"

    def test_emoji_property(self):
        """Test emoji property."""
        assert NotificationPriority.LOW.emoji == "ℹ️"
        assert NotificationPriority.NORMAL.emoji == "📋"
        assert NotificationPriority.HIGH.emoji == "⚠️"
        assert NotificationPriority.URGENT.emoji == "🚨"


class TestNotification:
    """Tests for Notification dataclass."""

    def test_notification_creation_minimal(self):
        """Test creating notification with minimal fields."""
        notif = Notification(title="Test Notification")
        assert notif.title == "Test Notification"
        assert notif.message == ""
        assert notif.priority == NotificationPriority.NORMAL
        assert notif.timestamp is not None

    def test_notification_creation_full(self):
        """Test creating notification with all fields."""
        notif = Notification(
            title="Task Complete",
            message="The task finished successfully",
            priority=NotificationPriority.HIGH,
            task_id="US-123",
            task_title="Fix login bug",
            status="success",
            pr_number=456,
            pr_url="https://github.com/org/repo/pull/456",
            deploy_url="https://preview.example.com",
            duration_seconds=125.5,
            timestamp="2025-01-16T12:00:00",
            metadata={"branch": "feature/login"},
        )
        assert notif.title == "Task Complete"
        assert notif.task_id == "US-123"
        assert notif.pr_number == 456
        assert notif.duration_seconds == 125.5

    def test_is_success(self):
        """Test is_success property."""
        success = Notification(title="T", status="success")
        completed = Notification(title="T", status="completed")
        passed = Notification(title="T", status="passed")
        failure = Notification(title="T", status="failure")

        assert success.is_success is True
        assert completed.is_success is True
        assert passed.is_success is True
        assert failure.is_success is False

    def test_is_failure(self):
        """Test is_failure property."""
        failure = Notification(title="T", status="failure")
        failed = Notification(title="T", status="failed")
        error = Notification(title="T", status="error")
        success = Notification(title="T", status="success")

        assert failure.is_failure is True
        assert failed.is_failure is True
        assert error.is_failure is True
        assert success.is_failure is False

    def test_status_emoji(self):
        """Test status_emoji property."""
        success = Notification(title="T", status="success")
        failure = Notification(title="T", status="failure")
        pending = Notification(title="T", status="pending")

        assert success.status_emoji == "✅"
        assert failure.status_emoji == "❌"
        assert pending.status_emoji == "🔄"

    def test_duration_formatted_seconds(self):
        """Test duration formatting for seconds."""
        notif = Notification(title="T", duration_seconds=45)
        assert notif.duration_formatted == "45s"

    def test_duration_formatted_minutes(self):
        """Test duration formatting for minutes."""
        notif = Notification(title="T", duration_seconds=125)
        assert notif.duration_formatted == "2m 5s"

    def test_duration_formatted_hours(self):
        """Test duration formatting for hours."""
        notif = Notification(title="T", duration_seconds=3725)
        assert notif.duration_formatted == "1h 2m"

    def test_duration_formatted_none(self):
        """Test duration formatting when None."""
        notif = Notification(title="T")
        assert notif.duration_formatted == ""

    def test_to_dict(self):
        """Test converting to dictionary."""
        notif = Notification(
            title="Test",
            message="Message",
            task_id="T-1",
            status="success",
        )
        data = notif.to_dict()

        assert data["title"] == "Test"
        assert data["message"] == "Message"
        assert data["task_id"] == "T-1"
        assert data["status"] == "success"

    def test_task_completed_success(self):
        """Test creating task completion notification."""
        notif = Notification.task_completed(
            task_id="US-100",
            task_title="Implement feature",
            success=True,
            duration_seconds=300,
        )

        assert "US-100" in notif.title
        assert "Success" in notif.title
        assert notif.task_id == "US-100"
        assert notif.is_success is True
        assert notif.priority == NotificationPriority.NORMAL

    def test_task_completed_failure(self):
        """Test creating failed task notification."""
        notif = Notification.task_completed(
            task_id="US-101",
            task_title="Fix bug",
            success=False,
        )

        assert "US-101" in notif.title
        assert "Failure" in notif.title
        assert notif.is_failure is True
        assert notif.priority == NotificationPriority.HIGH

    def test_batch_completed_all_success(self):
        """Test batch completion with all successes."""
        notif = Notification.batch_completed(
            total=10,
            succeeded=10,
            failed=0,
            duration_seconds=600,
        )

        assert "10/10" in notif.title
        assert notif.is_success is True
        assert notif.metadata["succeeded"] == 10

    def test_batch_completed_all_failure(self):
        """Test batch completion with all failures."""
        notif = Notification.batch_completed(
            total=5,
            succeeded=0,
            failed=5,
        )

        assert "0/5" in notif.title
        assert notif.is_failure is True

    def test_batch_completed_partial(self):
        """Test batch completion with partial success."""
        notif = Notification.batch_completed(
            total=10,
            succeeded=7,
            failed=3,
        )

        assert "7/10" in notif.title
        assert notif.status == "partial"
        assert notif.priority == NotificationPriority.HIGH


class TestNotificationResult:
    """Tests for NotificationResult dataclass."""

    def test_result_success(self):
        """Test successful result."""
        result = NotificationResult(
            success=True,
            channel="slack",
            response={"status_code": 200},
        )
        assert result.success is True
        assert result.channel == "slack"
        assert result.error is None

    def test_result_failure(self):
        """Test failed result."""
        result = NotificationResult(
            success=False,
            channel="discord",
            error="Connection timeout",
        )
        assert result.success is False
        assert result.error == "Connection timeout"

    def test_to_dict(self):
        """Test converting to dictionary."""
        result = NotificationResult(
            success=True,
            channel="telegram",
        )
        data = result.to_dict()

        assert data["success"] is True
        assert data["channel"] == "telegram"
