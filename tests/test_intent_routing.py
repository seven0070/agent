"""Intent routing: outcome selects a real capability, mock cannot fake success."""

from __future__ import annotations

import asyncio
import os
import tempfile

from agent.capabilities import CapabilityBroker, PermissionLevel
from agent.core import AgentTask, AgentV1
from agent.integrations.agentscope import AgentScopeAdapter, MockChatModel
from agent.orchestration import PlanOrchestrator, RuleBasedPlanner
from agent.orchestration.intent import (
    BUILD_PROGRAM,
    CHANGE_PROGRAM,
    COMPUTE,
    CONVERSE,
    QUERY_DATA,
    READ_TEXT,
    UNSUPPORTED,
    WRITE_TEXT,
    classify_intent,
)


def test_intent_selects_write_without_file_cue() -> None:
    intent = classify_intent("Put a note on my desktop saying I need to call John.")
    assert intent.kind == WRITE_TEXT
    assert intent.slots["filename"] == "note.txt"
    assert "I need to call John" in intent.slots["content"]


def test_intent_selects_program_from_conversion_outcome() -> None:
    intent = classify_intent("Make a small program that converts Celsius to Fahrenheit.")
    assert intent.kind == BUILD_PROGRAM


def test_intent_selects_change_for_existing_script(tmp_path) -> None:
    (tmp_path / "greet.py").write_text('GREETING = "Hello"\n', encoding="utf-8")
    intent = classify_intent(
        "The greeting in the existing Python script should say Good evening.",
        workspace_dir=str(tmp_path),
    )
    assert intent.kind == CHANGE_PROGRAM


def test_intent_selects_query_for_structured_records(tmp_path) -> None:
    (tmp_path / "players.json").write_text("[]", encoding="utf-8")
    intent = classify_intent(
        "Look at this JSON and tell me which user has the highest score.",
        workspace_dir=str(tmp_path),
    )
    assert intent.kind == QUERY_DATA
    assert intent.slots["filename"] == "players.json"


def test_intent_spoken_math_is_compute_not_mock() -> None:
    assert classify_intent("What is 18 times 7?").kind == COMPUTE
    assert classify_intent("How much is 144 divided by 12?").kind == COMPUTE


def test_intent_converse_and_unsupported() -> None:
    assert classify_intent("Hello there").kind == CONVERSE
    assert classify_intent("Email this report to the whole team.").kind == UNSUPPORTED


def test_existing_cued_goals_keep_previous_routing() -> None:
    planner = RuleBasedPlanner()
    write_plan = planner.create_plan("Create a file named alpha.txt containing the text ping-ok.")
    assert write_plan.tasks["task_write_1"].required_tool_id == "write_file-v1"
    read_plan = planner.create_plan("Read file beta.txt")
    assert read_plan.tasks["task_read_1"].required_tool_id == "read_file-v1"
    code_plan = planner.create_plan("Create python functions min_value and max_value with tests.")
    assert code_plan.tasks["task_code_1"].required_tool_id == "coding-engine-v1"
    calc_plan = planner.create_plan("Calculate 15 - 7")
    assert calc_plan.tasks["task_calc_1"].required_tool_id == "calculator-v1"


def test_open_ended_note_writes_workspace_file_not_mock() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        broker = CapabilityBroker(workspace_dir=tmp_dir)
        broker.permission_policy.set_permission("write_file-v1", PermissionLevel.ALLOW)
        planner = RuleBasedPlanner()
        plan = planner.create_plan(
            "Put a note on my desktop saying I need to call John.",
            workspace_dir=broker.workspace_manager.workspace_dir,
        )
        completed = PlanOrchestrator(broker=broker).execute_plan(plan)
        assert completed.status == "completed"
        content = broker.workspace_manager.read_file("note.txt")
        assert "I need to call John" in content
        desktop = os.path.join(os.path.expanduser("~"), "Desktop", "note.txt")
        assert not os.path.isfile(desktop) or "I need to call John" not in open(desktop, encoding="utf-8").read()


def test_open_ended_valid_task_does_not_use_mock_model() -> None:
    async def _run() -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            broker = CapabilityBroker(workspace_dir=tmp_dir)
            broker.permission_policy.set_permission("write_file-v1", PermissionLevel.ALLOW)
            adapter = AgentScopeAdapter(
                model=MockChatModel(mock_response="Custom test response"),
                broker=broker,
                planner=RuleBasedPlanner(),
                orchestrator=PlanOrchestrator(broker=broker),
            )
            agent = AgentV1(adapter=adapter)
            result = await agent.execute_task(
                AgentTask(task_id="t-note", prompt="Jot down that the oven is on.", session_id="s-note")
            )
            assert result.status in ("success", "completed")
            assert "Mocked AgentScope response content" not in result.output
            assert "Custom test response" not in result.output
            assert "oven is on" in broker.workspace_manager.read_file("note.txt")

    asyncio.run(_run())


def test_unsupported_capability_fails_honestly_not_mock() -> None:
    async def _run() -> None:
        adapter = AgentScopeAdapter(model=MockChatModel(mock_response="Custom test response"))
        agent = AgentV1(adapter=adapter)
        result = await agent.execute_task(
            AgentTask(task_id="t-mail", prompt="Email this report to the whole team.", session_id="s-mail")
        )
        assert result.status == "failed"
        assert "unavailable" in result.output.lower() or "no real operation" in result.output.lower()
        assert "Custom test response" not in result.output
        assert "Mocked AgentScope response content" not in result.output

    asyncio.run(_run())


def test_json_query_uses_inspect_capability() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        broker = CapabilityBroker(workspace_dir=tmp_dir)
        sandbox = broker.workspace_manager.workspace_dir
        with open(os.path.join(sandbox, "players.json"), "w", encoding="utf-8") as handle:
            handle.write('[{"user": "sam", "score": 10}, {"user": "ada", "score": 42}]')
        planner = RuleBasedPlanner()
        plan = planner.create_plan(
            "Look at this JSON and tell me which user has the highest score.",
            workspace_dir=sandbox,
        )
        completed = PlanOrchestrator(broker=broker).execute_plan(plan)
        assert completed.status == "completed"
        assert completed.tasks["task_inspect_1"].required_tool_id == "inspect_data-v1"
        assert "ada" in str(completed.tasks["task_inspect_1"].outputs)


def test_inspect_data_respects_workspace_boundary() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        broker = CapabilityBroker(workspace_dir=tmp_dir)
        res = broker.execute_tool(
            "inspect_data-v1",
            {"relative_path": "../../../../Windows/System32/drivers/etc/hosts", "query": "highest"},
        )
        assert res.success is False
        assert "Access Denied" in (res.error or "") or "Permission" in (res.error or "")


def test_multi_file_write_still_emits_two_tasks() -> None:
    planner = RuleBasedPlanner()
    plan = planner.create_plan(
        "Create a file named left.txt containing LEFT and a file named right.txt containing RIGHT."
    )
    assert plan.tasks["task_write_1"].inputs["relative_path"] == "left.txt"
    assert plan.tasks["task_write_2"].inputs["relative_path"] == "right.txt"


def test_read_outcome_without_read_file_phrase() -> None:
    intent = classify_intent("What's inside roster.json?")
    assert intent.kind == READ_TEXT
    assert intent.slots["filename"] == "roster.json"
