"""
AgentScope 2.x Adapter Implementation.
Maps application domain models (AgentTask, AgentResult) to AgentScope 2.x abstractions.
"""

from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from agentscope.agent import Agent
from agentscope.model import ChatModelBase, ChatResponse
from agentscope.message import Msg, UserMsg, TextBlock
from agentscope.formatter import OpenAIChatFormatter
from agent.core.models import AgentTask, AgentResult, ModelConfigInfo

class MockChatModel(ChatModelBase):
    """
    Deterministic Mock Chat Model inheriting from AgentScope's ChatModelBase.
    Used for unit/integration tests and environments without live cloud credentials.
    """

    def __init__(self, mock_response: str = "Mocked AgentScope response content", model_name: str = "mock-model-v1"):
        self.mock_response = mock_response
        self.model_name = model_name
        self.model = model_name
        self.formatter = OpenAIChatFormatter()
        self.context_size = 32768

    async def __call__(
        self,
        messages: List[Msg],
        tools: Optional[List[dict]] = None,
        tool_choice: Optional[Any] = None,
        **kwargs: Any,
    ) -> Union[ChatResponse, AsyncGenerator[ChatResponse, None]]:
        # Extract prompt for optional dynamic response echo if needed
        last_text = ""
        if messages:
            last_msg = messages[-1]
            last_text = last_msg.get_text_content()

        response_text = f"{self.mock_response}: {last_text}" if last_text else self.mock_response

        return ChatResponse(
            content=[TextBlock(type="text", text=response_text)],
            is_last=True,
        )

class AgentScopeAdapter:
    """
    Adapter decoupling application domain from AgentScope 2.x engine internals.
    """

    def __init__(
        self,
        name: str = "agent-v1-core",
        system_prompt: str = "You are a helpful AI assistant.",
        model: Optional[ChatModelBase] = None,
        model_config_info: Optional[ModelConfigInfo] = None,
    ) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.model_config_info = model_config_info or ModelConfigInfo()
        self.model = model or MockChatModel(model_name=self.model_config_info.model_name)

        # Initialize AgentScope Agent instance
        self._agentscope_agent = Agent(
            name=self.name,
            system_prompt=self.system_prompt,
            model=self.model,
        )

    def convert_task_to_msg(self, task: AgentTask) -> Msg:
        """Converts application AgentTask to AgentScope UserMsg."""
        return UserMsg(name="user", content=task.prompt)

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Executes a task through AgentScope 2.x Agent.reply().
        Converts response to structured AgentResult.
        """
        user_msg = self.convert_task_to_msg(task)

        # Call AgentScope agent reply
        reply_msg: Msg = await self._agentscope_agent.reply(inputs=user_msg)

        output_text = reply_msg.get_text_content() if reply_msg else ""

        return AgentResult(
            task_id=task.task_id,
            output=output_text,
            agent_version="agent-v1",
            model=self.model_config_info.model_name,
            status="success",
            metadata={
                "agentscope_agent_name": self.name,
                "session_id": task.session_id,
            },
        )
