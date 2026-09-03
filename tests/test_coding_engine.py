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
    """Named catalog functions must be implemented as themselves, not add_numbers."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        task = CodingTask(
            task_id="ct-ops-1",
            goal="Create python functions square and double with tests",
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
        assert "def square(" in source
        assert "def double(" in source
        assert "def add_numbers(" not in source
        ns = {}
        exec(source, ns)
        assert ns["square"](3) == 9
        assert ns["double"](4) == 8
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


def test_jcode_implements_unnamed_conversion_program() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        result = adapter.execute_coding_task(
            CodingTask(
                task_id="ct-convert",
                goal="Make a small program that converts Celsius to Fahrenheit.",
                workspace_dir=tmp_dir,
                test_command="pytest",
            )
        )
        assert result.status == "success"
        ns = {}
        exec(open(os.path.join(tmp_dir, "module.py"), encoding="utf-8").read(), ns)
        assert ns["celsius_to_fahrenheit"](0) == 32.0
        assert ns["celsius_to_fahrenheit"](100) == 212.0
        assert "def add(" not in open(os.path.join(tmp_dir, "module.py"), encoding="utf-8").read()


def test_jcode_patches_existing_greeting_script() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        with open(os.path.join(tmp_dir, "greet.py"), "w", encoding="utf-8") as handle:
            handle.write('GREETING = "Hello"\n\ndef greet():\n    return GREETING\n')
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        result = adapter.execute_coding_task(
            CodingTask(
                task_id="ct-greet",
                goal="The greeting in the existing Python script should say Good evening.",
                workspace_dir=tmp_dir,
                test_command="pytest",
            )
        )
        assert result.status == "success"
        source = open(os.path.join(tmp_dir, "greet.py"), encoding="utf-8").read()
        assert "Good evening" in source
        assert "def greet(" in source


def test_jcode_greeting_patch_does_not_rewrite_unrelated_modules() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        with open(os.path.join(tmp_dir, "greet.py"), "w", encoding="utf-8") as handle:
            handle.write('GREETING = "Hello"\n\ndef greet():\n    return GREETING\n')
        with open(os.path.join(tmp_dir, "module.py"), "w", encoding="utf-8") as handle:
            handle.write('"""Generated workspace module implementing the requested functions."""\n\ndef celsius_to_fahrenheit(celsius):\n    return celsius * 9 / 5 + 32\n')
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        result = adapter.execute_coding_task(
            CodingTask(
                task_id="ct-greet-isolated",
                goal="The greeting in the existing Python script should say Good evening.",
                workspace_dir=tmp_dir,
                test_command="pytest",
            )
        )
        assert result.status == "success"
        greet = open(os.path.join(tmp_dir, "greet.py"), encoding="utf-8").read()
        module = open(os.path.join(tmp_dir, "module.py"), encoding="utf-8").read()
        assert "Good evening" in greet
        assert "celsius_to_fahrenheit" in module
        assert "Good evening" not in module


def test_jcode_multi_file_project_layout() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        result = adapter.execute_coding_task(
            CodingTask(
                task_id="ct-project",
                goal="Make a tiny project that can add two numbers and prove it with tests.",
                workspace_dir=tmp_dir,
                test_command="pytest",
            )
        )
        assert result.status == "success"
        assert os.path.isfile(os.path.join(tmp_dir, "pkg", "core.py"))
        assert os.path.isfile(os.path.join(tmp_dir, "tests", "test_core.py"))
        ns = {}
        exec(open(os.path.join(tmp_dir, "pkg", "core.py"), encoding="utf-8").read(), ns)
        assert ns["add"](2, 3) == 5


def test_jcode_larger_of_two_without_named_function() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        result = adapter.execute_coding_task(
            CodingTask(
                task_id="ct-larger",
                goal="A program that reports the larger of two numbers, with tests.",
                workspace_dir=tmp_dir,
                test_command="pytest",
            )
        )
        assert result.status == "success"
        ns = {}
        exec(open(os.path.join(tmp_dir, "module.py"), encoding="utf-8").read(), ns)
        assert ns["larger"](3, 1) == 3


def test_jcode_single_catalog_function_square() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        result = adapter.execute_coding_task(
            CodingTask(
                task_id="ct-square",
                goal="Create a python function square with tests.",
                workspace_dir=tmp_dir,
                test_command="pytest",
            )
        )
        assert result.status == "success"
        ns: dict = {}
        exec(open(os.path.join(tmp_dir, "module.py"), encoding="utf-8").read(), ns)
        assert ns["square"](3) == 9


def test_jcode_factorial_from_named_function() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        result = adapter.execute_coding_task(
            CodingTask(
                task_id="ct-fact",
                goal="Create a python function factorial with tests.",
                workspace_dir=tmp_dir,
                test_command="pytest",
            )
        )
        assert result.status == "success"
        ns: dict = {}
        exec(open(os.path.join(tmp_dir, "module.py"), encoding="utf-8").read(), ns)
        assert ns["factorial"](5) == 120


def test_jcode_unknown_named_functions_fail_closed_not_identity_stubs() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        result = adapter.execute_coding_task(
            CodingTask(
                task_id="ct-stub",
                goal="Create python functions scale and offset with tests",
                workspace_dir=tmp_dir,
                test_command="pytest",
            )
        )
        assert result.status in ("failed", "error")
        module_path = os.path.join(tmp_dir, "module.py")
        if os.path.isfile(module_path):
            source = open(module_path, encoding="utf-8").read()
            assert "return value" not in source
        assert "Could not determine the requested program" in " ".join(result.errors)


def test_jcode_fails_honestly_when_goal_cannot_be_implemented() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        result = adapter.execute_coding_task(
            CodingTask(
                task_id="ct-empty",
                goal="Invent a quantum compiler backend for this workspace.",
                workspace_dir=tmp_dir,
                test_command="pytest",
            )
        )
        assert result.status in ("failed", "error")
        assert not os.path.isfile(os.path.join(tmp_dir, "module.py"))


def test_jcode_repairs_nested_repo_from_existing_tests() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.makedirs(os.path.join(tmp_dir, "pkg"))
        os.makedirs(os.path.join(tmp_dir, "tests"))
        open(os.path.join(tmp_dir, "pkg", "__init__.py"), "w", encoding="utf-8").write("")
        open(os.path.join(tmp_dir, "pkg", "mathutil.py"), "w", encoding="utf-8").write(
            "def cube(n):\n    return 0\n"
        )
        open(os.path.join(tmp_dir, "tests", "test_mathutil.py"), "w", encoding="utf-8").write(
            "from pkg.mathutil import cube\n\n\ndef test_cube():\n    assert cube(3) == 27\n    assert cube(2) == 8\n"
        )
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        result = adapter.execute_coding_task(
            CodingTask(
                task_id="ct-repo-cube",
                goal="Inspect this repository, fix the failing cube implementation, run the tests, and repair until they pass.",
                workspace_dir=tmp_dir,
                test_command="pytest",
            )
        )
        assert result.status == "success"
        ns: dict = {}
        exec(open(os.path.join(tmp_dir, "pkg", "mathutil.py"), encoding="utf-8").read(), ns)
        assert ns["cube"](3) == 27
        assert ns["cube"](2) == 8
        assert result.tests_failed == 0


def test_jcode_infers_unary_repair_from_failing_tests() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        open(os.path.join(tmp_dir, "module.py"), "w", encoding="utf-8").write("def triple(n):\n    return n\n")
        open(os.path.join(tmp_dir, "test_module.py"), "w", encoding="utf-8").write(
            "from module import triple\n\n\ndef test_triple():\n    assert triple(3) == 9\n    assert triple(4) == 12\n"
        )
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        result = adapter.execute_coding_task(
            CodingTask(
                task_id="ct-triple",
                goal="Repair the failing python tests and retest until they pass.",
                workspace_dir=tmp_dir,
                test_command="pytest",
            )
        )
        assert result.status == "success"
        ns: dict = {}
        exec(open(os.path.join(tmp_dir, "module.py"), encoding="utf-8").read(), ns)
        assert ns["triple"](3) == 9
        assert ns["triple"](4) == 12


def test_jcode_patches_distinct_assignments_in_multiple_files() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        open(os.path.join(tmp_dir, "greet.py"), "w", encoding="utf-8").write(
            'GREETING = "hi"\n\ndef greet():\n    return GREETING\n'
        )
        open(os.path.join(tmp_dir, "title.py"), "w", encoding="utf-8").write(
            'TITLE = "old"\n\ndef title():\n    return TITLE\n'
        )
        adapter = JcodeAdapter(workspace_dir=tmp_dir)
        result = adapter.execute_coding_task(
            CodingTask(
                task_id="ct-multi-assign",
                goal="Change the greeting to Hello Agent and the title to Deep Mode.",
                workspace_dir=tmp_dir,
                test_command="pytest",
            )
        )
        assert result.status == "success"
        greet = open(os.path.join(tmp_dir, "greet.py"), encoding="utf-8").read()
        title = open(os.path.join(tmp_dir, "title.py"), encoding="utf-8").read()
        assert 'GREETING = "Hello Agent"' in greet
        assert 'TITLE = "Deep Mode"' in title
        assert 'GREETING = "Deep Mode"' not in greet
        assert 'TITLE = "Hello Agent"' not in title
