"""
Layer 8 Verification Script.
Executes non-interactive verification checks for Layer 8 completion criteria.
"""

import sys
import os
import pytest

def check_file_structure() -> bool:
    required_paths = [
        "AGENTS.md",
        "README.md",
        "pyproject.toml",
        "src/agent/evaluation/__init__.py",
        "src/agent/evaluation/models.py",
        "src/agent/evaluation/metrics.py",
        "src/agent/evaluation/spec.py",
        "src/agent/evaluation/evaluators.py",
        "src/agent/evaluation/comparator.py",
        "src/agent/evaluation/runner.py",
        "docs/architecture/evaluation.md",
        "docs/architecture/layers.md",
        "tests/test_evaluation_system.py",
    ]

    missing = [path for path in required_paths if not os.path.exists(path)]
    if missing:
        print(f"[FAIL] Missing required files/paths: {missing}")
        return False
    print("[PASS] Layer 8 file structure verified.")
    return True

def run_verification_tests() -> bool:
    print("[INFO] Running full pytest verification suite (Layers 0-8)...")
    ret_code = pytest.main(["-v", "--tb=short", "tests"])
    if ret_code == 0:
        print("[PASS] All tests passed.")
        return True
    else:
        print(f"[FAIL] Pytest failed with return code {ret_code}")
        return False

def main() -> None:
    print("=== Layer 8 Verification Run ===")
    structure_ok = check_file_structure()
    tests_ok = run_verification_tests()

    if structure_ok and tests_ok:
        print("\n=== LAYER 8 VERIFICATION SUCCESSFUL ===")
        sys.exit(0)
    else:
        print("\n=== LAYER 8 VERIFICATION FAILED ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
