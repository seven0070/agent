"""
Layer 5 Verification Script.
Executes non-interactive verification checks for Layer 5 completion criteria.
"""

import sys
import os
import pytest

def check_file_structure() -> bool:
    required_paths = [
        "AGENTS.md",
        "README.md",
        "pyproject.toml",
        "src/agent/orchestration/__init__.py",
        "src/agent/orchestration/models.py",
        "src/agent/orchestration/planner.py",
        "src/agent/orchestration/orchestrator.py",
        "src/agent/orchestration/preparation.py",
        "docs/architecture/orchestration.md",
        "docs/architecture/layers.md",
        "tests/test_orchestration_system.py",
    ]

    missing = [path for path in required_paths if not os.path.exists(path)]
    if missing:
        print(f"[FAIL] Missing required files/paths: {missing}")
        return False
    print("[PASS] Layer 5 file structure verified.")
    return True

def run_verification_tests() -> bool:
    print("[INFO] Running full pytest verification suite (Layers 0-5)...")
    ret_code = pytest.main(["-v", "--tb=short", "tests"])
    if ret_code == 0:
        print("[PASS] All tests passed.")
        return True
    else:
        print(f"[FAIL] Pytest failed with return code {ret_code}")
        return False

def main() -> None:
    print("=== Layer 5 Verification Run ===")
    structure_ok = check_file_structure()
    tests_ok = run_verification_tests()

    if structure_ok and tests_ok:
        print("\n=== LAYER 5 VERIFICATION SUCCESSFUL ===")
        sys.exit(0)
    else:
        print("\n=== LAYER 5 VERIFICATION FAILED ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
