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
    READ_THEN_WRITE,
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
    assert classify_intent("Delete the note from my desktop.").kind == UNSUPPORTED
    assert classify_intent("Search the web for today's weather.").kind == UNSUPPORTED


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


def test_json_average_uses_inspect_capability() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        broker = CapabilityBroker(workspace_dir=tmp_dir)
        sandbox = broker.workspace_manager.workspace_dir
        with open(os.path.join(sandbox, "totals.json"), "w", encoding="utf-8") as handle:
            handle.write('[{"user": "sam", "score": 10}, {"user": "ada", "score": 20}, {"user": "lee", "score": 30}]')
        plan = RuleBasedPlanner().create_plan(
            "What is the average score in this JSON?",
            workspace_dir=sandbox,
        )
        completed = PlanOrchestrator(broker=broker).execute_plan(plan)
        assert completed.status == "completed"
        assert "20" in str(completed.tasks["task_inspect_1"].outputs)


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


def test_hyphenated_token_does_not_steal_write_intent() -> None:
    intent = classify_intent("Put a note on my desktop saying the code is ticket-14-1788.")
    assert intent.kind == WRITE_TEXT
    assert "ticket-14-1788" in intent.slots["content"]
    assert classify_intent("Jot down that the meeting is 3-4pm").kind == WRITE_TEXT


def test_change_file_to_say_is_write() -> None:
    intent = classify_intent("Change note.txt to say goodbye")
    assert intent.kind == WRITE_TEXT
    assert intent.slots["filename"] == "note.txt"
    assert intent.slots["content"] == "goodbye"


def test_remind_me_persists_reminder() -> None:
    intent = classify_intent("Remind me to buy milk")
    assert intent.kind == WRITE_TEXT
    assert intent.slots["filename"] == "reminder.txt"
    assert "buy milk" in intent.slots["content"]


def test_read_then_write_compound_plan() -> None:
    planner = RuleBasedPlanner()
    plan = planner.create_plan("Read info.txt and write what you found into summary.txt")
    assert plan.metadata["intent"] == READ_THEN_WRITE
    assert plan.tasks["task_read_1"].required_tool_id == "read_file-v1"
    assert plan.tasks["task_read_1"].inputs["relative_path"] == "info.txt"
    assert plan.tasks["task_write_2"].required_tool_id == "write_file-v1"
    assert plan.tasks["task_write_2"].inputs["relative_path"] == "summary.txt"
    assert plan.tasks["task_write_2"].inputs["content"] == "$task_read_1.output"


def test_write_answer_in_filename_is_extracted() -> None:
    planner = RuleBasedPlanner()
    plan = planner.create_plan("What is 9 times 8? Write the answer in result.txt")
    assert plan.tasks["task_calc_1"].required_tool_id == "calculator-v1"
    assert plan.tasks["task_write_2"].inputs["relative_path"] == "result.txt"


def test_natural_multi_file_without_named_cue() -> None:
    planner = RuleBasedPlanner()
    plan = planner.create_plan(
        "Create readme.txt containing Hello world and license.txt containing MIT"
    )
    assert plan.tasks["task_write_1"].inputs["relative_path"] == "readme.txt"
    assert "Hello world" in plan.tasks["task_write_1"].inputs["content"]
    assert plan.tasks["task_write_2"].inputs["relative_path"] == "license.txt"
    assert "MIT" in plan.tasks["task_write_2"].inputs["content"]


def test_follow_up_write_uses_session_last_output() -> None:
    planner = RuleBasedPlanner()
    plan = planner.create_plan(
        "Write that result to memory.txt",
        session_hints={"last_output": "42"},
    )
    assert plan.tasks["task_write_1"].inputs["relative_path"] == "memory.txt"
    assert plan.tasks["task_write_1"].inputs["content"] == "42"


def test_summarize_local_json_is_inspect_not_unsupported() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        broker = CapabilityBroker(workspace_dir=tmp_dir)
        sandbox = broker.workspace_manager.workspace_dir
        with open(os.path.join(sandbox, "players.json"), "w", encoding="utf-8") as handle:
            handle.write('[{"user": "sam", "score": 10}, {"user": "ada", "score": 42}]')
        intent = classify_intent("Summarize this JSON for me.", workspace_dir=sandbox)
        assert intent.kind == QUERY_DATA
        completed = PlanOrchestrator(broker=broker).execute_plan(
            RuleBasedPlanner().create_plan("Summarize this JSON for me.", workspace_dir=sandbox)
        )
        assert completed.status == "completed"
        blob = str(completed.tasks["task_inspect_1"].outputs)
        assert "2 records" in blob or "records" in blob.lower()


def test_session_follow_up_write_binds_prior_result() -> None:
    async def _run() -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            broker = CapabilityBroker(workspace_dir=tmp_dir)
            broker.permission_policy.set_permission("write_file-v1", PermissionLevel.ALLOW)
            adapter = AgentScopeAdapter(
                planner=RuleBasedPlanner(),
                broker=broker,
                orchestrator=PlanOrchestrator(broker=broker),
            )
            agent = AgentV1(adapter=adapter)
            first = await agent.execute_task(
                AgentTask(task_id="t-calc", prompt="Calculate 15 + 27", session_id="s-follow")
            )
            assert "42" in first.output
            second = await agent.execute_task(
                AgentTask(task_id="t-save", prompt="Write that result to memory.txt", session_id="s-follow")
            )
            assert second.status in ("success", "completed")
            assert "42" in broker.workspace_manager.read_file("memory.txt")

    asyncio.run(_run())


def test_json_total_uses_inspect_capability() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        broker = CapabilityBroker(workspace_dir=tmp_dir)
        sandbox = broker.workspace_manager.workspace_dir
        with open(os.path.join(sandbox, "players.json"), "w", encoding="utf-8") as handle:
            handle.write('[{"user": "sam", "score": 10}, {"user": "ada", "score": 42}, {"user": "lee", "score": 8}]')
        plan = RuleBasedPlanner().create_plan(
            "What is the total of the scores in players.json?",
            workspace_dir=sandbox,
        )
        completed = PlanOrchestrator(broker=broker).execute_plan(plan)
        assert completed.status == "completed"
        assert "60" in str(completed.tasks["task_inspect_1"].outputs)
