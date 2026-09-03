"""
AgentScope 2.x Adapter Implementation.
Maps application domain models (AgentTask, AgentResult) to AgentScope 2.x abstractions.
Integrated with Layer 2 ModelRouter, Layer 3 ContextBuilder, Layer 4 CapabilityBroker, and Layer 5 PlanOrchestrator.
"""

import json
from typing import Any, Dict, List, Optional
from agentscope.agent import Agent
from agentscope.model import ChatModelBase
from agentscope.message import Msg, UserMsg
from agentscope.tool import Toolkit, FunctionTool
from agent.core.models import AgentTask, AgentResult, ModelConfigInfo, ModelExecutionResult
from agent.models.router import ModelRouter
from agent.models.spec import ModelSpec
from agent.models.mock import MockChatModel
from agent.memory.context import ContextBuilder
from agent.memory.session import SessionMemoryManager
from agent.memory.sqlite import SQLiteMemoryBackend
from agent.memory.models import MemoryItem, MemoryType
from agent.capabilities.broker import CapabilityBroker
from agent.capabilities.models import CapabilityResult
from agent.orchestration.planner import RuleBasedPlanner
from agent.orchestration.orchestrator import PlanOrchestrator

_WM_MARKER = "WORKING_MEMORY_STATE"

class AgentScopeAdapter:
    """
    Adapter decoupling application domain from AgentScope 2.x engine internals.
    Integrates Layer 2 Router, Layer 3 Context, Layer 4 Broker, and Layer 5 Orchestration.
    """

    def __init__(
        self,
        name: str = "agent-v1-core",
        system_prompt: str = "You are a helpful AI assistant.",
        router: Optional[ModelRouter] = None,
        context_builder: Optional[ContextBuilder] = None,
        broker: Optional[CapabilityBroker] = None,
        planner: Optional[RuleBasedPlanner] = None,
        orchestrator: Optional[PlanOrchestrator] = None,
        model: Optional[ChatModelBase] = None,
        model_config_info: Optional[ModelConfigInfo] = None,
    ) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.router = router or ModelRouter()
        self.context_builder = context_builder or ContextBuilder(
            session_manager=SessionMemoryManager(),
            long_term_memory=SQLiteMemoryBackend(),
        )
        self.broker = broker or CapabilityBroker()
        self.planner = planner or RuleBasedPlanner()
        self.orchestrator = orchestrator or PlanOrchestrator(broker=self.broker)
        self.model_config_info = model_config_info or ModelConfigInfo()
        self.last_plan = None

        self.toolkit = self._build_toolkit()

        if model is not None:
            mock_name = getattr(model, "model_name", "custom-override")
            spec = ModelSpec(
                id="custom-override",
                provider="mock",
                model_name=str(mock_name),
                priority=0,
            )
            self.router.registry.register(spec)
            original_create = self.router.factory.create_model
            def _custom_create(s: ModelSpec) -> ChatModelBase:
                if s.id == "custom-override":
                    return model
                return original_create(s)
            self.router.factory.create_model = _custom_create

        init_model = model or self.router.factory.create_model(self.router.select_model())
        self._agentscope_agent = Agent(
            name=self.name,
            system_prompt=self.system_prompt,
            model=init_model,
            toolkit=self.toolkit,
        )

    def _build_toolkit(self) -> Toolkit:
        """Converts registered ToolSpec items into AgentScope FunctionTool instances."""
        tools_list = []
        for spec in self.broker.registry.list_tools():
            tool_id = spec.id
            def _make_func(tid: str):
                def _tool_func(**kwargs: Any) -> str:
                    res: CapabilityResult = self.broker.execute_tool(tid, kwargs)
                    if res.success:
                        return str(res.output)
                    return f"Error ({res.permission_status.value}): {res.error}"
                return _tool_func

            func_tool = FunctionTool(
                func=_make_func(tool_id),
                name=spec.name,
                description=spec.description,
            )
            tools_list.append(func_tool)

        return Toolkit(tools=tools_list)

    def convert_task_to_msg(self, task: AgentTask) -> Msg:
        """Converts application AgentTask to AgentScope UserMsg with ContextBuilder prompt."""
        contextual_prompt = self.context_builder.build_context_prompt(
            task_prompt=task.prompt,
            session_id=task.session_id,
        )
        return UserMsg(name="user", content=contextual_prompt)

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Executes a task through Layer 5 PlanOrchestrator or Layer 2 ModelRouter.
        Converts response to structured AgentResult and persists turn to memory.
        """
        if task.session_id and self.context_builder.session_manager:
            self._hydrate_working_memory(task.session_id)
            self.context_builder.session_manager.add_turn(
                session_id=task.session_id,
                role="user",
                content=task.prompt,
            )

        workspace_dir = None
        if getattr(self.broker, "workspace_manager", None) is not None:
            workspace_dir = self.broker.workspace_manager.workspace_dir
        session_hints: Dict[str, Any] = {}
        if task.session_id and self.context_builder.session_manager:
            working = self.context_builder.session_manager.get_working_memory(task.session_id)
            relevant = working.relevant_for(task.prompt)
            session_hints["working_memory"] = relevant
            follow = working.follow_up_value()
            if follow:
                session_hints["last_output"] = follow
            elif relevant.get("last_outputs"):
                session_hints["last_output"] = str(list(relevant["last_outputs"].values())[-1])
            elif relevant.get("artifacts"):
                session_hints["last_output"] = str(list(relevant["artifacts"].values())[-1])
            if not session_hints.get("last_output"):
                history = self.context_builder.session_manager.get_session_history(task.session_id, limit=12)
                for item in reversed(history):
                    if item.source in {"agent", "assistant"} and (item.content or "").strip():
                        session_hints["last_output"] = item.content
                        break
        plan = self.planner.create_plan(
            goal=task.prompt,
            workspace_dir=workspace_dir,
            session_hints=session_hints or None,
        )
        self.last_plan = plan
        tools_used: list[str] = []
        files_changed: list[str] = []

        has_tool_tasks = any(t.required_tool_id is not None for t in plan.tasks.values())
        if has_tool_tasks:
            completed_plan = self.orchestrator.execute_plan(plan)
            self.last_plan = completed_plan
            outputs_summary = []
            for tid, t in completed_plan.tasks.items():
                if t.required_tool_id:
                    tools_used.append(t.required_tool_id)
                if t.outputs is not None:
                    outputs_summary.append(str(t.outputs))
                if t.error:
                    outputs_summary.append(str(t.error))
                meta = t.metadata or {}
                if meta.get("files_changed"):
                    files_changed.extend(list(meta["files_changed"]))
            if task.session_id and self.context_builder.session_manager:
                mgr = self.context_builder.session_manager
                mgr.update_working_memory(
                    task.session_id,
                    goal=task.prompt,
                    active_plan_id=completed_plan.id,
                )
                for t in completed_plan.tasks.values():
                    mgr.record_step(
                        task.session_id,
                        t.description,
                        tool_id=t.required_tool_id,
                        output=t.outputs if t.outputs is not None else t.error,
                    )
                    resolved = (t.metadata or {}).get("resolved_inputs") or {}
                    if t.required_tool_id == "write_file-v1":
                        rel = str(resolved.get("relative_path") or t.inputs.get("relative_path") or "")
                        content = str(resolved.get("content") or "")
                        if rel:
                            mgr.record_artifact(task.session_id, rel, content or str(t.outputs or ""))
                    if t.required_tool_id == "coding-engine-v1":
                        mgr.record_step(task.session_id, "coding-complete", tool_id="coding-engine-v1", output=t.outputs)
                        for rel in (t.metadata or {}).get("files_changed") or []:
                            mgr.record_artifact(task.session_id, str(rel), str(t.outputs or ""))
                self._persist_working_memory(task.session_id)
            final_output = "\n".join(outputs_summary)
            exec_result = ModelExecutionResult(
                model_id="orchestrator",
                provider="orchestration",
                output=final_output,
                status="success" if completed_plan.status == "completed" else completed_plan.status,
                is_fallback=False,
            )
        else:
            from agent.orchestration.intent import CONVERSE, classify_intent

            intent = classify_intent(task.prompt, workspace_dir=workspace_dir)
            from agent.orchestration.intent import requested_provider

            named_provider = requested_provider(task.prompt)
            selected = None
            try:
                selected = self.router.select_model()
            except Exception:
                selected = None
            provider_mismatch = bool(
                named_provider
                and named_provider != "mock"
                and (selected is None or selected.provider.lower() != named_provider)
            )
            if intent.kind != CONVERSE or provider_mismatch:
                exec_result = ModelExecutionResult(
                    model_id="orchestrator",
                    provider="orchestration",
                    output=(
                        "Required capability/model is unavailable for this task. "
                        "No real operation was performed."
                    ),
                    status="failed",
                    is_fallback=False,
                    error="capability-unavailable",
                )
            else:
                user_msg = self.convert_task_to_msg(task)

                async def _invoke_model_spec(spec: ModelSpec) -> str:
                    chat_model = self.router.factory.create_model(spec)
                    agentscope_agent = Agent(
                        name=self.name,
                        system_prompt=self.system_prompt,
                        model=chat_model,
                        toolkit=self.toolkit,
                    )
                    reply_msg: Msg = await agentscope_agent.reply(inputs=user_msg)
                    return reply_msg.get_text_content() if reply_msg else ""

                exec_result = await self.router.execute_with_fallback(
                    task=task,
                    executor_fn=_invoke_model_spec,
                )

        if task.session_id and self.context_builder.session_manager:
            self.context_builder.session_manager.add_turn(
                session_id=task.session_id,
                role="agent",
                content=exec_result.output,
            )

        if self.context_builder.long_term_memory:
            turn_id = f"mem-{task.task_id}"
            self.context_builder.long_term_memory.store_memory(
                MemoryItem(
                    id=turn_id,
                    content=f"User: {task.prompt} | Agent: {exec_result.output}",
                    memory_type=MemoryType.CONVERSATION,
                    session_id=task.session_id,
                )
            )
        if task.session_id:
            self._persist_working_memory(task.session_id)

        return AgentResult(
            task_id=task.task_id,
            output=exec_result.output,
            agent_version="agent-v1",
            model=f"{exec_result.provider}:{exec_result.model_id}",
            status=exec_result.status,
            model_execution=exec_result,
            metadata={
                "agentscope_agent_name": self.name,
                "session_id": task.session_id,
                "plan_id": plan.id,
                "plan_version": plan.version,
                "plan_status": getattr(self.last_plan, "status", plan.status),
                "is_fallback": getattr(exec_result, "is_fallback", False),
                "tools_used": tools_used,
                "files_changed": files_changed,
            },
        )

    def _hydrate_working_memory(self, session_id: str) -> None:
        mgr = self.context_builder.session_manager
        if mgr is None:
            return
        working = mgr.get_working_memory(session_id)
        if working.artifacts or working.last_outputs:
            return
        backend = self.context_builder.long_term_memory
        if backend is None:
            return
        items = backend.retrieve_memories(
            query=_WM_MARKER,
            session_id=session_id,
            memory_type=MemoryType.TASK.value,
            limit=8,
        )
        for item in items:
            if _WM_MARKER not in (item.content or ""):
                continue
            raw = item.content.split(_WM_MARKER, 1)[-1].strip()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            working.goal = str(data.get("goal") or working.goal)
            working.active_plan_id = data.get("active_plan_id") or working.active_plan_id
            working.completed_steps = list(data.get("completed_steps") or working.completed_steps)
            working.artifacts = dict(data.get("artifacts") or working.artifacts)
            working.last_outputs = dict(data.get("last_outputs") or working.last_outputs)
            working.decisions = list(data.get("decisions") or working.decisions)
            return

    def _persist_working_memory(self, session_id: str) -> None:
        mgr = self.context_builder.session_manager
        backend = self.context_builder.long_term_memory
        if mgr is None or backend is None:
            return
        working = mgr.get_working_memory(session_id)
        payload = {
            "goal": working.goal,
            "active_plan_id": working.active_plan_id,
            "completed_steps": working.completed_steps[-20:],
            "artifacts": working.artifacts,
            "last_outputs": working.last_outputs,
            "decisions": working.decisions[-20:],
        }
        backend.store_memory(
            MemoryItem(
                id=f"wm-{session_id}",
                content=f"{_WM_MARKER} {json.dumps(payload)}",
                memory_type=MemoryType.TASK,
                source="system",
                session_id=session_id,
            )
        )
