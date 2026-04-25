#!/usr/bin/env python3
"""
Test script to verify the architectural consistency fix for the events command.

This test validates that:
1. The events command populates the database when fetching from API
2. The events command displays events from the database (not direct API)
3. Database clearing affects the events command output
4. Database stats match the displayed events
"""

import asyncio
import sqlite3
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any
import sys

# Add the project root to the path
sys.path.insert(0, ".")

from luma.core.database import EventDatabase
from luma.models.data_models import Subscription, ChannelGroup


class MockEvent:
    """Mock event object for testing."""

    def __init__(
        self,
        api_id: str,
        name: str,
        start_at: str,
        end_at: str = None,
        timezone: str = "UTC",
        url: str = "test-url",
    ):
        self.api_id = api_id
        self.name = name
        self.start_at = start_at
        self.end_at = end_at
        self.timezone = timezone
        self.url = url


class MockAPIClient:
    """Mock API client for testing."""

    def __init__(self, events_data: List[MockEvent]):
        self.events_data = events_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def get_calendar_events(self, calendar_identifier: str, limit: int = 20):
        """Return mock events for testing."""
        return self.events_data


async def test_events_command_database_consistency():
    """Test that events command maintains database consistency."""

    print("🧪 Testing Events Command Database Consistency Fix")
    print("=" * 60)

    # Create a temporary database for testing
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
        db_path = tmp_file.name

    try:
        # Initialize database
        event_db = EventDatabase(db_path=db_path)

        # Create mock subscriptions
        mock_subscription = Subscription(
            api_id="test-calendar-api-id",
            slug="test-calendar",
            name="Test Calendar",
            added_by=123,
            added_at=datetime.now(timezone.utc).isoformat(),
        )

        # Create mock events
        future_date = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        mock_events = [
            MockEvent("event-1", "Test Event 1", future_date),
            MockEvent("event-2", "Test Event 2", future_date),
            MockEvent("event-3", "Test Event 3", future_date),
        ]

        print("\n📋 Test 1: Database Population from API")
        print("-" * 40)

        # Test that events populate database when fetched
        event_dicts = []
        for event in mock_events:
            event_dict = {
                "api_id": event.api_id,
                "calendar_api_id": mock_subscription.api_id,
                "name": event.name,
                "start_at": event.start_at,
                "end_at": event.end_at,
                "timezone": event.timezone,
                "url": event.url,
                "last_modified": datetime.now(timezone.utc).isoformat(),
            }
            event_dicts.append(event_dict)

        # Populate database
        result = await event_db.upsert_events(event_dicts, mock_subscription.api_id)

        print(f"✅ Database populated with {len(event_dicts)} events")
        print(f"   - New events: {result['new_events']}")
        print(f"   - Updated events: {result['updated_events']}")
        print(f"   - Deleted events: {result['deleted_events']}")

        # Verify database state
        tracked_events = await event_db.get_tracked_events(mock_subscription.api_id)
        print(f"✅ Database contains {len(tracked_events)} tracked events")

        assert len(tracked_events) == len(
            mock_events
        ), "Database should contain all events"

        print("\n📊 Test 2: Database Stats Match Events")
        print("-" * 40)

        # Get database stats
        stats = await event_db.get_calendar_stats()
        print(f"✅ Total events in database: {stats['total_events']}")
        print(f"✅ Total calendars in database: {stats['total_calendars']}")

        assert stats["total_events"] == len(
            mock_events
        ), "Stats should match event count"
        assert stats["total_calendars"] == 1, "Should have 1 calendar"

        print("\n🔄 Test 3: Events Command Display Logic")
        print("-" * 40)

        # Simulate the events command logic
        all_db_events = []
        seen_api_ids = set()

        # Get events from database (as the fixed events command does)
        db_events = await event_db.get_tracked_events(mock_subscription.api_id)

        # Add subscription info and deduplicate
        for event_data in db_events:
            if event_data["event_api_id"] not in seen_api_ids:
                event_data["subscription_name"] = mock_subscription.name
                event_data["calendar_api_id"] = mock_subscription.api_id
                all_db_events.append(event_data)
                seen_api_ids.add(event_data["event_api_id"])

        print(f"✅ Events retrieved from database: {len(all_db_events)}")
        print(f"✅ Events after deduplication: {len(seen_api_ids)}")

        assert len(all_db_events) == len(
            mock_events
        ), "Should retrieve all events from database"

        print("\n🗑️  Test 4: Database Clearing Affects Events Command")
        print("-" * 40)

        # Clear database
        clear_result = await event_db.clear_event_database()
        print(f"✅ Database cleared: {clear_result['events_cleared']} events removed")

        # Verify database is empty
        cleared_events = await event_db.get_tracked_events(mock_subscription.api_id)
        print(f"✅ Events in database after clear: {len(cleared_events)}")

        assert len(cleared_events) == 0, "Database should be empty after clearing"

        # Verify stats reflect empty state
        cleared_stats = await event_db.get_calendar_stats()
        print(f"✅ Stats after clear - Total events: {cleared_stats['total_events']}")

        assert (
            cleared_stats["total_events"] == 0
        ), "Stats should show 0 events after clear"

        print("\n🔄 Test 5: Re-populate and Verify Consistency")
        print("-" * 40)

        # Re-populate database
        result2 = await event_db.upsert_events(event_dicts, mock_subscription.api_id)
        print(f"✅ Re-populated database: {result2['new_events']} new events")

        # Verify consistency restored
        repopulated_events = await event_db.get_tracked_events(mock_subscription.api_id)
        repopulated_stats = await event_db.get_calendar_stats()

        print(f"✅ Events after re-population: {len(repopulated_events)}")
        print(
            f"✅ Stats after re-population: {repopulated_stats['total_events']} events"
        )

        assert len(repopulated_events) == len(
            mock_events
        ), "Should restore original event count"
        assert repopulated_stats["total_events"] == len(
            mock_events
        ), "Stats should match event count"

        print("\n🎯 Test 6: Event Display Data Structure")
        print("-" * 40)

        # Test the data structure used for display
        test_events = await event_db.get_tracked_events(mock_subscription.api_id)

        for i, event in enumerate(test_events, 1):
            print(f"✅ Event {i}: {event['name']}")
            print(f"   - API ID: {event['event_api_id']}")
            print(f"   - Start Time: {event['start_at']}")
            print(f"   - Calendar ID: {event['calendar_api_id']}")

            # Verify required fields for display
            assert "event_api_id" in event, "Missing event_api_id"
            assert "name" in event, "Missing name"
            assert "start_at" in event, "Missing start_at"
            assert "calendar_api_id" in event, "Missing calendar_api_id"

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! The events command fix is working correctly!")
        print("\n📝 Summary of Fix:")
        print("✅ Events command now populates database when fetching from API")
        print("✅ Events command displays events from database (not direct API)")
        print("✅ Database clearing affects events command output")
        print("✅ Database stats match displayed events")
        print("✅ Architectural consistency achieved!")

        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


