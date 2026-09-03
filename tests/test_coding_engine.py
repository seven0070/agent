"""
Unit and Integration Tests for Layer 6 Jcode Coding Engine Subsystem.
"""

import pytest
import tempfile
import os
from agent.coding import (
    CodingTask,
    CodingResult,
    JcodeEvent,
    CodingEngineSpec,
)
from agent.coding.workspace import CodingWorkspaceRestrictor
from agent.coding.permissions import JcodePermissionInterceptor
from agent.coding.jcode.adapter import JcodeAdapter
from agent.capabilities import CapabilityBroker, PermissionLevel, ToolPermissionPolicy
from agent.orchestration import RuleBasedPlanner, PlanOrchestrator, TaskState

def test_workspace_path_traversal_restriction() -> None:
    """Tests that workspace restrictor blocks path traversal outside workspace root."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        restrictor = CodingWorkspaceRestrictor(workspace_dir=tmp_dir)

        valid_path = restrictor.validate_and_resolve("sub/module.py")
        assert valid_path.startswith(os.path.abspath(tmp_dir))

        with pytest.raises(PermissionError) as exc_info:
            restrictor.validate_and_resolve("../../../etc/passwd")

        assert "escapes coding workspace root" in str(exc_info.value)

def test_jcode_permission_interceptor() -> None:
    """Tests permission evaluation mapping for Jcode tool actions."""
    interceptor = JcodePermissionInterceptor()

    assert interceptor.evaluate_tool_request("read_file", "a.txt") == PermissionLevel.ALLOW
    assert interceptor.evaluate_tool_request("run_test", "pytest") == PermissionLevel.ALLOW
    assert interceptor.evaluate_tool_request("shell_exec", "bash") == PermissionLevel.DENY

def test_jcode_adapter_coding_task_execution() -> None:
    """Tests end-to-end coding task execution using JcodeAdapter."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        task = CodingTask(
            task_id="ct-exec-1",
            goal="Create python module and test",
            workspace_dir=tmp_dir,
            test_command="pytest",
        )

        result: CodingResult = adapter.execute_coding_task(task)

        assert result.status == "success"
        assert len(result.files_changed) == 2
        assert result.tests_run == 1
        assert result.tests_passed == 1
        assert len(adapter.events) >= 4

def test_jcode_adapter_permission_denial() -> None:
    """Tests execution halt when permission policy denies write access."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        denied_policy = ToolPermissionPolicy(overrides={"write_file-v1": PermissionLevel.DENY})
        interceptor = JcodePermissionInterceptor(policy=denied_policy)
        adapter = JcodeAdapter(workspace_dir=tmp_dir, permission_interceptor=interceptor)

        task = CodingTask(
            task_id="ct-deny-1",
            goal="Write python function",
            workspace_dir=tmp_dir,
        )

        result = adapter.execute_coding_task(task)
        assert result.status == "failed"
        assert "Permission Denied" in result.errors[0]

def test_jcode_events_stream() -> None:
    """Verifies event stream capture during JcodeAdapter execution."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        task = CodingTask(task_id="ct-evt-1", goal="Create python module")

        adapter.execute_coding_task(task)
        event_types = [e.event_type for e in adapter.events]

        assert "session_started" in event_types
        assert "tool_executed" in event_types
        assert "turn_completed" in event_types

def test_coding_engine_wrapper_and_broker_integration() -> None:
    """Tests coding-engine-v1 tool execution through CapabilityBroker."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        broker = CapabilityBroker(workspace_dir=tmp_dir)
        broker.permission_policy.set_permission("write_file-v1", PermissionLevel.ALLOW)

        res = broker.execute_tool("coding-engine-v1", {"goal": "Create python module"})
        assert res.success is True
        assert res.permission_status == PermissionLevel.ALLOW

def test_orchestrator_coding_goal_integration() -> None:
    """Tests multi-step orchestration integration for coding goals."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        broker = CapabilityBroker(workspace_dir=tmp_dir)
        broker.permission_policy.set_permission("write_file-v1", PermissionLevel.ALLOW)

        planner = RuleBasedPlanner()
        plan = planner.create_plan("Create python module and test")

        orchestrator = PlanOrchestrator(broker=broker)
        completed_plan = orchestrator.execute_plan(plan)

        assert completed_plan.status == "completed"
        assert completed_plan.tasks["task_code_1"].status == TaskState.SUCCEEDED


def test_jcode_implements_requested_functions_not_a_fixed_stub() -> None:
    """Jcode must implement the functions named in the goal, not a hardcoded add_numbers stub."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        task = CodingTask(
            task_id="ct-ops-1",
            goal="Create python functions scale and offset with tests",
            workspace_dir=tmp_dir,
            test_command="pytest",
        )
        result = adapter.execute_coding_task(task)
        assert result.status == "success"
        module_path = os.path.join(tmp_dir, "module.py")
        test_path = os.path.join(tmp_dir, "test_module.py")
        assert os.path.isfile(module_path)
        assert os.path.isfile(test_path)
        source = open(module_path, encoding="utf-8").read()
        assert "def scale(" in source
        assert "def offset(" in source
        assert "def add_numbers(" not in source
        assert result.tests_run >= 1
        assert result.tests_passed >= 1
        assert result.tests_failed == 0


def test_jcode_implements_listed_arithmetic_operations() -> None:
    """A listed set of arithmetic operations must all be generated and tested."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        task = CodingTask(
            task_id="ct-ops-2",
            goal="Implement python with add, subtract, multiply and divide functions. Create tests and run them.",
            workspace_dir=tmp_dir,
            test_command="pytest",
        )
        result = adapter.execute_coding_task(task)
        assert result.status == "success"
        source = open(os.path.join(tmp_dir, "module.py"), encoding="utf-8").read()
        for name in ("add", "subtract", "multiply", "divide"):
            assert f"def {name}(" in source
        tests = open(os.path.join(tmp_dir, "test_module.py"), encoding="utf-8").read()
        for name in ("add", "subtract", "multiply", "divide"):
            assert f"test_{name}_" in tests
        assert result.status == "success"
        assert result.tests_failed == 0
        assert result.tests_run >= 1
        assert tests.count("def test_") >= 4


def test_jcode_generates_min_max_from_requested_names() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        task = CodingTask(
            task_id="ct-minmax",
            goal="Create python functions min_value and max_value with tests.",
            workspace_dir=tmp_dir,
            test_command="pytest",
        )
        result = adapter.execute_coding_task(task)
        assert result.status == "success"
        ns = {}
        exec(open(os.path.join(tmp_dir, "module.py"), encoding="utf-8").read(), ns)
        assert ns["min_value"](3, 1) == 1
        assert ns["max_value"](3, 1) == 3


def test_jcode_repairs_existing_failing_implementation_from_tests() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        with open(os.path.join(tmp_dir, "module.py"), "w", encoding="utf-8") as handle:
            handle.write("def broken_add(a, b):\n    return a - b\n")
        with open(os.path.join(tmp_dir, "test_module.py"), "w", encoding="utf-8") as handle:
            handle.write("from module import broken_add\n\ndef test_broken_add():\n    assert broken_add(2, 3) == 5\n")
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        task = CodingTask(
            task_id="ct-repair",
            goal="Fix the python function broken_add so tests pass.",
            workspace_dir=tmp_dir,
            test_command="pytest",
        )
        result = adapter.execute_coding_task(task)
        assert result.status == "success"
        ns = {}
        exec(open(os.path.join(tmp_dir, "module.py"), encoding="utf-8").read(), ns)
        assert ns["broken_add"](2, 3) == 5
