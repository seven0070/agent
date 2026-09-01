"""
Structured Runtime Audit Events.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class RuntimeEvent(BaseModel):
    """
    Structured runtime audit event.
    """
    event_type: str = Field(..., description="Event classification (e.g. SANDBOX_CREATED, EXECUTION_STARTED)")
    session_id: str = Field(..., description="Associated runtime session ID")
    workspace_id: str = Field(..., description="Associated workspace ID")
    operation: str = Field(..., description="Execution operation description")
    status: str = Field(..., description="Operation status (success, failed, denied)")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp",
    )
    details: Dict[str, Any] = Field(default_factory=dict, description="Custom event metadata")
