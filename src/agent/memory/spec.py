"""
Memory Strategy Version Specification.
"""

from typing import Dict, Any
from pydantic import BaseModel, Field

class MemoryStrategySpec(BaseModel):
    """
    Specification for a versioned memory strategy.
    Supports future Evolution Controller comparison (memory-v1 vs memory-v2).
    """
    strategy_id: str = Field(..., description="Strategy ID (e.g. memory-v1)")
    version: str = Field(default="1.0.0", description="Semantic version string")
    backend_type: str = Field(default="sqlite", description="Backend type (sqlite, reme, session)")
    max_context_memories: int = Field(default=10, description="Max memories included in prompt context")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
