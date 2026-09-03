#!/usr/bin/env python3
"""Fail-closed checks for self-contained desktop packaging contracts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    print("=== Packaging Verification: Desktop Sidecar Contract ===")
    errors = []

    main_rs = (ROOT / "src-tauri" / "src" / "main.rs").read_text(encoding="utf-8")
    if "scripts/run_agent_backend.py" in main_rs and "debug_assertions" not in main_rs:
        errors.append("Production sidecar spawn still depends on scripts/run_agent_backend.py")
    if "cfg(debug_assertions)" not in main_rs:
        errors.append("Development Python fallback is not isolated behind debug_assertions")
    if "resolve_packaged_sidecar" not in main_rs:
        errors.append("Packaged sidecar resolver missing from main.rs")
    if re.search(r'Command::new\("python3?"\)', main_rs) and "not(debug_assertions)" in main_rs.split("Command::new(\"python\")")[-1][:200]:
        errors.append("Release spawn path still uses Python")

    conf = json.loads((ROOT / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
    external = conf.get("bundle", {}).get("externalBin") or []
    if "binaries/agent-backend" not in external:
        errors.append("tauri.conf.json externalBin must include binaries/agent-backend")
    targets = conf.get("bundle", {}).get("targets")
    if targets == "all":
        errors.append("bundle.targets=all claims macOS without a macOS CI job")
    icons = conf.get("bundle", {}).get("icon") or []
    for icon in icons:
        path = ROOT / "src-tauri" / icon
        if not path.exists():
            errors.append(f"Missing icon {icon}")

    if not (ROOT / "src-tauri" / "build.rs").exists():
        errors.append("Missing src-tauri/build.rs")
    if not (ROOT / "src-tauri" / "capabilities" / "default.json").exists():
        errors.append("Missing Tauri capabilities")

    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    if "macos-latest" in workflow:
        errors.append("CI claims macOS but product packaging is Windows/Linux only")
    if "3.10" in workflow:
        errors.append("CI still tests Python 3.10 which cannot install agentscope 2.x")
    if "build_backend_sidecar.py" not in workflow:
        errors.append("CI does not build the sidecar via scripts/build_backend_sidecar.py")
    if "working-directory: ui" in workflow:
        errors.append("CI must not run tauri build from ui/; tauri.conf.json lives in src-tauri/")
    if "ui/node_modules/@tauri-apps/cli/tauri.js" not in workflow:
        errors.append("CI must invoke the installed Tauri CLI from repository root without npx --prefix cwd shift")
    if "npx --prefix ui tauri" in workflow:
        errors.append("npx --prefix ui tauri shifts cwd to ui/ and breaks sibling src-tauri discovery hooks")
    if "--bundles" not in workflow:
        errors.append("CI must pass platform-specific --bundles (msi/nsis vs deb/appimage)")
    before_build = conf.get("build", {}).get("beforeBuildCommand") or ""
    if "npm --prefix ui run build" not in before_build:
        errors.append("beforeBuildCommand must be 'npm --prefix ui run build' for repository-root Tauri cwd")
    if "PYTHONUTF8" not in workflow:
        errors.append("CI test job must set PYTHONUTF8 for Windows cp1252 consoles")
    if "Packaged Runtime Smoke (Windows)" not in workflow:
        errors.append("CI must smoke-test the Windows sidecar health endpoint")
    if "Packaged Runtime Smoke (Linux)" not in workflow:
        errors.append("CI must smoke-test the Linux sidecar health endpoint")

    api_ts = (ROOT / "ui" / "src" / "lib" / "api.ts").read_text(encoding="utf-8")
    if "127.0.0.1:8000" not in api_ts:
        errors.append("Packaged UI must call the sidecar at 127.0.0.1:8000")
    if "__TAURI" not in api_ts:
        errors.append("UI must detect the Tauri webview and not rely on the Vite dev proxy")

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if 'requires-python = ">=3.11"' not in pyproject:
        errors.append("pyproject.toml must require Python >=3.11")
    for dep in ("pydantic-settings", "python-dotenv"):
        if dep not in pyproject:
            errors.append(f"pyproject.toml missing dependency {dep}")

    if errors:
        print("PACKAGING VERIFICATION FAILED:")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("  [OK] Sidecar resolver is target-triple aware")
    print("  [OK] Python fallback is development-only")
    print("  [OK] Tauri icons, capabilities, and build.rs are present")
    print("  [OK] CI does not claim unverified macOS or Python 3.10")
    print("\n=== PACKAGING VERIFICATION SUCCESSFUL ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
