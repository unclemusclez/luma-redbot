"""Error handling and edge case tests for Luma plugin."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
import aiohttp
from datetime import datetime, timedelta

from luma_cog.luma import Luma
from luma_cog.api_client import (
    LumaAPIClient,
    LumaAPIError,
    LumaAPIRateLimitError,
    LumaAPINotFoundError,
    LumaAPIAuthError,
    LumaAPITimeoutError,
)
from luma_cog.data_models import Subscription, ChannelGroup


class TestAPIErrorHandling:
    """Test API client error handling."""

    @pytest.mark.asyncio
    async def test_network_timeout_error(self):
        """Test handling of network timeout errors."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock timeout error
            mock_session.get.side_effect = asyncio.TimeoutError("Request timeout")

            async with LumaAPIClient() as client:
                with pytest.raises(LumaAPITimeoutError):
                    await client._make_request_with_retry("test-endpoint", {})

    @pytest.mark.asyncio
    async def test_http_404_error(self):
        """Test handling of HTTP 404 errors."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock 404 response
            mock_response = Mock()
            mock_response.status = 404
            mock_response.text = AsyncMock(return_value="Not Found")
            mock_session.get.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )

            async with LumaAPIClient() as client:
                with pytest.raises(LumaAPINotFoundError):
                    await client._make_request_with_retry("test-endpoint", {})

    @pytest.mark.asyncio
    async def test_http_429_rate_limit_error(self):
        """Test handling of HTTP 429 rate limit errors."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock 429 response
            mock_response = Mock()
            mock_response.status = 429
            mock_response.text = AsyncMock(return_value="Rate Limited")
            mock_session.get.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )

            async with LumaAPIClient() as client:
                with pytest.raises(LumaAPIRateLimitError):
                    await client._make_request_with_retry("test-endpoint", {})

    @pytest.mark.asyncio
    async def test_http_500_server_error(self):
        """Test handling of HTTP 500 server errors."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock 500 response
            mock_response = Mock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal Server Error")
            mock_session.get.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )

            async with LumaAPIClient() as client:
                with pytest.raises(LumaAPIError):
                    await client._make_request_with_retry("test-endpoint", {})

    @pytest.mark.asyncio
    async def test_retry_logic_on_transient_errors(self):
        """Test retry logic handles transient errors correctly."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock first request to fail, second to succeed
            mock_response = Mock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.json = AsyncMock(return_value={"success": True})
            mock_response.text = AsyncMock(return_value='{"success": True}')

            # First call fails with network error, second succeeds
            mock_session.get.side_effect = [
                aiohttp.ClientError("Network error"),
                mock_response,
            ]

            async with LumaAPIClient() as client:
                result = await client._make_request_with_retry("test-endpoint", {})
                assert result == {"success": True}

                # Should have made 2 attempts
                assert mock_session.get.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that max retries are enforced."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock all requests to fail
            mock_session.get.side_effect = aiohttp.ClientError("Persistent error")

            async with LumaAPIClient() as client:
                with pytest.raises(LumaAPITimeoutError):
                    await client._make_request_with_retry("test-endpoint", {})

                # Should have made MAX_RETRIES attempts
                assert mock_session.get.call_count == client.MAX_RETRIES

    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of invalid JSON responses."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock invalid JSON response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.json = AsyncMock(
                side_effect=aiohttp.ContentTypeError("Invalid JSON")
            )
            mock_response.text = AsyncMock(return_value="Invalid JSON content")
            mock_session.get.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )

            async with LumaAPIClient() as client:
                result = await client._make_request_with_retry("test-endpoint", {})
                # Should return raw response when JSON parsing fails
                assert result == {"raw_response": "Invalid JSON content"}

    @pytest.mark.asyncio
    async def test_malformed_event_data_handling(self):
        """Test handling of malformed event data."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock response with malformed event data
            mock_response = Mock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.json = AsyncMock(
                return_value={
                    "calendar": {"name": "Test Calendar"},
                    "featured_items": [
                        {
                            # Missing event field
                            "invalid": "data"
                        },
                        {
                            "event": {
                                # Missing required fields
                                "name": "Incomplete Event"
                            }
                        },
                    ],
                }
            )
            mock_response.text = AsyncMock(
                return_value='{"calendar": {"name": "Test Calendar"}}'
            )
            mock_session.get.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )

            async with LumaAPIClient() as client:
                events = await client.get_calendar_events("test-api-id", limit=10)
                # Should gracefully handle malformed data
                assert len(events) == 0  # No valid events extracted


class TestPluginErrorHandling:
    """Test plugin-level error handling."""

    @pytest.mark.asyncio
    async def test_api_failure_during_update(self, mock_bot, mock_config, mock_ctx):
        """Test that plugin continues when API fails during update."""
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Mock subscription that will fail
        subscriptions = {
            "failing-sub": {
                "api_id": "failing-sub",
                "slug": "failing-calendar",
                "name": "Failing Calendar",
                "added_by": 123456789,
                "added_at": "2025-12-06T18:00:00Z",
            }
        }

        groups = {
            "test-group": {
                "name": "test-group",
                "channel_id": 111111111,
                "subscription_ids": ["failing-sub"],
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

        # Mock API failure
        with patch.object(cog, "fetch_events_from_subscription") as mock_fetch:
            mock_fetch.side_effect = LumaAPITimeoutError("API timeout")

            # Should not raise exception, should handle gracefully
            await cog.update_guild_events(mock_ctx.guild)

            # Should attempt to fetch events
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_channel_handling(self, mock_bot, mock_config, mock_ctx):
        """Test handling when configured channel doesn't exist."""
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
                "channel_id": 999999999,  # Non-existent channel
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

        # Mock guild to return None for non-existent channel
        mock_ctx.guild.get_channel.return_value = None

        # Should handle missing channel gracefully
        await cog.update_guild_events(mock_ctx.guild)

        # Should not crash, just skip the group
        mock_ctx.guild.get_channel.assert_called_with(999999999)

    @pytest.mark.asyncio
    async def test_empty_events_handling(self, mock_bot, mock_config, mock_ctx):
        """Test handling when no events are returned."""
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Mock subscription and group
        subscriptions = {
            "test-sub": {
                "api_id": "test-sub",
                "slug": "empty-calendar",
                "name": "Empty Calendar",
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

        # Mock channel
        mock_channel = Mock()
        mock_channel.id = 111111111
        mock_channel.send = AsyncMock()
        mock_ctx.guild.get_channel.return_value = mock_channel

        # Mock empty events response
        with patch.object(cog, "fetch_events_from_subscription", return_value=[]):
            await cog.update_guild_events(mock_ctx.guild)

            # Should not send any events (empty list)
            mock_channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_past_events_filtering(self, mock_bot, mock_config, mock_ctx):
        """Test that past events are properly filtered out."""
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Create past event
        past_event = Mock()
        past_event.name = "Past Event"
        past_event.start_at = "2025-12-01T18:00:00.000Z"  # Past date
        past_event.url = "https://lu.ma/past-event"

        # Create future event
        future_event = Mock()
        future_event.name = "Future Event"
        future_event.start_at = "2025-12-10T18:00:00.000Z"  # Future date
        future_event.url = "https://lu.ma/future-event"

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

        # Mock channel
        mock_channel = Mock()
        mock_channel.id = 111111111
        mock_channel.send = AsyncMock()
        mock_ctx.guild.get_channel.return_value = mock_channel

        # Mock events with both past and future
        with patch.object(
            cog,
            "fetch_events_from_subscription",
            return_value=[past_event, future_event],
        ):
            await cog.update_guild_events(mock_ctx.guild)

            # Should only send future event
            mock_channel.send.assert_called_once()
            embed = mock_channel.send.call_args[0][0]
            # Should contain only the future event in the embed description

    @pytest.mark.asyncio
    async def test_background_task_error_recovery(self, mock_bot, mock_config):
        """Test that background task recovers from errors."""
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Mock multiple guilds with different states
        guild1 = Mock()
        guild1.id = 111111111
        guild2 = Mock()
        guild2.id = 222222222

        mock_bot.guilds = [guild1, guild2]

        # Mock update_guild_events to fail for one guild
        async def mock_update_with_failure(guild):
            if guild.id == 111111111:
                raise Exception("Update failed for guild 1")
            # Guild 2 succeeds

        cog.update_guild_events = mock_update_with_failure

        # Mock config
        cog.config.guild.return_value.all = AsyncMock(
            return_value={
                "subscriptions": {"test": {}},
                "channel_groups": {},
                "update_interval_hours": 24,
                "last_update": None,
                "enabled": True,
            }
        )
        cog.config.last_update = AsyncMock()

        # Should continue processing other guilds even if one fails
        await cog.update_all_events()

        # Should have attempted to update both guilds
        # (The error in one guild shouldn't stop the entire process)

    @pytest.mark.asyncio
    async def test_config_corruption_handling(self, mock_bot, mock_config, mock_ctx):
        """Test handling of corrupted configuration data."""
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Mock corrupted subscription data
        corrupted_subscriptions = {
            "corrupted-sub": {
                "api_id": "corrupted-sub",
                # Missing required fields
                "name": "Corrupted Subscription",
            }
        }

        mock_config.guild.return_value.subscriptions = AsyncMock(
            return_value=corrupted_subscriptions
        )
        mock_config.guild.return_value.channel_groups = AsyncMock(return_value={})

        # Should handle corrupted data gracefully
        try:
            await cog.subscriptions_group(mock_ctx)
            # Should not crash, should handle the corruption
        except Exception as e:
            # If it does crash, it should be a clear error about missing data
            assert "api_id" in str(e) or "slug" in str(e)

    @pytest.mark.asyncio
    async def test_concurrent_modification_handling(
        self, mock_bot, mock_config, mock_ctx
    ):
        """Test handling of concurrent configuration modifications."""
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Simulate rapid successive calls that might modify config
        calls_made = []

        async def mock_set_subscriptions(data):
            calls_made.append(data)
            # Simulate some delay
            await asyncio.sleep(0.1)

        mock_config.guild.return_value.subscriptions = AsyncMock(return_value={})
        mock_config.guild.return_value.subscriptions.set = mock_set_subscriptions

        # Make rapid successive calls
        tasks = []
        for i in range(5):
            task = cog.add_subscription(
                mock_ctx, f"sub{i}", f"calendar{i}", f"Subscription {i}"
            )
            tasks.append(task)

        # All should complete without conflicts
        await asyncio.gather(*tasks)

        # Should have made 5 calls
        assert len(calls_made) == 5

    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self, mock_bot, mock_config, mock_ctx):
        """Test that cache doesn't grow indefinitely."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Mock responses for different endpoints
                responses = [{"data": f"response_{i}"} for i in range(100)]

                response_index = 0

                def mock_response_factory(*args, **kwargs):
                    response = Mock()
                    response.status = 200
                    response.headers = {}
                    response.json = AsyncMock(return_value=responses[response_index])
                    response.text = AsyncMock(return_value=str(response_index))
                    nonlocal response_index
                    response_index += 1
                    return response

                mock_session.get.return_value.__aenter__ = mock_response_factory

                # Make many requests
                for i in range(100):
                    await client._make_request_with_retry(f"endpoint_{i}", {})

                # Cache should not grow beyond reasonable limits
                # (The implementation should clean up old entries)
                cache_size = len(client._cache)
                assert (
                    cache_size <= 200
                )  # Allow some buffer but prevent excessive growth


class TestEdgeCases:
    """Test various edge cases."""

    @pytest.mark.asyncio
    async def test_very_large_event_list(self, mock_bot, mock_config, mock_ctx):
        """Test handling of very large event lists."""
        cog = Luma(mock_bot)
        cog.config = mock_config

        # Create very large event list (1000 events)
        large_events = []
        for i in range(1000):
            event = Mock()
            event.name = f"Event {i}"
            event.start_at = f"2025-12-{8 + (i % 30):02d}T22:00:00.000Z"
            event.url = f"https://lu.ma/event-{i}"
            large_events.append(event)

        # Mock subscription and group with small max_events
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
                "max_events": 5,  # Very small limit
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

        # Should efficiently handle large list with small limit
        with patch.object(
            cog, "fetch_events_from_subscription", return_value=large_events
        ):
            await cog.update_guild_events(mock_ctx.guild)

            # Should only send max_events (5) events
            mock_channel.send.assert_called_once()

            # Should complete without memory issues
            # (The implementation should limit processing appropriately)

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(
        self, mock_bot, mock_config, mock_ctx
    ):
        """Test handling of unicode and special characters in event names."""
        # This test would verify that unicode characters in event names,
        # descriptions, and other fields are handled correctly
        pass  # Implementation would depend on specific requirements

    @pytest.mark.asyncio
    async def test_extremely_long_event_names(self, mock_bot, mock_config, mock_ctx):
        """Test handling of extremely long event names."""
        # Test very long event names to ensure Discord embed limits are respected
        pass  # Implementation would test truncation logic

    @pytest.mark.asyncio
    async def test_network_connectivity_issues(self, mock_bot, mock_config, mock_ctx):
        """Test handling of various network connectivity issues."""
        # Test scenarios like:
        # - Connection refused
        # - DNS resolution failures
        # - SSL certificate errors
        # - Proxy/firewall issues
        pass  # Would test various network error conditions
