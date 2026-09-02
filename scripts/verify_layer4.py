"""
Layer 4 Verification Script.
Executes non-interactive verification checks for Layer 4 completion criteria.
"""

import sys
import os
import pytest

def check_file_structure() -> bool:
    required_paths = [
        "AGENTS.md",
        "README.md",
        "pyproject.toml",
        "src/agent/capabilities/__init__.py",
        "src/agent/capabilities/models.py",
        "src/agent/capabilities/permissions.py",
        "src/agent/capabilities/spec.py",
        "src/agent/capabilities/registry.py",
        "src/agent/capabilities/broker.py",
        "src/agent/capabilities/tools/calculator.py",
        "src/agent/capabilities/tools/workspace.py",
        "src/agent/capabilities/skills/file_management.py",
        "src/agent/capabilities/mcp.py",
        "docs/architecture/capabilities.md",
        "docs/architecture/layers.md",
        "tests/test_capabilities_system.py",
    ]

    missing = [path for path in required_paths if not os.path.exists(path)]
    if missing:
        print(f"[FAIL] Missing required files/paths: {missing}")
        return False
    print("[PASS] Layer 4 file structure verified.")
    return True

def run_verification_tests() -> bool:
    print("[INFO] Running full pytest verification suite (Layers 0-4)...")
    ret_code = pytest.main(["-v", "--tb=short", "tests"])
    if ret_code == 0:
        print("[PASS] All tests passed.")
        return True
    else:
        print(f"[FAIL] Pytest failed with return code {ret_code}")
        return False

def main() -> None:
    print("=== Layer 4 Verification Run ===")
    structure_ok = check_file_structure()
    tests_ok = run_verification_tests()

    if structure_ok and tests_ok:
        print("\n=== LAYER 4 VERIFICATION SUCCESSFUL ===")
        sys.exit(0)
    else:
        print("\n=== LAYER 4 VERIFICATION FAILED ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
