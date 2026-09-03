"""
Plan Orchestrator and Failure Recovery Engine.
Executes plan DAG tasks through CapabilityBroker, handles retries, replanning, and event emissions.
"""

from typing import List, Dict, Any, Optional
from agent.orchestration.models import Plan, PlanTask, TaskState, OrchestrationEvent, transition_task_state
from agent.capabilities.broker import CapabilityBroker
from agent.capabilities.models import CapabilityResult
from agent.logging import get_logger

logger = get_logger("agent.orchestration.orchestrator")

class PlanOrchestrator:
    """
    Executes versioned plans, unlocks ready tasks, enforces Layer 4 capability permissions,
    handles retries, replanning, and emits orchestration audit events.
    """

    def __init__(self, broker: Optional[CapabilityBroker] = None) -> None:
        self.broker = broker or CapabilityBroker()
        self.events: List[OrchestrationEvent] = []

    def _emit_event(self, event_type: str, plan: Plan, task_id: Optional[str] = None, status: str = "ok", metadata: Optional[Dict[str, Any]] = None) -> None:
        evt = OrchestrationEvent(
            event_type=event_type,
            plan_id=plan.id,
            plan_version=plan.version,
            task_id=task_id,
            status=status,
            metadata=metadata or {},
        )
        self.events.append(evt)
        logger.info(f"OrchestrationEvent: {event_type} [plan={plan.id} ({plan.version}), task={task_id}, status={status}]")

    def validate_plan_dag(self, plan: Plan) -> None:
        """
        Validates plan dependency graph using DFS cycle detection.
        Raises ValueError if a cycle is detected.
        """
        visited: Dict[str, int] = {tid: 0 for tid in plan.tasks}  # 0: unvisited, 1: visiting, 2: visited

        def _dfs(tid: str) -> None:
            if tid not in plan.tasks:
                return
            visited[tid] = 1
            for dep_id in plan.tasks[tid].dependencies:
                if dep_id in visited:
                    if visited[dep_id] == 1:
                        raise ValueError(f"Cyclic dependency detected in Plan '{plan.id}': {tid} <-> {dep_id}")
                    if visited[dep_id] == 0:
                        _dfs(dep_id)
            visited[tid] = 2

        for tid in plan.tasks:
            if visited[tid] == 0:
                _dfs(tid)

    def _update_task_states_for_ready(self, plan: Plan) -> List[str]:
        """
        Scans PENDING tasks and transitions them to READY if all dependencies SUCCEEDED.
        Returns list of newly READY task IDs.
        """
        newly_ready: List[str] = []
        for tid, task in plan.tasks.items():
            if task.status in [TaskState.PENDING, TaskState.BLOCKED]:
                deps_succeeded = all(
                    dep_id in plan.tasks and plan.tasks[dep_id].status == TaskState.SUCCEEDED
                    for dep_id in task.dependencies
                )
                if deps_succeeded:
                    task.status = transition_task_state(task.status, TaskState.READY)
                    newly_ready.append(tid)
        return newly_ready

    def execute_plan(self, plan: Plan) -> Plan:
        """
        Executes a plan graph through CapabilityBroker until completion or permanent failure.
        Handles retries and replanning.
        """
        self.validate_plan_dag(plan)
        self._emit_event("PLAN_CREATED", plan, status="active")

        while True:
            # Unlock READY tasks
            self._update_task_states_for_ready(plan)

            # Find next READY task
            ready_tasks = [t for t in plan.tasks.values() if t.status == TaskState.READY]
            if not ready_tasks:
                # Check if all tasks SUCCEEDED
                all_succeeded = all(t.status == TaskState.SUCCEEDED for t in plan.tasks.values())
                if all_succeeded:
                    if not self._verify_final(plan):
                        plan.status = "failed"
                        self._emit_event("PLAN_FAILED", plan, status="failed", metadata={"error": "final verification failed"})
                        return plan
                    plan.status = "completed"
                    self._emit_event("PLAN_COMPLETED", plan, status="success")
                    return plan

                # Check if any task permanently FAILED or BLOCKED
                failed_tasks = [t for t in plan.tasks.values() if t.status in [TaskState.FAILED, TaskState.CANCELLED]]
                if failed_tasks:
                    failed = failed_tasks[0]
                    security_fail = "Access Denied" in (failed.error or "") or "Permission Denied" in (failed.error or "")
                    if security_fail:
                        plan.status = "failed"
                        self._emit_event("PLAN_FAILED", plan, status="failed", metadata={"error": failed.error})
                        return plan
                    replanned = self.replan(plan, failed.id)
                    if replanned:
                        plan = replanned
                        continue
                    else:
                        plan.status = "failed"
                        self._emit_event("PLAN_FAILED", plan, status="failed")
                        return plan

                # No ready tasks and not all succeeded -> deadlock/blocked
                plan.status = "blocked"
                self._emit_event("PLAN_BLOCKED", plan, status="blocked")
                return plan

            # Execute first READY task
            task = ready_tasks[0]
            task.status = transition_task_state(task.status, TaskState.RUNNING)
            self._emit_event("TASK_STARTED", plan, task_id=task.id, status="running")

            outputs = {
                tid: item.outputs for tid, item in plan.tasks.items() if item.outputs is not None
            }
            from agent.orchestration.decompose import resolve_placeholders

            resolved_inputs: Dict[str, Any] = {}
            for k, v in task.inputs.items():
                resolved_inputs[k] = resolve_placeholders(v, outputs)

            # Execute through CapabilityBroker if required_tool_id is present
            if task.required_tool_id:
                res: CapabilityResult = self.broker.execute_tool(task.required_tool_id, resolved_inputs)

                if res.success:
                    task.outputs = res.output
                    task.metadata = {
                        **(task.metadata or {}),
                        **(res.metadata or {}),
                        "resolved_inputs": resolved_inputs,
                    }
                    if not self._verify_task_output(plan, task, resolved_inputs):
                        task.error = task.error or "Intermediate result failed verification"
                        if task.retry_count >= task.max_retries:
                            task.status = transition_task_state(task.status, TaskState.FAILED)
                            self._emit_event("TASK_FAILED", plan, task_id=task.id, status="failed", metadata={"error": task.error})
                        else:
                            task.retry_count += 1
                            task.status = transition_task_state(task.status, TaskState.READY)
                            self._emit_event("TASK_RETRIED", plan, task_id=task.id, status="retrying")
                        continue
                    task.status = transition_task_state(task.status, TaskState.SUCCEEDED)
                    self._emit_event("TASK_COMPLETED", plan, task_id=task.id, status="success")
                else:
                    task.error = res.error
                    security_fail = "Access Denied" in (res.error or "") or "Permission Denied" in (res.error or "")
                    if security_fail or task.retry_count >= task.max_retries:
                        task.status = transition_task_state(task.status, TaskState.FAILED)
                        self._emit_event("TASK_FAILED", plan, task_id=task.id, status="failed", metadata={"error": res.error})
                    else:
                        task.retry_count += 1
                        logger.warning(f"Task '{task.id}' failed. Retrying attempt {task.retry_count}/{task.max_retries}")
                        task.status = transition_task_state(task.status, TaskState.READY)
                        self._emit_event("TASK_RETRIED", plan, task_id=task.id, status="retrying", metadata={"retry_count": task.retry_count})
            else:
                # Default generic task without tool requirement -> auto SUCCEEDED
                task.outputs = f"Executed generic prompt: {task.description}"
                task.status = transition_task_state(task.status, TaskState.SUCCEEDED)
                self._emit_event("TASK_COMPLETED", plan, task_id=task.id, status="success")

    def _verify_task_output(self, plan: Plan, task: PlanTask, resolved_inputs: Dict[str, Any]) -> bool:
        """Reject empty tool successes that cannot satisfy a later write/compute."""
        if task.required_tool_id in {"read_file-v1", "inspect_data-v1"}:
            if task.outputs is None or str(task.outputs).strip() == "":
                task.error = "Empty intermediate result"
                return False
        if task.required_tool_id == "write_file-v1":
            rel = str(resolved_inputs.get("relative_path") or "")
            expected = str(resolved_inputs.get("content") or "")
            if not rel:
                task.error = "Write missing path"
                return False
            try:
                actual = self.broker.workspace_manager.read_file(rel)
            except Exception as exc:  # noqa: BLE001
                task.error = f"Write verification failed: {exc}"
                return False
            if expected and expected.strip() and expected.strip() not in actual and actual.strip() not in expected.strip():
                task.error = "Written content did not match the resolved input"
                return False
        return True

    def _verify_final(self, plan: Plan) -> bool:
        """Confirm every successful write is present in the governed workspace."""
        for task in plan.tasks.values():
            if task.required_tool_id != "write_file-v1" or task.status != TaskState.SUCCEEDED:
                continue
            resolved = (task.metadata or {}).get("resolved_inputs") or {}
            rel = str(resolved.get("relative_path") or task.inputs.get("relative_path") or "")
            if not rel:
                return False
            try:
                actual = self.broker.workspace_manager.read_file(rel)
            except Exception:
                self._emit_event("PLAN_VERIFY_FAILED", plan, task_id=task.id, status="failed")
                return False
            if actual is None:
                return False
        return True

    def replan(self, plan: Plan, failed_task_id: str) -> Optional[Plan]:
        """
        Generates a new plan version when a failed step can be repaired from runtime state.
        Does not invent successful calculator results.
        """
        failed = plan.tasks.get(failed_task_id)
        if failed is None:
            return None
        error = (failed.error or "").lower()
        security_fail = "access denied" in error or "permission denied" in error
        if security_fail or failed.required_tool_id in {"calculator-v1", "capability-unavailable", None}:
            return None

        alt_path = None
        if failed.required_tool_id in {"read_file-v1", "inspect_data-v1"}:
            alt_path = self._alternate_workspace_file(failed)
        if not alt_path:
            return None

        curr_version_num = 1
        if "plan-v" in plan.version:
            try:
                curr_version_num = int(plan.version.split("plan-v")[1])
            except ValueError:
                curr_version_num = 1
        new_version = f"plan-v{curr_version_num + 1}"
        logger.info(
            f"Replanning: Bumping plan version from '{plan.version}' to '{new_version}' due to failure in '{failed_task_id}'"
        )

        new_tasks: Dict[str, PlanTask] = {}
        repair_id = f"{failed_task_id}_repair"
        for tid, t in plan.tasks.items():
            if tid == failed_task_id:
                repaired_inputs = dict(t.inputs)
                repaired_inputs["relative_path"] = alt_path
                new_tasks[repair_id] = PlanTask(
                    id=repair_id,
                    description=f"Retry {t.description} with {alt_path}",
                    dependencies=list(t.dependencies),
                    required_tool_id=t.required_tool_id,
                    inputs=repaired_inputs,
                    max_retries=t.max_retries,
                )
            else:
                cloned_inputs = dict(t.inputs)
                for key, value in list(cloned_inputs.items()):
                    if isinstance(value, str):
                        cloned_inputs[key] = value.replace(f"${failed_task_id}.output", f"${repair_id}.output")
                new_tasks[t.id] = PlanTask(
                    id=t.id,
                    description=t.description,
                    dependencies=[repair_id if d == failed_task_id else d for d in t.dependencies],
                    required_tool_id=t.required_tool_id,
                    inputs=cloned_inputs,
                    status=TaskState.PENDING,
                    max_retries=t.max_retries,
                )

        new_plan = Plan(
            id=plan.id,
            goal=plan.goal,
            version=new_version,
            tasks=new_tasks,
            status="active",
            metadata={"replanned_from": plan.version, "failed_task": failed_task_id, "repair_path": alt_path},
        )
        self._emit_event("PLAN_REVISED", new_plan, status="replanned", metadata={"previous_version": plan.version})
        return new_plan

    def _alternate_workspace_file(self, task: PlanTask) -> Optional[str]:
        wanted = str(task.inputs.get("relative_path") or "")
        suffix = ""
        if "." in wanted:
            suffix = wanted[wanted.rfind(".") :].lower()
        try:
            root = self.broker.workspace_manager.workspace_dir
        except Exception:
            return None
        import os

        candidates: List[str] = []
        if not os.path.isdir(root):
            return None
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                if suffix and name.lower().endswith(suffix):
                    rel = os.path.relpath(os.path.join(dirpath, name), root).replace("\\", "/")
                    if rel != wanted:
                        candidates.append(rel)
        if len(candidates) == 1:
            return candidates[0]
        return None
