"""
Unified Agent execution pipeline.

USER GOAL → MEMORY → PLANNER → TOOLS / JCODE → RUNTIME → EVALUATION → RESULT
Observations from this path feed Layer 9 (never a disconnected demo loop).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from agent.capabilities.broker import CapabilityBroker
from agent.capabilities.models import PermissionLevel
from agent.constitution import ConstitutionalGuard
from agent.core.agent import AgentV1
from agent.core.models import AgentResult, AgentTask
from agent.evolution.controller import EvolutionController
from agent.integrations.agentscope.adapter import AgentScopeAdapter
from agent.logging import get_logger
from agent.orchestration.models import Plan, TaskState

logger = get_logger("agent.core.pipeline")

EventSink = Callable[[str, Dict[str, Any]], None]


class AgentPipeline:
    """Single production execution path used by the API, CLI, and evaluation."""

    def __init__(
        self,
        adapter: AgentScopeAdapter,
        evolution: EvolutionController,
        broker: CapabilityBroker,
        guard: Optional[ConstitutionalGuard] = None,
    ) -> None:
        self.adapter = adapter
        self.evolution = evolution
        self.broker = broker
        self.guard = guard or ConstitutionalGuard()
        self.agent = AgentV1(adapter=adapter)
        self.activity: List[Dict[str, Any]] = []
        # Local-first desktop: a submitted goal is implicit approval for workspace writes.
        # Shell / unrestricted network remain DENY.
        self.broker.permission_policy.set_permission("write_file-v1", PermissionLevel.ALLOW)
        self.broker.permission_policy.set_permission("coding-engine-v1", PermissionLevel.ALLOW)

    def _record_activity(self, event_type: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        frame = {
            "event_type": event_type,
            "session_id": session_id,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.activity.append(frame)
        if len(self.activity) > 400:
            self.activity = self.activity[-400:]
        return frame

    def recent_activity(self, limit: int = 80, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        items = self.activity
        if session_id:
            items = [e for e in items if e.get("session_id") == session_id]
        return items[-limit:]

    async def execute(
        self,
        session_id: str,
        prompt: str,
        sink: Optional[EventSink] = None,
    ) -> Dict[str, Any]:
        self.guard.validate_action({"type": "execute_task", "target": "agent_core"})
        task_id = f"task-{uuid.uuid4().hex[:8]}"

        def emit(event_type: str, payload: Dict[str, Any]) -> None:
            frame = self._record_activity(event_type, session_id, payload)
            if sink:
                sink(event_type, payload)
            logger.info(f"{event_type} session={session_id} task={task_id}")
            return frame

        emit("MESSAGE_STARTED", {"prompt": prompt, "status": "processing", "task_id": task_id})
        emit("MEMORY_CONTEXT", {"session_id": session_id, "status": "assembled"})

        task = AgentTask(task_id=task_id, prompt=prompt, session_id=session_id)
        result: AgentResult = await self.agent.execute_task(task)

        plan: Optional[Plan] = getattr(self.adapter, "last_plan", None)
        tools_used: List[str] = list((result.metadata or {}).get("tools_used") or [])
        jcode_files: List[str] = list((result.metadata or {}).get("files_changed") or [])

        if plan is not None:
            emit(
                "PLAN_CREATED",
                {
                    "plan_id": plan.id,
                    "version": plan.version,
                    "status": plan.status,
                    "tasks": [t.model_dump() for t in plan.tasks.values()],
                },
            )
            for event in getattr(self.adapter.orchestrator, "events", [])[-20:]:
                emit(
                    event.event_type,
                    {
                        "plan_id": event.plan_id,
                        "task_id": event.task_id,
                        "status": event.status,
                        "metadata": event.metadata,
                    },
                )
            for task_obj in plan.tasks.values():
                if task_obj.required_tool_id:
                    emit(
                        "TOOL_EXECUTED",
                        {
                            "tool_id": task_obj.required_tool_id,
                            "success": task_obj.status == TaskState.SUCCEEDED,
                            "output": task_obj.outputs,
                            "error": task_obj.error,
                        },
                    )
                    if task_obj.required_tool_id == "coding-engine-v1":
                        emit(
                            "JCODE_COMPLETED",
                            {
                                "status": task_obj.status.value,
                                "output": task_obj.outputs,
                                "files_changed": jcode_files,
                            },
                        )

        emit("RUNTIME_ACTIVITY", {"sandbox": "layer-7", "tools_used": tools_used})

        observations = self._observations_from_result(result, plan)
        for obs in observations:
            self.evolution.observer.record_observation(
                component=obs["component"],
                success=obs["success"],
                error=obs.get("error"),
                latency_ms=obs.get("latency_ms", 0.0),
                metadata=obs.get("metadata") or {},
            )
        emit("OBSERVATION_RECORDED", {"count": len(observations)})

        status = result.status if result.status in ("success", "completed", "failed", "error") else (
            "success" if plan is None or plan.status == "completed" else plan.status
        )
        emit(
            "MESSAGE_COMPLETED",
            {
                "content": result.output,
                "status": status,
                "plan_id": plan.id if plan else None,
                "plan_status": plan.status if plan else None,
                "tools_used": tools_used,
                "model": result.model,
            },
        )
        return {
            "task_id": task_id,
            "result": result,
            "plan": plan,
            "observations": observations,
        }

    @staticmethod
    def _observations_from_result(result: AgentResult, plan: Optional[Plan]) -> List[Dict[str, Any]]:
        observations: List[Dict[str, Any]] = []
        if plan is None:
            observations.append(
                {
                    "component": "model",
                    "success": result.status in ("success", "completed"),
                    "error": None if result.status in ("success", "completed") else result.status,
                }
            )
            return observations
        for task in plan.tasks.values():
            success = task.status == TaskState.SUCCEEDED
            if task.required_tool_id == "coding-engine-v1":
                component = "coding"
            elif task.required_tool_id:
                component = "tool"
            else:
                component = "planner"
            observations.append(
                {
                    "component": component,
                    "success": success,
                    "error": task.error if not success else None,
                    "metadata": {"tool_id": task.required_tool_id, "task_id": task.id},
                }
            )
        if plan.status == "failed":
            observations.append(
                {
                    "component": "planner",
                    "success": False,
                    "error": "plan_failed",
                    "metadata": {"plan_id": plan.id},
                }
            )
        return observations
