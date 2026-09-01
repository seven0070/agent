"""
Permission Interceptor Mapping Jcode Tool Requests to Layer 4 ToolPermissionPolicy.
"""

from typing import Dict, Any, Optional
from agent.capabilities.models import PermissionLevel, ToolRiskLevel
from agent.logging import get_logger

logger = get_logger("agent.coding.permissions")

class JcodePermissionInterceptor:
    """
    Intercepts Jcode tool execution requests and validates them against Layer 4 ToolPermissionPolicy.
    """

    def __init__(self, policy: Optional[Any] = None) -> None:
        if policy is None:
            from agent.capabilities.permissions import ToolPermissionPolicy
            self.policy = ToolPermissionPolicy()
        else:
            self.policy = policy

    def evaluate_tool_request(self, jcode_action: str, target: str) -> PermissionLevel:
        """
        Evaluates Jcode action against permission policy rules.
        """
        action_lower = jcode_action.lower()
        if "shell" in action_lower or "sys" in action_lower or "admin" in action_lower or "os_exec" in action_lower:
            return PermissionLevel.DENY
        elif "read" in action_lower or "inspect" in action_lower:
            return self.policy.get_permission("read_file-v1", risk_level=ToolRiskLevel.LOW)
        elif "write" in action_lower or "edit" in action_lower or "create" in action_lower:
            return self.policy.get_permission("write_file-v1", risk_level=ToolRiskLevel.MEDIUM)
        elif "test" in action_lower or "run" in action_lower or "exec" in action_lower:
            return PermissionLevel.ALLOW

        return PermissionLevel.REQUIRE_APPROVAL
