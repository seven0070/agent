"""
Component Versioning Foundation for Layer 0.
Specifies standards for component candidates during future metamorphosis.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ComponentVersionSpec(BaseModel):
    """
    Specification for versioned components.
    Ensures that mutations are always distinct versioned candidates rather than un-versioned source edits.
    """
    component_type: str = Field(..., description="Type of component (e.g., planner, memory, skill, tool)")
    name: str = Field(..., description="Component identifier (e.g. planner-v1)")
    version: str = Field(..., description="Semantic or generation version (e.g. 1.0.0)")
    parent_version: Optional[str] = Field(None, description="Parent version identifier if evolved")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom component parameters")

    def get_full_identifier(self) -> str:
        return f"{self.component_type}:{self.name}@{self.version}"

class VersionRegistry:
    """
    Registry for managing registered component version specifications.
    """
    def __init__(self) -> None:
        self._registry: Dict[str, ComponentVersionSpec] = {}

    def register(self, spec: ComponentVersionSpec) -> None:
        identifier = spec.get_full_identifier()
        self._registry[identifier] = spec

    def get(self, identifier: str) -> Optional[ComponentVersionSpec]:
        return self._registry.get(identifier)

    def list_components(self) -> Dict[str, ComponentVersionSpec]:
        return dict(self._registry)
