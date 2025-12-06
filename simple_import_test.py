#!/usr/bin/env python3
"""
Simple import test for RedBot cog fixes
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, ".")


def test_imports():
    """Test all the key imports that were causing issues."""
    print("Testing imports for RedBot cog...")

    tests = [
        ("Event class", "from luma_cog.models.calendar_get import Event"),
        ("Subscription class", "from luma_cog.models.data_models import Subscription"),
        ("LumaAPIClient class", "from luma_cog.api_client import LumaAPIClient"),
        ("Luma class", "from luma_cog.luma import Luma"),
        ("luma_cog package", "import luma_cog"),
    ]

    results = []

    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"✅ {name}: SUCCESS")
            results.append(True)
        except Exception as e:
            print(f"❌ {name}: FAILED - {e}")
            results.append(False)

    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\nSummary: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All imports working correctly!")
        return True
    else:
        print("⚠️ Some imports still failing")
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
