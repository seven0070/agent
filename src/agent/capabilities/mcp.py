"""
Model Context Protocol (MCP) Client Integration Wrapper.
"""

from typing import List, Dict, Any, Optional
from agentscope.mcp import MCPClient, StdioMCPConfig, HttpMCPConfig
from agent.capabilities.permissions import ToolPermissionPolicy
from agent.capabilities.models import PermissionLevel, ToolRiskLevel
from agent.logging import get_logger

logger = get_logger("agent.capabilities.mcp")

class MCPClientWrapper:
    """
    Wrapper for managing AgentScope MCPClient instances subject to security permission checks.
    """

    def __init__(
        self,
        server_name: str,
        config: Optional[Any] = None,
        permission_policy: Optional[ToolPermissionPolicy] = None,
    ) -> None:
        self.server_name = server_name
        self.config = config or StdioMCPConfig(command="echo", args=["mcp-server"])
        self.permission_policy = permission_policy or ToolPermissionPolicy()
        self.client: Optional[MCPClient] = None

    def initialize_client(self) -> Dict[str, Any]:
        """
        Initializes AgentScope MCPClient instance for configured server.
        """
        try:
            is_stateful = isinstance(self.config, StdioMCPConfig)
            self.client = MCPClient(
                name=self.server_name,
                is_stateful=is_stateful,
                mcp_config=self.config,
            )
            logger.info(f"Initialized MCPClient for server '{self.server_name}'")
            return {
                "server_name": self.server_name,
                "status": "initialized",
                "tools_discovered": [],
            }
        except Exception as exc:
            logger.error(f"Failed to initialize MCPClient for '{self.server_name}': {str(exc)}")
            return {
                "server_name": self.server_name,
                "status": "error",
                "error": str(exc),
            }

    def is_tool_permitted(self, mcp_tool_name: str) -> PermissionLevel:
        """Checks if a tool exposed by the MCP server is permitted by security policy."""
        tool_id = f"mcp:{self.server_name}:{mcp_tool_name}"
        return self.permission_policy.get_permission(tool_id, risk_level=ToolRiskLevel.MEDIUM)
