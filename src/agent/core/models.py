"""
Core Data Models and Contracts for Agent Execution.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class AgentTask(BaseModel):
    """Input payload representing a task assigned to the agent."""
    task_id: str = Field(..., description="Unique task identifier")
    prompt: str = Field(..., description="Task prompt or user instructions")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    required_capabilities: Dict[str, bool] = Field(default_factory=dict, description="Required model capability flags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional contextual parameters")

class ModelExecutionResult(BaseModel):
    """Detailed result model for model invocation."""
    model_id: str = Field(..., description="Model ID executed")
    provider: str = Field(..., description="Provider used")
    output: str = Field(..., description="Generated text output")
    status: str = Field(default="success", description="Execution status (success, error)")
    latency_ms: Optional[float] = Field(default=None, description="Execution latency in milliseconds")
    usage: Dict[str, Any] = Field(default_factory=dict, description="Token usage metadata if available")
    is_fallback: bool = Field(default=False, description="Whether fallback model was used")
    error: Optional[str] = Field(default=None, description="Error details if execution failed")

class AgentResult(BaseModel):
    """Structured execution result returned by the agent layer."""
    task_id: str = Field(..., description="Unique task identifier")
    output: str = Field(..., description="Response content produced by the agent")
    agent_version: str = Field(default="agent-v1", description="Version of the executing agent")
    model: str = Field(..., description="Model identifier used for generation")
    status: str = Field(default="success", description="Execution status (success, error)")
    model_execution: Optional[ModelExecutionResult] = Field(default=None, description="Layer 2 model execution details")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")

class ModelConfigInfo(BaseModel):
    """Model provider configuration metadata."""
    provider: str = Field(default="mock", description="Model provider (openai, dashscope, mock, etc.)")
    model_name: str = Field(default="mock-model-v1", description="Model name or ID")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=1024, description="Maximum token generation limit")
