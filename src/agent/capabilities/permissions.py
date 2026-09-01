"""
Tool Permission Policy Engine.
"""

from typing import Dict, Optional
from agent.capabilities.models import PermissionLevel, ToolRiskLevel

class ToolPermissionPolicy:
    """
    Policy engine mapping tool identifiers to permission levels.
    """

    DEFAULT_POLICIES: Dict[str, PermissionLevel] = {
        "calculator-v1": PermissionLevel.ALLOW,
        "read_file-v1": PermissionLevel.ALLOW,
        "write_file-v1": PermissionLevel.REQUIRE_APPROVAL,
        "shell-v1": PermissionLevel.DENY,
    }

    def __init__(self, overrides: Optional[Dict[str, PermissionLevel]] = None) -> None:
        self._policies: Dict[str, PermissionLevel] = dict(self.DEFAULT_POLICIES)
        if overrides:
            self._policies.update(overrides)

    def get_permission(self, tool_id: str, risk_level: ToolRiskLevel = ToolRiskLevel.LOW) -> PermissionLevel:
        """Returns the permission level for a tool ID."""
        if tool_id in self._policies:
            return self._policies[tool_id]
        if risk_level == ToolRiskLevel.CRITICAL or "shell" in tool_id.lower():
            return PermissionLevel.DENY
        elif risk_level == ToolRiskLevel.HIGH:
            return PermissionLevel.REQUIRE_APPROVAL
        return PermissionLevel.ALLOW

    def set_permission(self, tool_id: str, level: PermissionLevel) -> None:
        """Sets permission level for a tool ID."""
        self._policies[tool_id] = level
