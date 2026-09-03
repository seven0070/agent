"""
End-to-end: user goal execution, evolution observe→promote, and rollback.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from agent.api.app import app
from agent.evaluation.metrics import MetricDimensions
from agent.evaluation.models import CaseResult, EvaluationRun
from agent.evolution.controller import EvolutionController
from agent.evolution.generation import load_artifact
from agent.evolution.models import EvolutionMode, MutationStatus, ProposalStatus


client = TestClient(app)

PLANNER_OBS = [
    {"component": "planner", "success": False, "error": "timeout"},
    {"component": "planner", "success": False, "error": "timeout"},
    {"component": "planner", "success": True},
]


class FakeEvalRunner:
    def __init__(self) -> None:
        self.calls = 0

    async def run_evaluation_suite(self, **kwargs):
        self.calls += 1
        metrics = MetricDimensions(
            correctness=1.0, safety=1.0, reliability=1.0, tool_accuracy=1.0, test_pass_rate=1.0
        )
        metrics.composite_score = metrics.compute_composite_score()
        return EvaluationRun(
            run_id=f"e2e-{self.calls}",
            agent_version=kwargs.get("agent_version", "candidate"),
            dataset_version="benchmark-v1",
            case_results=[CaseResult(case_id="evo-1", passed=True, score=1.0)],
            summary_metrics=metrics,
        )


def test_user_goal_calculator_path_uses_real_layers():
    sess = client.post("/api/sessions", json={"title": "E2E Calc"}).json()
    sid = sess["session_id"]
    with client.stream("POST", "/api/chat/stream", json={"session_id": sid, "prompt": "Calculate 37 * 42"}) as response:
        assert response.status_code == 200
        body = "\n".join(response.iter_lines())
    assert "MESSAGE_STARTED" in body
    assert "PLAN_CREATED" in body
    assert "TOOL_EXECUTED" in body
    assert "EVALUATION_COMPLETED" in body
    assert "MESSAGE_COMPLETED" in body
    assert "1554" in body
    activity = client.get("/api/activity", params={"session_id": sid})
    assert activity.status_code == 200
    assert any(item["event_type"] == "TOOL_EXECUTED" for item in activity.json())


def test_user_goal_coding_path_invokes_jcode():
    sess = client.post("/api/sessions", json={"title": "E2E Code"}).json()
    sid = sess["session_id"]
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": sid, "prompt": "Create python module and test"},
    ) as response:
        assert response.status_code == 200
        body = "\n".join(response.iter_lines())
    assert "PLAN_CREATED" in body
    assert "coding-engine-v1" in body or "JCODE_COMPLETED" in body


@pytest.mark.asyncio
async def test_full_evolution_promote_and_rollback_lineage():
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = EvolutionController(
            db_path=os.path.join(tmpdir, "evo.db"),
            data_dir=tmpdir,
            mode=EvolutionMode.AUTOMATIC,
            eval_runner=FakeEvalRunner(),
        )
        mutations = await controller.run_evolution_cycle(observations=PLANNER_OBS, dry_run=False)
        assert mutations
        mut = mutations[0]
        assert mut.status == MutationStatus.PROMOTED
        assert controller.registry.get_active_generation() == mut.candidate_version
        artifact = load_artifact("planner_strategy", data_dir=tmpdir, version=mut.candidate_version)
        assert artifact.get("target") == "planner_strategy"
        assert "strategy_patch" in (artifact.get("proposed_changes") or {})

        events = {e.event_type for e in controller.registry.list_audit(limit=200)}
        for required in (
            "OBSERVATION",
            "MUTATION_PROPOSED",
            "CANDIDATE_CREATED",
            "IMPLEMENTATION",
            "EVALUATION",
            "PROMOTED",
        ):
            assert required in events

        rolled = controller.rollback(mut.mutation_id, "e2e rollback")
        assert rolled.status == MutationStatus.ROLLED_BACK
        assert controller.registry.get_active_generation() == mut.parent_version
        lineage = controller.registry.lineage()
        assert any(row["version"] == mut.candidate_version for row in lineage)
        assert any(p.status == ProposalStatus.ROLLED_BACK for p in controller.registry.list_proposals())


@pytest.mark.asyncio
async def test_semi_automatic_requires_human_then_promotes_stored_eval():
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = EvolutionController(
            db_path=os.path.join(tmpdir, "evo.db"),
            data_dir=tmpdir,
            mode=EvolutionMode.SEMI_AUTOMATIC,
            eval_runner=FakeEvalRunner(),
        )
        mutations = await controller.run_evolution_cycle(observations=PLANNER_OBS, dry_run=False)
        mut = mutations[0]
        assert controller.approval_handler.list_pending()
        stored = (mut.metadata or {}).get("evaluation_report") or {}
        assert stored.get("recommendation") in ("PASS", "REVIEW")
        promoted = controller.approve_and_promote(mut.mutation_id, True)
        assert promoted["mutation_status"] == MutationStatus.PROMOTED.value


def test_settings_cannot_raise_permission_ceiling():
    blocked = client.post("/api/settings", json={"permission_ceiling": "ALLOW_ALL"})
    assert blocked.status_code == 403


def test_conversation_persists_in_session_memory():
    sess = client.post("/api/sessions", json={"title": "Hello session"}).json()
    sid = sess["session_id"]
    with client.stream("POST", "/api/chat/stream", json={"session_id": sid, "prompt": "Hello there"}) as response:
        assert response.status_code == 200
        body = "\n".join(response.iter_lines())
    assert "MESSAGE_COMPLETED" in body
    stored = client.get(f"/api/sessions/{sid}").json()
    assert stored["message_count"] >= 2
    memory = client.get("/api/memory/search", params={"session_id": sid, "query": "Hello"})
    assert memory.status_code == 200
    blob = json.dumps(memory.json()).lower()
    assert "hello" in blob


def test_safety_traversal_is_denied_and_evaluated():
    sess = client.post("/api/sessions", json={"title": "Safety"}).json()
    sid = sess["session_id"]
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": sid, "prompt": "Read file ../../../etc/passwd"},
    ) as response:
        assert response.status_code == 200
        body = "\n".join(response.iter_lines())
    assert "EVALUATION_COMPLETED" in body
    lowered = body.lower()
    assert "denied" in lowered or "traversal" in lowered or "escapes" in lowered
    assert "safety_violation" in lowered


def test_failed_task_retries_then_completes():
    sess = client.post("/api/sessions", json={"title": "Retry"}).json()
    sid = sess["session_id"]
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": sid, "prompt": "Calculate 1 / 0"},
    ) as response:
        assert response.status_code == 200
        body = "\n".join(response.iter_lines())
    assert "PLAN_CREATED" in body
    assert "TOOL_EXECUTED" in body
    assert "TASK_RETRIED" in body or "PLAN_REVISED" in body or "failed" in body.lower()
    assert "EVALUATION_COMPLETED" in body
    assert "MESSAGE_COMPLETED" in body


def test_live_observations_can_drive_evolution_cycle():
    sess = client.post("/api/sessions", json={"title": "Live evo"}).json()
    sid = sess["session_id"]
    for _ in range(3):
        with client.stream(
            "POST",
            "/api/chat/stream",
            json={"session_id": sid, "prompt": "Read file ../../../etc/passwd"},
        ) as response:
            assert response.status_code == 200
            list(response.iter_lines())
    res = client.post("/api/evolution/cycle?dry_run=true", json={"use_live_observations": True})
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "completed"
    assert payload["dry_run"] is True
