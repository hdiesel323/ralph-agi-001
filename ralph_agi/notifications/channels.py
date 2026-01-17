"""Notification channel implementations.

Provides concrete implementations for:
- Slack webhooks
- Discord webhooks
- Telegram bots
- Desktop notifications
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Optional

from ralph_agi.notifications.base import (
    Notification,
    NotificationChannel,
    NotificationResult,
)

logger = logging.getLogger(__name__)

# Optional httpx import
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


@dataclass
class SlackChannel(NotificationChannel):
    """Slack webhook notification channel.

    Attributes:
        webhook_url: Slack incoming webhook URL.
        channel: Override channel (optional).
        username: Bot username (optional).
        icon_emoji: Bot icon emoji (optional).
    """

    webhook_url: str = ""
    channel: Optional[str] = None
    username: str = "RALPH-AGI"
    icon_emoji: str = ":robot_face:"

    @property
    def name(self) -> str:
        """Get channel name."""
        return "slack"

    @property
    def is_configured(self) -> bool:
        """Check if channel is configured."""
        return bool(self.webhook_url)

    def format_notification(self, notification: Notification) -> dict[str, Any]:
        """Format notification for Slack.

        Args:
            notification: Notification to format.

        Returns:
            Slack message payload.
        """
        # Build blocks for rich formatting
        blocks = []

        # Header block
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": notification.title[:150],
                "emoji": True,
            },
        })

        # Message section
        if notification.message:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": notification.message[:3000],
                },
            })

        # Context with metadata
        context_elements = []

        if notification.task_id:
            context_elements.append({
                "type": "mrkdwn",
                "text": f"*Task:* {notification.task_id}",
            })

        if notification.duration_formatted:
            context_elements.append({
                "type": "mrkdwn",
                "text": f"*Duration:* {notification.duration_formatted}",
            })

        if notification.status:
            context_elements.append({
                "type": "mrkdwn",
                "text": f"*Status:* {notification.status_emoji} {notification.status}",
            })

        if context_elements:
            blocks.append({
                "type": "context",
                "elements": context_elements[:10],  # Slack limit
            })

        # Actions/links
        if notification.pr_url or notification.deploy_url:
            actions = []
            if notification.pr_url:
                actions.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": f"PR #{notification.pr_number or 'View'}"},
                    "url": notification.pr_url,
                })
            if notification.deploy_url:
                actions.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Preview"},
                    "url": notification.deploy_url,
                })
            blocks.append({
                "type": "actions",
                "elements": actions,
            })

        payload = {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "blocks": blocks,
            "text": notification.title,  # Fallback for notifications
        }

        if self.channel:
            payload["channel"] = self.channel

        return payload

    async def send(self, notification: Notification) -> NotificationResult:
        """Send notification to Slack.

        Args:
            notification: Notification to send.

        Returns:
            Result of the send operation.
        """
        if not self.is_configured:
            return NotificationResult(
                success=False,
                channel=self.name,
                error="Slack webhook URL not configured",
            )

        if not HAS_HTTPX:
            return NotificationResult(
                success=False,
                channel=self.name,
                error="httpx library not installed",
            )

        try:
            payload = self.format_notification(notification)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10.0,
                )

            if response.status_code == 200:
                return NotificationResult(
                    success=True,
                    channel=self.name,
                    response={"status_code": response.status_code},
                )
            else:
                return NotificationResult(
                    success=False,
                    channel=self.name,
                    error=f"HTTP {response.status_code}: {response.text}",
                )

        except Exception as e:
            logger.warning(f"Slack notification failed: {e}")
            return NotificationResult(
                success=False,
                channel=self.name,
                error=str(e),
            )


@dataclass
class DiscordChannel(NotificationChannel):
    """Discord webhook notification channel.

    Attributes:
        webhook_url: Discord webhook URL.
        username: Bot username (optional).
        avatar_url: Bot avatar URL (optional).
    """

    webhook_url: str = ""
    username: str = "RALPH-AGI"
    avatar_url: Optional[str] = None

    @property
    def name(self) -> str:
        """Get channel name."""
        return "discord"

    @property
    def is_configured(self) -> bool:
        """Check if channel is configured."""
        return bool(self.webhook_url)

    def format_notification(self, notification: Notification) -> dict[str, Any]:
        """Format notification for Discord.

        Args:
            notification: Notification to format.

        Returns:
            Discord message payload.
        """
        # Determine embed color based on status
        if notification.is_success:
            color = 0x2ECC71  # Green
        elif notification.is_failure:
            color = 0xE74C3C  # Red
        else:
            color = 0x3498DB  # Blue

        # Build embed
        embed = {
            "title": notification.title[:256],
            "color": color,
            "timestamp": notification.timestamp,
        }

        if notification.message:
            embed["description"] = notification.message[:4096]

        # Add fields
        fields = []

        if notification.task_id:
            fields.append({
                "name": "Task",
                "value": notification.task_id,
                "inline": True,
            })

        if notification.status:
            fields.append({
                "name": "Status",
                "value": f"{notification.status_emoji} {notification.status}",
                "inline": True,
            })

        if notification.duration_formatted:
            fields.append({
                "name": "Duration",
                "value": notification.duration_formatted,
                "inline": True,
            })

        if notification.pr_url:
            fields.append({
                "name": "Pull Request",
                "value": f"[PR #{notification.pr_number}]({notification.pr_url})" if notification.pr_number else notification.pr_url,
                "inline": True,
            })

        if notification.deploy_url:
            fields.append({
                "name": "Preview",
                "value": f"[View]({notification.deploy_url})",
                "inline": True,
            })

        if fields:
            embed["fields"] = fields[:25]  # Discord limit

        payload = {
            "username": self.username,
            "embeds": [embed],
        }

        if self.avatar_url:
            payload["avatar_url"] = self.avatar_url

        return payload

    async def send(self, notification: Notification) -> NotificationResult:
        """Send notification to Discord.

        Args:
            notification: Notification to send.

        Returns:
            Result of the send operation.
        """
        if not self.is_configured:
            return NotificationResult(
                success=False,
                channel=self.name,
                error="Discord webhook URL not configured",
            )

        if not HAS_HTTPX:
            return NotificationResult(
                success=False,
                channel=self.name,
                error="httpx library not installed",
            )

        try:
            payload = self.format_notification(notification)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10.0,
                )

            if response.status_code in (200, 204):
                return NotificationResult(
                    success=True,
                    channel=self.name,
                    response={"status_code": response.status_code},
                )
            else:
                return NotificationResult(
                    success=False,
                    channel=self.name,
                    error=f"HTTP {response.status_code}: {response.text}",
                )

        except Exception as e:
            logger.warning(f"Discord notification failed: {e}")
            return NotificationResult(
                success=False,
                channel=self.name,
                error=str(e),
            )


@dataclass
class TelegramChannel(NotificationChannel):
    """Telegram bot notification channel.

    Attributes:
        bot_token: Telegram bot token.
        chat_id: Chat/channel ID to send to.
        parse_mode: Message parse mode (HTML or Markdown).
    """

    bot_token: str = ""
    chat_id: str = ""
    parse_mode: str = "HTML"

    @property
    def name(self) -> str:
        """Get channel name."""
        return "telegram"

    @property
    def is_configured(self) -> bool:
        """Check if channel is configured."""
        return bool(self.bot_token and self.chat_id)

    def format_notification(self, notification: Notification) -> str:
        """Format notification for Telegram.

        Args:
            notification: Notification to format.

        Returns:
            Formatted message string.
        """
        lines = [f"<b>{notification.title}</b>"]

        if notification.message:
            lines.append(f"\n{notification.message}")

        lines.append("")

        if notification.task_id:
            lines.append(f"<b>Task:</b> {notification.task_id}")

        if notification.status:
            lines.append(f"<b>Status:</b> {notification.status_emoji} {notification.status}")

        if notification.duration_formatted:
            lines.append(f"<b>Duration:</b> {notification.duration_formatted}")

        if notification.pr_url:
            pr_text = f"PR #{notification.pr_number}" if notification.pr_number else "View PR"
            lines.append(f'<b>PR:</b> <a href="{notification.pr_url}">{pr_text}</a>')

        if notification.deploy_url:
            lines.append(f'<b>Preview:</b> <a href="{notification.deploy_url}">View</a>')

        return "\n".join(lines)

    async def send(self, notification: Notification) -> NotificationResult:
        """Send notification to Telegram.

        Args:
            notification: Notification to send.

        Returns:
            Result of the send operation.
        """
        if not self.is_configured:
            return NotificationResult(
                success=False,
                channel=self.name,
                error="Telegram bot token or chat ID not configured",
            )

        if not HAS_HTTPX:
            return NotificationResult(
                success=False,
                channel=self.name,
                error="httpx library not installed",
            )

        try:
            message = self.format_notification(notification)
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": message,
                        "parse_mode": self.parse_mode,
                        "disable_web_page_preview": True,
                    },
                    timeout=10.0,
                )

            data = response.json()
            if data.get("ok"):
                return NotificationResult(
                    success=True,
                    channel=self.name,
                    response=data,
                )
            else:
                return NotificationResult(
                    success=False,
                    channel=self.name,
                    error=data.get("description", "Unknown error"),
                )

        except Exception as e:
            logger.warning(f"Telegram notification failed: {e}")
            return NotificationResult(
                success=False,
                channel=self.name,
                error=str(e),
            )


@dataclass
class DesktopChannel(NotificationChannel):
    """Desktop notification channel.

    Uses native OS notifications:
    - macOS: osascript
    - Linux: notify-send
    - Windows: toast notifications (requires additional setup)

    Attributes:
        title_prefix: Prefix for notification titles.
        sound: Whether to play a sound (macOS only).
    """

    title_prefix: str = "RALPH-AGI"
    sound: bool = True

    @property
    def name(self) -> str:
        """Get channel name."""
        return "desktop"

    @property
    def is_configured(self) -> bool:
        """Check if desktop notifications are available."""
        return sys.platform in ("darwin", "linux")

    async def send(self, notification: Notification) -> NotificationResult:
        """Send desktop notification.

        Args:
            notification: Notification to send.

        Returns:
            Result of the send operation.
        """
        if not self.is_configured:
            return NotificationResult(
                success=False,
                channel=self.name,
                error=f"Desktop notifications not supported on {sys.platform}",
            )

        try:
            title = f"{self.title_prefix}: {notification.title}"[:100]
            message = notification.message[:200] if notification.message else notification.status

            if sys.platform == "darwin":
                # macOS
                script = f'''
                display notification "{message}" with title "{title}"
                '''
                if self.sound:
                    script += ' sound name "default"'

                subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    timeout=5,
                )

            elif sys.platform == "linux":
                # Linux with notify-send
                urgency = "critical" if notification.is_failure else "normal"
                subprocess.run(
                    ["notify-send", "-u", urgency, title, message],
                    capture_output=True,
                    timeout=5,
                )

            return NotificationResult(
                success=True,
                channel=self.name,
            )

        except FileNotFoundError:
            return NotificationResult(
                success=False,
                channel=self.name,
                error="Notification command not found",
            )
        except subprocess.TimeoutExpired:
            return NotificationResult(
                success=False,
                channel=self.name,
                error="Notification command timed out",
            )
        except Exception as e:
            logger.warning(f"Desktop notification failed: {e}")
            return NotificationResult(
                success=False,
                channel=self.name,
                error=str(e),
            )
