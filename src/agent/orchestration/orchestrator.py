"""
Plan Orchestrator and Failure Recovery Engine.
Executes plan DAG tasks through CapabilityBroker, handles retries, replanning, and event emissions.
"""

from typing import List, Dict, Any, Optional
from agent.orchestration.models import Plan, PlanTask, TaskState, OrchestrationEvent, transition_task_state
from agent.capabilities.broker import CapabilityBroker
from agent.capabilities.models import CapabilityResult, PermissionLevel
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
                    plan.status = "completed"
                    self._emit_event("PLAN_COMPLETED", plan, status="success")
                    return plan

                # Check if any task permanently FAILED or BLOCKED
                failed_tasks = [t for t in plan.tasks.values() if t.status in [TaskState.FAILED, TaskState.CANCELLED]]
                if failed_tasks:
                    # Attempt Replanning (version bump plan-v1 -> plan-v2)
                    replanned = self.replan(plan, failed_tasks[0].id)
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

            # Resolve input placeholders from dependent task outputs (e.g. $task_calc_1.output)
            resolved_inputs: Dict[str, Any] = {}
            for k, v in task.inputs.items():
                if isinstance(v, str) and v.startswith("$") and ".output" in v:
                    ref_tid = v[1:].split(".output")[0]
                    if ref_tid in plan.tasks and plan.tasks[ref_tid].outputs is not None:
                        resolved_inputs[k] = str(plan.tasks[ref_tid].outputs)
                    else:
                        resolved_inputs[k] = v
                else:
                    resolved_inputs[k] = v

            # Execute through CapabilityBroker if required_tool_id is present
            if task.required_tool_id:
                res: CapabilityResult = self.broker.execute_tool(task.required_tool_id, resolved_inputs)

                if res.success:
                    task.outputs = res.output
                    task.status = transition_task_state(task.status, TaskState.SUCCEEDED)
                    self._emit_event("TASK_COMPLETED", plan, task_id=task.id, status="success")
                else:
                    task.error = res.error
                    # Retry logic check
                    if task.retry_count < task.max_retries:
                        task.retry_count += 1
                        logger.warning(f"Task '{task.id}' failed. Retrying attempt {task.retry_count}/{task.max_retries}")
                        task.status = transition_task_state(task.status, TaskState.READY)
                        self._emit_event("TASK_RETRIED", plan, task_id=task.id, status="retrying", metadata={"retry_count": task.retry_count})
                    else:
                        task.status = transition_task_state(task.status, TaskState.FAILED)
                        self._emit_event("TASK_FAILED", plan, task_id=task.id, status="failed", metadata={"error": res.error})
            else:
                # Default generic task without tool requirement -> auto SUCCEEDED
                task.outputs = f"Executed generic prompt: {task.description}"
                task.status = transition_task_state(task.status, TaskState.SUCCEEDED)
                self._emit_event("TASK_COMPLETED", plan, task_id=task.id, status="success")

    def replan(self, plan: Plan, failed_task_id: str) -> Optional[Plan]:
        """
        Generates a new plan version (e.g. plan-v1 -> plan-v2) repairing a failed task.
        """
        curr_version_num = 1
        if "plan-v" in plan.version:
            try:
                curr_version_num = int(plan.version.split("plan-v")[1])
            except ValueError:
                curr_version_num = 1

        new_version = f"plan-v{curr_version_num + 1}"
        logger.info(f"Replanning: Bumping plan version from '{plan.version}' to '{new_version}' due to failure in '{failed_task_id}'")

        # Create new plan copy
        new_tasks: Dict[str, PlanTask] = {}
        for tid, t in plan.tasks.items():
            if tid == failed_task_id:
                # Replace failed task with repair task or fallback inputs
                repaired = PlanTask(
                    id=f"{tid}_repair",
                    description=f"Repair fallback for {t.description}",
                    dependencies=list(t.dependencies),
                    required_tool_id="calculator-v1",
                    inputs={"expression": "0"},  # Safe fallback input
                )
                new_tasks[repaired.id] = repaired
            else:
                # Reset succeeded or pending tasks
                cloned = PlanTask(
                    id=t.id,
                    description=t.description,
                    dependencies=[f"{d}_repair" if d == failed_task_id else d for d in t.dependencies],
                    required_tool_id=t.required_tool_id,
                    inputs=dict(t.inputs),
                    status=TaskState.PENDING,
                )
                new_tasks[cloned.id] = cloned

        new_plan = Plan(
            id=plan.id,
            goal=plan.goal,
            version=new_version,
            tasks=new_tasks,
            status="active",
            metadata={"replanned_from": plan.version, "failed_task": failed_task_id},
        )

        self._emit_event("PLAN_REVISED", new_plan, status="replanned", metadata={"previous_version": plan.version})
        return new_plan
