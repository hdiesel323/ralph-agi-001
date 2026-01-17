"""Notification system for RALPH-AGI.

Provides external notifications for task completion via:
- Slack webhooks
- Discord webhooks
- Telegram bots
- Desktop notifications
"""

from ralph_agi.notifications.base import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationResult,
)
from ralph_agi.notifications.manager import (
    NotificationManager,
    get_notification_manager,
)
from ralph_agi.notifications.channels import (
    SlackChannel,
    DiscordChannel,
    TelegramChannel,
    DesktopChannel,
)

__all__ = [
    # Base
    "Notification",
    "NotificationChannel",
    "NotificationPriority",
    "NotificationResult",
    # Manager
    "NotificationManager",
    "get_notification_manager",
    # Channels
    "SlackChannel",
    "DiscordChannel",
    "TelegramChannel",
    "DesktopChannel",
]
