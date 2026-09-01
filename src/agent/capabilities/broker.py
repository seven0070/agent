"""
Capability Broker Enforcing Security Permissions and Executing Tools.
"""

import time
from typing import Dict, Any, Callable, Optional, List
from agent.capabilities.models import PermissionLevel, ToolRiskLevel, CapabilityResult
from agent.capabilities.permissions import ToolPermissionPolicy
from agent.capabilities.registry import ToolRegistry
from agent.capabilities.spec import ToolSpec
from agent.capabilities.tools.calculator import evaluate_math_expression
from agent.capabilities.tools.workspace import WorkspaceManager
from agent.capabilities.tools.coding import CodingEngineToolWrapper
from agent.logging import get_logger

logger = get_logger("agent.capabilities.broker")

class CapabilityBroker:
    """
    Security boundary broker managing tool execution, permission enforcement, and result normalization.
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        permission_policy: Optional[ToolPermissionPolicy] = None,
        workspace_dir: str = "data/workspace",
    ) -> None:
        self.registry = registry or ToolRegistry()
        self.permission_policy = permission_policy or ToolPermissionPolicy()
        self.workspace_manager = WorkspaceManager(workspace_dir=workspace_dir)

        from agent.coding.jcode.adapter import JcodeAdapter
        from agent.coding.permissions import JcodePermissionInterceptor

        jcode_adapter = JcodeAdapter(
            workspace_dir=workspace_dir,
            permission_interceptor=JcodePermissionInterceptor(policy=self.permission_policy),
        )
        self.coding_tool_wrapper = CodingEngineToolWrapper(adapter=jcode_adapter)
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Registers initial safe development tools."""
        self.registry.register_tool(
            ToolSpec(
                id="calculator-v1",
                name="calculator",
                description="Safely evaluates mathematical expressions (e.g. '37 * 42')",
                risk_level=ToolRiskLevel.LOW,
                input_schema={"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
            )
        )
        self.registry.register_tool(
            ToolSpec(
                id="read_file-v1",
                name="read_file",
                description="Reads file contents from the restricted workspace directory",
                risk_level=ToolRiskLevel.LOW,
                input_schema={"type": "object", "properties": {"relative_path": {"type": "string"}}, "required": ["relative_path"]},
            )
        )
        self.registry.register_tool(
            ToolSpec(
                id="write_file-v1",
                name="write_file",
                description="Writes file contents to the restricted workspace directory",
                risk_level=ToolRiskLevel.MEDIUM,
                input_schema={"type": "object", "properties": {"relative_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["relative_path", "content"]},
            )
        )
        self.registry.register_tool(
            ToolSpec(
                id="coding-engine-v1",
                name="coding_engine",
                description="Specialized Jcode coding engine for inspecting workspace, creating/editing code files, and running test suites",
                risk_level=ToolRiskLevel.MEDIUM,
                input_schema={"type": "object", "properties": {"goal": {"type": "string"}}, "required": ["goal"]},
            )
        )

    def execute_tool(self, tool_id: str, kwargs: Dict[str, Any]) -> CapabilityResult:
        """
        Executes a registered tool if permitted by ToolPermissionPolicy.
        Normalizes outputs, permission denials, and execution errors.
        """
        spec = self.registry.get_tool(tool_id)
        risk = spec.risk_level if spec else ToolRiskLevel.LOW
        perm = self.permission_policy.get_permission(tool_id, risk_level=risk)

        start_time = time.perf_counter()

        if perm == PermissionLevel.DENY:
            logger.warning(f"Tool execution DENIED by security policy: '{tool_id}'")
            return CapabilityResult(
                tool_id=tool_id,
                success=False,
                error=f"Permission Denied: Execution of tool '{tool_id}' is prohibited by security policy.",
                permission_status=PermissionLevel.DENY,
                execution_time_ms=0.0,
            )

        if perm == PermissionLevel.REQUIRE_APPROVAL:
            logger.info(f"Tool execution REQUIRES APPROVAL: '{tool_id}'")
            return CapabilityResult(
                tool_id=tool_id,
                success=False,
                error=f"Permission Approval Required: Execution of tool '{tool_id}' requires human authorization.",
                permission_status=PermissionLevel.REQUIRE_APPROVAL,
                execution_time_ms=0.0,
            )

        # Execute approved tool
        try:
            if tool_id == "calculator-v1":
                expr = kwargs.get("expression", "")
                res = evaluate_math_expression(expr)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return CapabilityResult(
                    tool_id=tool_id,
                    success=True,
                    output=res,
                    permission_status=PermissionLevel.ALLOW,
                    execution_time_ms=round(elapsed_ms, 2),
                )

            elif tool_id == "read_file-v1":
                rel_path = kwargs.get("relative_path", "")
                content = self.workspace_manager.read_file(rel_path)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return CapabilityResult(
                    tool_id=tool_id,
                    success=True,
                    output=content,
                    permission_status=PermissionLevel.ALLOW,
                    execution_time_ms=round(elapsed_ms, 2),
                )

            elif tool_id == "write_file-v1":
                rel_path = kwargs.get("relative_path", "")
                content = kwargs.get("content", "")
                msg = self.workspace_manager.write_file(rel_path, content)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return CapabilityResult(
                    tool_id=tool_id,
                    success=True,
                    output=msg,
                    permission_status=PermissionLevel.ALLOW,
                    execution_time_ms=round(elapsed_ms, 2),
                )

            elif tool_id == "coding-engine-v1":
                coding_res = self.coding_tool_wrapper.execute(kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return CapabilityResult(
                    tool_id=tool_id,
                    success=(coding_res.status == "success"),
                    output=coding_res.summary,
                    error=str(coding_res.errors) if coding_res.errors else None,
                    permission_status=PermissionLevel.ALLOW,
                    execution_time_ms=round(elapsed_ms, 2),
                    metadata={"files_changed": coding_res.files_changed, "tests_passed": coding_res.tests_passed},
                )

            else:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return CapabilityResult(
                    tool_id=tool_id,
                    success=False,
                    error=f"Unknown Tool: Tool '{tool_id}' is not implemented in CapabilityBroker.",
                    permission_status=PermissionLevel.ALLOW,
                    execution_time_ms=round(elapsed_ms, 2),
                )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Tool execution failed for '{tool_id}': {str(exc)}")
            return CapabilityResult(
                tool_id=tool_id,
                success=False,
                error=f"Tool Execution Failure: {str(exc)}",
                permission_status=PermissionLevel.ALLOW,
                execution_time_ms=round(elapsed_ms, 2),
            )
