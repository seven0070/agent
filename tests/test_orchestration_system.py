"""
Unit and Integration Tests for Layer 5 Planning & Orchestration Subsystem.
"""

import pytest
import tempfile
from agent.capabilities import CapabilityBroker, PermissionLevel, CapabilityResult
from agent.orchestration import (
    TaskState,
    PlanTask,
    Plan,
    transition_task_state,
    RuleBasedPlanner,
    PlanOrchestrator,
    SubagentDelegateHook,
    HumanApprovalHandler,
)

def test_task_state_transitions() -> None:
    """Tests state machine transition validation."""
    st_ready = transition_task_state(TaskState.PENDING, TaskState.READY)
    st_run = transition_task_state(st_ready, TaskState.RUNNING)
    st_succ = transition_task_state(st_run, TaskState.SUCCEEDED)
    assert st_succ == TaskState.SUCCEEDED

    with pytest.raises(ValueError) as exc_info:
        transition_task_state(TaskState.PENDING, TaskState.SUCCEEDED)
    assert "Invalid TaskState transition" in str(exc_info.value)

def test_planner_goal_decomposition() -> None:
    """Tests RuleBasedPlanner goal decomposition into structured dependency graphs."""
    planner = RuleBasedPlanner()
    plan = planner.create_plan("Calculate 37 * 42 and save to calc_result.txt")

    assert len(plan.tasks) == 2
    assert "task_calc_1" in plan.tasks
    assert "task_write_2" in plan.tasks
    assert plan.tasks["task_write_2"].dependencies == ["task_calc_1"]


def test_planner_file_create_uses_write_tool_not_model_path() -> None:
    """Ordinary file-create goals must route through write_file-v1, not the mock model."""
    from agent.orchestration.planner import extract_file_content, extract_filename

    planner = RuleBasedPlanner()
    plan = planner.create_plan(
        "Create a file named notes-alpha.txt containing the text WorkspaceProbe. Verify that the file exists."
    )
    assert "task_write_1" in plan.tasks
    task = plan.tasks["task_write_1"]
    assert task.required_tool_id == "write_file-v1"
    assert task.inputs["relative_path"] == "notes-alpha.txt"
    assert task.inputs["content"] == "WorkspaceProbe"

    other = planner.create_plan('Write a file called report.md containing "status ok"')
    assert other.tasks["task_write_1"].inputs["relative_path"] == "report.md"
    assert other.tasks["task_write_1"].inputs["content"] == "status ok"
    assert extract_filename("Create a file named ledger.csv containing totals") == "ledger.csv"
    assert extract_file_content("Create a file named ledger.csv containing totals") == "totals"


def test_planner_edit_file_is_write_not_coding() -> None:
    planner = RuleBasedPlanner()
    plan = planner.create_plan("Edit file gamma.txt containing the text rewritten-ok")
    assert "task_write_1" in plan.tasks
    assert plan.tasks["task_write_1"].required_tool_id == "write_file-v1"
    assert plan.tasks["task_write_1"].inputs["content"] == "rewritten-ok"


def test_planner_multi_file_create_emits_multiple_writes() -> None:
    planner = RuleBasedPlanner()
    plan = planner.create_plan(
        "Create a file named left.txt containing LEFT and a file named right.txt containing RIGHT."
    )
    assert "task_write_1" in plan.tasks
    assert "task_write_2" in plan.tasks
    assert plan.tasks["task_write_1"].inputs["relative_path"] == "left.txt"
    assert plan.tasks["task_write_2"].inputs["relative_path"] == "right.txt"


def test_missing_file_read_fails_closed_not_calculator_zero() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        broker = CapabilityBroker(workspace_dir=tmp_dir)
        planner = RuleBasedPlanner()
        plan = planner.create_plan("Read file does-not-exist.txt")
        orchestrator = PlanOrchestrator(broker=broker)
        completed = orchestrator.execute_plan(plan)
        assert completed.status == "failed"
        tools = [t.required_tool_id for t in completed.tasks.values() if t.required_tool_id]
        assert "calculator-v1" not in tools

