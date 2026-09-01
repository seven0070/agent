"""
Memory Data Models and Memory Item Schemas.
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class MemoryType(str, Enum):
    """Taxonomy of memory item types."""
    CONVERSATION = "conversation"
    FACT = "fact"
    PREFERENCE = "preference"
    TASK = "task"
    DECISION = "decision"
    KNOWLEDGE = "knowledge"

class MemoryItem(BaseModel):
    """
    Structured Memory Card representation.
    """
    id: str = Field(..., description="Unique memory ID")
    content: str = Field(..., description="Memory content body")
    memory_type: MemoryType = Field(default=MemoryType.CONVERSATION, description="Category of memory")
    source: str = Field(default="user", description="Source of memory (user, agent, system)")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp",
    )
    session_id: Optional[str] = Field(default=None, description="Associated session ID")
    importance: float = Field(default=0.5, description="Importance score (0.0 to 1.0)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata attributes")
