"""
Versioned Evaluation Dataset Specifications.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field

class DatasetSpec(BaseModel):
    """
    Specification card for a versioned evaluation dataset.
    """
    dataset_id: str = Field(default="benchmark-v1", description="Unique dataset specification ID")
    version: str = Field(default="1.0.0", description="Semantic dataset version")
    description: str = Field(default="Standard benchmark suite for agent, tools, planning, and safety", description="Suite description")
    case_ids: List[str] = Field(default_factory=list, description="Included case IDs")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom parameters")
