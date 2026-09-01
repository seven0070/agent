"""
Registry for Managing Tools and Skills.
"""

from typing import Dict, List, Optional
from agent.capabilities.spec import ToolSpec, SkillSpec

class ToolRegistry:
    """
    Registry for managing tool specifications and skills.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}
        self._skills: Dict[str, SkillSpec] = {}

    def register_tool(self, spec: ToolSpec) -> None:
        """Registers a tool specification."""
        self._tools[spec.id] = spec

    def register_skill(self, spec: SkillSpec) -> None:
        """Registers a skill specification."""
        self._skills[spec.id] = spec

    def get_tool(self, tool_id: str) -> Optional[ToolSpec]:
        """Retrieves a tool spec by ID."""
        return self._tools.get(tool_id)

    def get_skill(self, skill_id: str) -> Optional[SkillSpec]:
        """Retrieves a skill spec by ID."""
        return self._skills.get(skill_id)

    def list_tools(self) -> List[ToolSpec]:
        """Lists all registered enabled tools."""
        return [t for t in self._tools.values() if t.enabled]

    def list_skills(self) -> List[SkillSpec]:
        """Lists all registered skills."""
        return list(self._skills.values())

    def set_tool_enabled(self, tool_id: str, enabled: bool) -> None:
        """Enables or disables a registered tool."""
        if tool_id in self._tools:
            self._tools[tool_id].enabled = enabled
