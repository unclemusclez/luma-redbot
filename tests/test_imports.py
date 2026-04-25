#!/usr/bin/env python3
"""
Test script to validate RedBot cog imports are working correctly.
This script tests all the modules and classes that were causing import errors.
"""

import sys
import traceback
from typing import List, Dict, Any


def test_import(test_name: str, import_func):
    """Test an import and report results."""
    print(f"\n🧪 Testing {test_name}...")
    try:
        result = import_func()
        print(f"✅ {test_name} - SUCCESS")
        return True, result
    except Exception as e:
        print(f"❌ {test_name} - FAILED: {e}")
        traceback.print_exc()
        return False, None


def test_models_imports():
    """Test imports from models package."""
    print("\n=== Testing Models Package Imports ===")

    results = {}

    # Test models.__init__.py
    success, _ = test_import(
        "models.__init__.py",
        lambda: __import__("luma_cog.models", fromlist=["Event", "Subscription"]),
    )
    results["models_init"] = success

    # Test individual model classes
    success, _ = test_import(
        "Event class",
        lambda: __import__("luma_cog.models.calendar_get", fromlist=["Event"]).Event,
    )
    results["event_class"] = success

    success, _ = test_import(
        "Model class",
        lambda: __import__("luma_cog.models.calendar_get", fromlist=["Model"]).Model,
    )
    results["model_class"] = success

    success, _ = test_import(
        "Subscription class",
        lambda: __import__(
            "luma_cog.models.data_models", fromlist=["Subscription"]
        ).Subscription,
    )
    results["subscription_class"] = success

    success, _ = test_import(
        "ChannelGroup class",
        lambda: __import__(
            "luma_cog.models.data_models", fromlist=["ChannelGroup"]
        ).ChannelGroup,
    )
    results["channel_group_class"] = success

    success, _ = test_import(
        "LumaConfig class",
        lambda: __import__(
            "luma_cog.models.data_models", fromlist=["LumaConfig"]
        ).LumaConfig,
    )
    results["luma_config_class"] = success

    return results


def test_api_client_imports():
    """Test imports from api_client module."""
    print("\n=== Testing API Client Imports ===")

    results = {}

    success, _ = test_import(
        "LumaAPIClient class",
        lambda: __import__(
            "luma_cog.api_client", fromlist=["LumaAPIClient"]
        ).LumaAPIClient,
    )
    results["luma_api_client"] = success

    success, _ = test_import(
        "LumaAPIError exception",
        lambda: __import__(
            "luma_cog.api_client", fromlist=["LumaAPIError"]
        ).LumaAPIError,
    )
    results["luma_api_error"] = success

    success, _ = test_import(
        "LumaAPIRateLimitError exception",
        lambda: __import__(
            "luma_cog.api_client", fromlist=["LumaAPIRateLimitError"]
        ).LumaAPIRateLimitError,
    )
    results["luma_rate_limit_error"] = success

    success, _ = test_import(
        "LumaAPINotFoundError exception",
        lambda: __import__(
            "luma_cog.api_client", fromlist=["LumaAPINotFoundError"]
        ).LumaAPINotFoundError,
    )
    results["luma_not_found_error"] = success

    return results


def test_main_cog_imports():
    """Test imports from main luma module."""
    print("\n=== Testing Main Cog Imports ===")

    results = {}

    success, _ = test_import(
        "Luma class", lambda: __import__("luma_cog.luma", fromlist=["Luma"]).Luma
    )
    results["luma_class"] = success

    # Test the main cog __init__.py
    success, _ = test_import(
        "luma_cog.__init__.py", lambda: __import__("luma_cog", fromlist=["Luma"])
    )
    results["cog_init"] = success

    return results


def test_cross_module_imports():
    """Test that cross-module imports work correctly."""
    print("\n=== Testing Cross-Module Imports ===")

    results = {}

    # Test that api_client can import from models
    success, _ = test_import(
        "api_client -> models import",
        lambda: __import__("luma_cog.api_client", fromlist=[]),
    )
    results["api_client_imports_models"] = success

    # Test that luma.py can import everything it needs
    success, _ = test_import(
        "luma.py imports", lambda: __import__("luma_cog.luma", fromlist=[])
    )
    results["luma_imports_all"] = success

    return results


def test_syntax_validation():
    """Check syntax of all modified files."""
    print("\n=== Testing File Syntax ===")

    import ast

    files_to_check = [
        "luma_cog/__init__.py",
        "luma_cog/models/__init__.py",
        "luma_cog/api_client.py",
        "luma_cog/luma.py",
        "luma_cog/models/calendar_get.py",
        "luma_cog/models/data_models.py",
    ]

    results = {}

    for file_path in files_to_check:
        success, _ = test_import(
            f"syntax check - {file_path}",
            lambda fp=file_path: open(fp, "r").close() or ast.parse(open(fp).read()),
        )
        results[file_path] = success

    return results


def main():
    """Run all import tests."""
    print("🚀 Starting RedBot Cog Import Validation Tests")
    print("=" * 50)

    # Add the current directory to Python path for imports
    sys.path.insert(0, ".")

    all_results = {}

    # Run all test suites
    all_results.update(test_models_imports())
    all_results.update(test_api_client_imports())
    all_results.update(test_main_cog_imports())
    all_results.update(test_cross_module_imports())
    all_results.update(test_syntax_validation())

    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)

    total_tests = len(all_results)
    passed_tests = sum(1 for result in all_results.values() if result)
    failed_tests = total_tests - passed_tests

    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

    if failed_tests > 0:
        print("\n❌ FAILED TESTS:")
        for test_name, result in all_results.items():
            if not result:
                print(f"  - {test_name}")

    print("\n🎯 CONCLUSION:")
    if failed_tests == 0:
        print("✅ All import tests PASSED! The cog should load successfully.")
        return True
    else:
        print(f"❌ {failed_tests} import tests FAILED. Check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
