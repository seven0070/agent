"""
Unit and Integration Tests for Layer 7 Runtime / Sandbox Subsystem.
"""

import pytest
import tempfile
import os
from agent.runtime import (
    RuntimeSession,
    RuntimeStatus,
    NetworkPolicy,
    ResourceLimits,
    RuntimeEvent,
    RuntimeSandbox,
    LocalAgentScopeRuntime,
)
from agent.capabilities import CapabilityBroker, PermissionLevel
from agent.orchestration import RuleBasedPlanner, PlanOrchestrator, TaskState

def test_runtime_session_lifecycle() -> None:
    """Tests runtime session lifecycle creation, status transitions, and cleanup."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        runtime = LocalAgentScopeRuntime(base_workspace_dir=tmp_dir)
        sess = runtime.create_session()

        assert sess.status == RuntimeStatus.INITIALIZED
        assert sess.session_id in runtime.sessions

        sandbox = runtime.get_sandbox(sess.session_id)
        assert sandbox is not None

        runtime.cleanup_all()
        assert runtime.sessions[sess.session_id].status == RuntimeStatus.CLOSED

def test_sandbox_path_traversal_restriction() -> None:
    """Tests workspace path traversal restriction blocking relative and absolute escapes."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        runtime = LocalAgentScopeRuntime(base_workspace_dir=tmp_dir)
        sess = runtime.create_session()
        sandbox = runtime.get_sandbox(sess.session_id)

        valid_path = sandbox.resolve_and_validate_path("sub/file.txt")
        assert valid_path.startswith(sandbox.workspace_dir)

        # Path traversal escape attempt
        with pytest.raises(PermissionError) as exc_info:
            sandbox.resolve_and_validate_path("../../../etc/passwd")

        assert "escapes sandbox workspace root" in str(exc_info.value)

def test_sandbox_process_timeout_enforcement() -> None:
    """Tests process execution timeout enforcement."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        runtime = LocalAgentScopeRuntime(base_workspace_dir=tmp_dir)
        sess = runtime.create_session(limits=ResourceLimits(timeout_seconds=1.0))
        sandbox = runtime.get_sandbox(sess.session_id)

        res = sandbox.execute_process(["python3", "-c", "import time; time.sleep(3)"])
        assert res["success"] is False
        assert "timed out" in res["stderr"]

def test_sandbox_output_buffer_capping() -> None:
    """Tests output buffer size truncation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        runtime = LocalAgentScopeRuntime(base_workspace_dir=tmp_dir)
        sess = runtime.create_session(limits=ResourceLimits(max_output_bytes=20))
        sandbox = runtime.get_sandbox(sess.session_id)

        res = sandbox.execute_process(["python3", "-c", "print('B' * 500)"])
        assert res["success"] is True
        assert len(res["stdout"]) <= 20
        assert res["truncated"] is True

def test_sandbox_network_policy_enforcement() -> None:
    """Tests NetworkPolicy enforcement (DENY vs ALLOWLIST)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        runtime = LocalAgentScopeRuntime(base_workspace_dir=tmp_dir)

        # DENY policy session
        sess_deny = runtime.create_session(network_policy=NetworkPolicy.DENY)
        sb_deny = runtime.get_sandbox(sess_deny.session_id)
        assert sb_deny.check_network_allowed("api.openai.com") is False

        # ALLOWLIST policy session
        sess_allow = runtime.create_session(network_policy=NetworkPolicy.ALLOWLIST)
        sess_allow.metadata["allowed_hosts"] = ["api.openai.com"]
        sb_allow = runtime.get_sandbox(sess_allow.session_id)
        assert sb_allow.check_network_allowed("api.openai.com") is True
        assert sb_allow.check_network_allowed("unauthorized.com") is False

def test_runtime_audit_events_emission() -> None:
    """Verifies emission of structured runtime audit events."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        runtime = LocalAgentScopeRuntime(base_workspace_dir=tmp_dir)
        sess = runtime.create_session()
        sandbox = runtime.get_sandbox(sess.session_id)

        sandbox.execute_process(["python3", "-c", "print('audit test')"])
        event_types = [e.event_type for e in sandbox.events]

        assert "SANDBOX_CREATED" in event_types
        assert "EXECUTION_STARTED" in event_types
        assert "EXECUTION_COMPLETED" in event_types

def test_broker_and_jcode_runtime_integration() -> None:
    """Tests CapabilityBroker and JcodeAdapter executing inside Layer 7 sandbox."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        broker = CapabilityBroker(workspace_dir=tmp_dir)
        broker.permission_policy.set_permission("write_file-v1", PermissionLevel.ALLOW)

        planner = RuleBasedPlanner()
        plan = planner.create_plan("Create python module and test")

        orchestrator = PlanOrchestrator(broker=broker)
        completed_plan = orchestrator.execute_plan(plan)

        assert completed_plan.status == "completed"
        assert completed_plan.tasks["task_code_1"].status == TaskState.SUCCEEDED
        assert len(broker.sandbox.events) > 0
