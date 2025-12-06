"""Integration tests for Luma plugin end-to-end workflows."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from datetime import datetime, timedelta
import json

from luma.luma import Luma
from luma.api_client import LumaAPIClient, LumaAPITimeoutError, LumaAPINotFoundError
from luma.data_models import Subscription, ChannelGroup


class TestEndToEndWorkflows:
    """Test complete workflows across multiple components."""

    @pytest.fixture
    def mock_luma_data(self):
        """Load mock Luma API data for testing."""
        # This would normally load from .data/genai-ny.json
        return {
            "calendar": {
                "api_id": "cal-r8BcsXhhHYmA3tp",
                "name": "Bond AI - New York",
                "slug": "genai-ny",
            },
            "featured_items": [
                {
                    "event": {
                        "api_id": "evt-test-1",
                        "name": "Test Event 1",
                        "start_at": "2025-12-08T22:00:00.000Z",
                        "end_at": "2025-12-09T02:00:00.000Z",
                        "url": "https://lu.ma/test-event-1",
                    }
                },
                {
                    "event": {
                        "api_id": "evt-test-2",
                        "name": "Test Event 2",
                        "start_at": "2025-12-10T22:00:00.000Z",
                        "end_at": "2025-12-11T02:00:00.000Z",
                        "url": "https://lu.ma/test-event-2",
                    }
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_complete_subscription_workflow(
        self, mock_bot, mock_config, mock_luma_data, mock_ctx
    ):
        """Test complete workflow: add subscription -> create group -> test -> update."""
        # Setup
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Mock responses
        mock_config.guild.return_value.subscriptions = AsyncMock(return_value={})
        mock_config.guild.return_value.channel_groups = AsyncMock(return_value={})
        mock_config.guild.return_value.update_interval_hours = AsyncMock(
            return_value=24
        )
        mock_config.guild.return_value.enabled = AsyncMock(return_value=True)

        # Step 1: Add subscription
        mock_config.guild.return_value.subscriptions.set = AsyncMock()
        await cog.add_subscription(
            mock_ctx, "test-api-id", "test-calendar", "Test Calendar"
        )

        # Verify subscription was added
        mock_config.guild.return_value.subscriptions.set.assert_called_once()
        subscriptions = mock_config.guild.return_value.subscriptions.set.call_args[0][0]
        assert "test-api-id" in subscriptions
        assert subscriptions["test-api-id"]["name"] == "Test Calendar"

        # Step 2: Create channel group
        mock_channel = Mock()
        mock_channel.id = 987654321
        mock_channel.mention = "#events"

        mock_config.guild.return_value.channel_groups.set = AsyncMock()
        await cog.create_group(mock_ctx, "events-group", mock_channel, 5)

        # Verify group was created
        mock_config.guild.return_value.channel_groups.set.assert_called_once()
        groups = mock_config.guild.return_value.channel_groups.set.call_args[0][0]
        assert "events-group" in groups
        assert groups["events-group"]["max_events"] == 5

        # Step 3: Add subscription to group
        await cog.add_subscription_to_group(mock_ctx, "events-group", "test-api-id")

        # Verify subscription was added to group
        groups_after = cog.config.guild.return_value.channel_groups.set.call_args[0][0]
        assert "test-api-id" in groups_after["events-group"]["subscription_ids"]

        # Step 4: Test the subscription (mock API call)
        with patch.object(cog, "fetch_events_from_subscription") as mock_fetch:
            mock_fetch.return_value = [Mock(), Mock()]  # Two events
            await cog.test_subscription(mock_ctx, "test-api-id")

            # Verify fetch was called
            mock_fetch.assert_called_once()

        # Verify all steps completed successfully
        assert mock_ctx.send.call_count >= 3  # Multiple success messages sent

    @pytest.mark.asyncio
    async def test_full_update_workflow(
        self, mock_bot, mock_config, mock_ctx, mock_luma_data
    ):
        """Test complete update workflow with multiple subscriptions and groups."""
        # Setup
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Mock subscriptions
        subscriptions = {
            "sub1": {
                "api_id": "sub1",
                "slug": "calendar1",
                "name": "Calendar 1",
                "added_by": 123456789,
                "added_at": "2025-12-06T18:00:00Z",
            },
            "sub2": {
                "api_id": "sub2",
                "slug": "calendar2",
                "name": "Calendar 2",
                "added_by": 123456789,
                "added_at": "2025-12-06T18:00:00Z",
            },
        }

        # Mock channel groups
        groups = {
            "group1": {
                "name": "group1",
                "channel_id": 111111111,
                "subscription_ids": ["sub1", "sub2"],
                "max_events": 10,
                "created_by": 123456789,
                "created_at": "2025-12-06T18:00:00Z",
            }
        }

        mock_config.guild.return_value.subscriptions = AsyncMock(
            return_value=subscriptions
        )
        mock_config.guild.return_value.channel_groups = AsyncMock(return_value=groups)

        # Mock channel
        mock_channel = Mock()
        mock_channel.id = 111111111
        mock_channel.send = AsyncMock()
        mock_ctx.guild.get_channel.return_value = mock_channel

        # Mock API client
        mock_events = [Mock(), Mock(), Mock()]  # Three events
        with patch.object(cog, "fetch_events_from_subscription") as mock_fetch:
            mock_fetch.return_value = mock_events

            # Execute full update workflow
            await cog.update_guild_events(mock_ctx.guild)

            # Verify both subscriptions were fetched
            assert mock_fetch.call_count == 2  # Called for each subscription
            mock_fetch.assert_any_call(Subscription.from_dict(subscriptions["sub1"]))
            mock_fetch.assert_any_call(Subscription.from_dict(subscriptions["sub2"]))

        # Verify events were sent to channel
        mock_channel.send.assert_called_once()
        embed = mock_channel.send.call_args[0][0]
        assert isinstance(embed.title, str)  # Should have a title

    @pytest.mark.asyncio
    async def test_api_failure_recovery_workflow(self, mock_bot, mock_config, mock_ctx):
        """Test workflow with API failures and recovery."""
        # Setup
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Mock subscriptions - one working, one failing
        subscriptions = {
            "working-sub": {
                "api_id": "working-sub",
                "slug": "working-calendar",
                "name": "Working Calendar",
                "added_by": 123456789,
                "added_at": "2025-12-06T18:00:00Z",
            },
            "failing-sub": {
                "api_id": "failing-sub",
                "slug": "failing-calendar",
                "name": "Failing Calendar",
                "added_by": 123456789,
                "added_at": "2025-12-06T18:00:00Z",
            },
        }

        # Mock channel group
        groups = {
            "test-group": {
                "name": "test-group",
                "channel_id": 111111111,
                "subscription_ids": ["working-sub", "failing-sub"],
                "max_events": 10,
                "created_by": 123456789,
                "created_at": "2025-12-06T18:00:00Z",
            }
        }

        mock_config.guild.return_value.subscriptions = AsyncMock(
            return_value=subscriptions
        )
        mock_config.guild.return_value.channel_groups = AsyncMock(return_value=groups)

        # Mock channel
        mock_channel = Mock()
        mock_channel.id = 111111111
        mock_channel.send = AsyncMock()
        mock_ctx.guild.get_channel.return_value = mock_channel

        # Mock API client to fail for one subscription
        def mock_fetch_events(subscription):
            if subscription.api_id == "failing-sub":
                raise LumaAPITimeoutError("API timeout")
            else:
                return [Mock(), Mock()]  # Return events for working subscription

        with patch.object(
            cog, "fetch_events_from_subscription", side_effect=mock_fetch_events
        ):
            # Execute update workflow
            await cog.update_guild_events(mock_ctx.guild)

            # Should still send events from working subscription
            mock_channel.send.assert_called_once()

        # The workflow should continue despite API failure

    @pytest.mark.asyncio
    async def test_no_events_workflow(self, mock_bot, mock_config, mock_ctx):
        """Test workflow when no events are found."""
        # Setup
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Mock subscription
        subscriptions = {
            "test-sub": {
                "api_id": "test-sub",
                "slug": "empty-calendar",
                "name": "Empty Calendar",
                "added_by": 123456789,
                "added_at": "2025-12-06T18:00:00Z",
            }
        }

        # Mock channel group
        groups = {
            "test-group": {
                "name": "test-group",
                "channel_id": 111111111,
                "subscription_ids": ["test-sub"],
                "max_events": 10,
                "created_by": 123456789,
                "created_at": "2025-12-06T18:00:00Z",
            }
        }

        mock_config.guild.return_value.subscriptions = AsyncMock(
            return_value=subscriptions
        )
        mock_config.guild.return_value.channel_groups = AsyncMock(return_value=groups)

        # Mock channel
        mock_channel = Mock()
        mock_channel.id = 111111111
        mock_channel.send = AsyncMock()
        mock_ctx.guild.get_channel.return_value = mock_channel

        # Mock API client to return no events
        with patch.object(cog, "fetch_events_from_subscription", return_value=[]):
            # Execute update workflow
            await cog.update_guild_events(mock_ctx.guild)

            # Should not send any events (empty list)
            mock_channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_permission_denied_workflow(self, mock_bot, mock_config, mock_ctx):
        """Test workflow when bot lacks permissions."""
        # Setup
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Mock subscription and group
        subscriptions = {
            "test-sub": {
                "api_id": "test-sub",
                "slug": "test-calendar",
                "name": "Test Calendar",
                "added_by": 123456789,
                "added_at": "2025-12-06T18:00:00Z",
            }
        }

        groups = {
            "test-group": {
                "name": "test-group",
                "channel_id": 111111111,
                "subscription_ids": ["test-sub"],
                "max_events": 10,
                "created_by": 123456789,
                "created_at": "2025-12-06T18:00:00Z",
            }
        }

        mock_config.guild.return_value.subscriptions = AsyncMock(
            return_value=subscriptions
        )
        mock_config.guild.return_value.channel_groups = AsyncMock(return_value=groups)

        # Mock channel without send permission
        mock_channel = Mock()
        mock_channel.id = 111111111
        mock_channel.permissions_for.return_value.send_messages = False
        mock_channel.send = AsyncMock()
        mock_ctx.guild.get_channel.return_value = mock_channel

        # Mock events
        with patch.object(cog, "fetch_events_from_subscription", return_value=[Mock()]):
            # Execute update workflow
            await cog.update_guild_events(mock_ctx.guild)

            # Should not attempt to send due to permission check
            mock_channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_background_task_workflow(self, mock_bot, mock_config, mock_ctx):
        """Test background task functionality."""
        # Setup
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Mock multiple guilds
        guild1 = Mock()
        guild1.id = 111111111
        guild2 = Mock()
        guild2.id = 222222222

        mock_bot.guilds = [guild1, guild2]

        # Mock config for both guilds
        async def mock_all_guild1():
            return {
                "subscriptions": {"test": {"api_id": "test"}},
                "channel_groups": {},
                "update_interval_hours": 24,
                "last_update": None,
                "enabled": True,
            }

        async def mock_all_guild2():
            return {
                "subscriptions": {},
                "channel_groups": {},
                "update_interval_hours": 24,
                "last_update": None,
                "enabled": False,  # Disabled guild
            }

        # Mock update_guild_events for each guild
        cog.update_guild_events = AsyncMock()

        # Mock config to return different data for each guild
        def mock_guild_config(guild_id):
            mock = Mock()
            if guild_id == 111111111:
                mock.all = mock_all_guild1
                mock.subscriptions = AsyncMock(
                    return_value={"test": {"api_id": "test"}}
                )
                mock.channel_groups = AsyncMock(return_value={})
            elif guild_id == 222222222:
                mock.all = mock_all_guild2
                mock.subscriptions = AsyncMock(return_value={})
                mock.channel_groups = AsyncMock(return_value={})
            return mock

        cog.config.guild.side_effect = mock_guild_config

        # Mock last_update
        cog.config.last_update = AsyncMock()

        # Execute background update
        await cog.update_all_events()

        # Should update enabled guilds only
        cog.update_guild_events.assert_called_once_with(guild1)
        # Disabled guild should not be updated
        # assert cog.update_guild_events.call_count == 1

    @pytest.mark.asyncio
    async def test_configuration_change_workflow(self, mock_bot, mock_config, mock_ctx):
        """Test workflow when configuration changes."""
        # Setup
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Test interval change
        mock_config.guild.return_value.update_interval_hours = AsyncMock()
        mock_config.guild.return_value.enabled = AsyncMock(return_value=True)
        cog.start_update_task = AsyncMock()

        # Change interval
        await cog.set_update_interval(mock_ctx, 12)

        # Verify configuration was updated
        mock_config.guild.return_value.update_interval_hours.set.assert_called_once_with(
            12
        )
        cog.start_update_task.assert_called_once()

        # Test enable/disable
        await cog.enable_updates(mock_ctx)
        mock_config.guild.return_value.enabled.set.assert_called_with(True)

        # Mock update task
        cog.update_task = Mock()
        cog.update_task.cancel = Mock()

        await cog.disable_updates(mock_ctx)
        mock_config.guild.return_value.enabled.set.assert_called_with(False)
        cog.update_task.cancel.assert_called_once()


class TestPerformanceWorkflows:
    """Test performance aspects of the workflows."""

    @pytest.mark.asyncio
    async def test_concurrent_subscription_updates(
        self, mock_bot, mock_config, mock_ctx
    ):
        """Test updating multiple subscriptions concurrently."""
        # Setup
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Create many subscriptions
        subscriptions = {}
        for i in range(10):
            subscriptions[f"sub{i}"] = {
                "api_id": f"sub{i}",
                "slug": f"calendar{i}",
                "name": f"Calendar {i}",
                "added_by": 123456789,
                "added_at": "2025-12-06T18:00:00Z",
            }

        groups = {
            "test-group": {
                "name": "test-group",
                "channel_id": 111111111,
                "subscription_ids": list(subscriptions.keys()),
                "max_events": 10,
                "created_by": 123456789,
                "created_at": "2025-12-06T18:00:00Z",
            }
        }

        mock_config.guild.return_value.subscriptions = AsyncMock(
            return_value=subscriptions
        )
        mock_config.guild.return_value.channel_groups = AsyncMock(return_value=groups)

        # Mock channel
        mock_channel = Mock()
        mock_channel.id = 111111111
        mock_channel.send = AsyncMock()
        mock_ctx.guild.get_channel.return_value = mock_channel

        # Mock API client to simulate varying response times
        async def mock_fetch_with_delay(subscription):
            await asyncio.sleep(0.1)  # Simulate network delay
            return [Mock()]

        start_time = asyncio.get_event_loop().time()

        with patch.object(
            cog, "fetch_events_from_subscription", side_effect=mock_fetch_with_delay
        ):
            await cog.update_guild_events(mock_ctx.guild)

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # Should complete within reasonable time (allowing for network simulation)
        assert (
            duration < 5.0
        )  # Should not take more than 5 seconds for 10 subscriptions

    @pytest.mark.asyncio
    async def test_cache_performance(self, mock_bot, mock_config, mock_ctx):
        """Test caching performance."""
        # Setup API client
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Mock response
                mock_response = Mock()
                mock_response.status = 200
                mock_response.headers = {}
                mock_response.json = AsyncMock(return_value={"test": "data"})
                mock_session.get.return_value.__aenter__ = AsyncMock(
                    return_value=mock_response
                )

                # First request - should hit API
                result1 = await client._make_request_with_retry("test-endpoint", {})

                # Second request - should use cache
                result2 = await client._make_request_with_retry("test-endpoint", {})

                # Should return same data
                assert result1 == result2

                # Should only make one API call due to caching
                assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limiting_performance(self, mock_bot, mock_config, mock_ctx):
        """Test rate limiting doesn't cause excessive delays."""
        # Setup API client
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Mock fast responses
                mock_response = Mock()
                mock_response.status = 200
                mock_response.headers = {}
                mock_response.json = AsyncMock(return_value={"test": "data"})
                mock_session.get.return_value.__aenter__ = AsyncMock(
                    return_value=mock_response
                )

                start_time = asyncio.get_event_loop().time()

                # Make multiple requests
                for i in range(5):
                    await client._make_request_with_retry(f"endpoint{i}", {})

                end_time = asyncio.get_event_loop().time()
                duration = end_time - start_time

                # Should not take excessive time due to rate limiting
                # (allowing for the 1-second delay between requests)
                assert duration < 10.0  # Should complete within 10 seconds

    @pytest.mark.asyncio
    async def test_large_event_list_processing(self, mock_bot, mock_config, mock_ctx):
        """Test processing of large event lists."""
        # Setup
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Create large event list
        large_events = []
        for i in range(100):  # 100 events
            event = Mock()
            event.name = f"Event {i}"
            day = 8 + (i % 30)
            event.start_at = f"2025-12-{day:02d}T22:00:00.000Z"
            event.url = f"https://lu.ma/event-{i}"
            large_events.append(event)

        # Mock subscription and group
        subscriptions = {
            "test-sub": {
                "api_id": "test-sub",
                "slug": "large-calendar",
                "name": "Large Calendar",
                "added_by": 123456789,
                "added_at": "2025-12-06T18:00:00Z",
            }
        }

        groups = {
            "test-group": {
                "name": "test-group",
                "channel_id": 111111111,
                "subscription_ids": ["test-sub"],
                "max_events": 10,  # Limit to 10 events
                "created_by": 123456789,
                "created_at": "2025-12-06T18:00:00Z",
            }
        }

        mock_config.guild.return_value.subscriptions = AsyncMock(
            return_value=subscriptions
        )
        mock_config.guild.return_value.channel_groups = AsyncMock(return_value=groups)

        # Mock channel
        mock_channel = Mock()
        mock_channel.id = 111111111
        mock_channel.send = AsyncMock()
        mock_ctx.guild.get_channel.return_value = mock_channel

        # Process large event list
        with patch.object(
            cog, "fetch_events_from_subscription", return_value=large_events
        ):
            await cog.update_guild_events(mock_ctx.guild)

            # Should only send max_events (10) events
            mock_channel.send.assert_called_once()
            embed = mock_channel.send.call_args[0][0]

            # Should contain only the limited number of events in the description
            # (The exact parsing depends on the implementation)
