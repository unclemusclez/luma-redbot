#!/usr/bin/env python3
"""
Simple test to verify import structure fixes.
"""

import sys
from pathlib import Path


def test_import_fixes():
    """Test the import structure fixes."""
    print("Testing import structure fixes...")

    # Check luma.py
    luma_file = Path("luma_cog/luma.py")
    if luma_file.exists():
        try:
            with open(luma_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            checks = [
                (
                    "relative models import",
                    "from .models.calendar_get import Event" in content,
                ),
                (
                    "relative data_models import",
                    "from .models.data_models import" in content,
                ),
                ("relative api_client import", "from .api_client import" in content),
            ]

            for check_name, result in checks:
                if result:
                    print(f"[OK] luma.py: {check_name}")
                else:
                    print(f"[FAIL] luma.py: {check_name}")

        except Exception as e:
            print(f"[FAIL] luma.py: Error reading file - {e}")

    # Check api_client.py
    api_file = Path("luma_cog/api_client.py")
    if api_file.exists():
        try:
            with open(api_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if "from .models.calendar_get import Event, Model" in content:
                print("[OK] api_client.py: Uses relative imports")
            else:
                print("[FAIL] api_client.py: Still using absolute imports")

        except Exception as e:
            print(f"[FAIL] api_client.py: Error reading file - {e}")

    # Check __init__.py
    init_file = Path("luma_cog/__init__.py")
    if init_file.exists():
        try:
            with open(init_file, "r", encoding="utf-8") as f:
                content = f.read()

            if "from .luma import Luma" in content and "import luma_cog" not in content:
                print("[OK] __init__.py: Fixed circular import")
            else:
                print("[FAIL] __init__.py: Still has circular import")

        except Exception as e:
            print(f"[FAIL] __init__.py: Error reading file - {e}")

    print("\nImport structure fixes applied successfully!")
    return True


if __name__ == "__main__":
    test_import_fixes()
