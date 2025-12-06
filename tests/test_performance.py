"""Performance tests for Luma plugin caching and rate limiting."""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import aiohttp

from luma.api_client import LumaAPIClient, LumaCacheEntry


class TestCachePerformance:
    """Test cache performance and behavior."""

    @pytest.mark.asyncio
    async def test_cache_hit_performance(self):
        """Test that cache hits are significantly faster than cache misses."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Mock API response
                mock_response = Mock()
                mock_response.status = 200
                mock_response.headers = {}
                mock_response.json = AsyncMock(return_value={"data": "test"})
                mock_response.text = AsyncMock(return_value='{"data": "test"}')
                mock_session.get.return_value.__aenter__ = AsyncMock(
                    return_value=mock_response
                )

                # Measure cache miss time
                start_time = time.time()
                result1 = await client._make_request_with_retry(
                    "test-endpoint", {"param": "value"}
                )
                miss_time = time.time() - start_time

                # Measure cache hit time
                start_time = time.time()
                result2 = await client._make_request_with_retry(
                    "test-endpoint", {"param": "value"}
                )
                hit_time = time.time() - start_time

                # Cache hit should be much faster
                assert hit_time < miss_time * 0.1  # At least 10x faster
                assert result1 == result2

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Create cache entry that expires in 1 second
                expires_at = datetime.utcnow() + timedelta(seconds=1)
                entry = LumaCacheEntry({"data": "test"}, expires_at)
                client._cache["test_key"] = entry

                # Should be valid immediately
                assert client._is_cached_entry_valid(entry)

                # Wait for expiration
                await asyncio.sleep(1.1)

                # Should be expired now
                assert not client._is_cached_entry_valid(entry)

    @pytest.mark.asyncio
    async def test_cache_cleanup_performance(self):
        """Test that cache cleanup doesn't impact performance significantly."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Add many expired entries
                for i in range(100):
                    expires_at = datetime.utcnow() - timedelta(seconds=i)
                    entry = LumaCacheEntry({"data": f"expired_{i}"}, expires_at)
                    client._cache[f"expired_{i}"] = entry

                # Add some valid entries
                for i in range(50):
                    expires_at = datetime.utcnow() + timedelta(minutes=5)
                    entry = LumaCacheEntry({"data": f"valid_{i}"}, expires_at)
                    client._cache[f"valid_{i}"] = entry

                # Measure cleanup time
                start_time = time.time()
                client._clean_expired_cache()
                cleanup_time = time.time() - start_time

                # Should complete quickly
                assert cleanup_time < 0.1  # Less than 100ms

                # Should have removed expired entries
                assert len(client._cache) == 50

    @pytest.mark.asyncio
    async def test_large_cache_performance(self):
        """Test performance with large cache."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Fill cache with many entries
                for i in range(1000):
                    expires_at = datetime.utcnow() + timedelta(minutes=10)
                    entry = LumaCacheEntry({"data": f"large_cache_{i}"}, expires_at)
                    client._cache[f"key_{i}"] = entry

                # Measure access time to random cache entry
                start_time = time.time()
                test_key = "key_500"
                result = client._get_cached_response(test_key)
                access_time = time.time() - start_time

                # Should access quickly even with large cache
                assert access_time < 0.01  # Less than 10ms
                assert result == {"data": "large_cache_500"}

    @pytest.mark.asyncio
    async def test_cache_memory_efficiency(self):
        """Test that cache doesn't consume excessive memory."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Fill cache with large data entries
                large_data = {"large_field": "x" * 10000}  # 10KB per entry

                for i in range(100):
                    expires_at = datetime.utcnow() + timedelta(minutes=10)
                    entry = LumaCacheEntry(large_data, expires_at)
                    client._cache[f"large_entry_{i}"] = entry

                # Cache should exist and be accessible
                assert len(client._cache) == 100

                # Test cache stats
                stats = client.get_cache_stats()
                assert stats["total_entries"] == 100
                assert stats["valid_entries"] == 100
                assert stats["expired_entries"] == 0


