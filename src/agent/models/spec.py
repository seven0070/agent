"""
Model Specification and Health Status Schemas.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ModelHealthStatus(str, Enum):
    """Health status of a model instance."""
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    DISABLED = "DISABLED"

class ModelCapabilities(BaseModel):
    """Feature capabilities supported by a model."""
    supports_tools: bool = Field(default=True, description="Supports function/tool calling")
    supports_vision: bool = Field(default=False, description="Supports image/vision input")
    supports_streaming: bool = Field(default=True, description="Supports streaming output")
    supports_json_output: bool = Field(default=True, description="Supports structured JSON output")

class ModelSpec(BaseModel):
    """
    Specification card for a registered model.
    """
    id: str = Field(..., description="Unique model configuration ID (e.g. primary, fallback-1, local)")
    provider: str = Field(..., description="Provider identifier (openai, dashscope, ollama, mock)")
    model_name: str = Field(..., description="Provider model name (e.g. gpt-4o-mini, qwen-max, mock-model-v1)")
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities, description="Model capability flags")
    context_window: int = Field(default=32768, description="Maximum context window tokens")
    health_status: ModelHealthStatus = Field(default=ModelHealthStatus.AVAILABLE, description="Model health state")
    enabled: bool = Field(default=True, description="Whether model is enabled")
    priority: int = Field(default=10, description="Priority rank (lower = higher priority)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom provider parameters")
