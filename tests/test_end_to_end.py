"""
End-to-end: user goal execution, evolution observe→promote, and rollback.
"""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from agent.api.app import app
from agent.evaluation.metrics import MetricDimensions
from agent.evaluation.models import CaseResult, EvaluationRun
from agent.evolution.controller import EvolutionController
from agent.evolution.generation import load_artifact
from agent.evolution.models import EvolutionMode, MutationStatus


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
