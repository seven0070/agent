"""
Deterministic Mock Chat Model for Testing and Offline Fallbacks.
"""

from typing import Any, List, Optional, Union, AsyncGenerator
from agentscope.model import ChatModelBase, ChatResponse
from agentscope.message import Msg, TextBlock
from agentscope.formatter import OpenAIChatFormatter

class MockChatModel(ChatModelBase):
    """
    Deterministic conversational mock for tests and offline development.

    It must not be used as a silent success path for tasks that require a real
    filesystem, coding, calculator, or data-inspection capability.
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
        last_text = ""
        if messages:
            last_msg = messages[-1]
            last_text = last_msg.get_text_content()

        response_text = f"{self.mock_response}: {last_text}" if last_text else self.mock_response

        return ChatResponse(
            content=[TextBlock(type="text", text=response_text)],
            is_last=True,
        )
