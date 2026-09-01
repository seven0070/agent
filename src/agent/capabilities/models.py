"""
Capability Domain Models, Permission Levels, and Tool Result Schemas.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class PermissionLevel(str, Enum):
    """Permission level governing tool execution."""
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"

class ToolRiskLevel(str, Enum):
    """Risk assessment classification for tools."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class CapabilityResult(BaseModel):
    """
    Normalized result returned from tool or skill execution.
    """
    tool_id: str = Field(..., description="ID of the executed tool or capability")
    success: bool = Field(..., description="Execution status boolean")
    output: Any = Field(default="", description="Output result data or text")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
    permission_status: PermissionLevel = Field(default=PermissionLevel.ALLOW, description="Applied permission level")
    execution_time_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata attributes")