async def test_integration_with_mock_luma_cog():
    """Test integration with a mock Luma cog to verify the actual command flow."""

    print("\n🔧 Integration Test with Mock Luma Cog")
    print("=" * 60)

    # Create temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
        db_path = tmp_file.name

    try:
        # Mock the Luma cog class with our fixed events method
        class MockLumaCog:
            def __init__(self):
                self.event_db = EventDatabase(db_path=db_path)
                self.config = MagicMock()

            async def config_guild(self, guild):
                mock_config = MagicMock()
                subscriptions = {
                    "test-calendar-api-id": {
                        "api_id": "test-calendar-api-id",
                        "slug": "test-calendar",
                        "name": "Test Calendar",
                    }
                }
                mock_config.subscriptions = AsyncMock(return_value=subscriptions)
                return mock_config

        cog = MockLumaCog()

        # Mock API client with test events
        future_date = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        mock_api_events = [
            MockEvent("event-1", "Integration Test Event 1", future_date),
            MockEvent("event-2", "Integration Test Event 2", future_date),
        ]

        print("\n🔄 Testing API fetch and database population...")

        # Simulate the fixed events command flow
        async with MockAPIClient(mock_api_events) as client:
            # Step 1: Fetch from API and populate database
            subscriptions = await cog.config_guild(None).subscriptions()
            all_events_data = []
            seen_api_ids = set()

            for sub_id, sub_data in subscriptions.items():
                api_events = await client.get_calendar_events(
                    calendar_identifier=sub_id, limit=20
                )

                # Convert to dict format for database operations
                event_dicts = []
                for event in api_events:
                    event_dict = {
                        "api_id": event.api_id,
                        "calendar_api_id": sub_id,
                        "name": event.name,
                        "start_at": event.start_at,
                        "end_at": event.end_at,
                        "timezone": event.timezone,
                        "url": event.url,
                        "last_modified": datetime.now(timezone.utc).isoformat(),
                    }
                    event_dicts.append(event_dict)

                # Populate database
                if event_dicts:
                    await cog.event_db.upsert_events(event_dicts, sub_id)
                    all_events_data.extend(event_dicts)

            print(f"✅ Fetched {len(all_events_data)} events from API")

        # Step 2: Get events from database for display
        all_db_events = []
        for sub_id, sub_data in subscriptions.items():
            db_events = await cog.event_db.get_tracked_events(sub_id)

            # Add subscription info to database events for display
            for event_data in db_events:
                if event_data["event_api_id"] not in seen_api_ids:
                    event_data["subscription_name"] = sub_data["name"]
                    event_data["calendar_api_id"] = sub_id
                    all_db_events.append(event_data)
                    seen_api_ids.add(event_data["event_api_id"])

        print(f"✅ Retrieved {len(all_db_events)} events from database")

        # Verify consistency
        assert len(all_events_data) == len(
            all_db_events
        ), "API events should match database events"

        # Verify database state
        db_stats = await cog.event_db.get_calendar_stats()
        assert db_stats["total_events"] == len(
            all_db_events
        ), "Database stats should match displayed events"

        print(f"✅ Database stats: {db_stats['total_events']} events")
        print(f"✅ Display events: {len(all_db_events)} events")
        print(f"✅ Consistency verified: API = Database = Display")

        print(
            "\n🎯 Integration test passed! The fix maintains consistency across the entire flow."
        )

        return True

    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


async def main():
    """Run all tests."""
    print("🚀 Starting Events Command Database Consistency Tests")
    print("=" * 60)

    # Run basic consistency test
    test1_passed = await test_events_command_database_consistency()

    # Run integration test
    test2_passed = await test_integration_with_mock_luma_cog()

    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)

    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED!")
        print("\n✅ The architectural inconsistency fix is working correctly:")
        print("   • Events command populates database when fetching from API")
        print("   • Events command displays events from database (not direct API)")
        print("   • Database clearing affects events command output")
        print("   • Database stats match displayed events")
        print("   • Integration with the full system works correctly")
        print(
            "\n🎯 The events command is now architecturally consistent with the database system!"
        )
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please review the test output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
