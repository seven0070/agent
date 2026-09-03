"""
Jcode Adapter Implementation of CodingEngineInterface.
Manages session lifecycle, workspace file operations, test execution, permission checks, and event capture.
"""

import time
import os
import re
import uuid
from typing import List, Optional, Dict, Any
from agent.coding.interface import CodingEngineInterface
from agent.coding.models import CodingTask, CodingResult, JcodeEvent
from agent.coding.workspace import CodingWorkspaceRestrictor
from agent.coding.permissions import JcodePermissionInterceptor
from agent.coding.jcode.bridge import JcodeBridge
from agent.capabilities.models import PermissionLevel
from agent.logging import get_logger

logger = get_logger("agent.coding.jcode.adapter")


class JcodeAdapter(CodingEngineInterface):
    """
    Adapter bridging Main Agent to Jcode specialized coding engine.
    """

    def __init__(
        self,
        workspace_dir: str = "data/workspace",
        permission_interceptor: Optional[JcodePermissionInterceptor] = None,
        bridge: Optional[JcodeBridge] = None,
    ) -> None:
        self.workspace_restrictor = CodingWorkspaceRestrictor(workspace_dir=workspace_dir)
        self.permission_interceptor = permission_interceptor or JcodePermissionInterceptor()
        self.bridge = bridge or JcodeBridge()
        self.events: List[JcodeEvent] = []

    def _emit_event(self, event_type: str, session_id: str, task_id: str, payload: Dict[str, Any]) -> None:
        evt = JcodeEvent(
            event_type=event_type,
            session_id=session_id,
            task_id=task_id,
            payload=payload,
        )
        self.events.append(evt)
        logger.info(f"JcodeEvent: {event_type} [session={session_id}, task={task_id}]")

    def execute_coding_task(self, task: CodingTask) -> CodingResult:
        """
        Executes a coding task through Jcode engine session lifecycle.
        Inspects workspace, performs file edits, executes tests, and captures events.
        """
        start_time = time.perf_counter()
        session_id = f"jcode-sess-{uuid.uuid4().hex[:8]}"

        self._emit_event("session_started", session_id, task.task_id, {"workspace": task.workspace_dir})

        write_perm = self.permission_interceptor.evaluate_tool_request("write_file", task.goal)
        if write_perm == PermissionLevel.DENY:
            self._emit_event("error", session_id, task.task_id, {"error": "Permission Denied"})
            return CodingResult(
                task_id=task.task_id,
                status="failed",
                summary="Coding task execution DENIED by security policy.",
                errors=["Permission Denied by JcodePermissionInterceptor"],
                duration_ms=0.0,
            )

        files_changed: List[str] = []
        errors: List[str] = []

        try:
            workspace_root = self.workspace_restrictor.workspace_dir
            explicit_files: Dict[str, str] = (task.metadata or {}).get("files") or {}
            generated_test = None

            if explicit_files:
                for rel_path, content in explicit_files.items():
                    abs_path = self.workspace_restrictor.validate_and_resolve(rel_path)
                    parent = os.path.dirname(abs_path)
                    if parent:
                        os.makedirs(parent, exist_ok=True)
                    with open(abs_path, "w", encoding="utf-8") as handle:
                        handle.write(content)
                    files_changed.append(rel_path.replace("\\", "/"))
                    self._emit_event(
                        "tool_executed",
                        session_id,
                        task.task_id,
                        {"action": "create_file", "file": rel_path},
                    )
                self.bridge.execute_bridge_session(
                    {
                        "task_id": task.task_id,
                        "workspace_dir": workspace_root,
                        "files_to_create": files_changed,
                    }
                )
            else:
                from agent.coding.generator import generate_module_source, generate_workspace_files, infer_spec_from_workspace
                from agent.coding.goal_spec import parse_coding_goal

                repair_goal = bool(re.search(r"\b(debug|fix|repair|broken|failing)\b", task.goal, flags=re.IGNORECASE))
                inferred = infer_spec_from_workspace(workspace_root) if repair_goal else None
                spec = inferred or parse_coding_goal(task.goal)
                generated_test = spec.test_name
                if inferred is not None:
                    generated = {spec.module_name: generate_module_source(spec)}
                else:
                    generated = generate_workspace_files(spec)
                for rel_path, content in generated.items():
                    abs_path = self.workspace_restrictor.validate_and_resolve(rel_path)
                    parent = os.path.dirname(abs_path)
                    if parent:
                        os.makedirs(parent, exist_ok=True)
                    with open(abs_path, "w", encoding="utf-8") as handle:
                        handle.write(content)
                    files_changed.append(rel_path.replace("\\", "/"))
                    self._emit_event(
                        "tool_executed",
                        session_id,
                        task.task_id,
                        {"action": "create_file", "file": rel_path},
                    )
                self.bridge.execute_bridge_session(
                    {
                        "task_id": task.task_id,
                        "workspace_dir": workspace_root,
                        "files_to_create": files_changed,
                        "goal": task.goal,
                    }
                )

            tests_run = 0
            tests_passed = 0
            tests_failed = 0

            if task.test_command:
                self._emit_event("tool_started", session_id, task.task_id, {"action": "run_tests", "command": task.test_command})
                from agent.runtime.pytest_runner import run_workspace_tests

                test_file = generated_test
                if test_file and not os.path.isfile(os.path.join(workspace_root, test_file)):
                    test_file = None
                proc = run_workspace_tests(workspace_root, test_target=test_file)
                tests_run = 1
                if proc.get("success"):
                    tests_passed = 1
                    self._emit_event("tool_executed", session_id, task.task_id, {"action": "run_tests", "status": "passed"})
                else:
                    tests_failed = 1
                    errors.append(f"Test suite failure: {proc.get('stderr')}")
                    self._emit_event("tool_executed", session_id, task.task_id, {"action": "run_tests", "status": "failed"})

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._emit_event("turn_completed", session_id, task.task_id, {"files_changed": files_changed})

            return CodingResult(
                task_id=task.task_id,
                status="success" if tests_failed == 0 else "failed",
                summary=f"Jcode completed task '{task.task_id}'. Created/edited {len(files_changed)} files.",
                files_changed=files_changed,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                tool_calls_count=len(files_changed) + (1 if task.test_command else 0),
                errors=errors,
                duration_ms=round(elapsed_ms, 2),
                metadata={"session_id": session_id, "workspace_dir": task.workspace_dir},
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._emit_event("error", session_id, task.task_id, {"error": str(exc)})
            return CodingResult(
                task_id=task.task_id,
                status="error",
                summary=f"Jcode execution error in task '{task.task_id}'",
                errors=[str(exc)],
                duration_ms=round(elapsed_ms, 2),
                metadata={"session_id": session_id},
            )
