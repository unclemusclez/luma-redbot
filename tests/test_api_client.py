"""Unit tests for Luma API client functionality."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import aiohttp

from luma.api_client import (
    LumaAPIClient,
    LumaAPIError,
    LumaAPIRateLimitError,
    LumaAPINotFoundError,
    LumaAPIAuthError,
    LumaAPITimeoutError,
    LumaCacheEntry,
)


class TestLumaCacheEntry:
    """Test the LumaCacheEntry class."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        data = {"test": "data"}
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        entry = LumaCacheEntry(data, expires_at)
        assert entry.data == data
        assert entry.expires_at == expires_at

    def test_cache_entry_not_expired(self):
        """Test cache entry is not expired when still valid."""
        data = {"test": "data"}
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        entry = LumaCacheEntry(data, expires_at)
        assert not entry.is_expired()

    def test_cache_entry_expired(self):
        """Test cache entry is expired when past expiry time."""
        data = {"test": "data"}
        expires_at = datetime.utcnow() - timedelta(minutes=5)

        entry = LumaCacheEntry(data, expires_at)
        assert entry.is_expired()


class TestLumaAPIClient:
    """Test the LumaAPIClient class."""

    @pytest.fixture
    def client(self, mock_session):
        """Create a client instance for testing."""
        client = LumaAPIClient(session=mock_session)
        return client

    @pytest.fixture
    def mock_client(self, mock_session):
        """Create a mock client with session."""
        client = LumaAPIClient(session=mock_session)
        return client

    def test_client_initialization(self, mock_session):
        """Test client initialization."""
        client = LumaAPIClient(session=mock_session)
        assert client.session == mock_session
        assert client._cache == {}
        assert client._last_request_time == 0
        assert client._rate_limit_delay == 1.0
        assert client.BASE_URL == "https://api.lu.ma"
        assert client.DEFAULT_TIMEOUT == 30
        assert client.MAX_RETRIES == 3

    def test_client_context_manager(self, mock_session):
        """Test client as context manager."""
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = mock_session

            with LumaAPIClient() as client:
                assert client.session is not None

            # Session should be closed when exiting context
            mock_session.close.assert_called_once()

    def test_get_cache_key(self, client):
        """Test cache key generation."""
        endpoint = "v1/public/calendars/test"
        params = {"limit": 50, "order": "start_at"}

        cache_key = client._get_cache_key(endpoint, params)
        assert "v1/public/calendars/test" in cache_key
        assert "limit=50" in cache_key
        assert "order=start_at" in cache_key

    def test_get_cache_key_no_params(self, client):
        """Test cache key generation without params."""
        endpoint = "v1/public/calendars/test"

        cache_key = client._get_cache_key(endpoint, None)
        assert cache_key == "v1/public/calendars/test?"

    def test_is_cached_entry_valid(self, client):
        """Test cached entry validation."""
        valid_entry = LumaCacheEntry(
            {"test": "data"}, datetime.utcnow() + timedelta(minutes=5)
        )
        expired_entry = LumaCacheEntry(
            {"test": "data"}, datetime.utcnow() - timedelta(minutes=5)
        )

        assert client._is_cached_entry_valid(valid_entry) == True
        assert client._is_cached_entry_valid(expired_entry) == False

    @pytest.mark.asyncio
    async def test_get_cached_response(self, client):
        """Test getting cached response."""
        cache_key = "test_key"
        data = {"cached": "data"}
        entry = LumaCacheEntry(data, datetime.utcnow() + timedelta(minutes=5))

        client._cache[cache_key] = entry

        result = client._get_cached_response(cache_key)
        assert result == data

    @pytest.mark.asyncio
    async def test_get_cached_response_expired(self, client):
        """Test getting expired cached response."""
        cache_key = "test_key"
        data = {"cached": "data"}
        entry = LumaCacheEntry(data, datetime.utcnow() - timedelta(minutes=5))

        client._cache[cache_key] = entry

        result = client._get_cached_response(cache_key)
        assert result is None
        assert cache_key not in client._cache

    @pytest.mark.asyncio
    async def test_cache_response(self, client):
        """Test caching a response."""
        cache_key = "test_key"
        data = {"test": "data"}

        client._cache_response(cache_key, data)

        assert cache_key in client._cache
        entry = client._cache[cache_key]
        assert entry.data == data
        assert entry.expires_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_clean_expired_cache(self, client):
        """Test cleaning expired cache entries."""
        # Add some entries
        client._cache["valid"] = LumaCacheEntry(
            {"test": "data"}, datetime.utcnow() + timedelta(minutes=5)
        )
        client._cache["expired"] = LumaCacheEntry(
            {"test": "data"}, datetime.utcnow() - timedelta(minutes=5)
        )
        client._cache["valid2"] = LumaCacheEntry(
            {"test": "data"}, datetime.utcnow() + timedelta(minutes=10)
        )

        client._clean_expired_cache()

        assert "valid" in client._cache
        assert "expired" not in client._cache
        assert "valid2" in client._cache

    def test_calculate_rate_limit_delay_low_remaining(self, client):
        """Test rate limit delay calculation when close to limit."""
        response_headers = {
            "x-ratelimit-remaining": "5",
            "x-ratelimit-reset": str(datetime.utcnow().timestamp() + 30),
        }

        client._calculate_rate_limit_delay(response_headers)
        assert client._rate_limit_delay >= 30  # Should be at least reset delay

    def test_calculate_rate_limit_delay_normal(self, client):
        """Test rate limit delay calculation in normal conditions."""
        response_headers = {
            "x-ratelimit-remaining": "100",
        }

        original_delay = client._rate_limit_delay
        client._calculate_rate_limit_delay(response_headers)
        assert client._rate_limit_delay <= original_delay

    @pytest.mark.asyncio
    async def test_rate_limit_wait(self, client):
        """Test rate limit waiting logic."""
        # Set last request time to now
        client._last_request_time = datetime.utcnow().timestamp()

        # Should wait since we just made a request
        await client._rate_limit_wait()

        # Verify that some time has passed
        assert client._last_request_time > datetime.utcnow().timestamp() - 1

    def test_handle_response_status_200(self, client):
        """Test handling 200 status response."""
        try:
            client._handle_response_status(200, "OK")
        except Exception as e:
            pytest.fail(f"Should not raise exception for 200 status: {e}")

    def test_handle_response_status_401(self, client):
        """Test handling 401 status response."""
        with pytest.raises(LumaAPIAuthError):
            client._handle_response_status(401, "Unauthorized")

    def test_handle_response_status_404(self, client):
        """Test handling 404 status response."""
        with pytest.raises(LumaAPINotFoundError):
            client._handle_response_status(404, "Not Found")

    def test_handle_response_status_429(self, client):
        """Test handling 429 status response."""
        with pytest.raises(LumaAPIRateLimitError):
            client._handle_response_status(429, "Rate Limited")

    def test_handle_response_status_500(self, client):
        """Test handling 500 status response."""
        with pytest.raises(LumaAPIError):
            client._handle_response_status(500, "Server Error")

    @pytest.mark.asyncio
    async def test_make_request_with_retry_success(self, mock_client, mock_session):
        """Test successful request with retry logic."""
        endpoint = "v1/public/calendars/test"
        params = {"limit": 50}

        # Mock successful response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.text = AsyncMock(return_value='{"test": "data"}')
        mock_response.json = AsyncMock(return_value={"test": "data"})
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await mock_client._make_request_with_retry(endpoint, params)

        assert result == {"test": "data"}
        mock_session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_with_retry_rate_limit(self, mock_client, mock_session):
        """Test request with rate limit retry logic."""
        endpoint = "v1/public/calendars/test"

        # Mock rate limit response
        mock_response = Mock()
        mock_response.status = 429
        mock_response.headers = {}
        mock_response.text = AsyncMock(return_value='{"error": "rate_limited"}')
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        with pytest.raises(LumaAPIRateLimitError):
            await mock_client._make_request_with_retry(endpoint)

    @pytest.mark.asyncio
    async def test_make_request_with_retry_network_error(
        self, mock_client, mock_session
    ):
        """Test request with network error and retries."""
        endpoint = "v1/public/calendars/test"

        # Mock network error
        mock_session.get.side_effect = aiohttp.ClientError("Network error")

        with pytest.raises(LumaAPITimeoutError):
            await mock_client._make_request_with_retry(endpoint)

    @pytest.mark.asyncio
    async def test_get_calendar_events_success(self, mock_client, mock_session):
        """Test successful calendar events fetch."""
        calendar_slug = "test-calendar"

        # Mock successful response
        mock_response_data = {
            "calendar": {"name": "Test Calendar"},
            "featured_items": [
                {
                    "event": {
                        "api_id": "event1",
                        "name": "Event 1",
                        "start_at": "2025-12-07T18:00:00Z",
                    }
                }
            ],
        }

        with patch.object(mock_client, "_make_request_with_retry") as mock_request:
            mock_request.return_value = mock_response_data

            events = await mock_client.get_calendar_events(calendar_slug, limit=10)

            assert len(events) == 1
            assert events[0].api_id == "event1"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_calendar_events_empty_response(self, mock_client, mock_session):
        """Test calendar events fetch with empty response."""
        calendar_slug = "test-calendar"

        # Mock empty response
        mock_response_data = {
            "calendar": {"name": "Test Calendar"},
            "featured_items": [],
        }

        with patch.object(mock_client, "_make_request_with_retry") as mock_request:
            mock_request.return_value = mock_response_data

            events = await mock_client.get_calendar_events(calendar_slug, limit=10)

            assert len(events) == 0

    @pytest.mark.asyncio
    async def test_get_calendar_events_error(self, mock_client, mock_session):
        """Test calendar events fetch with error."""
        calendar_slug = "test-calendar"

        with patch.object(mock_client, "_make_request_with_retry") as mock_request:
            mock_request.side_effect = LumaAPINotFoundError("Calendar not found")

            with pytest.raises(LumaAPIError):
                await mock_client.get_calendar_events(calendar_slug, limit=10)

    @pytest.mark.asyncio
    async def test_get_calendar_info_success(self, mock_client, mock_session):
        """Test successful calendar info fetch."""
        calendar_slug = "test-calendar"

        # Mock successful response
        mock_response_data = {
            "calendar": {"name": "Test Calendar", "slug": "test-calendar"}
        }

        with patch.object(mock_client, "_make_request_with_retry") as mock_request:
            mock_request.return_value = mock_response_data

            info = await mock_client.get_calendar_info(calendar_slug)

            assert info == {"name": "Test Calendar", "slug": "test-calendar"}
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_calendar_info_not_found(self, mock_client, mock_session):
        """Test calendar info fetch when not found."""
        calendar_slug = "nonexistent"

        with patch.object(mock_client, "_make_request_with_retry") as mock_request:
            mock_request.side_effect = LumaAPINotFoundError("Not found")

            info = await mock_client.get_calendar_info(calendar_slug)

            assert info is None

    def test_clear_cache(self, client):
        """Test clearing the cache."""
        client._cache["test"] = Mock()
        client._cache["test2"] = Mock()

        client.clear_cache()

        assert len(client._cache) == 0

    def test_get_cache_stats(self, client):
        """Test getting cache statistics."""
        client._cache["valid"] = LumaCacheEntry(
            {"test": "data"}, datetime.utcnow() + timedelta(minutes=5)
        )
        client._cache["expired"] = LumaCacheEntry(
            {"test": "data"}, datetime.utcnow() - timedelta(minutes=5)
        )

        stats = client.get_cache_stats()

        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 1
        assert stats["expired_entries"] == 1

    def test_get_cache_stats_empty(self, client):
        """Test getting cache statistics with empty cache."""
        stats = client.get_cache_stats()

        assert stats["total_entries"] == 0
        assert stats["valid_entries"] == 0
        assert stats["expired_entries"] == 0
