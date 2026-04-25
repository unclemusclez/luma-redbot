#!/usr/bin/env python3
"""
Test for event deduplication fix.

This test verifies that events with the same api_id are not duplicated
in the output, even when they have multiple hosts/organizers.
"""

import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

# Add the luma directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "luma"))

from luma.core.api_client import LumaAPIClient


async def test_event_deduplication():
    """Test that events are deduplicated by api_id."""
    print("🧪 Testing event deduplication logic...")

    # Mock response data that would cause duplication
    # Same event appears twice with different hosts
    mock_response_data = {
        "calendar": {
            "api_id": "cal_123",
            "name": "Test Calendar",
            "slug": "test-calendar",
        },
        "featured_items": [
            {
                "event": {
                    "api_id": "evt_duplicate_1",
                    "name": "Agents & APIs NYC Developer Meetup",
                    "start_at": "2025-12-08T22:00:00.000Z",
                    "end_at": "2025-12-09T02:00:00.000Z",
                    "timezone": "America/New_York",
                    "url": "agents-apis-nyc-meetup",
                },
                "hosts": [{"name": "Bond AI", "slug": "bond-ai"}],
            },
            {
                "event": {
                    "api_id": "evt_duplicate_1",  # Same api_id - should be deduplicated
                    "name": "Agents & APIs NYC Developer Meetup",
                    "start_at": "2025-12-08T22:00:00.000Z",
                    "end_at": "2025-12-09T02:00:00.000Z",
                    "timezone": "America/New_York",
                    "url": "agents-apis-nyc-meetup",
                },
                "hosts": [
                    {"name": "MCP Server Builders Series", "slug": "mcp-builders"}
                ],
            },
            {
                "event": {
                    "api_id": "evt_duplicate_2",
                    "name": "AI Lightning Talks",
                    "start_at": "2025-12-10T20:00:00.000Z",
                    "end_at": "2025-12-10T22:00:00.000Z",
                    "timezone": "America/New_York",
                    "url": "ai-lightning-talks",
                },
                "hosts": [{"name": "Bond AI", "slug": "bond-ai"}],
            },
            {
                "event": {
                    "api_id": "evt_duplicate_2",  # Same api_id - should be deduplicated
                    "name": "AI Lightning Talks",
                    "start_at": "2025-12-10T20:00:00.000Z",
                    "end_at": "2025-12-10T22:00:00.000Z",
                    "timezone": "America/New_York",
                    "url": "ai-lightning-talks",
                },
                "hosts": [{"name": "Hathora", "slug": "hathora"}],
            },
            {
                "event": {
                    "api_id": "evt_unique_1",
                    "name": "The future of MCP: Model Context Protocol",
                    "start_at": "2025-12-12T18:00:00.000Z",
                    "end_at": "2025-12-12T20:00:00.000Z",
                    "timezone": "America/New_York",
                    "url": "future-of-mcp",
                },
                "hosts": [{"name": "MCP Community", "slug": "mcp-community"}],
            },
        ],
    }

    # Create the API client
    client = LumaAPIClient()

    # Mock the _make_request_with_retry method to return our test data
    with patch.object(
        client, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        mock_request.return_value = mock_response_data

        # Fetch events
        events = await client.get_calendar_events("cal_123")

        print(f"📊 Fetched {len(events)} events")

        # Verify deduplication worked
        api_ids = [event.api_id for event in events]
        unique_api_ids = set(api_ids)

        print(f"📋 Total events: {len(events)}")
        print(f"🔍 Unique api_ids: {len(unique_api_ids)}")

        # Check for the specific events mentioned in the problem
        agent_event = next((e for e in events if "Agents & APIs NYC" in e.name), None)
        ai_talks_event = next(
            (e for e in events if "AI Lightning Talks" in e.name), None
        )
        mcp_event = next((e for e in events if "future of MCP" in e.name), None)

        # Verify results
        success = True

        if not agent_event:
            print("❌ ERROR: 'Agents & APIs NYC Developer Meetup' not found")
            success = False
        elif api_ids.count(agent_event.api_id) > 1:
            print(
                f"❌ ERROR: 'Agents & APIs NYC Developer Meetup' appears {api_ids.count(agent_event.api_id)} times (should be 1)"
            )
            success = False
        else:
            print("✅ 'Agents & APIs NYC Developer Meetup' appears exactly once")

        if not ai_talks_event:
            print("❌ ERROR: 'AI Lightning Talks' not found")
            success = False
        elif api_ids.count(ai_talks_event.api_id) > 1:
            print(
                f"❌ ERROR: 'AI Lightning Talks' appears {api_ids.count(ai_talks_event.api_id)} times (should be 1)"
            )
            success = False
        else:
            print("✅ 'AI Lightning Talks' appears exactly once")

        if not mcp_event:
            print("❌ ERROR: 'The future of MCP' not found")
            success = False
        elif api_ids.count(mcp_event.api_id) > 1:
            print(
                f"❌ ERROR: 'The future of MCP' appears {api_ids.count(mcp_event.api_id)} times (should be 1)"
            )
            success = False
        else:
            print("✅ 'The future of MCP' appears exactly once")

        # Check total count
        if len(events) != 3:
            print(f"❌ ERROR: Expected 3 unique events, got {len(events)}")
            success = False
        else:
            print("✅ Correct total number of unique events (3)")

        if success:
            print("\n🎉 SUCCESS: Event deduplication is working correctly!")
            print("   Each event appears exactly once, regardless of multiple hosts.")
        else:
            print("\n💥 FAILURE: Event deduplication has issues!")

        return success


async def test_raw_data_deduplication():
    """Test deduplication in raw data parsing path."""
    print("\n🧪 Testing raw data deduplication logic...")

    # Mock response data for raw data path (no Model object)
    mock_response_data = {
        "calendar": {
            "api_id": "cal_456",
            "name": "Raw Data Calendar",
            "slug": "raw-calendar",
        },
        "featured_items": [
            {
                "event": {
                    "api_id": "evt_raw_1",
                    "name": "Raw Event Duplicate",
                    "start_at": "2025-12-15T20:00:00.000Z",
                    "end_at": "2025-12-15T22:00:00.000Z",
                    "timezone": "UTC",
                    "url": "raw-event-dup",
                },
                "hosts": [{"name": "Host A", "slug": "host-a"}],
            },
            {
                "event": {
                    "api_id": "evt_raw_1",  # Duplicate
                    "name": "Raw Event Duplicate",
                    "start_at": "2025-12-15T20:00:00.000Z",
                    "end_at": "2025-12-15T22:00:00.000Z",
                    "timezone": "UTC",
                    "url": "raw-event-dup",
                },
                "hosts": [{"name": "Host B", "slug": "host-b"}],
            },
        ],
    }

    # Create the API client
    client = LumaAPIClient()

    # Mock the _make_request_with_retry method
    with patch.object(
        client, "_make_request_with_retry", new_callable=AsyncMock
    ) as mock_request:
        mock_request.return_value = mock_response_data

        # Fetch events
        events = await client.get_calendar_events("cal_456")

        print(f"📊 Fetched {len(events)} events from raw data path")

        # Should only have 1 event despite 2 entries
        if len(events) == 1:
            print("✅ Raw data deduplication working correctly")
            return True
        else:
            print(
                f"❌ Raw data deduplication failed: Expected 1 event, got {len(events)}"
            )
            return False


async def main():
    """Run all deduplication tests."""
    print("🚀 Running Event Deduplication Tests\n")

    test1_result = await test_event_deduplication()
    test2_result = await test_raw_data_deduplication()

    if test1_result and test2_result:
        print("\n🎯 ALL TESTS PASSED: Event deduplication fix is working!")
        return 0
    else:
        print("\n💥 SOME TESTS FAILED: Event deduplication needs more work!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
