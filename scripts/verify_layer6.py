"""
Layer 6 Verification Script.
Executes non-interactive verification checks for Layer 6 completion criteria.
"""

import sys
import os
import pytest

def check_file_structure() -> bool:
    required_paths = [
        "AGENTS.md",
        "README.md",
        "pyproject.toml",
        "src/agent/coding/__init__.py",
        "src/agent/coding/models.py",
        "src/agent/coding/spec.py",
        "src/agent/coding/interface.py",
        "src/agent/coding/workspace.py",
        "src/agent/coding/permissions.py",
        "src/agent/coding/jcode/bridge.py",
        "src/agent/coding/jcode/adapter.py",
        "src/agent/capabilities/tools/coding.py",
        "docs/architecture/jcode.md",
        "docs/architecture/layers.md",
        "tests/test_coding_engine.py",
    ]

    missing = [path for path in required_paths if not os.path.exists(path)]
    if missing:
        print(f"[FAIL] Missing required files/paths: {missing}")
        return False
    print("[PASS] Layer 6 file structure verified.")
    return True

def run_verification_tests() -> bool:
    print("[INFO] Running full pytest verification suite (Layers 0-6)...")
    ret_code = pytest.main(["-v", "--tb=short", "tests"])
    if ret_code == 0:
        print("[PASS] All tests passed.")
        return True
    else:
        print(f"[FAIL] Pytest failed with return code {ret_code}")
        return False

def main() -> None:
    print("=== Layer 6 Verification Run ===")
    structure_ok = check_file_structure()
    tests_ok = run_verification_tests()

    if structure_ok and tests_ok:
        print("\n=== LAYER 6 VERIFICATION SUCCESSFUL ===")
        sys.exit(0)
    else:
        print("\n=== LAYER 6 VERIFICATION FAILED ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
