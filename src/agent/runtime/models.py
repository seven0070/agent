"""
Runtime Domain Models and Session Lifecycle Schemas.
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from agent.runtime.policy import ResourceLimits

class RuntimeStatus(str, Enum):
    """Runtime session lifecycle states."""
    CREATED = "CREATED"
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"

class NetworkPolicy(str, Enum):
    """Network access policy mode."""
    DENY = "DENY"
    ALLOWLIST = "ALLOWLIST"
    FULL = "FULL"

class RuntimeSession(BaseModel):
    """
    Session container for sandboxed execution environment.
    """
    session_id: str = Field(..., description="Unique runtime session ID")
    workspace_id: str = Field(..., description="Associated workspace ID")
    workspace_dir: str = Field(default="data/workspace", description="Explicit workspace root path")
    status: RuntimeStatus = Field(default=RuntimeStatus.CREATED, description="Lifecycle state")
    network_policy: NetworkPolicy = Field(default=NetworkPolicy.DENY, description="Active network policy")
    limits: ResourceLimits = Field(default_factory=ResourceLimits, description="Resource limit constraints")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp",
    )
    closed_at: Optional[str] = Field(default=None, description="ISO 8601 closure timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom session metadata")