class TestRateLimitingPerformance:
    """Test rate limiting performance."""

    @pytest.mark.asyncio
    async def test_rate_limit_delay_accuracy(self):
        """Test that rate limiting delays are accurate."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Set rate limit delay
                client._rate_limit_delay = 0.5  # 500ms

                # Mock quick responses
                mock_response = Mock()
                mock_response.status = 200
                mock_response.headers = {}
                mock_response.json = AsyncMock(return_value={"success": True})
                mock_response.text = AsyncMock(return_value='{"success": True}')
                mock_session.get.return_value.__aenter__ = AsyncMock(
                    return_value=mock_response
                )

                # Make multiple requests and measure timing
                start_time = time.time()
                for i in range(3):
                    await client._make_request_with_retry(f"endpoint_{i}", {})
                end_time = time.time()

                total_time = end_time - start_time

                # Should have at least 2 delays (between 3 requests)
                # 2 * 0.5 = 1 second minimum
                assert total_time >= 1.0
                assert total_time < 2.0  # Allow some overhead

    @pytest.mark.asyncio
    async def test_rate_limit_adaptation(self):
        """Test that rate limiting adapts based on response headers."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Test with low remaining requests
                low_remaining_headers = {
                    "x-ratelimit-remaining": "5",
                    "x-ratelimit-reset": str(time.time() + 2),  # Reset in 2 seconds
                }

                client._calculate_rate_limit_delay(low_remaining_headers)

                # Should increase delay significantly
                assert client._rate_limit_delay >= 2.0

                # Test with normal remaining requests
                normal_headers = {
                    "x-ratelimit-remaining": "100",
                    "x-ratelimit-reset": str(time.time() + 2),
                }

                original_delay = client._rate_limit_delay
                client._calculate_rate_limit_delay(normal_headers)

                # Should reduce delay
                assert client._rate_limit_delay <= original_delay

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_rate_limiting(self):
        """Test that concurrent requests respect rate limiting."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Mock quick responses
                mock_response = Mock()
                mock_response.status = 200
                mock_response.headers = {}
                mock_response.json = AsyncMock(return_value={"success": True})
                mock_response.text = AsyncMock(return_value='{"success": True}')
                mock_session.get.return_value.__aenter__ = AsyncMock(
                    return_value=mock_response
                )

                # Make concurrent requests
                start_time = time.time()
                tasks = []
                for i in range(3):
                    task = client._make_request_with_retry(f"endpoint_{i}", {})
                    tasks.append(task)

                results = await asyncio.gather(*tasks)
                end_time = time.time()

                # Should respect rate limiting even with concurrency
                total_time = end_time - start_time
                assert total_time >= 1.5  # At least 1.5 seconds for 3 requests

                # All should succeed
                assert all(r == {"success": True} for r in results)

    @pytest.mark.asyncio
    async def test_rate_limit_recovery(self):
        """Test that rate limiting recovers when limits are reset."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Set high delay due to rate limiting
                client._rate_limit_delay = 5.0

                # Mock response indicating rate limit reset
                normal_headers = {
                    "x-ratelimit-remaining": "1000",
                    "x-ratelimit-reset": str(time.time() + 1),
                }

                # Update based on normal response
                client._calculate_rate_limit_delay(normal_headers)

                # Should gradually reduce delay
                assert client._rate_limit_delay < 5.0
                assert client._rate_limit_delay >= 0.5  # But not below minimum

    @pytest.mark.asyncio
    async def test_api_timeout_handling(self):
        """Test API timeout handling performance."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Mock timeout error
                mock_session.get.side_effect = asyncio.TimeoutError("Request timeout")

                start_time = time.time()

                try:
                    await client._make_request_with_retry("slow-endpoint", {})
                except Exception:
                    pass  # Expected to fail

                end_time = time.time()

                # Should fail within reasonable time (not hang indefinitely)
                timeout_time = end_time - start_time
                assert timeout_time < 10.0  # Less than 10 seconds for timeout handling


class TestAPIResponsePerformance:
    """Test API response parsing performance."""

    @pytest.mark.asyncio
    async def test_large_response_parsing(self):
        """Test parsing of large API responses."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Create large response data
                large_response = {
                    "calendar": {"name": "Large Calendar"},
                    "featured_items": [],
                }

                # Add many events to featured_items
                for i in range(1000):
                    event_data = {
                        "event": {
                            "api_id": f"evt-{i}",
                            "name": f"Event {i}" * 10,  # Long names
                            "start_at": "2025-12-08T22:00:00.000Z",
                            "end_at": "2025-12-09T02:00:00.000Z",
                            "url": f"https://lu.ma/event-{i}",
                            "description": "x" * 1000,  # Long descriptions
                        }
                    }
                    large_response["featured_items"].append(event_data)

                # Mock API response
                mock_response = Mock()
                mock_response.status = 200
                mock_response.headers = {}
                mock_response.json = AsyncMock(return_value=large_response)
                mock_response.text = AsyncMock(return_value=str(large_response))
                mock_session.get.return_value.__aenter__ = AsyncMock(
                    return_value=mock_response
                )

                # Measure parsing time
                start_time = time.time()
                events = await client.get_calendar_events("large-calendar", limit=1000)
                end_time = time.time()

                parsing_time = end_time - start_time

                # Should parse within reasonable time
                assert parsing_time < 5.0  # Less than 5 seconds
                assert len(events) == 1000  # Should parse all events

    @pytest.mark.asyncio
    async def test_malformed_response_handling_performance(self):
        """Test performance when handling malformed responses."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Create malformed response
                malformed_response = {
                    "calendar": {"name": "Test Calendar"},
                    "featured_items": [
                        {"invalid": "structure"},
                        {"event": {"incomplete": "data"}},
                        None,  # Null entry
                        {
                            "event": {"api_id": "valid-event", "name": "Valid Event"}
                        },  # One valid
                    ],
                }

                # Mock API response
                mock_response = Mock()
                mock_response.status = 200
                mock_response.headers = {}
                mock_response.json = AsyncMock(return_value=malformed_response)
                mock_response.text = AsyncMock(return_value=str(malformed_response))
                mock_session.get.return_value.__aenter__ = AsyncMock(
                    return_value=mock_response
                )

                # Measure parsing time for malformed data
                start_time = time.time()
                events = await client.get_calendar_events(
                    "malformed-calendar", limit=100
                )
                end_time = time.time()

                parsing_time = end_time - start_time

                # Should handle malformed data quickly (skip invalid entries)
                assert parsing_time < 2.0  # Less than 2 seconds
                assert len(events) == 1  # Should extract only valid events

    @pytest.mark.asyncio
    async def test_batch_processing_performance(self):
        """Test performance of batch processing multiple subscriptions."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Create simple response for each subscription
                simple_response = {
                    "calendar": {"name": "Test Calendar"},
                    "featured_items": [
                        {
                            "event": {
                                "api_id": "evt-1",
                                "name": "Event 1",
                                "start_at": "2025-12-08T22:00:00.000Z",
                                "url": "https://lu.ma/event-1",
                            }
                        },
                        {
                            "event": {
                                "api_id": "evt-2",
                                "name": "Event 2",
                                "start_at": "2025-12-09T22:00:00.000Z",
                                "url": "https://lu.ma/event-2",
                            }
                        },
                    ],
                }

                # Mock API response
                mock_response = Mock()
                mock_response.status = 200
                mock_response.headers = {}
                mock_response.json = AsyncMock(return_value=simple_response)
                mock_response.text = AsyncMock(return_value=str(simple_response))
                mock_session.get.return_value.__aenter__ = AsyncMock(
                    return_value=mock_response
                )

                # Process multiple subscriptions
                start_time = time.time()
                tasks = []
                for i in range(10):
                    task = client.get_calendar_events(f"sub-{i}", limit=50)
                    tasks.append(task)

                results = await asyncio.gather(*tasks)
                end_time = time.time()

                batch_time = end_time - start_time

                # Should complete within reasonable time (with rate limiting)
                assert batch_time < 30.0  # Less than 30 seconds for 10 subscriptions

                # All should return events
                assert all(len(result) == 2 for result in results)


