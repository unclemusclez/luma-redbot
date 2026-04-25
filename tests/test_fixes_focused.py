#!/usr/bin/env python3
"""
Test script to verify the critical fixes for the Luma cog.
This script tests the fixes for:
1. Event object subscriptable errors
2. Model validation errors (tiktok_handle)
3. Database UNIQUE constraint errors
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

# Add the luma package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "luma"))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("test_fixes")


def test_event_model_validation():
    """Test that the Event model can be instantiated without tiktok_handle errors."""
    print("\n=== Testing Event Model Validation ===")
    try:
        from luma.models.calendar_get import Event, Host, FeaturedItem

        # Test Host model with tiktok_handle as optional
        host_data = {
            "name": "Test Host",
            "api_id": "test_api_123",
            "timezone": "UTC",
            "avatar_url": "https://example.com/avatar.jpg",
            "is_verified": False,
            "tiktok_handle": "torc.dev",  # This should work now
        }

        host = Host(**host_data)
        print(
            f"✅ Host model validation passed: {host.name} (tiktok: {host.tiktok_handle})"
        )

        # Test Event model
        event_data = {
            "api_id": "event_123",
            "calendar_api_id": "cal_456",
            "cover_url": "https://example.com/cover.jpg",
            "end_at": "2025-12-07T10:00:00Z",
            "event_type": "public",
            "hide_rsvp": False,
            "location_type": "physical",
            "name": "Test Event",
            "one_to_one": False,
            "show_guest_list": False,
            "start_at": "2025-12-07T09:00:00Z",
            "timezone": "UTC",
            "url": "https://example.com/event",
            "user_api_id": "user_123",
            "visibility": "public",
            "waitlist_enabled": False,
            "virtual_info": {"has_access": True},
            "geo_address_visibility": "public",
        }

        event = Event(**event_data)
        print(f"✅ Event model validation passed: {event.name}")

        return True

    except Exception as e:
        print(f"❌ Model validation failed: {e}")
        return False


def test_database_upsert_logic():
    """Test the database upsert logic with duplicate handling."""
    print("\n=== Testing Database Upsert Logic ===")
    try:
        from luma.core.database import EventDatabase

        # Create in-memory database for testing
        db = EventDatabase(db_path=":memory:")

        # Test events data
        test_events = [
            {
                "api_id": "event_1",
                "name": "Test Event 1",
                "start_at": "2025-12-07T09:00:00Z",
                "end_at": "2025-12-07T10:00:00Z",
                "timezone": "UTC",
                "event_type": "public",
                "url": "https://example.com/event1",
            },
            {
                "api_id": "event_2",
                "name": "Test Event 2",
                "start_at": "2025-12-08T09:00:00Z",
                "end_at": "2025-12-08T10:00:00Z",
                "timezone": "UTC",
                "event_type": "public",
                "url": "https://example.com/event2",
            },
        ]

        # Test first upsert
        async def test_first_upsert():
            result1 = await db.upsert_events(test_events, "calendar_123")
            print(f"First upsert result: {result1}")
            assert (
                result1["new_events"] == 2
            ), f"Expected 2 new events, got {result1['new_events']}"
            print("✅ First upsert successful")

            # Test duplicate upsert (should handle UNIQUE constraint)
            test_events[0]["name"] = "Updated Test Event 1"  # Modify first event
            result2 = await db.upsert_events(test_events, "calendar_123")
            print(f"Duplicate upsert result: {result2}")
            assert (
                result2["updated_events"] == 1
            ), f"Expected 1 updated event, got {result2['updated_events']}"
            assert (
                result2["new_events"] == 1
            ), f"Expected 1 new event, got {result2['new_events']}"
            print("✅ Duplicate upsert successful (no UNIQUE constraint error)")

            return True

        # Run the async test
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(test_first_upsert())

    except Exception as e:
        print(f"❌ Database upsert test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_event_object_access():
    """Test that Event objects can be accessed properly."""
    print("\n=== Testing Event Object Access ===")
    try:
        from luma.models.calendar_get import Event

        # Create a test event
        event_data = {
            "api_id": "test_event",
            "calendar_api_id": "test_cal",
            "cover_url": "https://example.com/cover.jpg",
            "end_at": "2025-12-07T10:00:00Z",
            "event_type": "public",
            "hide_rsvp": False,
            "location_type": "physical",
            "name": "Test Event",
            "one_to_one": False,
            "show_guest_list": False,
            "start_at": "2025-12-07T09:00:00Z",
            "timezone": "UTC",
            "url": "https://example.com/event",
            "user_api_id": "test_user",
            "visibility": "public",
            "waitlist_enabled": False,
            "virtual_info": {"has_access": True},
            "geo_address_visibility": "public",
        }

        event = Event(**event_data)

        # Test attribute access (not dictionary access)
        assert event.api_id == "test_event"
        assert event.name == "Test Event"
        assert event.start_at == "2025-12-07T09:00:00Z"

        print(f"✅ Event object access successful:")
        print(f"   - API ID: {event.api_id}")
        print(f"   - Name: {event.name}")
        print(f"   - Start time: {event.start_at}")

        return True

    except Exception as e:
        print(f"❌ Event object access test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_integration():
    """Test integration of all fixes."""
    print("\n=== Testing Integration ===")
    try:
        # This simulates the main workflow that was failing
        from luma.models.calendar_get import Event, Host
        from luma.core.database import EventDatabase

        # Test event processing workflow
        events_data = [
            {
                "api_id": "event_1",
                "calendar_api_id": "cal_123",
                "name": "Integration Test Event",
                "start_at": "2025-12-07T09:00:00Z",
                "end_at": "2025-12-07T10:00:00Z",
                "timezone": "UTC",
                "event_type": "public",
                "url": "https://example.com/event",
            }
        ]

        # Convert to Event objects (this would fail before the fixes)
        events = []
        for event_data in events_data:
            event = Event(**event_data)
            events.append(event)

        print(f"✅ Successfully created {len(events)} Event objects")

        # Test database operations
        db = EventDatabase(db_path=":memory:")
        result = await db.upsert_events(events_data, "cal_123")
        print(f"✅ Database upsert successful: {result}")

        # Test host with optional tiktok_handle
        host_data = {
            "name": "Test Host",
            "api_id": "host_123",
            "timezone": "UTC",
            "avatar_url": "https://example.com/avatar.jpg",
            "is_verified": False,
            "tiktok_handle": "torc.dev",
        }

        host = Host(**host_data)
        print(
            f"✅ Host creation successful: {host.name} (tiktok: {host.tiktok_handle})"
        )

        return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("🔧 Testing Luma Cog Critical Fixes")
    print("=" * 50)

    tests = [
        ("Model Validation", test_event_model_validation),
        ("Database Upsert Logic", test_database_upsert_logic),
        ("Event Object Access", test_event_object_access),
        ("Integration Test", lambda: asyncio.run(test_integration())),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running {test_name}...")
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nTotal: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\n🎉 All fixes are working correctly!")
        print("The manual update command should now work without errors.")
        return True
    else:
        print(
            f"\n⚠️  {len(results) - passed} test(s) failed. Please review the issues above."
        )
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
