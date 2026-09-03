"""Regression tests for general multi-step planning and orchestration."""

from __future__ import annotations

import os
import tempfile

from agent.capabilities import CapabilityBroker, PermissionLevel
from agent.orchestration import PlanOrchestrator, RuleBasedPlanner, TaskState
from agent.orchestration.decompose import compose_operations, resolve_placeholders, split_clauses


def _run(prompt: str, files: list[tuple[str, str]] | None = None):
    with tempfile.TemporaryDirectory() as tmp_dir:
        broker = CapabilityBroker(workspace_dir=tmp_dir)
        broker.permission_policy.set_permission("write_file-v1", PermissionLevel.ALLOW)
        sandbox = broker.workspace_manager.workspace_dir
        for rel, content in files or []:
            path = os.path.join(sandbox, rel)
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
        plan = RuleBasedPlanner().create_plan(prompt, workspace_dir=sandbox)
        completed = PlanOrchestrator(broker=broker).execute_plan(plan)
        snapshot = {
            name: open(os.path.join(sandbox, name), encoding="utf-8").read()
            for name in os.listdir(sandbox)
            if os.path.isfile(os.path.join(sandbox, name))
        }
        return completed, snapshot


def test_split_clauses_then() -> None:
    parts = split_clauses("Read a.txt and write it into b.txt, then write done.txt containing copied")
    assert len(parts) == 2
    assert "done.txt" in parts[1]


def test_placeholder_substitution_in_expression() -> None:
    got = resolve_placeholders("$task_read_1.output+$task_read_2.output", {"task_read_1": "10", "task_read_2": "32"})
    assert got == "10+32"


def test_read_two_files_add_and_write() -> None:
    completed, snapshot = _run(
        "Read left.txt and right.txt, add the numbers, and write the sum to sum.txt",
        [("left.txt", "10"), ("right.txt", "32")],
    )
    assert completed.status == "completed"
    tools = [t.required_tool_id for t in completed.tasks.values()]
    assert "read_file-v1" in tools
    assert "calculator-v1" in tools
    assert "write_file-v1" in tools
    assert "42" in snapshot.get("sum.txt", "")
    assert any(t.dependencies for t in completed.tasks.values())


def test_inspect_then_write_winner() -> None:
    completed, snapshot = _run(
        "Look at this JSON and write the highest scorer into winner.txt",
        [("players.json", '[{"user": "sam", "score": 10}, {"user": "ada", "score": 42}]')],
    )
    assert completed.status == "completed"
    assert "ada" in snapshot.get("winner.txt", "")


def test_read_inspect_write_average() -> None:
    completed, snapshot = _run(
        "Read players.json, compute the average score, and write it to avg.txt",
        [("players.json", '[{"user": "sam", "score": 10}, {"user": "ada", "score": 30}]')],
    )
    assert completed.status == "completed"
    assert "20" in snapshot.get("avg.txt", "")


def test_then_clause_second_write() -> None:
    completed, snapshot = _run(
        "Read source.txt and write what you found into dest.txt, then write done.txt containing copied",
        [("source.txt", "payload-ok")],
    )
    assert completed.status == "completed"
    assert snapshot.get("dest.txt") == "payload-ok"
    assert "copied" in snapshot.get("done.txt", "")


def test_invalid_calc_does_not_write_zero() -> None:
    completed, snapshot = _run("Calculate not-a-number and save to out.txt")
    assert completed.status == "failed"
    assert "out.txt" not in snapshot


def test_unsafe_read_does_not_write_stolen_copy() -> None:
    completed, snapshot = _run(
        "Read file ../../../../Windows/System32/drivers/etc/hosts and write it to stolen.txt"
    )
    assert completed.status == "failed"
    assert "stolen.txt" not in snapshot
    assert "hosts" not in snapshot


def test_missing_intermediate_does_not_fabricate_output() -> None:
    completed, snapshot = _run("Read missing.txt and write what you found into recovered.txt")
    assert completed.status == "failed"
    assert "recovered.txt" not in snapshot


def test_compose_does_not_duplicate_simple_calc() -> None:
    ops = compose_operations("Calculate 15 - 7")
    kinds = [op.kind for op in ops]
    assert kinds.count("compute") == 1
    assert "write" not in kinds
