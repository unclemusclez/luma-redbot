#!/usr/bin/env python3
"""
Test script to verify timezone conversion and formatting functionality
"""

import sys
import os

# Add the project root to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the functions we need to test
from luma.core.luma import get_timezone_abbr, convert_utc_to_timezone, format_local_time


def test_timezone_abbreviations():
    """Test timezone abbreviation mapping."""
    print("Testing timezone abbreviations...")

    test_cases = [
        ("America/New_York", "EST"),
        ("America/Chicago", "CST"),
        ("America/Los_Angeles", "PST"),
        ("Europe/London", "GMT"),
        ("Europe/Paris", "CET"),
        ("Asia/Tokyo", "JST"),
        ("Australia/Sydney", "AEST"),
        ("Invalid/Timezone", "UTC"),  # Fallback case
    ]

    for tz, expected in test_cases:
        result = get_timezone_abbr(tz)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {tz} -> {result} (expected {expected})")

    print()


def test_timezone_conversion():
    """Test timezone conversion functionality."""
    print("Testing timezone conversion...")

    # Test UTC to EST conversion (UTC time that would be 7:30 PM EST)
    utc_time = "2025-12-07T00:30:00Z"
    est_time = convert_utc_to_timezone(utc_time, "America/New_York")
    print(f"  UTC {utc_time} -> EST {est_time.strftime('%I:%M %p')}")

    # Test UTC to PST conversion
    pst_time = convert_utc_to_timezone(utc_time, "America/Los_Angeles")
    print(f"  UTC {utc_time} -> PST {pst_time.strftime('%I:%M %p')}")

    # Test UTC to Tokyo time
    tokyo_time = convert_utc_to_timezone(utc_time, "Asia/Tokyo")
    print(f"  UTC {utc_time} -> JST {tokyo_time.strftime('%I:%M %p')}")

    print()


def test_local_time_formatting():
    """Test the complete local time formatting function."""
    print("Testing local time formatting...")

    test_cases = [
        ("2025-12-07T21:30:00Z", "America/New_York", False, None),
        ("2025-12-07T21:30:00Z", "America/Los_Angeles", True, "2025-12-07T22:30:00Z"),
        ("2025-12-08T09:00:00Z", "Europe/London", False, None),
        ("2025-12-08T15:30:00Z", "Asia/Tokyo", True, "2025-12-09T00:30:00Z"),
    ]

    for utc_time, timezone, include_end, end_time in test_cases:
        result = format_local_time(utc_time, timezone, include_end, end_time)
        end_str = f" - {end_time}" if include_end and end_time else ""
        print(f"  {utc_time} {timezone}{end_str} -> {result}")

    print()


def main():
    """Run all tests."""
    print("=== Luma Timezone Conversion Tests ===\n")

    try:
        test_timezone_abbreviations()
        test_timezone_conversion()
        test_local_time_formatting()
        print("All tests completed!")

    except Exception as e:
        print(f"Error running tests: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
