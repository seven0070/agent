"""
Intelligence / Model Subsystem Package (Layer 2).
"""

from agent.models.spec import ModelCapabilities, ModelHealthStatus, ModelSpec
from agent.models.registry import ModelRegistry
from agent.models.provider import ProviderCredentials, load_provider_credentials, check_local_model_readiness
from agent.models.mock import MockChatModel
from agent.models.factory import ModelFactory
from agent.models.router import ModelRouter

__all__ = [
    "ModelCapabilities",
    "ModelHealthStatus",
    "ModelSpec",
    "ModelRegistry",
    "ProviderCredentials",
    "load_provider_credentials",
    "check_local_model_readiness",
    "MockChatModel",
    "ModelFactory",
    "ModelRouter",
]
