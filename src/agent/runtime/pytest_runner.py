"""Run workspace tests without treating a frozen sidecar executable as Python."""

from __future__ import annotations

import os
import runpy
import sys
import traceback
from typing import Any, Dict, Optional


def run_workspace_tests(
    workspace_dir: str,
    test_target: Optional[str] = None,
    timeout_seconds: float = 30.0,
) -> Dict[str, Any]:
    """
    Execute pytest-style tests inside a sandbox workspace.

    Packaged sidecars cannot spawn ``sys.executable -m pytest`` because the
    executable is the FastAPI backend, not a Python interpreter.
    """
    workspace_dir = os.path.abspath(workspace_dir)
    if getattr(sys, "frozen", False):
        return _run_stdlib_tests(workspace_dir, test_target)

    from agent.runtime.models import NetworkPolicy, RuntimeSession
    from agent.runtime.policy import ResourceLimits
    from agent.runtime.sandbox import RuntimeSandbox

    sandbox = RuntimeSandbox(
        session=RuntimeSession(
            session_id="pytest-runner",
            workspace_id="pytest-runner",
            workspace_dir=workspace_dir,
            network_policy=NetworkPolicy.DENY,
            limits=ResourceLimits(timeout_seconds=timeout_seconds, max_output_bytes=65536),
        )
    )
    target = test_target or "."
    if os.path.isabs(target):
        rel = os.path.relpath(target, workspace_dir)
        sandbox.resolve_and_validate_path(rel)
        cmd_target = rel
    else:
        sandbox.resolve_and_validate_path(target)
        cmd_target = target
    cmd = [sys.executable, "-m", "pytest", cmd_target, "-q"]
    return sandbox.execute_process(
        cmd=cmd,
        cwd=".",
        env={**os.environ, "PYTHONPATH": workspace_dir},
    )


def _run_stdlib_tests(workspace_dir: str, test_target: Optional[str]) -> Dict[str, Any]:
    """Discover and execute ``test_*`` functions without an external pytest binary."""
    if test_target and os.path.isfile(test_target):
        files = [test_target]
    elif test_target and os.path.isfile(os.path.join(workspace_dir, test_target)):
        files = [os.path.join(workspace_dir, test_target)]
    else:
        files = []
        for root, _, filenames in os.walk(workspace_dir):
            for filename in filenames:
                if filename.startswith("test_") and filename.endswith(".py"):
                    files.append(os.path.join(root, filename))
                elif filename.endswith("_test.py"):
                    files.append(os.path.join(root, filename))
        files = sorted(files)
    if not files:
        return {
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": "No test_*.py files found in workspace.",
        }

    old_cwd = os.getcwd()
    old_path = list(sys.path)
    failures = []
    ran = 0
    try:
        os.chdir(workspace_dir)
        if workspace_dir not in sys.path:
            sys.path.insert(0, workspace_dir)
        for path in files:
            ns: Dict[str, Any] = runpy.run_path(path, run_name=os.path.basename(path))
            for name, fn in list(ns.items()):
                if not name.startswith("test_") or not callable(fn):
                    continue
                ran += 1
                try:
                    fn()
                except Exception:  # noqa: BLE001 — collect assertion failures
                    failures.append(f"{os.path.basename(path)}::{name}\n{traceback.format_exc()}")
    finally:
        os.chdir(old_cwd)
        sys.path[:] = old_path

    stderr = "\n".join(failures)
    return {
        "success": ran > 0 and not failures,
        "exit_code": 0 if ran > 0 and not failures else 1,
        "stdout": f"ran {ran} tests",
        "stderr": stderr,
    }