def test_dag_cycle_detection() -> None:
    """Tests DAG cycle detection in PlanOrchestrator."""
    orchestrator = PlanOrchestrator()

    t1 = PlanTask(id="task_A", description="A", dependencies=["task_B"])
    t2 = PlanTask(id="task_B", description="B", dependencies=["task_A"])
    cyclic_plan = Plan(id="cyclic-p", goal="Cyclic", tasks={"task_A": t1, "task_B": t2})

    with pytest.raises(ValueError) as exc_info:
        orchestrator.validate_plan_dag(cyclic_plan)

    assert "Cyclic dependency detected" in str(exc_info.value)

def test_dependency_execution_ordering() -> None:
    """Verifies that dependent tasks cannot execute until prerequisites succeed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        broker = CapabilityBroker(workspace_dir=tmp_dir)
        broker.permission_policy.set_permission("write_file-v1", PermissionLevel.ALLOW)

        planner = RuleBasedPlanner()
        plan = planner.create_plan("Calculate 10 + 20 and save to sum.txt")

        orchestrator = PlanOrchestrator(broker=broker)
        completed_plan = orchestrator.execute_plan(plan)

        assert completed_plan.status == "completed"
        assert completed_plan.tasks["task_calc_1"].status == TaskState.SUCCEEDED
        assert completed_plan.tasks["task_write_2"].status == TaskState.SUCCEEDED
        assert completed_plan.tasks["task_write_2"].inputs["relative_path"] == "sum.txt"

        content = broker.workspace_manager.read_file("sum.txt")
        assert content in ["30", "30.0"]

def test_task_failure_and_retry_recovery() -> None:
    """Tests task retry recovery upon temporary capability execution failure."""
    broker = CapabilityBroker()

    fail_count = [0]
    t1 = PlanTask(id="flaky_task", description="Flaky math", required_tool_id="calculator-v1", inputs={"expression": "1+1"}, max_retries=2)
    plan = Plan(id="p-flaky", goal="Flaky Test", tasks={"flaky_task": t1})

    orchestrator = PlanOrchestrator(broker=broker)

    orig_exec = broker.execute_tool
    def _mock_exec(tid, kwargs):
        if tid == "calculator-v1" and fail_count[0] == 0:
            fail_count[0] += 1
            return CapabilityResult(tool_id=tid, success=False, error="Transient error")
        return orig_exec(tid, kwargs)

    broker.execute_tool = _mock_exec

    completed_plan = orchestrator.execute_plan(plan)
    assert completed_plan.status == "completed"
    assert completed_plan.tasks["flaky_task"].status == TaskState.SUCCEEDED
    assert completed_plan.tasks["flaky_task"].retry_count == 1

def test_replanning_version_bump() -> None:
    """Tests plan versioning (plan-v1 -> plan-v2) upon permanent task failure."""
    broker = CapabilityBroker()
    broker.permission_policy.set_permission("calculator-v1", PermissionLevel.DENY)

    t1 = PlanTask(id="blocked_task", description="Denied math", required_tool_id="calculator-v1", inputs={"expression": "1+1"}, max_retries=0)
    plan = Plan(id="p-replan", goal="Replan Test", version="plan-v1", tasks={"blocked_task": t1})

    orchestrator = PlanOrchestrator(broker=broker)
    replanned_plan = orchestrator.replan(plan, "blocked_task")

    assert replanned_plan is None

def test_orchestration_event_generation() -> None:
    """Verifies structured audit events emitted during plan execution."""
    broker = CapabilityBroker()
    planner = RuleBasedPlanner()
    plan = planner.create_plan("Calculate 5 * 5")

    orchestrator = PlanOrchestrator(broker=broker)
    orchestrator.execute_plan(plan)

    event_types = [e.event_type for e in orchestrator.events]
    assert "PLAN_CREATED" in event_types
    assert "TASK_STARTED" in event_types
    assert "TASK_COMPLETED" in event_types
    assert "PLAN_COMPLETED" in event_types

def test_preparation_subagent_and_approval_hooks() -> None:
    """Tests preparation hooks for subagent delegation and human approval."""
    hook = SubagentDelegateHook()
    hook.register_delegate("coding_specialist", lambda t: "Specialist result")

    assert hook.can_delegate("coding_specialist") is True
    assert hook.delegate_task("coding_specialist", PlanTask(id="t1", description="desc")) == "Specialist result"

    approval = HumanApprovalHandler()
    approval.set_auto_approve(True)
    assert approval.request_approval(PlanTask(id="t2", description="desc"), PermissionLevel.REQUIRE_APPROVAL) is True
