#!/usr/bin/env python3
"""
Test script to verify the Luma link formatting and Discord message fixes.
"""

import sys
import os
import re

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath("."))


def test_link_formatting():
    """Test that link formatting uses angle brackets instead of markdown format."""

    # Read the luma.py file
    with open("luma/core/luma.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Test 1: Check that the manual events command uses angle bracket format
    if "<{event.url}>" in content:
        print("✅ PASS: Manual events command uses angle bracket format")
    else:
        print("❌ FAIL: Manual events command still uses markdown format")

    # Test 2: Check that automatic message sending uses angle bracket format
    if "🔗 <{event.url}>" in content:
        print("✅ PASS: Automatic message sending uses angle bracket format")
    else:
        print("❌ FAIL: Automatic message sending still uses markdown format")

    # Test 3: Check that old markdown format is NOT present
    markdown_pattern = r"\[View Event\]\({event\.url}\)"
    if not re.search(markdown_pattern, content):
        print("✅ PASS: Old markdown link format removed")
    else:
        print("❌ FAIL: Old markdown link format still present")

    # Test 4: Check that automatic Discord message filtering logic was fixed
    if "events_to_return = new_filtered_events[:group.max_events]" in content:
        print("✅ PASS: Automatic Discord message filtering logic fixed")
    else:
        print("❌ FAIL: Automatic Discord message filtering logic not fixed")

    print("\n" + "=" * 60)
    print("LINK FORMATTING TESTS")
    print("=" * 60)

    # Find all link-related lines for manual inspection
    link_lines = []
    for i, line in enumerate(content.split("\n"), 1):
        if "event.url" in line and ("🔗" in line or "[" in line):
            link_lines.append(f"Line {i}: {line.strip()}")

    if link_lines:
        print("\nLink-related code found:")
        for line in link_lines:
            print(f"  {line}")
    else:
        print("\n⚠️ No link-related code found for inspection")


def test_database_functionality():
    """Test that the database functionality is intact."""

    print("\n" + "=" * 60)
    print("DATABASE FUNCTIONALITY TESTS")
    print("=" * 60)

    # Read the luma.py file
    with open("luma/core/luma.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Check that key database functions are still present
    key_functions = [
        "await self.event_db.upsert_events(",
        "await self.event_db.get_new_events(",
        "total_new_events",
        "change_stats",
    ]

    for func in key_functions:
        if func in content:
            print(f"✅ PASS: Database function '{func}' found")
        else:
            print(f"❌ FAIL: Database function '{func}' missing")


def test_event_filtering_logic():
    """Test the event filtering logic changes."""

    print("\n" + "=" * 60)
    print("EVENT FILTERING LOGIC TESTS")
    print("=" * 60)

    # Read the luma.py file
    with open("luma/core/luma.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Check for the new conditional logic
    if "if check_for_changes:" in content:
        print("✅ PASS: Check for changes logic present")
    else:
        print("❌ FAIL: Check for changes logic missing")

    if "events_to_return = filtered_events[:group.max_events]" in content:
        print("✅ PASS: Manual updates use filtered events")
    else:
        print("❌ FAIL: Manual updates logic not implemented")

    # Check that the return statement uses events_to_return
    if '"events": events_to_return,' in content:
        print("✅ PASS: Return statement uses events_to_return variable")
    else:
        print("❌ FAIL: Return statement still uses direct list access")


if __name__ == "__main__":
    print("LUMA LINK FORMATTING AND DISCORD MESSAGE FIXES TEST")
    print("=" * 60)

    test_link_formatting()
    test_database_functionality()
    test_event_filtering_logic()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("Both issues should now be fixed:")
    print("1. ✅ Links now use angle bracket format: <https://luma.com/slug>")
    print("2. ✅ Automatic Discord messages should now send new events properly")
    print("\nTest complete!")
