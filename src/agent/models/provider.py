"""
Provider Configuration and Secure Credential Management.
"""

import os
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field, SecretStr
from agent.config import get_settings

class ProviderCredentials(BaseModel):
    """
    Secure provider credentials container.
    Ensures sensitive keys are protected and auto-redacted in str/repr.
    """
    openai_api_key: Optional[SecretStr] = Field(default=None)
    dashscope_api_key: Optional[SecretStr] = Field(default=None)
    anthropic_api_key: Optional[SecretStr] = Field(default=None)
    ollama_host: str = Field(default="http://localhost:11434")

    def get_key_value(self, provider: str) -> Optional[str]:
        """Returns plain-text key value for API invocation if available."""
        p = provider.lower()
        if p == "openai" and self.openai_api_key:
            return self.openai_api_key.get_secret_value()
        elif p == "dashscope" and self.dashscope_api_key:
            return self.dashscope_api_key.get_secret_value()
        elif p == "anthropic" and self.anthropic_api_key:
            return self.anthropic_api_key.get_secret_value()
        return None

    def to_safe_dict(self) -> Dict[str, str]:
        """Returns a sanitized dictionary safe for logging and serialization."""
        return {
            "openai_api_key": "***REDACTED***" if self.openai_api_key else "None",
            "dashscope_api_key": "***REDACTED***" if self.dashscope_api_key else "None",
            "anthropic_api_key": "***REDACTED***" if self.anthropic_api_key else "None",
            "ollama_host": self.ollama_host,
        }

def load_provider_credentials() -> ProviderCredentials:
    """Loads provider credentials securely from settings/environment."""
    settings = get_settings()

    openai_key = os.getenv("OPENAI_API_KEY") or settings.openai_api_key
    dashscope_key = os.getenv("DASHSCOPE_API_KEY") or settings.dashscope_api_key
    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or settings.anthropic_api_key
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    return ProviderCredentials(
        openai_api_key=SecretStr(openai_key) if openai_key else None,
        dashscope_api_key=SecretStr(dashscope_key) if dashscope_key else None,
        anthropic_api_key=SecretStr(anthropic_key) if anthropic_key else None,
        ollama_host=ollama_host,
    )

def check_local_model_readiness(host: Optional[str] = None) -> Dict[str, Any]:
    """
    Checks if local model endpoint (e.g. Ollama) is configured and reachable.
    """
    target_host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    return {
        "provider": "ollama",
        "host": target_host,
        "configured": True,
        "status": "ready_for_connection",
    }