class TestMemoryPerformance:
    """Test memory usage and performance."""

    @pytest.mark.asyncio
    async def test_memory_usage_with_large_datasets(self):
        """Test memory usage doesn't grow excessively with large datasets."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Process many requests to see if memory grows
                initial_cache_size = len(client._cache)

                for batch in range(10):  # 10 batches
                    for i in range(50):  # 50 requests per batch
                        # Mock different responses
                        mock_response = Mock()
                        mock_response.status = 200
                        mock_response.headers = {}
                        mock_response.json = AsyncMock(
                            return_value={
                                "data": f"batch_{batch}_request_{i}",
                                "large_field": "x"
                                * 1000,  # Some data to simulate memory usage
                            }
                        )
                        mock_response.text = AsyncMock(return_value=str(i))
                        mock_session.get.return_value.__aenter__ = AsyncMock(
                            return_value=mock_response
                        )

                        await client._make_request_with_retry(
                            f"endpoint_{i}", {"batch": batch}
                        )

                    # Clean up expired cache entries periodically
                    client._clean_expired_cache()

                # Cache should be manageable
                final_cache_size = len(client._cache)

                # Cache size should not grow indefinitely
                assert final_cache_size < 500  # Reasonable limit

                # Should have cleaned up some entries
                if initial_cache_size == 0:
                    assert final_cache_size > 0  # Should have some entries
                    assert final_cache_size < 200  # But not too many


class TestNetworkPerformance:
    """Test network-related performance aspects."""

    @pytest.mark.asyncio
    async def test_connection_pool_reuse(self):
        """Test that HTTP connection pooling works efficiently."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            # Test with explicit session reuse
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient(session=mock_session) as client:
                # Mock response
                mock_response = Mock()
                mock_response.status = 200
                mock_response.headers = {}
                mock_response.json = AsyncMock(return_value={"success": True})
                mock_response.text = AsyncMock(return_value='{"success": True}')
                mock_session.get.return_value.__aenter__ = AsyncMock(
                    return_value=mock_response
                )

                # Make multiple requests with same client (should reuse connection)
                for i in range(5):
                    await client._make_request_with_retry(f"endpoint_{i}", {})

                # Should reuse the same session
                assert client.session is mock_session

    @pytest.mark.asyncio
    async def test_request_timeout_performance(self):
        """Test that timeouts are handled promptly."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with LumaAPIClient() as client:
                # Mock slow response
                async def slow_response(*args, **kwargs):
                    await asyncio.sleep(2)  # 2 second delay
                    response = Mock()
                    response.status = 200
                    response.headers = {}
                    response.json = AsyncMock(return_value={"success": True})
                    response.text = AsyncMock(return_value='{"success": True}')
                    return response

                mock_session.get.return_value.__aenter__ = slow_response

                start_time = time.time()

                try:
                    await client._make_request_with_retry("slow-endpoint", {})
                except Exception:
                    pass  # Expected to timeout

                end_time = time.time()

                # Should timeout within reasonable time
                timeout_duration = end_time - start_time
                assert (
                    timeout_duration < client.DEFAULT_TIMEOUT + 2
                )  # Allow some overhead
