"""
AgentScope 2.x Adapter Implementation.
Maps application domain models (AgentTask, AgentResult) to AgentScope 2.x abstractions.
Integrated with Layer 2 ModelRouter for dynamic provider selection and fallback.
"""

from typing import Any, Dict, List, Optional
from agentscope.agent import Agent
from agentscope.model import ChatModelBase
from agentscope.message import Msg, UserMsg
from agent.core.models import AgentTask, AgentResult, ModelConfigInfo, ModelExecutionResult
from agent.models.router import ModelRouter
from agent.models.spec import ModelSpec
from agent.models.mock import MockChatModel

class AgentScopeAdapter:
    """
    Adapter decoupling application domain from AgentScope 2.x engine internals.
    Uses Layer 2 ModelRouter for provider management and fallback execution.
    """

    def __init__(
        self,
        name: str = "agent-v1-core",
        system_prompt: str = "You are a helpful AI assistant.",
        router: Optional[ModelRouter] = None,
        model: Optional[ChatModelBase] = None,
        model_config_info: Optional[ModelConfigInfo] = None,
    ) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.router = router or ModelRouter()
        self.model_config_info = model_config_info or ModelConfigInfo()

        # Backward compatibility support if direct model instance is passed
        if model is not None:
            mock_name = getattr(model, "model_name", "custom-model")
            spec = ModelSpec(
                id="custom-override",
                provider="mock",
                model_name=str(mock_name),
                priority=0,
            )
            self.router.registry.register(spec)
            # Override factory creation for custom-override ID to return passed model
            original_create = self.router.factory.create_model
            def _custom_create(s: ModelSpec) -> ChatModelBase:
                if s.id == "custom-override":
                    return model
                return original_create(s)
            self.router.factory.create_model = _custom_create

        # Helper property for Layer 1 test assertion compatibility
        init_model = model or self.router.factory.create_model(self.router.select_model())
        self._agentscope_agent = Agent(
            name=self.name,
            system_prompt=self.system_prompt,
            model=init_model,
        )

    def convert_task_to_msg(self, task: AgentTask) -> Msg:
        """Converts application AgentTask to AgentScope UserMsg."""
        return UserMsg(name="user", content=task.prompt)

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Executes a task through Layer 2 ModelRouter and AgentScope Agent.reply().
        Converts response to structured AgentResult with ModelExecutionResult details.
        """
        user_msg = self.convert_task_to_msg(task)

        async def _invoke_model_spec(spec: ModelSpec) -> str:
            chat_model = self.router.factory.create_model(spec)
            agentscope_agent = Agent(
                name=self.name,
                system_prompt=self.system_prompt,
                model=chat_model,
            )
            reply_msg: Msg = await agentscope_agent.reply(inputs=user_msg)
            return reply_msg.get_text_content() if reply_msg else ""

        exec_result: ModelExecutionResult = await self.router.execute_with_fallback(
            task=task,
            executor_fn=_invoke_model_spec,
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
                "is_fallback": exec_result.is_fallback,
            },
        )
