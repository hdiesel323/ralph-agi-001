"""Notification manager for orchestrating notifications.

Handles sending notifications through multiple channels with
configuration management and graceful error handling.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ralph_agi.notifications.base import (
    Notification,
    NotificationChannel,
    NotificationResult,
)
from ralph_agi.notifications.channels import (
    SlackChannel,
    DiscordChannel,
    TelegramChannel,
    DesktopChannel,
)

logger = logging.getLogger(__name__)

# Global manager instance
_manager: Optional[NotificationManager] = None


@dataclass
class NotificationConfig:
    """Configuration for notification channels.

    Attributes:
        enabled: Whether notifications are enabled globally.
        slack: Slack channel configuration.
        discord: Discord channel configuration.
        telegram: Telegram channel configuration.
        desktop: Desktop notification configuration.
    """

    enabled: bool = True
    slack: dict[str, Any] = field(default_factory=dict)
    discord: dict[str, Any] = field(default_factory=dict)
    telegram: dict[str, Any] = field(default_factory=dict)
    desktop: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotificationConfig:
        """Create from dictionary.

        Args:
            data: Configuration dictionary.

        Returns:
            NotificationConfig instance.
        """
        return cls(
            enabled=data.get("enabled", True),
            slack=data.get("slack", {}),
            discord=data.get("discord", {}),
            telegram=data.get("telegram", {}),
            desktop=data.get("desktop", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "slack": self.slack,
            "discord": self.discord,
            "telegram": self.telegram,
            "desktop": self.desktop,
        }


class NotificationManager:
    """Manager for sending notifications through multiple channels.

    Handles channel configuration, sending notifications, and
    aggregating results from multiple channels.
    """

    def __init__(self, config: Optional[NotificationConfig] = None) -> None:
        """Initialize notification manager.

        Args:
            config: Notification configuration.
        """
        self._config = config or NotificationConfig()
        self._channels: list[NotificationChannel] = []
        self._setup_channels()

    def _setup_channels(self) -> None:
        """Set up notification channels from config."""
        self._channels = []

        # Slack
        if self._config.slack:
            slack = SlackChannel(
                webhook_url=self._config.slack.get("webhook_url", ""),
                channel=self._config.slack.get("channel"),
                username=self._config.slack.get("username", "RALPH-AGI"),
                icon_emoji=self._config.slack.get("icon_emoji", ":robot_face:"),
            )
            if slack.is_configured:
                self._channels.append(slack)

        # Discord
        if self._config.discord:
            discord = DiscordChannel(
                webhook_url=self._config.discord.get("webhook_url", ""),
                username=self._config.discord.get("username", "RALPH-AGI"),
                avatar_url=self._config.discord.get("avatar_url"),
            )
            if discord.is_configured:
                self._channels.append(discord)

        # Telegram
        if self._config.telegram:
            telegram = TelegramChannel(
                bot_token=self._config.telegram.get("bot_token", ""),
                chat_id=self._config.telegram.get("chat_id", ""),
                parse_mode=self._config.telegram.get("parse_mode", "HTML"),
            )
            if telegram.is_configured:
                self._channels.append(telegram)

        # Desktop
        if self._config.desktop.get("enabled", True):
            desktop = DesktopChannel(
                title_prefix=self._config.desktop.get("title_prefix", "RALPH-AGI"),
                sound=self._config.desktop.get("sound", True),
            )
            if desktop.is_configured:
                self._channels.append(desktop)

    @property
    def enabled(self) -> bool:
        """Check if notifications are enabled."""
        return self._config.enabled

    @property
    def channels(self) -> list[NotificationChannel]:
        """Get configured channels."""
        return self._channels

    @property
    def channel_names(self) -> list[str]:
        """Get names of configured channels."""
        return [c.name for c in self._channels]

    def add_channel(self, channel: NotificationChannel) -> None:
        """Add a notification channel.

        Args:
            channel: Channel to add.
        """
        self._channels.append(channel)

    def remove_channel(self, name: str) -> bool:
        """Remove a notification channel by name.

        Args:
            name: Channel name to remove.

        Returns:
            True if channel was removed.
        """
        for i, channel in enumerate(self._channels):
            if channel.name == name:
                del self._channels[i]
                return True
        return False

    async def send(
        self,
        notification: Notification,
        channels: Optional[list[str]] = None,
    ) -> list[NotificationResult]:
        """Send notification through configured channels.

        Args:
            notification: Notification to send.
            channels: Specific channels to use (all if None).

        Returns:
            Results from each channel.
        """
        if not self.enabled:
            return []

        # Filter channels if specific ones requested
        target_channels = self._channels
        if channels:
            target_channels = [c for c in self._channels if c.name in channels]

        if not target_channels:
            return []

        # Send to all channels concurrently
        tasks = [channel.send(notification) for channel in target_channels]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(NotificationResult(
                    success=False,
                    channel=target_channels[i].name,
                    error=str(result),
                ))
            else:
                final_results.append(result)

        return final_results

    def send_sync(
        self,
        notification: Notification,
        channels: Optional[list[str]] = None,
    ) -> list[NotificationResult]:
        """Synchronous wrapper for send.

        Args:
            notification: Notification to send.
            channels: Specific channels to use.

        Returns:
            Results from each channel.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Already in async context, create new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.send(notification, channels),
                )
                return future.result(timeout=30)
        else:
            return asyncio.run(self.send(notification, channels))

    async def notify_task_completed(
        self,
        task_id: str,
        task_title: str,
        success: bool = True,
        duration_seconds: Optional[float] = None,
        pr_number: Optional[int] = None,
        pr_url: Optional[str] = None,
        channels: Optional[list[str]] = None,
    ) -> list[NotificationResult]:
        """Send task completion notification.

        Convenience method for task completion notifications.

        Args:
            task_id: Task identifier.
            task_title: Human-readable title.
            success: Whether task succeeded.
            duration_seconds: Time taken.
            pr_number: PR number if applicable.
            pr_url: PR URL if applicable.
            channels: Specific channels to use.

        Returns:
            Results from each channel.
        """
        notification = Notification.task_completed(
            task_id=task_id,
            task_title=task_title,
            success=success,
            duration_seconds=duration_seconds,
            pr_number=pr_number,
            pr_url=pr_url,
        )
        return await self.send(notification, channels)

    async def notify_batch_completed(
        self,
        total: int,
        succeeded: int,
        failed: int,
        duration_seconds: Optional[float] = None,
        channels: Optional[list[str]] = None,
    ) -> list[NotificationResult]:
        """Send batch completion notification.

        Convenience method for batch completion notifications.

        Args:
            total: Total tasks in batch.
            succeeded: Number of successful tasks.
            failed: Number of failed tasks.
            duration_seconds: Total time taken.
            channels: Specific channels to use.

        Returns:
            Results from each channel.
        """
        notification = Notification.batch_completed(
            total=total,
            succeeded=succeeded,
            failed=failed,
            duration_seconds=duration_seconds,
        )
        return await self.send(notification, channels)


def get_notification_manager(
    config: Optional[NotificationConfig] = None,
) -> NotificationManager:
    """Get or create the global notification manager.

    Args:
        config: Configuration for new manager.

    Returns:
        NotificationManager instance.
    """
    global _manager

    if _manager is None or config is not None:
        _manager = NotificationManager(config)

    return _manager


def configure_notifications(config: dict[str, Any]) -> NotificationManager:
    """Configure notifications from dictionary.

    Args:
        config: Configuration dictionary.

    Returns:
        Configured NotificationManager.
    """
    notification_config = NotificationConfig.from_dict(config)
    return get_notification_manager(notification_config)
