"""
Layer 0 Verification Script.
Executes non-interactive verification checks for Layer 0 completion criteria.
"""

import sys
import os
import pytest

def check_file_structure() -> bool:
    required_paths = [
        "AGENTS.md",
        "README.md",
        "pyproject.toml",
        ".gitignore",
        ".env.example",
        "src/agent/__init__.py",
        "src/agent/__main__.py",
        "src/agent/config.py",
        "src/agent/logging.py",
        "src/agent/versioning.py",
        "src/agent/constitution.py",
        "docs/architecture/overview.md",
        "docs/architecture/layers.md",
        "docs/architecture/constitution.md",
        "docs/architecture/evolution.md",
        "examples/basic_init.py",
        "tests/test_smoke.py",
    ]

    missing = [path for path in required_paths if not os.path.exists(path)]
    if missing:
        print(f"[FAIL] Missing required files/paths: {missing}")
        return False
    print("[PASS] File structure verified.")
    return True

def run_verification_tests() -> bool:
    print("[INFO] Running pytest verification suite...")
    ret_code = pytest.main(["-v", "--tb=short", "tests"])
    if ret_code == 0:
        print("[PASS] All tests passed.")
        return True
    else:
        print(f"[FAIL] Pytest failed with return code {ret_code}")
        return False

def main() -> None:
    print("=== Layer 0 Verification Run ===")
    structure_ok = check_file_structure()
    tests_ok = run_verification_tests()

    if structure_ok and tests_ok:
        print("\n=== LAYER 0 VERIFICATION SUCCESSFUL ===")
        sys.exit(0)
    else:
        print("\n=== LAYER 0 VERIFICATION FAILED ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
