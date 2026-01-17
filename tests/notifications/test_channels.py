"""Tests for notification channels."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import sys

from ralph_agi.notifications.base import Notification, NotificationResult
from ralph_agi.notifications.channels import (
    SlackChannel,
    DiscordChannel,
    TelegramChannel,
    DesktopChannel,
)


class TestSlackChannel:
    """Tests for SlackChannel."""

    def test_name(self):
        """Test channel name."""
        channel = SlackChannel()
        assert channel.name == "slack"

    def test_is_configured_false(self):
        """Test is_configured when not configured."""
        channel = SlackChannel()
        assert channel.is_configured is False

    def test_is_configured_true(self):
        """Test is_configured when configured."""
        channel = SlackChannel(webhook_url="https://hooks.slack.com/services/...")
        assert channel.is_configured is True

    def test_format_notification(self):
        """Test notification formatting."""
        channel = SlackChannel(webhook_url="https://test.com")
        notif = Notification(
            title="Test Task Complete",
            message="Details here",
            task_id="US-123",
            status="success",
            duration_seconds=60,
        )

        payload = channel.format_notification(notif)

        assert payload["username"] == "RALPH-AGI"
        assert "blocks" in payload
        assert payload["text"] == "Test Task Complete"

    def test_format_notification_with_links(self):
        """Test notification formatting with PR and deploy URLs."""
        channel = SlackChannel(webhook_url="https://test.com")
        notif = Notification(
            title="Task Done",
            pr_number=100,
            pr_url="https://github.com/test/pr/100",
            deploy_url="https://preview.test.com",
        )

        payload = channel.format_notification(notif)

        # Should have actions block with buttons
        actions = [b for b in payload["blocks"] if b.get("type") == "actions"]
        assert len(actions) == 1
        assert len(actions[0]["elements"]) == 2

    @pytest.mark.asyncio
    async def test_send_not_configured(self):
        """Test send when not configured."""
        channel = SlackChannel()
        notif = Notification(title="Test")

        result = await channel.send(notif)

        assert result.success is False
        assert "not configured" in result.error


class TestDiscordChannel:
    """Tests for DiscordChannel."""

    def test_name(self):
        """Test channel name."""
        channel = DiscordChannel()
        assert channel.name == "discord"

    def test_is_configured_false(self):
        """Test is_configured when not configured."""
        channel = DiscordChannel()
        assert channel.is_configured is False

    def test_is_configured_true(self):
        """Test is_configured when configured."""
        channel = DiscordChannel(webhook_url="https://discord.com/api/webhooks/...")
        assert channel.is_configured is True

    def test_format_notification_success(self):
        """Test notification formatting for success."""
        channel = DiscordChannel(webhook_url="https://test.com")
        notif = Notification(
            title="Task Complete",
            message="All tests passed",
            status="success",
        )

        payload = channel.format_notification(notif)

        assert payload["username"] == "RALPH-AGI"
        assert "embeds" in payload
        assert len(payload["embeds"]) == 1
        assert payload["embeds"][0]["color"] == 0x2ECC71  # Green

    def test_format_notification_failure(self):
        """Test notification formatting for failure."""
        channel = DiscordChannel(webhook_url="https://test.com")
        notif = Notification(
            title="Task Failed",
            status="failure",
        )

        payload = channel.format_notification(notif)

        assert payload["embeds"][0]["color"] == 0xE74C3C  # Red

    @pytest.mark.asyncio
    async def test_send_not_configured(self):
        """Test send when not configured."""
        channel = DiscordChannel()
        notif = Notification(title="Test")

        result = await channel.send(notif)

        assert result.success is False
        assert "not configured" in result.error


class TestTelegramChannel:
    """Tests for TelegramChannel."""

    def test_name(self):
        """Test channel name."""
        channel = TelegramChannel()
        assert channel.name == "telegram"

    def test_is_configured_false_missing_token(self):
        """Test is_configured when token is missing."""
        channel = TelegramChannel(chat_id="123")
        assert channel.is_configured is False

    def test_is_configured_false_missing_chat_id(self):
        """Test is_configured when chat_id is missing."""
        channel = TelegramChannel(bot_token="token123")
        assert channel.is_configured is False

    def test_is_configured_true(self):
        """Test is_configured when configured."""
        channel = TelegramChannel(bot_token="token123", chat_id="123")
        assert channel.is_configured is True

    def test_format_notification(self):
        """Test notification formatting."""
        channel = TelegramChannel(bot_token="token", chat_id="123")
        notif = Notification(
            title="Task Done",
            message="Details",
            task_id="T-1",
            status="success",
            duration_seconds=30,
        )

        message = channel.format_notification(notif)

        assert "<b>Task Done</b>" in message
        assert "Details" in message
        assert "T-1" in message
        assert "✅" in message

    def test_format_notification_with_links(self):
        """Test notification formatting with links."""
        channel = TelegramChannel(bot_token="token", chat_id="123")
        notif = Notification(
            title="PR Created",
            pr_number=50,
            pr_url="https://github.com/test/pr/50",
        )

        message = channel.format_notification(notif)

        assert 'href="https://github.com/test/pr/50"' in message

    @pytest.mark.asyncio
    async def test_send_not_configured(self):
        """Test send when not configured."""
        channel = TelegramChannel()
        notif = Notification(title="Test")

        result = await channel.send(notif)

        assert result.success is False
        assert "not configured" in result.error


class TestDesktopChannel:
    """Tests for DesktopChannel."""

    def test_name(self):
        """Test channel name."""
        channel = DesktopChannel()
        assert channel.name == "desktop"

    def test_is_configured_macos(self):
        """Test is_configured on macOS."""
        channel = DesktopChannel()
        if sys.platform == "darwin":
            assert channel.is_configured is True

    def test_is_configured_linux(self):
        """Test is_configured on Linux."""
        channel = DesktopChannel()
        if sys.platform == "linux":
            assert channel.is_configured is True

    @pytest.mark.asyncio
    async def test_send_unsupported_platform(self):
        """Test send on unsupported platform."""
        channel = DesktopChannel()

        # Use PropertyMock to mock the is_configured property on the class
        with patch.object(
            type(channel), "is_configured", new_callable=PropertyMock, return_value=False
        ):
            notif = Notification(title="Test")
            result = await channel.send(notif)

            assert result.success is False
            assert "not supported" in result.error

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        sys.platform not in ("darwin", "linux"),
        reason="Only runs on macOS/Linux",
    )
    async def test_send_macos_linux(self):
        """Test send on macOS/Linux with mocked subprocess."""
        channel = DesktopChannel()
        notif = Notification(title="Test Notification", message="Test message")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = await channel.send(notif)

            assert result.success is True
            mock_run.assert_called_once()
