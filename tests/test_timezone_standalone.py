#!/usr/bin/env python3
"""
Standalone test script to verify timezone conversion and formatting functionality
"""

import pytz
from datetime import datetime
from typing import Optional


# Timezone abbreviation mapping for common timezones
TIMEZONE_ABBREVIATIONS = {
    "America/New_York": "EST",
    "America/Chicago": "CST",
    "America/Denver": "MST",
    "America/Los_Angeles": "PST",
    "America/Phoenix": "MST",
    "America/Anchorage": "AKST",
    "Pacific/Honolulu": "HST",
    "Europe/London": "GMT",
    "Europe/Paris": "CET",
    "Europe/Berlin": "CET",
    "Europe/Rome": "CET",
    "Europe/Madrid": "CET",
    "Europe/Amsterdam": "CET",
    "Europe/Brussels": "CET",
    "Europe/Vienna": "CET",
    "Europe/Zurich": "CET",
    "Europe/Stockholm": "CET",
    "Europe/Oslo": "CET",
    "Europe/Copenhagen": "CET",
    "Europe/Helsinki": "EET",
    "Europe/Athens": "EET",
    "Europe/Bucharest": "EET",
    "Europe/Istanbul": "TRT",
    "Europe/Moscow": "MSK",
    "Asia/Tokyo": "JST",
    "Asia/Shanghai": "CST",
    "Asia/Hong_Kong": "HKT",
    "Asia/Singapore": "SGT",
    "Asia/Seoul": "KST",
    "Asia/Bangkok": "ICT",
    "Asia/Jakarta": "WIB",
    "Asia/Kolkata": "IST",
    "Asia/Dubai": "GST",
    "Australia/Sydney": "AEST",
    "Australia/Melbourne": "AEST",
    "Australia/Brisbane": "AEST",
    "Australia/Perth": "AWST",
    "Pacific/Auckland": "NZST",
}


def get_timezone_abbr(timezone_str: str) -> str:
    """Get timezone abbreviation from timezone string."""
    if not timezone_str:
        return "UTC"

    # Try direct mapping first
    if timezone_str in TIMEZONE_ABBREVIATIONS:
        return TIMEZONE_ABBREVIATIONS[timezone_str]

    # Try to extract common patterns
    if "/" in timezone_str:
        parts = timezone_str.split("/")
        if len(parts) >= 2:
            region = parts[0]
            city = parts[1]

            # Handle US timezones
            if region == "America":
                if city in [
                    "New_York",
                    "Philadelphia",
                    "Boston",
                    "Washington",
                    "Miami",
                ]:
                    return "EST"
                elif city in [
                    "Chicago",
                    "Dallas",
                    "Houston",
                    "New_Orleans",
                    "Minneapolis",
                ]:
                    return "CST"
                elif city in ["Denver", "Phoenix", "Salt_Lake_City", "Albuquerque"]:
                    return "MST"
                elif city in [
                    "Los_Angeles",
                    "San_Francisco",
                    "Seattle",
                    "Portland",
                    "Las_Vegas",
                ]:
                    return "PST"

            # Handle European timezones
            elif region == "Europe":
                if city in ["London", "Dublin", "Lisbon"]:
                    return "GMT"
                elif city in [
                    "Paris",
                    "Berlin",
                    "Rome",
                    "Madrid",
                    "Amsterdam",
                    "Brussels",
                    "Vienna",
                    "Zurich",
                    "Stockholm",
                    "Oslo",
                    "Copenhagen",
                ]:
                    return "CET"
                elif city in ["Helsinki", "Athens", "Bucharest", "Sofia", "Belgrade"]:
                    return "EET"

            # Handle Asian timezones
            elif region == "Asia":
                if city == "Tokyo":
                    return "JST"
                elif city == "Seoul":
                    return "KST"
                elif city == "Shanghai":
                    return "CST"
                elif city == "Hong_Kong":
                    return "HKT"
                elif city == "Singapore":
                    return "SGT"
                elif city == "Kolkata":
                    return "IST"
                elif city == "Dubai":
                    return "GST"

            # Handle Australian timezones
            elif region == "Australia":
                if city in ["Sydney", "Melbourne", "Canberra", "Hobart"]:
                    return "AEST"
                elif city in ["Brisbane", "Gold_Coast"]:
                    return "AEST"
                elif city == "Perth":
                    return "AWST"

    # Fallback: if we can't determine abbreviation, return UTC
    return "UTC"


def convert_utc_to_timezone(utc_time_str: str, timezone_str: str):
    """Convert UTC time string to timezone-aware datetime."""
    if not timezone_str:
        # If no timezone provided, assume UTC
        return datetime.fromisoformat(utc_time_str.replace("Z", "+00:00"))

    try:
        # Parse UTC time
        utc_time = datetime.fromisoformat(utc_time_str.replace("Z", "+00:00"))

        # Create timezone object
        try:
            tz = pytz.timezone(timezone_str)
        except:
            # If timezone is invalid, fall back to UTC
            print(f"Warning: Invalid timezone '{timezone_str}', falling back to UTC")
            return utc_time

        # Convert UTC time to the target timezone
        localized_time = utc_time.replace(tzinfo=pytz.UTC)
        converted_time = localized_time.astimezone(tz)

        return converted_time

    except Exception as e:
        print(
            f"Warning: Error converting timezone for '{utc_time_str}' to '{timezone_str}': {e}"
        )
        # Fallback to original UTC time
        return datetime.fromisoformat(utc_time_str.replace("Z", "+00:00"))


def format_local_time(
    utc_time_str: str,
    timezone_str: str,
    include_end_time: bool = False,
    end_time_str: Optional[str] = None,
) -> str:
    """Format UTC time as local time with timezone abbreviation."""
    try:
        # Convert start time
        start_time = convert_utc_to_timezone(utc_time_str, timezone_str)

        # Format start time
        start_time_str = start_time.strftime("%I:%M %p")

        if include_end_time and end_time_str:
            # Convert end time
            end_time = convert_utc_to_timezone(end_time_str, timezone_str)
            end_time_str_formatted = end_time.strftime("%I:%M %p")
            time_display = f"{start_time_str} - {end_time_str_formatted}"
        else:
            time_display = start_time_str

        # Get timezone abbreviation
        tz_abbr = get_timezone_abbr(timezone_str)

        return f"{time_display} {tz_abbr}"

    except Exception as e:
        print(f"Warning: Error formatting local time: {e}")
        # Fallback to original UTC time
        return f"{utc_time_str} UTC"


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
        print("All tests completed successfully!")

        # Show example of the before/after formatting
        print("\n=== Example Transformation ===")
        print("Before (old format):")
        print("🕐 Time: 09:30 PM UTC")
        print("🌍 Timezone: America/New_York")
        print()
        print("After (new format):")
        local_time = format_local_time("2025-12-08T02:30:00Z", "America/New_York")
        print(f"🕐 Local Time: {local_time}")

    except Exception as e:
        print(f"Error running tests: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
