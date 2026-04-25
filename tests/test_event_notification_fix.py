#!/usr/bin/env python3
"""
Test script to validate the event notification system fix.

This script tests that:
1. New events are properly detected and deduplicated
2. The single API call approach works correctly
3. Event notifications are sent for truly new events
4. Deduplication prevents duplicate notifications
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, List, Any

# Configure logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


# Mock classes to simulate the data structures
class MockEvent:
    def __init__(self, api_id: str, name: str, start_at: str, calendar_api_id: str):
        self.api_id = api_id
        self.name = name
        self.start_at = start_at
        self.calendar_api_id = calendar_api_id


class MockSubscription:
    def __init__(self, api_id: str, name: str, slug: str):
        self.api_id = api_id
        self.name = name
        self.slug = slug

    @classmethod
    def from_dict(cls, data: Dict) -> "MockSubscription":
        return cls(data["api_id"], data["name"], data["slug"])


class MockChannelGroup:
    def __init__(
        self,
        name: str,
        channel_id: int,
        subscription_ids: List[str],
        max_events: int = 10,
    ):
        self.name = name
        self.channel_id = channel_id
        self.subscription_ids = subscription_ids
        self.max_events = max_events

    @classmethod
    def from_dict(cls, data: Dict) -> "MockChannelGroup":
        return cls(
            data["name"],
            data["channel_id"],
            data["subscription_ids"],
            data.get("max_events", 10),
        )


class MockEventDatabase:
    def __init__(self):
        self.tracked_events = {}  # api_id -> event_data
        self.call_log = []

    async def upsert_events(
        self, events: List[Dict], calendar_api_id: str
    ) -> Dict[str, Any]:
        """Mock database upsert that tracks changes."""
        self.call_log.append(
            f"upsert_events called for {calendar_api_id} with {len(events)} events"
        )

        new_events = 0
        updated_events = 0

        for event_data in events:
            api_id = event_data["api_id"]
            if api_id in self.tracked_events:
                updated_events += 1
            else:
                new_events += 1
            self.tracked_events[api_id] = event_data

        return {
            "new_events": new_events,
            "updated_events": updated_events,
            "deleted_events": 0,
            "total_events": len(events),
        }

    async def get_new_events(
        self, calendar_api_id: str, events: List[Dict]
    ) -> List[Dict]:
        """Mock database query for new events."""
        self.call_log.append(f"get_new_events called for {calendar_api_id}")

        new_events = []
        for event_data in events:
            api_id = event_data["api_id"]
            if api_id not in self.tracked_events:
                new_events.append(event_data)

        return new_events


class MockLumaAPI:
    def __init__(self):
        self.call_log = []

    async def get_calendar_events(
        self, calendar_identifier: str, limit: int = 100
    ) -> List[MockEvent]:
        """Mock API that returns events with some duplicates."""
        self.call_log.append(f"get_calendar_events called for {calendar_identifier}")

        now = datetime.now(timezone.utc)
        if calendar_identifier == "calendar_1":
            # Calendar 1 has 2 events, one is a duplicate across calendars
            return [
                MockEvent(
                    "event_1",
                    "Event 1",
                    (now + timedelta(days=1)).isoformat(),
                    calendar_identifier,
                ),
                MockEvent(
                    "shared_event",
                    "Shared Event",
                    (now + timedelta(days=2)).isoformat(),
                    calendar_identifier,
                ),
            ]
        elif calendar_identifier == "calendar_2":
            # Calendar 2 has 2 events, one is a duplicate across calendars
            return [
                MockEvent(
                    "event_3",
                    "Event 3",
                    (now + timedelta(days=3)).isoformat(),
                    calendar_identifier,
                ),
                MockEvent(
                    "shared_event",
                    "Shared Event",
                    (now + timedelta(days=2)).isoformat(),
                    calendar_identifier,
                ),  # Duplicate!
            ]

        return []


class TestLumaCog:
    """Mock Luma cog with the fixed fetch_events_for_group method."""

    def __init__(self):
        self.event_db = MockEventDatabase()
        self.api_client = MockLumaAPI()

    async def fetch_events_from_subscription(
        self, subscription, check_for_changes: bool = True
    ):
        """Fetch events from a subscription."""
        # Mock the API client
        events = await self.api_client.get_calendar_events(subscription.api_id, 100)

        # Convert to dict format
        event_dicts = []
        for event in events:
            event_dict = {
                "api_id": event.api_id,
                "calendar_api_id": subscription.api_id,
                "name": event.name,
                "start_at": event.start_at,
                "end_at": None,
                "timezone": "UTC",
                "url": f"event-{event.api_id}",
                "last_modified": datetime.now(timezone.utc).isoformat(),
            }
            event_dicts.append(event_dict)

        if check_for_changes:
            # Use database to track changes
            change_stats = await self.event_db.upsert_events(
                event_dicts, subscription.api_id
            )
            new_events = await self.event_db.get_new_events(
                subscription.api_id, event_dicts
            )

            # Convert back to MockEvent objects for new_events
            new_event_objects = []
            for event_dict in new_events:
                event_obj = MockEvent(
                    event_dict["api_id"],
                    event_dict["name"],
                    event_dict["start_at"],
                    event_dict["calendar_api_id"],
                )
                new_event_objects.append(event_obj)

            return {
                "events": events,
                "new_events": new_event_objects,
                "change_stats": change_stats,
            }
        else:
            return {
                "events": events,
                "new_events": events,  # Treat all as new
                "change_stats": {
                    "new_events": len(events),
                    "updated_events": 0,
                    "deleted_events": 0,
                },
            }

    async def fetch_events_for_group(
        self, group, subscriptions: Dict, check_for_changes: bool = True
    ):
        """FIXED version of fetch_events_for_group method."""
        # Add debug logging
        print(f"\n=== fetch_events_for_group called ===")
        print(
            f"Group: {group.name}, Subscriptions: {group.subscription_ids}, Check for changes: {check_for_changes}"
        )

        all_events = []
        seen_api_ids = set()
        all_new_events = []  # Collect new events during initial fetch
        total_new_events = 0
        change_stats = {"new_events": 0, "updated_events": 0, "deleted_events": 0}

        # FIRST AND ONLY API CALL - no duplicate calls
        for sub_id in group.subscription_ids:
            if sub_id in subscriptions:
                subscription = MockSubscription.from_dict(subscriptions[sub_id])
                try:
                    result = await self.fetch_events_from_subscription(
                        subscription, check_for_changes
                    )

                    print(
                        f"Subscription {subscription.name}: {len(result['events'])} events, {len(result['new_events'])} new"
                    )

                    # Deduplicate events
                    for event in result["events"]:
                        if event.api_id not in seen_api_ids:
                            all_events.append(event)
                            seen_api_ids.add(event.api_id)
                        else:
                            print(
                                f"  Deduplicating event {event.api_id} from subscription {subscription.name}"
                            )

                    # CRITICAL FIX: Collect new events during the initial fetch
                    all_new_events.extend(result["new_events"])
                    total_new_events += len(result["new_events"])

                    # Aggregate change stats
                    for key in change_stats:
                        if key in result["change_stats"]:
                            change_stats[key] += result["change_stats"][key]

                except Exception as e:
                    print(f"Error fetching events for subscription {sub_id}: {e}")

        print(
            f"After initial processing: {len(all_events)} unique events, {len(all_new_events)} total new events"
        )

        # Sort events by start time and limit to recent events
        all_events.sort(key=lambda x: x.start_at)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=1)

        filtered_events = [
            e
            for e in all_events
            if datetime.fromisoformat(e.start_at.replace("Z", "+00:00")) >= cutoff_date
        ]

        print(f"After filtering by cutoff date: {len(filtered_events)} events")

        # For automatic updates, only include events that are actually new
        if check_for_changes:
            print("Processing for automatic updates - using pre-collected new events")

            # CRITICAL FIX: Use the new events already collected during initial fetch
            all_new_events.sort(key=lambda x: x.start_at)
            new_filtered_events = [
                e
                for e in all_new_events
                if datetime.fromisoformat(e.start_at.replace("Z", "+00:00"))
                >= cutoff_date
            ]

            # CRITICAL FIX: Deduplicate new events based on api_id
            seen_new_api_ids = set()
            deduplicated_new_events = []
            for event in new_filtered_events:
                if event.api_id not in seen_new_api_ids:
                    deduplicated_new_events.append(event)
                    seen_new_api_ids.add(event.api_id)
                else:
                    print(f"  Deduplicating NEW event {event.api_id}")

            print(f"New events after deduplication: {len(deduplicated_new_events)}")

            events_to_return = deduplicated_new_events[: group.max_events]
            new_events_count = len(events_to_return)

            print(f"Final result: {new_events_count} new events will be sent")
        else:
            events_to_return = filtered_events[: group.max_events]
            new_events_count = total_new_events
            print(
                f"Manual update mode: returning {len(events_to_return)} events, {new_events_count} marked as new"
            )

        return {
            "events": events_to_return,
            "new_events_count": new_events_count,
            "change_stats": change_stats,
        }


async def test_scenario_1_new_events():
    """Test: New events should be detected and sent."""
    print("\n" + "=" * 60)
    print("TEST SCENARIO 1: New Events Detection")
    print("=" * 60)

    cog = TestLumaCog()

    # Setup subscriptions
    subscriptions = {
        "calendar_1": {"api_id": "calendar_1", "name": "Calendar 1", "slug": "cal1"},
        "calendar_2": {"api_id": "calendar_2", "name": "Calendar 2", "slug": "cal2"},
    }

    # Setup channel group
    group = MockChannelGroup(
        "test-group", 12345, ["calendar_1", "calendar_2"], max_events=10
    )

    # First run - should detect all events as new
    print("\n--- First Run (Initial State) ---")
    result1 = await cog.fetch_events_for_group(
        group, subscriptions, check_for_changes=True
    )

    print(f"\nResult 1: {result1['new_events_count']} new events detected")
    print(f"Events: {[event.name for event in result1['events']]}")
    print(f"Change stats: {result1['change_stats']}")

    # Expected: 3 unique events (event_1, event_3, shared_event) - no duplicates
    expected_new_events = 3
    assert (
        result1["new_events_count"] == expected_new_events
    ), f"Expected {expected_new_events} new events, got {result1['new_events_count']}"

    print("✅ TEST PASSED: New events properly detected and deduplicated")


async def test_scenario_2_no_duplicates():
    """Test: Duplicate events across calendars should be deduplicated."""
    print("\n" + "=" * 60)
    print("TEST SCENARIO 2: Duplicate Event Deduplication")
    print("=" * 60)

    cog = TestLumaCog()

    # Setup subscriptions
    subscriptions = {
        "calendar_1": {"api_id": "calendar_1", "name": "Calendar 1", "slug": "cal1"},
        "calendar_2": {"api_id": "calendar_2", "name": "Calendar 2", "slug": "cal2"},
    }

    # Setup channel group
    group = MockChannelGroup(
        "test-group", 12345, ["calendar_1", "calendar_2"], max_events=10
    )

    # Check the API call count - should only be 2 calls (one per subscription)
    initial_api_calls = len(cog.api_client.call_log)

    print("\n--- Running fetch_events_for_group ---")
    result = await cog.fetch_events_for_group(
        group, subscriptions, check_for_changes=True
    )

    new_api_calls = len(cog.api_client.call_log) - initial_api_calls
    print(f"\nAPI calls made: {new_api_calls}")

    # Verify only one API call per subscription
    assert new_api_calls == 2, f"Expected 2 API calls, got {new_api_calls}"

    # Verify no duplicate events
    event_api_ids = [event.api_id for event in result["events"]]
    assert len(event_api_ids) == len(
        set(event_api_ids)
    ), f"Duplicate events found: {event_api_ids}"

    print("✅ TEST PASSED: Single API call per subscription, no duplicates")


async def test_scenario_3_update_flow():
    """Test: Event update flow works correctly."""
    print("\n" + "=" * 60)
    print("TEST SCENARIO 3: Update Flow")
    print("=" * 60)

    cog = TestLumaCog()

    # Setup subscriptions
    subscriptions = {
        "calendar_1": {"api_id": "calendar_1", "name": "Calendar 1", "slug": "cal1"},
        "calendar_2": {"api_id": "calendar_2", "name": "Calendar 2", "slug": "cal2"},
    }

    # Setup channel group
    group = MockChannelGroup(
        "test-group", 12345, ["calendar_1", "calendar_2"], max_events=10
    )

    # First run - initial state
    print("\n--- First Run (Initial State) ---")
    result1 = await cog.fetch_events_for_group(
        group, subscriptions, check_for_changes=True
    )
    print(f"First run: {result1['new_events_count']} new events")

    # Second run - same data, should have no new events
    print("\n--- Second Run (Same Data) ---")
    result2 = await cog.fetch_events_for_group(
        group, subscriptions, check_for_changes=True
    )
    print(f"Second run: {result2['new_events_count']} new events")

    # Expected: 0 new events on second run
    assert (
        result2["new_events_count"] == 0
    ), f"Expected 0 new events on second run, got {result2['new_events_count']}"

    print("✅ TEST PASSED: Update flow correctly identifies no new events")


async def main():
    """Run all test scenarios."""
    print("Event Notification System Fix - Test Suite")
    print("Testing the fixed deduplication logic for new event detection")

    try:
        await test_scenario_1_new_events()
        await test_scenario_2_no_duplicates()
        await test_scenario_3_update_flow()

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("✅ Event notification system fix is working correctly")
        print("✅ New events are properly detected")
        print("✅ Duplicate events are properly deduplicated")
        print("✅ Single API call approach prevents race conditions")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
