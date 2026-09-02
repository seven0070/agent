"""
Runtime Sandbox Enforcing Workspace Path Restrictions, Process Limits, and Network Policies.
Cross-platform Windows & POSIX canonical path resolution.
"""

import os
import subprocess
import time
from typing import Dict, Any, Optional, List
from agent.runtime.models import RuntimeSession, NetworkPolicy
from agent.runtime.policy import ResourceLimits
from agent.runtime.events import RuntimeEvent
from agent.logging import get_logger

logger = get_logger("agent.runtime.sandbox")

class RuntimeSandbox:
    """
    Sandboxed execution boundary controlling filesystem paths, process execution,
    timeouts, output buffer limits, and network access policies.
    """

    def __init__(self, session: RuntimeSession) -> None:
        self.session = session
        self.workspace_dir = os.path.realpath(os.path.abspath(session.workspace_dir))
        os.makedirs(self.workspace_dir, exist_ok=True)
        self.events: List[RuntimeEvent] = []

    def _emit_event(self, event_type: str, operation: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        evt = RuntimeEvent(
            event_type=event_type,
            session_id=self.session.session_id,
            workspace_id=self.session.workspace_id,
            operation=operation,
            status=status,
            details=details or {},
        )
        self.events.append(evt)
        logger.info(f"RuntimeEvent: {event_type} [{operation} -> {status}]")

    def resolve_and_validate_path(self, relative_path: str) -> str:
        """
        Resolves path and enforces strict workspace root isolation.
        Cross-platform Windows (drive letters, backslashes) & POSIX canonical resolution.
        Prevents path traversal attacks (e.g. '../', 'C:\\Windows', absolute escapes).
        """
        clean_path = relative_path.lstrip("/\\")
        target_path = os.path.realpath(os.path.abspath(os.path.join(self.workspace_dir, clean_path)))

        try:
            common = os.path.commonpath([self.workspace_dir, target_path])
        except ValueError:
            # Raised on Windows when paths are on different drive letters (e.g. C: vs D:)
            self._emit_event("PERMISSION_DENIED", "path_validation", "denied", {"path": relative_path})
            raise PermissionError(f"Access Denied: Path '{relative_path}' escapes sandbox workspace root.")

        if common != self.workspace_dir:
            self._emit_event("PERMISSION_DENIED", "path_validation", "denied", {"path": relative_path})
            raise PermissionError(f"Access Denied: Path '{relative_path}' escapes sandbox workspace root.")

        return target_path

    def check_network_allowed(self, target_host: str) -> bool:
        """Checks if outbound network connection is allowed under current NetworkPolicy."""
        if self.session.network_policy == NetworkPolicy.DENY:
            self._emit_event("PERMISSION_DENIED", "network_access", "blocked", {"host": target_host})
            return False
        elif self.session.network_policy == NetworkPolicy.ALLOWLIST:
            allowed = self.session.metadata.get("allowed_hosts", [])
            is_allowed = target_host in allowed
            if not is_allowed:
                self._emit_event("PERMISSION_DENIED", "network_access", "blocked", {"host": target_host})
            return is_allowed
        return True

    def execute_process(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a process with timeout enforcement and output buffer size capping.
        """
        target_cwd = self.resolve_and_validate_path(cwd) if cwd else self.workspace_dir
        timeout = self.session.limits.timeout_seconds
        max_output = self.session.limits.max_output_bytes

        # Sanitize environment variables: do not inherit sensitive host keys directly
        safe_env = dict(env or os.environ)
        safe_env.pop("OPENAI_API_KEY", None)
        safe_env.pop("DASHSCOPE_API_KEY", None)
        safe_env.pop("ANTHROPIC_API_KEY", None)

        self._emit_event("EXECUTION_STARTED", "process_run", "running", {"cmd": cmd, "cwd": target_cwd})
        start_time = time.perf_counter()

        try:
            proc = subprocess.run(
                cmd,
                cwd=target_cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=safe_env,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            stdout = proc.stdout[:max_output]
            stderr = proc.stderr[:max_output]

            status = "success" if proc.returncode == 0 else "failed"
            self._emit_event("EXECUTION_COMPLETED", "process_run", status, {"exit_code": proc.returncode})

            return {
                "success": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "duration_ms": round(elapsed_ms, 2),
                "truncated": len(proc.stdout) > max_output or len(proc.stderr) > max_output,
            }

        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._emit_event("RESOURCE_LIMIT", "process_run", "timeout", {"timeout_seconds": timeout})
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Process execution timed out after {timeout} seconds.",
                "duration_ms": round(elapsed_ms, 2),
                "truncated": False,
            }
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._emit_event("EXECUTION_FAILED", "process_run", "error", {"error": str(exc)})
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution Error: {str(exc)}",
                "duration_ms": round(elapsed_ms, 2),
                "truncated": False,
            }
