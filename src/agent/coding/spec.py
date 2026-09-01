"""
Coding Engine Version Specification Cards.
"""

from typing import Dict, Any
from pydantic import BaseModel, Field

class CodingEngineSpec(BaseModel):
    """
    Specification card for the coding engine version.
    Supports future Evolution Controller evaluation (coding-engine-v1 vs coding-engine-v2).
    """
    engine_id: str = Field(default="coding-engine-v1", description="Engine identifier")
    version: str = Field(default="1.0.0", description="Semantic engine version")
    jcode_version: str = Field(default="1.1.0", description="Jcode SDK/binary version")
    sdk_package: str = Field(default="@1jehuang/jcode-sdk", description="NPM SDK package name")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom parameters")
