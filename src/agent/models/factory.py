"""
Model Factory for Instantiating AgentScope ChatModelBase Adapters.
"""

from typing import Optional
from agentscope.model import ChatModelBase, OpenAIChatModel, OllamaChatModel
from agentscope.credential import OpenAICredential, OllamaCredential
from agent.models.spec import ModelSpec
from agent.models.provider import ProviderCredentials, load_provider_credentials
from agent.models.mock import MockChatModel

class ModelFactory:
    """
    Factory creating AgentScope ChatModelBase instances from ModelSpec cards.
    """

    def __init__(self, credentials: Optional[ProviderCredentials] = None):
        self.credentials = credentials or load_provider_credentials()

    def create_model(self, spec: ModelSpec) -> ChatModelBase:
        """Creates an AgentScope ChatModelBase instance corresponding to spec."""
        provider = spec.provider.lower()

        if provider == "mock":
            mock_resp = spec.metadata.get("mock_response", "Mocked AgentScope response content")
            return MockChatModel(mock_response=mock_resp, model_name=spec.model_name)

        elif provider == "openai":
            api_key = self.credentials.get_key_value("openai")
            if not api_key:
                return MockChatModel(
                    mock_response=f"[OpenAI fallback mock] {spec.model_name} response",
                    model_name=spec.model_name,
                )
            cred = OpenAICredential(api_key=api_key)
            return OpenAIChatModel(credential=cred, model=spec.model_name)

        elif provider == "ollama":
            host = self.credentials.ollama_host
            cred = OllamaCredential(host=host)
            return OllamaChatModel(credential=cred, model=spec.model_name)

        else:
            return MockChatModel(
                mock_response=f"[{provider} mock] {spec.model_name} response",
                model_name=spec.model_name,
            )
