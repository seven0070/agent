#!/usr/bin/env python3
"""Build the PyInstaller Agent backend sidecar with Tauri target-triple naming."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def target_triple() -> str:
    override = os.environ.get("AGENT_TARGET_TRIPLE")
    if override:
        return override
    platform = sys.platform
    arch = os.environ.get("PROCESSOR_ARCHITECTURE", "").lower()
    machine = os.uname().machine.lower() if hasattr(os, "uname") else arch
    if platform.startswith("win"):
        if "arm" in machine or "arm" in arch:
            return "aarch64-pc-windows-msvc"
        return "x86_64-pc-windows-msvc"
    if platform == "darwin":
        return "aarch64-apple-darwin" if machine in {"arm64", "aarch64"} else "x86_64-apple-darwin"
    if machine in {"aarch64", "arm64"}:
        return "aarch64-unknown-linux-gnu"
    return "x86_64-unknown-linux-gnu"


def sidecar_filename(triple: str) -> str:
    name = f"agent-backend-{triple}"
    if sys.platform.startswith("win"):
        return f"{name}.exe"
    return name


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Agent backend sidecar")
    parser.add_argument("--triple", default=target_triple())
    parser.add_argument("--output-dir", default="src-tauri/binaries")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    output_dir = (repo / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = repo / "dist"
    dist_dir.mkdir(exist_ok=True)

    filename = sidecar_filename(args.triple)
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--name",
        "agent-backend",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(repo / "build" / "pyinstaller"),
        "--specpath",
        str(repo / "build"),
        "--hidden-import",
        "agent.api.app",
        "--hidden-import",
        "agent.api.main",
        "--hidden-import",
        "uvicorn",
        "--hidden-import",
        "pydantic_settings",
        "--hidden-import",
        "dotenv",
        "--collect-submodules",
        "agent",
        str(repo / "src" / "agent" / "api" / "main.py"),
    ]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=repo)

    built = dist_dir / ("agent-backend.exe" if sys.platform.startswith("win") else "agent-backend")
    if not built.exists():
        raise SystemExit(f"PyInstaller did not produce {built}")
    dest = output_dir / filename
    shutil.copy2(built, dest)
    dest.chmod(dest.stat().st_mode | 0o111)
    print(f"Sidecar written to {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
