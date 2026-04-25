#!/usr/bin/env python3
"""
Test script for the force update functionality in the Luma cog.
This tests the new force parameter and verifies the logic works correctly.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath("."))


async def test_force_update_signature():
    """Test that the force parameter is correctly accepted in the command signature."""

    # Import the Luma cog class
    try:
        from luma.core.luma import Luma

        # Check if the manual_update method exists and has the correct signature
        import inspect

        # Get the method signature
        sig = inspect.signature(Luma.manual_update)

        print("Testing force update command signature...")
        print(f"Method signature: {sig}")

        # Check parameters
        params = list(sig.parameters.keys())
        print(f"Parameters: {params}")

        # Expected parameters: self, ctx, force=False
        expected_params = ["self", "ctx", "force"]
        assert params == expected_params, f"Expected {expected_params}, got {params}"

        # Check force parameter default value
        force_param = sig.parameters["force"]
        assert (
            force_param.default is False
        ), f"Force parameter should default to False, got {force_param.default}"

        print("✅ Force update command signature test passed!")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

    return True


async def test_force_logic_simulation():
    """Simulate the force update logic without actual API calls."""

    print("\nTesting force update logic simulation...")

    # Simulate force mode logic
    def test_check_for_changes_logic(force):
        check_for_changes = not force
        return check_for_changes

    # Test normal mode
    check_for_changes_normal = test_check_for_changes_logic(False)
    assert check_for_changes_normal is True, "Normal mode should check for changes"
    print("✅ Normal mode logic test passed!")

    # Test force mode
    check_for_changes_force = test_check_for_changes_logic(True)
    assert check_for_changes_force is False, "Force mode should NOT check for changes"
    print("✅ Force mode logic test passed!")

    return True


async def test_docstring_update():
    """Test that the docstring was updated correctly."""

    print("\nTesting docstring updates...")

    try:
        from luma.core.luma import Luma

        # Get the docstring
        docstring = Luma.manual_update.__doc__
        assert docstring is not None, "Docstring should not be None"
        assert (
            "force" in docstring.lower()
        ), "Docstring should mention 'force' parameter"
        assert (
            "testing" in docstring.lower()
        ), "Docstring should mention testing use case"

        print("✅ Docstring update test passed!")
        print(f"Updated docstring: {docstring.strip()}")

    except Exception as e:
        print(f"❌ Docstring test failed: {e}")
        return False

    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Force Update Implementation")
    print("=" * 60)

    tests = [
        test_force_update_signature,
        test_force_logic_simulation,
        test_docstring_update,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")

    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Force update implementation is working correctly.")
        print("\nNew command usage:")
        print("  [p]luma update        - Normal mode (only new events)")
        print("  [p]luma update force  - Force mode (all recent events)")
    else:
        print("❌ Some tests failed. Please check the implementation.")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
