#!/usr/bin/env python3
"""
Test script to verify the critical fixes for the Luma cog.
"""

import sys
import traceback
from pathlib import Path

# Add the luma directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "luma"))


def test_database_initialization():
    """Test that the database can be initialized properly."""
    print("Testing database initialization...")

    try:
        from luma.core.database import EventDatabase

        # Test with in-memory database first
        db = EventDatabase(db_path=":memory:")
        print("✓ Database initialization with in-memory path successful")

        # Test database operations
        import asyncio

        async def test_db_ops():
            # Test upsert_events
            result = await db.upsert_events([], "test_calendar")
            assert isinstance(result, dict)
            assert "new_events" in result
            print("✓ Database upsert operations working")

            # Test stats
            stats = await db.get_calendar_stats()
            assert isinstance(stats, dict)
            print("✓ Database stats working")

        asyncio.run(test_db_ops())
        return True

    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        traceback.print_exc()
        return False


def test_model_validation():
    """Test that the Pydantic models handle None values properly."""
    print("\nTesting model validation...")

    try:
        from luma.models.calendar_get import (
            Calendar,
            Event,
            GeoAddressInfo,
            RefundPolicy,
            ContentItem,
            ContentItem1,
            FeaturedItem,
            Model,
        )

        # Test Calendar model with None values
        calendar_data = {
            "access_level": "public",
            "api_id": "test_id",
            "avatar_url": "https://example.com/avatar.jpg",
            "coordinate": None,
            "cover_image_url": "https://example.com/cover.jpg",
            "description_short": "Test calendar",
            "event_submission_restriction": "open",
            "geo_city": "Test City",
            "geo_country": "Test Country",
            "geo_region": "Test Region",
            "google_measurement_id": None,
            "instagram_handle": None,
            "is_blocked": False,
            "launch_status": "active",
            "linkedin_handle": None,
            "luma_plus_active": False,
            "meta_pixel_id": None,
            "name": "Test Calendar",
            "personal_user_api_id": None,
            "refund_policy": None,
            "show_subscriber_count": False,
            "slug": "test-calendar",
            "social_image_url": None,
            "stripe_account_id": None,
            "tax_config": None,
            "tiktok_handle": None,
            "timezone": "UTC",
            "tint_color": "#000000",
            "track_meta_ads_from_luma": False,
            "twitter_handle": None,
            "verified_at": None,
            "website": None,
            "youtube_handle": None,
            "is_personal": False,
        }

        calendar = Calendar(**calendar_data)
        print("✓ Calendar model with None values successful")

        # Test GeoAddressInfo with None city_state
        geo_data = {
            "mode": None,
            "city_state": None,
            "sublocality": None,
            "city": None,
            "type": None,
            "region": None,
            "address": None,
            "country": None,
            "place_id": None,
            "description": None,
            "country_code": None,
            "full_address": None,
            "apple_maps_place_id": None,
        }

        geo_info = GeoAddressInfo(**geo_data)
        print("✓ GeoAddressInfo model with None values successful")

        # Test RefundPolicy with None content
        refund_data = {"type": "refundable", "content": None}

        refund_policy = RefundPolicy(**refund_data)
        print("✓ RefundPolicy model with None content successful")

        return True

    except Exception as e:
        print(f"✗ Model validation failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("LUMA COG CRITICAL FIXES TEST")
    print("=" * 60)

    tests = [
        ("Database Initialization", test_database_initialization),
        ("Model Validation", test_model_validation),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * len(test_name))
        result = test_func()
        results.append((test_name, result))

    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! The critical fixes are working correctly.")
        print("\nThe Luma cog should now:")
        print("  ✓ Load without database path errors")
        print("  ✓ Handle API responses with None values")
        print("  ✓ Function properly without validation errors")
    else:
        print("❌ SOME TESTS FAILED! Please review the errors above.")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
