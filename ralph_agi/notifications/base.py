"""Base classes for the notification system.

Defines the core abstractions for notifications and channels.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Priority levels for notifications."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

    @property
    def emoji(self) -> str:
        """Get emoji for priority level."""
        emojis = {
            NotificationPriority.LOW: "ℹ️",
            NotificationPriority.NORMAL: "📋",
            NotificationPriority.HIGH: "⚠️",
            NotificationPriority.URGENT: "🚨",
        }
        return emojis.get(self, "📋")


@dataclass
class Notification:
    """A notification to be sent.

    Attributes:
        title: Notification title/subject.
        message: Main notification content.
        priority: Notification priority level.
        task_id: Associated task identifier.
        task_title: Human-readable task title.
        status: Task status (success/failure/etc).
        pr_number: Pull request number if applicable.
        pr_url: Pull request URL if applicable.
        deploy_url: Deploy preview URL if applicable.
        duration_seconds: Time taken for task.
        timestamp: When the notification was created.
        metadata: Additional metadata.
    """

    title: str
    message: str = ""
    priority: NotificationPriority = NotificationPriority.NORMAL
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    status: str = "completed"
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    deploy_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    timestamp: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    @property
    def is_success(self) -> bool:
        """Check if this is a success notification."""
        return self.status.lower() in ("success", "completed", "passed")

    @property
    def is_failure(self) -> bool:
        """Check if this is a failure notification."""
        return self.status.lower() in ("failure", "failed", "error")

    @property
    def status_emoji(self) -> str:
        """Get emoji for status."""
        if self.is_success:
            return "✅"
        elif self.is_failure:
            return "❌"
        else:
            return "🔄"

    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string."""
        if self.duration_seconds is None:
            return ""

        seconds = int(self.duration_seconds)
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins}m {secs}s"
        else:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            return f"{hours}h {mins}m"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "task_id": self.task_id,
            "task_title": self.task_title,
            "status": self.status,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "deploy_url": self.deploy_url,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def task_completed(
        cls,
        task_id: str,
        task_title: str,
        success: bool = True,
        duration_seconds: Optional[float] = None,
        pr_number: Optional[int] = None,
        pr_url: Optional[str] = None,
        **kwargs,
    ) -> Notification:
        """Create a task completion notification.

        Args:
            task_id: Task identifier.
            task_title: Human-readable title.
            success: Whether task succeeded.
            duration_seconds: Time taken.
            pr_number: PR number if applicable.
            pr_url: PR URL if applicable.
            **kwargs: Additional arguments.

        Returns:
            Notification instance.
        """
        status = "success" if success else "failure"
        emoji = "✅" if success else "❌"
        title = f"{emoji} Task {task_id}: {status.title()}"

        return cls(
            title=title,
            message=task_title,
            task_id=task_id,
            task_title=task_title,
            status=status,
            duration_seconds=duration_seconds,
            pr_number=pr_number,
            pr_url=pr_url,
            priority=NotificationPriority.NORMAL if success else NotificationPriority.HIGH,
            **kwargs,
        )

    @classmethod
    def batch_completed(
        cls,
        total: int,
        succeeded: int,
        failed: int,
        duration_seconds: Optional[float] = None,
        **kwargs,
    ) -> Notification:
        """Create a batch completion notification.

        Args:
            total: Total tasks in batch.
            succeeded: Number of successful tasks.
            failed: Number of failed tasks.
            duration_seconds: Total time taken.
            **kwargs: Additional arguments.

        Returns:
            Notification instance.
        """
        if failed == 0:
            emoji = "✅"
            status = "success"
            priority = NotificationPriority.NORMAL
        elif succeeded == 0:
            emoji = "❌"
            status = "failure"
            priority = NotificationPriority.HIGH
        else:
            emoji = "⚠️"
            status = "partial"
            priority = NotificationPriority.HIGH

        title = f"{emoji} Batch Complete: {succeeded}/{total} succeeded"
        message = f"Succeeded: {succeeded}, Failed: {failed}"

        return cls(
            title=title,
            message=message,
            status=status,
            duration_seconds=duration_seconds,
            priority=priority,
            metadata={"total": total, "succeeded": succeeded, "failed": failed},
            **kwargs,
        )


@dataclass
class NotificationResult:
    """Result of sending a notification.

    Attributes:
        success: Whether notification was sent successfully.
        channel: Channel name that was used.
        error: Error message if failed.
        response: Response data if available.
    """

    success: bool
    channel: str
    error: Optional[str] = None
    response: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "channel": self.channel,
            "error": self.error,
            "response": self.response,
        }


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get channel name."""
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if channel is properly configured."""
        pass

    @abstractmethod
    async def send(self, notification: Notification) -> NotificationResult:
        """Send a notification through this channel.

        Args:
            notification: Notification to send.

        Returns:
            Result of the send operation.
        """
        pass

    def format_notification(self, notification: Notification) -> str:
        """Format notification for this channel.

        Default implementation returns a simple text format.
        Subclasses can override for channel-specific formatting.

        Args:
            notification: Notification to format.

        Returns:
            Formatted message string.
        """
        parts = [notification.title]

        if notification.message:
            parts.append(notification.message)

        if notification.duration_formatted:
            parts.append(f"Duration: {notification.duration_formatted}")

        if notification.pr_url:
            parts.append(f"PR: {notification.pr_url}")

        if notification.deploy_url:
            parts.append(f"Preview: {notification.deploy_url}")

        return "\n".join(parts)
