"""
Tool & Skill Version Specification Cards.
"""

from typing import Dict, Any, Callable, Optional
from pydantic import BaseModel, Field
from agent.capabilities.models import ToolRiskLevel, PermissionLevel

class ToolSpec(BaseModel):
    """
    Specification card for a registered tool.
    """
    id: str = Field(..., description="Unique versioned tool ID (e.g. calculator-v1)")
    name: str = Field(..., description="Display or function name")
    description: str = Field(..., description="Tool description for LLM capability discovery")
    risk_level: ToolRiskLevel = Field(default=ToolRiskLevel.LOW, description="Tool risk classification")
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    version: str = Field(default="1.0.0", description="Semantic tool version")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema for parameters")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom tool metadata")

class SkillSpec(BaseModel):
    """
    Specification card for a composed skill workflow.
    """
    id: str = Field(..., description="Unique versioned skill ID (e.g. file-management-skill-v1)")
    name: str = Field(..., description="Skill display name")
    description: str = Field(..., description="Skill description and procedural guidelines")
    version: str = Field(default="1.0.0", description="Semantic skill version")
    tool_ids: list[str] = Field(default_factory=list, description="IDs of tools used by skill")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom skill metadata")
