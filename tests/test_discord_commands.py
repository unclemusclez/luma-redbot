"""Unit tests for Luma Discord bot commands."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import discord
from redbot.core import Config, commands, checks

from luma_cog.luma import Luma
from luma_cog.data_models import Subscription, ChannelGroup


class TestLumaCommands:
    """Test the Luma Discord commands."""

    @pytest.fixture
    def luma_cog(self, mock_bot, mock_config):
        """Create a Luma cog instance for testing."""
        cog = Luma(mock_bot)
        cog.config = mock_config
        return cog

    @pytest.fixture
    def mock_permissions(self):
        """Mock Discord permissions."""
        perms = Mock()
        perms.send_messages = True
        return perms

    @pytest.mark.asyncio
    async def test_luma_group_command(self, luma_cog, mock_ctx):
        """Test the main luma group command."""
        # Mock the invoked_subcommand check
        mock_ctx.invoked_subcommand = None

        await luma_cog.luma_group(mock_ctx)

        # Verify that ctx.send was called with an embed
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args
        embed = call_args[0][0]  # First positional argument

        assert isinstance(embed, discord.Embed)
        assert embed.title == "Luma Events Plugin"
        assert "subscriptions" in embed.description
        assert "groups" in embed.description
        assert "config" in embed.description

    @pytest.mark.asyncio
    async def test_subscriptions_group_command_empty(self, luma_cog, mock_ctx):
        """Test subscriptions group command with no subscriptions."""
        # Mock empty subscriptions
        luma_cog.config.guild.return_value.subscriptions = AsyncMock(return_value={})

        await luma_cog.subscriptions_group(mock_ctx)

        # Should send a message about no subscriptions
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args
        message = call_args[0][0]
        assert "No subscriptions configured" in message

    @pytest.mark.asyncio
    async def test_subscriptions_group_command_with_subscriptions(
        self, luma_cog, mock_ctx
    ):
        """Test subscriptions group command with subscriptions."""
        # Mock subscriptions data
        subscriptions = {
            "test-sub-1": {
                "api_id": "test-sub-1",
                "slug": "test-calendar",
                "name": "Test Calendar",
                "added_by": 123456789,
                "added_at": "2025-12-06T18:00:00Z",
            }
        }
        luma_cog.config.guild.return_value.subscriptions = AsyncMock(
            return_value=subscriptions
        )

        await luma_cog.subscriptions_group(mock_ctx)

        # Should send an embed with subscription info
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args
        embed = call_args[0][0]

        assert isinstance(embed, discord.Embed)
        assert embed.title == "Current Subscriptions"
        assert embed.color == discord.Color.green()

    @pytest.mark.asyncio
    async def test_add_subscription_success(self, luma_cog, mock_ctx):
        """Test adding a subscription successfully."""
        # Mock existing subscriptions (empty)
        luma_cog.config.guild.return_value.subscriptions = AsyncMock(return_value={})

        # Mock setting new subscriptions
        luma_cog.config.guild.return_value.subscriptions.set = AsyncMock()

        # Call the command
        await luma_cog.add_subscription(
            mock_ctx, "test-api-id", "test-calendar", "Test Calendar"
        )

        # Verify the subscription was added
        luma_cog.config.guild.return_value.subscriptions.set.assert_called_once()
        call_args = luma_cog.config.guild.return_value.subscriptions.set.call_args
        new_subscriptions = call_args[0][0]

        assert "test-api-id" in new_subscriptions
        assert new_subscriptions["test-api-id"]["name"] == "Test Calendar"
        assert new_subscriptions["test-api-id"]["slug"] == "test-calendar"

        # Verify success message was sent
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args
        embed = call_args[0][0]

        assert isinstance(embed, discord.Embed)
        assert embed.title == "Subscription Added"
        assert embed.color == discord.Color.green()
        assert "Test Calendar" in embed.description

    @pytest.mark.asyncio
    async def test_add_subscription_duplicate(self, luma_cog, mock_ctx):
        """Test adding a duplicate subscription."""
        # Mock existing subscriptions with duplicate
        subscriptions = {
            "test-api-id": {
                "api_id": "test-api-id",
                "slug": "existing-calendar",
                "name": "Existing Calendar",
                "added_by": 123456789,
                "added_at": "2025-12-06T18:00:00Z",
            }
        }
        luma_cog.config.guild.return_value.subscriptions = AsyncMock(
            return_value=subscriptions
        )

        # Call the command
        await luma_cog.add_subscription(
            mock_ctx, "test-api-id", "test-calendar", "Test Calendar"
        )

        # Should send duplicate message
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args
        message = call_args[0][0]
        assert "already exists" in message

    @pytest.mark.asyncio
    async def test_remove_subscription_success(self, luma_cog, mock_ctx):
        """Test removing a subscription successfully."""
        # Mock existing subscriptions
        subscriptions = {
            "test-api-id": {
                "api_id": "test-api-id",
                "slug": "test-calendar",
                "name": "Test Calendar",
                "added_by": 123456789,
                "added_at": "2025-12-06T18:00:00Z",
            }
        }
        luma_cog.config.guild.return_value.subscriptions = AsyncMock(
            return_value=subscriptions
        )
        luma_cog.config.guild.return_value.subscriptions.set = AsyncMock()

        # Call the command
        await luma_cog.remove_subscription(mock_ctx, "test-api-id")

        # Verify subscription was removed
        luma_cog.config.guild.return_value.subscriptions.set.assert_called_once()
        call_args = luma_cog.config.guild.return_value.subscriptions.set.call_args
        remaining_subscriptions = call_args[0][0]

        assert "test-api-id" not in remaining_subscriptions

        # Verify success message
        mock_ctx.send.assert_called_once()
        embed = mock_ctx.send.call_args[0][0]
        assert embed.title == "Subscription Removed"
        assert embed.color == discord.Color.red()

    @pytest.mark.asyncio
    async def test_remove_subscription_not_found(self, luma_cog, mock_ctx):
        """Test removing a non-existent subscription."""
        # Mock empty subscriptions
        luma_cog.config.guild.return_value.subscriptions = AsyncMock(return_value={})

        # Call the command
        await luma_cog.remove_subscription(mock_ctx, "nonexistent-id")

        # Should send not found message
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args
        message = call_args[0][0]
        assert "No subscription found" in message

    @pytest.mark.asyncio
    async def test_groups_group_command_empty(self, luma_cog, mock_ctx):
        """Test groups group command with no groups."""
        # Mock empty channel groups
        luma_cog.config.guild.return_value.channel_groups = AsyncMock(return_value={})

        await luma_cog.groups_group(mock_ctx)

        # Should send a message about no groups
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args
        message = call_args[0][0]
        assert "No channel groups configured" in message

    @pytest.mark.asyncio
    async def test_groups_group_command_with_groups(self, luma_cog, mock_ctx):
        """Test groups group command with groups."""
        # Mock channel groups data
        channel_groups = {
            "test-group": {
                "name": "test-group",
                "channel_id": 987654321,
                "subscription_ids": ["sub1"],
                "max_events": 10,
                "created_by": 123456789,
                "created_at": "2025-12-06T18:00:00Z",
            }
        }
        luma_cog.config.guild.return_value.channel_groups = AsyncMock(
            return_value=channel_groups
        )

        # Mock guild get_channel to return a channel
        mock_channel = Mock()
        mock_channel.name = "test-channel"
        mock_ctx.guild.get_channel.return_value = mock_channel

        await luma_cog.groups_group(mock_ctx)

        # Should send an embed with group info
        mock_ctx.send.assert_called_once()
        embed = mock_ctx.send.call_args[0][0]

        assert isinstance(embed, discord.Embed)
        assert embed.title == "Current Channel Groups"
        assert embed.color == discord.Color.blue()

    @pytest.mark.asyncio
    async def test_create_group_success(self, luma_cog, mock_ctx):
        """Test creating a channel group successfully."""
        # Mock empty channel groups
        luma_cog.config.guild.return_value.channel_groups = AsyncMock(return_value={})
        luma_cog.config.guild.return_value.channel_groups.set = AsyncMock()

        # Mock channel
        mock_channel = Mock()
        mock_channel.id = 987654321
        mock_channel.mention = "#test-channel"

        # Call the command
        await luma_cog.create_group(mock_ctx, "test-group", mock_channel, 15)

        # Verify group was created
        luma_cog.config.guild.return_value.channel_groups.set.assert_called_once()
        call_args = luma_cog.config.guild.return_value.channel_groups.set.call_args
        new_groups = call_args[0][0]

        assert "test-group" in new_groups
        assert new_groups["test-group"]["channel_id"] == 987654321
        assert new_groups["test-group"]["max_events"] == 15

        # Verify success message
        mock_ctx.send.assert_called_once()
        embed = mock_ctx.send.call_args[0][0]
        assert embed.title == "Channel Group Created"
        assert embed.color == discord.Color.green()

    @pytest.mark.asyncio
    async def test_create_group_duplicate(self, luma_cog, mock_ctx):
        """Test creating a duplicate channel group."""
        # Mock existing groups
        channel_groups = {
            "test-group": {
                "name": "test-group",
                "channel_id": 111111111,
                "subscription_ids": [],
                "max_events": 10,
                "created_by": 123456789,
                "created_at": "2025-12-06T18:00:00Z",
            }
        }
        luma_cog.config.guild.return_value.channel_groups = AsyncMock(
            return_value=channel_groups
        )

        # Mock channel
        mock_channel = Mock()
        mock_channel.id = 987654321
        mock_channel.mention = "#test-channel"

        # Call the command
        await luma_cog.create_group(mock_ctx, "test-group", mock_channel, 15)

        # Should send duplicate message
        mock_ctx.send.assert_called_once()
        message = mock_ctx.send.call_args[0][0]
        assert "already exists" in message

    @pytest.mark.asyncio
    async def test_add_subscription_to_group_success(self, luma_cog, mock_ctx):
        """Test adding a subscription to a group successfully."""
        # Mock existing data
        channel_groups = {
            "test-group": {
                "name": "test-group",
                "channel_id": 987654321,
                "subscription_ids": [],
                "max_events": 10,
                "created_by": 123456789,
                "created_at": "2025-12-06T18:00:00Z",
            }
        }
        subscriptions = {
            "test-sub": {
                "api_id": "test-sub",
                "slug": "test-calendar",
                "name": "Test Calendar",
                "added_by": 123456789,
                "added_at": "2025-12-06T18:00:00Z",
            }
        }

        luma_cog.config.guild.return_value.channel_groups = AsyncMock(
            return_value=channel_groups
        )
        luma_cog.config.guild.return_value.subscriptions = AsyncMock(
            return_value=subscriptions
        )
        luma_cog.config.guild.return_value.channel_groups.set = AsyncMock()

        # Call the command
        await luma_cog.add_subscription_to_group(mock_ctx, "test-group", "test-sub")

        # Verify subscription was added to group
        luma_cog.config.guild.return_value.channel_groups.set.assert_called_once()
        call_args = luma_cog.config.guild.return_value.channel_groups.set.call_args
        updated_groups = call_args[0][0]

        assert "test-sub" in updated_groups["test-group"]["subscription_ids"]

        # Verify success message
        mock_ctx.send.assert_called_once()
        embed = mock_ctx.send.call_args[0][0]
        assert embed.title == "Subscription Added to Group"
        assert embed.color == discord.Color.green()

    @pytest.mark.asyncio
    async def test_add_subscription_to_group_not_found_group(self, luma_cog, mock_ctx):
        """Test adding subscription to non-existent group."""
        # Mock empty channel groups
        luma_cog.config.guild.return_value.channel_groups = AsyncMock(return_value={})

        # Call the command
        await luma_cog.add_subscription_to_group(
            mock_ctx, "nonexistent-group", "test-sub"
        )

        # Should send not found message
        mock_ctx.send.assert_called_once()
        message = mock_ctx.send.call_args[0][0]
        assert "No channel group found" in message

    @pytest.mark.asyncio
    async def test_add_subscription_to_group_not_found_subscription(
        self, luma_cog, mock_ctx
    ):
        """Test adding non-existent subscription to group."""
        # Mock existing group but empty subscriptions
        channel_groups = {
            "test-group": {
                "name": "test-group",
                "channel_id": 987654321,
                "subscription_ids": [],
                "max_events": 10,
                "created_by": 123456789,
                "created_at": "2025-12-06T18:00:00Z",
            }
        }
        luma_cog.config.guild.return_value.channel_groups = AsyncMock(
            return_value=channel_groups
        )
        luma_cog.config.guild.return_value.subscriptions = AsyncMock(return_value={})

        # Call the command
        await luma_cog.add_subscription_to_group(
            mock_ctx, "test-group", "nonexistent-sub"
        )

        # Should send not found message
        mock_ctx.send.assert_called_once()
        message = mock_ctx.send.call_args[0][0]
        assert "No subscription found" in message

    @pytest.mark.asyncio
    async def test_config_group_command(self, luma_cog, mock_ctx):
        """Test config group command."""
        # Mock config data
        config_data = {
            "subscriptions": {},
            "channel_groups": {},
            "update_interval_hours": 24,
            "last_update": "2025-12-06T18:00:00Z",
            "enabled": True,
        }
        luma_cog.config.guild.return_value.all = AsyncMock(return_value=config_data)

        await luma_cog.config_group(mock_ctx)

        # Should send config embed
        mock_ctx.send.assert_called_once()
        embed = mock_ctx.send.call_args[0][0]

        assert isinstance(embed, discord.Embed)
        assert embed.title == "Luma Configuration"
        assert embed.color == discord.Color.blue()

    @pytest.mark.asyncio
    async def test_set_update_interval_success(self, luma_cog, mock_ctx):
        """Test setting update interval successfully."""
        luma_cog.config.guild.return_value.update_interval_hours = AsyncMock()
        luma_cog.config.guild.return_value.enabled = AsyncMock(return_value=True)
        luma_cog.start_update_task = AsyncMock()

        # Call the command
        await luma_cog.set_update_interval(mock_ctx, 12)

        # Verify interval was set
        luma_cog.config.guild.return_value.update_interval_hours.set.assert_called_once_with(
            12
        )

        # Verify task was restarted
        luma_cog.start_update_task.assert_called_once()

        # Verify success message
        mock_ctx.send.assert_called_once()
        embed = mock_ctx.send.call_args[0][0]
        assert embed.title == "Update Interval Updated"
        assert embed.color == discord.Color.green()
        assert "12 hours" in embed.description

    @pytest.mark.asyncio
    async def test_set_update_interval_invalid_range(self, luma_cog, mock_ctx):
        """Test setting update interval with invalid range."""
        # Call the command with invalid value
        await luma_cog.set_update_interval(mock_ctx, 200)  # Too high

        # Should send error message
        mock_ctx.send.assert_called_once()
        message = mock_ctx.send.call_args[0][0]
        assert "must be between 1 and 168 hours" in message

    @pytest.mark.asyncio
    async def test_enable_updates(self, luma_cog, mock_ctx):
        """Test enabling automatic updates."""
        luma_cog.config.guild.return_value.enabled = AsyncMock()
        luma_cog.start_update_task = AsyncMock()

        # Call the command
        await luma_cog.enable_updates(mock_ctx)

        # Verify updates were enabled
        luma_cog.config.guild.return_value.enabled.set.assert_called_once_with(True)

        # Verify task was started
        luma_cog.start_update_task.assert_called_once()

        # Verify success message
        mock_ctx.send.assert_called_once()
        embed = mock_ctx.send.call_args[0][0]
        assert embed.title == "Updates Enabled"
        assert embed.color == discord.Color.green()

    @pytest.mark.asyncio
    async def test_disable_updates(self, luma_cog, mock_ctx):
        """Test disabling automatic updates."""
        # Mock update task
        luma_cog.update_task = Mock()
        luma_cog.update_task.cancel = Mock()

        luma_cog.config.guild.return_value.enabled = AsyncMock()

        # Call the command
        await luma_cog.disable_updates(mock_ctx)

        # Verify updates were disabled
        luma_cog.config.guild.return_value.enabled.set.assert_called_once_with(False)

        # Verify task was cancelled
        luma_cog.update_task.cancel.assert_called_once()
        assert luma_cog.update_task is None

        # Verify success message
        mock_ctx.send.assert_called_once()
        embed = mock_ctx.send.call_args[0][0]
        assert embed.title == "Updates Disabled"
        assert embed.color == discord.Color.red()

    @pytest.mark.asyncio
    async def test_manual_update_success(self, luma_cog, mock_ctx):
        """Test manual update command success."""
        luma_cog.update_guild_events = AsyncMock()

        # Call the command
        await luma_cog.manual_update(mock_ctx)

        # Verify update was triggered
        luma_cog.update_guild_events.assert_called_once_with(mock_ctx.guild)

        # Verify messages were sent
        assert mock_ctx.send.call_count == 2

        # Check final success message
        final_embed = mock_ctx.send.call_args[0][0]
        assert final_embed.title == "Manual Update"
        assert "completed successfully" in final_embed.description
        assert final_embed.color == discord.Color.green()

    @pytest.mark.asyncio
    async def test_manual_update_failure(self, luma_cog, mock_ctx):
        """Test manual update command failure."""
        # Mock update to raise exception
        luma_cog.update_guild_events = AsyncMock(side_effect=Exception("Test error"))

        # Call the command
        await luma_cog.manual_update(mock_ctx)

        # Verify update was attempted
        luma_cog.update_guild_events.assert_called_once_with(mock_ctx.guild)

        # Verify error message was sent
        final_embed = mock_ctx.send.call_args[0][0]
        assert final_embed.title == "Manual Update"
        assert "failed" in final_embed.description
        assert final_embed.color == discord.Color.red()

    @pytest.mark.asyncio
    async def test_test_subscription_success(self, luma_cog, mock_ctx):
        """Test subscription testing with successful fetch."""
        # Mock subscription data
        subscriptions = {
            "test-sub": {
                "api_id": "test-sub",
                "slug": "test-calendar",
                "name": "Test Calendar",
                "added_by": 123456789,
                "added_at": "2025-12-06T18:00:00Z",
            }
        }
        luma_cog.config.guild.return_value.subscriptions = AsyncMock(
            return_value=subscriptions
        )

        # Mock fetch_events_from_subscription to return events
        mock_events = [Mock(), Mock()]  # Two mock events
        luma_cog.fetch_events_from_subscription = AsyncMock(return_value=mock_events)

        # Call the command
        await luma_cog.test_subscription(mock_ctx, "test-sub")

        # Verify fetch was called
        luma_cog.fetch_events_from_subscription.assert_called_once()

        # Verify success message
        mock_ctx.send.assert_called()
        final_embed = mock_ctx.send.call_args[0][0]
        assert final_embed.title == "✅ Test Successful"
        assert final_embed.color == discord.Color.green()
        assert "2 events" in final_embed.description

    @pytest.mark.asyncio
    async def test_test_subscription_not_found(self, luma_cog, mock_ctx):
        """Test subscription testing with non-existent subscription."""
        # Mock empty subscriptions
        luma_cog.config.guild.return_value.subscriptions = AsyncMock(return_value={})

        # Call the command
        await luma_cog.test_subscription(mock_ctx, "nonexistent-sub")

        # Should send not found message
        mock_ctx.send.assert_called_once()
        message = mock_ctx.send.call_args[0][0]
        assert "No subscription found" in message

    @pytest.mark.asyncio
    async def test_cache_info(self, luma_cog, mock_ctx):
        """Test cache info command."""
        # Call the command
        await luma_cog.cache_info(mock_ctx)

        # Should send cache info embed
        mock_ctx.send.assert_called_once()
        embed = mock_ctx.send.call_args[0][0]

        assert isinstance(embed, discord.Embed)
        assert embed.title == "API Cache Statistics"
        assert embed.color == discord.Color.blue()
        assert "Cache TTL" in embed.fields[0].name
        assert "5 minutes" in embed.fields[0].value

    # Test command permissions (admin checks would be tested separately)
    # These are integration-level tests that would require proper Discord context mocking
