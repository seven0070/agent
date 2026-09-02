"""
Layer 3 Verification Script.
Executes non-interactive verification checks for Layer 3 completion criteria.
"""

import sys
import os
import pytest

def check_file_structure() -> bool:
    required_paths = [
        "AGENTS.md",
        "README.md",
        "pyproject.toml",
        "src/agent/memory/__init__.py",
        "src/agent/memory/models.py",
        "src/agent/memory/spec.py",
        "src/agent/memory/base.py",
        "src/agent/memory/session.py",
        "src/agent/memory/sqlite.py",
        "src/agent/memory/embeddings.py",
        "src/agent/memory/rag.py",
        "src/agent/memory/context.py",
        "docs/architecture/memory.md",
        "docs/architecture/layers.md",
        "tests/test_memory_system.py",
    ]

    missing = [path for path in required_paths if not os.path.exists(path)]
    if missing:
        print(f"[FAIL] Missing required files/paths: {missing}")
        return False
    print("[PASS] Layer 3 file structure verified.")
    return True

def run_verification_tests() -> bool:
    print("[INFO] Running full pytest verification suite (Layers 0-3)...")
    ret_code = pytest.main(["-v", "--tb=short", "tests"])
    if ret_code == 0:
        print("[PASS] All tests passed.")
        return True
    else:
        print(f"[FAIL] Pytest failed with return code {ret_code}")
        return False

def main() -> None:
    print("=== Layer 3 Verification Run ===")
    structure_ok = check_file_structure()
    tests_ok = run_verification_tests()

    if structure_ok and tests_ok:
        print("\n=== LAYER 3 VERIFICATION SUCCESSFUL ===")
        sys.exit(0)
    else:
        print("\n=== LAYER 3 VERIFICATION FAILED ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
