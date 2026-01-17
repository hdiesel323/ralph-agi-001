"""Tests for notification manager."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ralph_agi.notifications.base import Notification, NotificationResult
from ralph_agi.notifications.manager import (
    NotificationManager,
    NotificationConfig,
    get_notification_manager,
    configure_notifications,
)
from ralph_agi.notifications.channels import SlackChannel, DiscordChannel


class TestNotificationConfig:
    """Tests for NotificationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = NotificationConfig()
        assert config.enabled is True
        assert config.slack == {}
        assert config.discord == {}

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "enabled": True,
            "slack": {"webhook_url": "https://hooks.slack.com/test"},
            "discord": {"webhook_url": "https://discord.com/api/webhooks/test"},
            "desktop": {"sound": False},
        }
        config = NotificationConfig.from_dict(data)

        assert config.enabled is True
        assert config.slack["webhook_url"] == "https://hooks.slack.com/test"
        assert config.discord["webhook_url"] == "https://discord.com/api/webhooks/test"
        assert config.desktop["sound"] is False

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = NotificationConfig(
            enabled=True,
            slack={"webhook_url": "test"},
        )
        data = config.to_dict()

        assert data["enabled"] is True
        assert data["slack"]["webhook_url"] == "test"


class TestNotificationManager:
    """Tests for NotificationManager class."""

    def test_manager_creation_default(self):
        """Test creating manager with default config."""
        manager = NotificationManager()
        assert manager.enabled is True

    def test_manager_creation_with_config(self):
        """Test creating manager with custom config."""
        config = NotificationConfig(enabled=False)
        manager = NotificationManager(config)
        assert manager.enabled is False

    def test_setup_channels_slack(self):
        """Test that Slack channel is set up from config."""
        config = NotificationConfig(
            slack={"webhook_url": "https://hooks.slack.com/test"},
        )
        manager = NotificationManager(config)

        assert "slack" in manager.channel_names

    def test_setup_channels_discord(self):
        """Test that Discord channel is set up from config."""
        config = NotificationConfig(
            discord={"webhook_url": "https://discord.com/api/webhooks/test"},
        )
        manager = NotificationManager(config)

        assert "discord" in manager.channel_names

    def test_setup_channels_desktop(self):
        """Test that desktop channel is set up by default."""
        config = NotificationConfig(desktop={"enabled": True})
        manager = NotificationManager(config)

        # Desktop is available on macOS/Linux
        import sys
        if sys.platform in ("darwin", "linux"):
            assert "desktop" in manager.channel_names

    def test_add_channel(self):
        """Test adding a channel."""
        manager = NotificationManager()
        channel = SlackChannel(webhook_url="https://test.com")
        manager.add_channel(channel)

        assert "slack" in manager.channel_names

    def test_remove_channel(self):
        """Test removing a channel."""
        config = NotificationConfig(
            slack={"webhook_url": "https://test.com"},
        )
        manager = NotificationManager(config)

        removed = manager.remove_channel("slack")

        assert removed is True
        assert "slack" not in manager.channel_names

    def test_remove_nonexistent_channel(self):
        """Test removing a channel that doesn't exist."""
        manager = NotificationManager()
        removed = manager.remove_channel("nonexistent")
        assert removed is False

    @pytest.mark.asyncio
    async def test_send_disabled(self):
        """Test send when notifications are disabled."""
        config = NotificationConfig(enabled=False)
        manager = NotificationManager(config)

        notif = Notification(title="Test")
        results = await manager.send(notif)

        assert results == []

    @pytest.mark.asyncio
    async def test_send_no_channels(self):
        """Test send with no configured channels."""
        config = NotificationConfig(desktop={"enabled": False})
        manager = NotificationManager(config)

        notif = Notification(title="Test")
        results = await manager.send(notif)

        assert results == []

    @pytest.mark.asyncio
    async def test_send_to_specific_channels(self):
        """Test sending to specific channels."""
        manager = NotificationManager()

        # Add mock channels
        slack = MagicMock()
        slack.name = "slack"
        slack.send = AsyncMock(return_value=NotificationResult(success=True, channel="slack"))

        discord = MagicMock()
        discord.name = "discord"
        discord.send = AsyncMock(return_value=NotificationResult(success=True, channel="discord"))

        manager._channels = [slack, discord]

        notif = Notification(title="Test")
        results = await manager.send(notif, channels=["slack"])

        assert len(results) == 1
        assert results[0].channel == "slack"
        slack.send.assert_called_once()
        discord.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_concurrent(self):
        """Test that channels are called concurrently."""
        manager = NotificationManager()

        # Add multiple mock channels
        channels = []
        for name in ["ch1", "ch2", "ch3"]:
            ch = MagicMock()
            ch.name = name
            ch.send = AsyncMock(return_value=NotificationResult(success=True, channel=name))
            channels.append(ch)

        manager._channels = channels

        notif = Notification(title="Test")
        results = await manager.send(notif)

        assert len(results) == 3
        for ch in channels:
            ch.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_handles_exceptions(self):
        """Test that exceptions from channels are handled."""
        manager = NotificationManager()

        failing = MagicMock()
        failing.name = "failing"
        failing.send = AsyncMock(side_effect=Exception("Connection error"))

        manager._channels = [failing]

        notif = Notification(title="Test")
        results = await manager.send(notif)

        assert len(results) == 1
        assert results[0].success is False
        assert "Connection error" in results[0].error

    @pytest.mark.asyncio
    async def test_notify_task_completed(self):
        """Test notify_task_completed convenience method."""
        manager = NotificationManager()

        mock_channel = MagicMock()
        mock_channel.name = "test"
        mock_channel.send = AsyncMock(return_value=NotificationResult(success=True, channel="test"))
        manager._channels = [mock_channel]

        results = await manager.notify_task_completed(
            task_id="US-123",
            task_title="Fix bug",
            success=True,
            duration_seconds=60,
        )

        assert len(results) == 1
        mock_channel.send.assert_called_once()
        call_args = mock_channel.send.call_args[0][0]
        assert call_args.task_id == "US-123"

    @pytest.mark.asyncio
    async def test_notify_batch_completed(self):
        """Test notify_batch_completed convenience method."""
        manager = NotificationManager()

        mock_channel = MagicMock()
        mock_channel.name = "test"
        mock_channel.send = AsyncMock(return_value=NotificationResult(success=True, channel="test"))
        manager._channels = [mock_channel]

        results = await manager.notify_batch_completed(
            total=10,
            succeeded=8,
            failed=2,
        )

        assert len(results) == 1
        mock_channel.send.assert_called_once()


class TestGlobalManager:
    """Tests for global manager functions."""

    def test_get_notification_manager(self):
        """Test getting global manager."""
        # Reset global state
        import ralph_agi.notifications.manager as manager_module
        manager_module._manager = None

        manager = get_notification_manager()
        assert isinstance(manager, NotificationManager)

    def test_get_notification_manager_singleton(self):
        """Test that same manager is returned."""
        import ralph_agi.notifications.manager as manager_module
        manager_module._manager = None

        manager1 = get_notification_manager()
        manager2 = get_notification_manager()
        assert manager1 is manager2

    def test_get_notification_manager_new_config(self):
        """Test that new config creates new manager."""
        import ralph_agi.notifications.manager as manager_module
        manager_module._manager = None

        manager1 = get_notification_manager()
        config = NotificationConfig(enabled=False)
        manager2 = get_notification_manager(config)

        assert manager2.enabled is False

    def test_configure_notifications(self):
        """Test configure_notifications helper."""
        import ralph_agi.notifications.manager as manager_module
        manager_module._manager = None

        manager = configure_notifications({
            "enabled": True,
            "slack": {"webhook_url": "https://test.com"},
        })

        assert manager.enabled is True
        assert "slack" in manager.channel_names
