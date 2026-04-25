#!/usr/bin/env python3
"""
Test script to validate RedBot cog import structure fixes.
This tests the import structure without importing RedBot dependencies.
"""

import sys
import ast
from pathlib import Path


def check_file_syntax(file_path):
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        ast.parse(content)
        return True, None
    except Exception as e:
        return False, str(e)


def test_import_structure():
    """Test the import structure fixes."""
    print("Testing RedBot cog import structure fixes...")

    # Test files
    test_files = [
        "luma_cog/__init__.py",
        "luma_cog/luma.py",
        "luma_cog/api_client.py",
        "luma_cog/models/__init__.py",
        "luma_cog/models/calendar_get.py",
        "luma_cog/models/data_models.py",
    ]

    results = []

    for file_path in test_files:
        path = Path(file_path)
        if path.exists():
            success, error = check_file_syntax(file_path)
            if success:
                print(f"[OK] {file_path}: Valid syntax")
                results.append(True)
            else:
                print(f"[FAIL] {file_path}: Syntax error - {error}")
                results.append(False)
        else:
            print(f"[FAIL] {file_path}: File not found")
            results.append(False)

    # Check for relative imports in the fixed files
    print("\nChecking import statements...")

    # Check luma.py for relative imports
    luma_file = Path("luma_cog/luma.py")
    if luma_file.exists():
        with open(luma_file, "r") as f:
            content = f.read()

        if "from .models.calendar_get import Event" in content:
            print("[OK] luma.py: Uses relative imports for models")
            results.append(True)
        else:
            print("[FAIL] luma.py: Still using absolute imports")
            results.append(False)

        if "from .api_client import" in content:
            print("[OK] luma.py: Uses relative imports for api_client")
            results.append(True)
        else:
            print("[FAIL] luma.py: Still using absolute imports for api_client")
            results.append(False)

    # Check api_client.py for relative imports
    api_file = Path("luma_cog/api_client.py")
    if api_file.exists():
        with open(api_file, "r") as f:
            content = f.read()

        if "from .models.calendar_get import Event, Model" in content:
            print("[OK] api_client.py: Uses relative imports for models")
            results.append(True)
        else:
            print("[FAIL] api_client.py: Still using absolute imports")
            results.append(False)

    # Check __init__.py for circular import fix
    init_file = Path("luma_cog/__init__.py")
    if init_file.exists():
        with open(init_file, "r") as f:
            content = f.read()

        if "from .luma import Luma" in content and "import luma_cog" not in content:
            print("[OK] __init__.py: Fixed circular import")
            results.append(True)
        else:
            print("[FAIL] __init__.py: Still has circular import")
            results.append(False)

    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("[OK] All import structure fixes are correct!")
        return True
    else:
        print("[FAIL] Some import structure issues remain")
        return False


if __name__ == "__main__":
    success = test_import_structure()
    sys.exit(0 if success else 1)
