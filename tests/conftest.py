"""Test configuration and shared fixtures for Luma plugin tests."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta
import discord
from typing import Dict, List, Any

# Mock data for testing
MOCK_EVENT_DATA = {
    "api_id": "test-event-123",
    "calendar_api_id": "test-calendar-456",
    "cover_url": "https://example.com/cover.jpg",
    "end_at": "2025-12-07T20:00:00Z",
    "event_type": "online",
    "hide_rsvp": False,
    "location_type": "online",
    "name": "Test Event",
    "one_to_one": False,
    "recurrence_id": None,
    "show_guest_list": True,
    "start_at": "2025-12-07T18:00:00Z",
    "timezone": "UTC",
    "url": "https://lu.ma/test-event",
    "user_api_id": "user-789",
    "visibility": "public",
    "waitlist_enabled": False,
    "virtual_info": {"has_access": True},
    "geo_address_info": {"mode": "online"},
    "geo_address_visibility": "public",
    "coordinate": {"latitude": 0.0, "longitude": 0.0},
}

MOCK_SUBSCRIPTION_DATA = {
    "api_id": "test-subscription-123",
    "slug": "test-calendar",
    "name": "Test Calendar",
    "added_by": 123456789,
    "added_at": "2025-12-06T18:00:00Z",
}

MOCK_CHANNEL_GROUP_DATA = {
    "name": "test-group",
    "channel_id": 987654321,
    "subscription_ids": ["test-subscription-123"],
    "max_events": 10,
    "created_by": 123456789,
    "created_at": "2025-12-06T18:00:00Z",
}


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_bot():
    """Create a mock Red bot instance."""
    bot = Mock()
    bot.loop = asyncio.get_event_loop()
    bot.guilds = []
    return bot


@pytest.fixture
def mock_guild():
    """Create a mock Discord guild."""
    guild = Mock(spec=discord.Guild)
    guild.id = 123456789
    guild.me = Mock()
    guild.me.permissions_for.return_value.send_messages = True
    return guild


@pytest.fixture
def mock_channel():
    """Create a mock Discord text channel."""
    channel = Mock(spec=discord.TextChannel)
    channel.id = 987654321
    channel.name = "test-channel"
    channel.permissions_for.return_value.send_messages = True
    return channel


@pytest.fixture
def mock_ctx():
    """Create a mock Discord command context."""
    ctx = Mock()
    ctx.author = Mock()
    ctx.author.id = 123456789
    ctx.author.mention = "<@123456789>"
    ctx.guild = Mock()
    ctx.guild.id = 123456789
    ctx.guild.get_channel.return_value = Mock()
    ctx.guild.get_channel.return_value.mention = "#test-channel"
    ctx.channel = Mock()
    ctx.channel.send = AsyncMock()
    ctx.channel.id = 111111111
    ctx.send = AsyncMock()
    return ctx


@pytest.fixture
def mock_config():
    """Create a mock Config instance."""
    config = Mock()
    config.guild = Mock()
    config.guild.return_value.subscriptions = AsyncMock(return_value={})
    config.guild.return_value.channel_groups = AsyncMock(return_value={})
    config.guild.return_value.update_interval_hours = AsyncMock(return_value=24)
    config.guild.return_value.enabled = AsyncMock(return_value=True)
    config.guild.return_value.last_update = AsyncMock(return_value=None)
    config.guild.return_value.all = AsyncMock(
        return_value={
            "subscriptions": {},
            "channel_groups": {},
            "update_interval_hours": 24,
            "last_update": None,
            "enabled": True,
        }
    )
    config.enabled = AsyncMock(return_value=True)
    config.last_update = AsyncMock()
    return config


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    response = Mock()
    response.status = 200
    response.headers = {}
    response.text = AsyncMock(return_value='{"test": "data"}')
    response.json = AsyncMock(return_value={"test": "data"})
    return response


@pytest.fixture
def sample_events():
    """Create sample event objects for testing."""
    from models.calendar_get import Event

    # Create two test events
    events = []
    for i in range(2):
        event = Event(**MOCK_EVENT_DATA)
        event.name = f"Test Event {i+1}"
        event.api_id = f"test-event-{i+1}"
        events.append(event)

    return events


@pytest.fixture
def sample_subscription():
    """Create a sample subscription for testing."""
    from luma.data_models import Subscription

    return Subscription(**MOCK_SUBSCRIPTION_DATA)


@pytest.fixture
def sample_channel_group():
    """Create a sample channel group for testing."""
    from luma.data_models import ChannelGroup

    return ChannelGroup(**MOCK_CHANNEL_GROUP_DATA)


@pytest.fixture
def luma_config_data():
    """Create sample Luma configuration data."""
    return {
        "subscriptions": {"test-subscription-123": MOCK_SUBSCRIPTION_DATA},
        "channel_groups": {"test-group": MOCK_CHANNEL_GROUP_DATA},
        "update_interval_hours": 24,
        "last_update": "2025-12-06T18:00:00Z",
        "enabled": True,
    }
