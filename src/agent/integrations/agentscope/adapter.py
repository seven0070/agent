"""
AgentScope 2.x Adapter Implementation.
Maps application domain models (AgentTask, AgentResult) to AgentScope 2.x abstractions.
Integrated with Layer 2 ModelRouter, Layer 3 ContextBuilder, Layer 4 CapabilityBroker, and Layer 5 PlanOrchestrator.
"""

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
            self.context_builder.session_manager.add_turn(
                session_id=task.session_id,
                role="user",
                content=task.prompt,
            )

        plan = self.planner.create_plan(goal=task.prompt)

        has_tool_tasks = any(t.required_tool_id is not None for t in plan.tasks.values())
        if has_tool_tasks:
            completed_plan = self.orchestrator.execute_plan(plan)
            outputs_summary = [f"{tid}: {t.outputs}" for tid, t in completed_plan.tasks.items()]
            final_output = "\n".join(outputs_summary)

            exec_result = ModelExecutionResult(
                model_id="orchestrator",
                provider="orchestration",
                output=final_output,
                status=completed_plan.status,
                is_fallback=False,
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
                "is_fallback": getattr(exec_result, "is_fallback", False),
            },
        )
