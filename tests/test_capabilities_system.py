"""
Unit and Integration Tests for Layer 4 Tools / Skills / MCP Capabilities Subsystem.
"""

import pytest
import tempfile
import os
from agent.capabilities import (
    PermissionLevel,
    ToolRiskLevel,
    CapabilityResult,
    ToolPermissionPolicy,
    ToolSpec,
    SkillSpec,
    ToolRegistry,
    CapabilityBroker,
    evaluate_math_expression,
    WorkspaceManager,
    BasicFileManagementSkill,
    MCPClientWrapper,
)
from agent.core import AgentTask, AgentResult, AgentV1
from agent.integrations.agentscope import AgentScopeAdapter

def test_tool_registry_operations() -> None:
    """Tests tool registry registration, lookup, listing, and enable/disable operations."""
    reg = ToolRegistry()
    tool1 = ToolSpec(id="t-1", name="tool1", description="Tool 1")
    tool2 = ToolSpec(id="t-2", name="tool2", description="Tool 2")

    reg.register_tool(tool1)
    reg.register_tool(tool2)

    assert len(reg.list_tools()) == 2
    assert reg.get_tool("t-1").name == "tool1"

    reg.set_tool_enabled("t-2", False)
    assert len(reg.list_tools()) == 1
    assert reg.list_tools()[0].id == "t-1"

def test_permission_policy_enforcement() -> None:
    """Tests ToolPermissionPolicy permission resolution and overrides."""
    policy = ToolPermissionPolicy()

    assert policy.get_permission("calculator-v1") == PermissionLevel.ALLOW
    assert policy.get_permission("shell-v1") == PermissionLevel.DENY

    policy.set_permission("custom-tool", PermissionLevel.REQUIRE_APPROVAL)
    assert policy.get_permission("custom-tool") == PermissionLevel.REQUIRE_APPROVAL

def test_calculator_tool_evaluation() -> None:
    """Tests safe mathematical expression evaluation in calculator tool."""
    assert evaluate_math_expression("37 * 42") == 1554
    assert evaluate_math_expression("10 + 20 / 4") == 15.0
    assert evaluate_math_expression("2 ** 3") == 8

    with pytest.raises(ZeroDivisionError):
        evaluate_math_expression("10 / 0")

    with pytest.raises(ValueError):
        evaluate_math_expression("import os; os.system('ls')")

def test_workspace_file_tools_path_traversal() -> None:
    """Tests WorkspaceManager file I/O and verifies path traversal security restriction."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ws = WorkspaceManager(workspace_dir=tmp_dir)

        ws.write_file("sub/test.txt", "Workspace File Content")
        assert ws.read_file("sub/test.txt") == "Workspace File Content"

        with pytest.raises(PermissionError) as exc_info:
            ws.resolve_path("../../../etc/passwd")

        assert "traverses outside workspace" in str(exc_info.value)

def test_capability_broker_execution() -> None:
    """Tests CapabilityBroker tool execution and permission status normalization."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        broker = CapabilityBroker(workspace_dir=tmp_dir)

        res_calc = broker.execute_tool("calculator-v1", {"expression": "100 + 200"})
        assert res_calc.success is True
        assert res_calc.output == 300

        res_write = broker.execute_tool("write_file-v1", {"relative_path": "a.txt", "content": "data"})
        assert res_write.success is False
        assert res_write.permission_status == PermissionLevel.REQUIRE_APPROVAL

        res_shell = broker.execute_tool("shell-v1", {})
        assert res_shell.success is False
        assert res_shell.permission_status == PermissionLevel.DENY

def test_basic_file_management_skill() -> None:
    """Tests BasicFileManagementSkill workflow."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        broker = CapabilityBroker(workspace_dir=tmp_dir)
        broker.permission_policy.set_permission("write_file-v1", PermissionLevel.ALLOW)

        skill = BasicFileManagementSkill(broker=broker)
        res = skill.create_and_verify_file("doc.txt", "Skill verified content")

        assert res.success is True
        assert res.metadata["verified"] is True
        assert broker.workspace_manager.read_file("doc.txt") == "Skill verified content"

def test_mcp_client_wrapper_initialization() -> None:
    """Tests MCPClientWrapper initialization and tool permission check."""
    mcp = MCPClientWrapper(server_name="test-mcp-server")
    res = mcp.initialize_client()

    assert res["server_name"] == "test-mcp-server"
    assert res["status"] == "initialized"
    assert mcp.is_tool_permitted("remote_action") == PermissionLevel.ALLOW

@pytest.mark.asyncio
async def test_adapter_toolkit_integration() -> None:
    """Tests AgentScopeAdapter integration with Layer 4 Toolkit and CapabilityBroker."""
    broker = CapabilityBroker()
    adapter = AgentScopeAdapter(name="layer4-adapter-test", broker=broker)
    agent = AgentV1(adapter=adapter)

    task = AgentTask(task_id="t-l4", prompt="Calculate 12 * 12", session_id="s-l4")
    result: AgentResult = await agent.execute_task(task)

    assert result.status in ["success", "completed"]
    assert adapter.toolkit is not None
    assert len(adapter.broker.registry.list_tools()) >= 3
