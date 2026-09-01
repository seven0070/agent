"""
Structured Evolution Audit Events.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class EvolutionEvent(BaseModel):
    """
    Structured audit event emitted by the Evolution Controller.
    """
    event_type: str = Field(..., description="Event type (e.g. EVOLUTION_TRIGGERED, MUTATION_PROPOSED)")
    mutation_id: Optional[str] = Field(default=None, description="Associated mutation ID if applicable")
    parent_version: str = Field(default="agent-v1", description="Parent active agent version")
    candidate_version: Optional[str] = Field(default=None, description="Candidate agent version if applicable")
    decision: str = Field(..., description="Decision or status payload (e.g. PROMOTED, REJECTED)")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 event timestamp",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom event metadata")
