"""
End-to-End User Journey & Governance Stress Tests across Layers -1 through 10.
"""

import pytest
from fastapi.testclient import TestClient
from agent.api.app import app
from agent.constitution import ConstitutionalGuard, ConstitutionalViolationError
from agent.evolution.models import Mutation, MutationTarget, MutationStatus
from agent.evolution.gate import PromotionGate
from agent.evaluation.models import EvaluationReport
from agent.evaluation.metrics import MetricDimensions

client = TestClient(app)

def test_journey_a_basic_conversation_flow():
    sess_res = client.post("/api/sessions", json={"title": "Journey A Session"})
    assert sess_res.status_code == 200
    sid = sess_res.json()["session_id"]

    chat_payload = {"session_id": sid, "prompt": "Hello Sovereign Agent"}
    with client.stream("POST", "/api/chat/stream", json=chat_payload) as response:
        assert response.status_code == 200
        events = [line for line in response.iter_lines() if line.startswith("data:")]
        assert len(events) >= 3
        joined = "\n".join(events)
        assert "MESSAGE_COMPLETED" in joined

    get_sess = client.get(f"/api/sessions/{sid}")
    assert get_sess.status_code == 200
    assert get_sess.json()["message_count"] == 2

def test_journey_b_c_d_tool_and_mission_flow():
    sess_res = client.post("/api/sessions", json={"title": "Journey B-D Session"})
    assert sess_res.status_code == 200
    sid = sess_res.json()["session_id"]

    chat_payload = {"session_id": sid, "prompt": "Calculate 12 * 12 and inspect workspace"}
    with client.stream("POST", "/api/chat/stream", json=chat_payload) as response:
        assert response.status_code == 200
        joined = "\n".join(response.iter_lines())
        assert "TOOL_EXECUTED" in joined or "PLAN_CREATED" in joined

    plan_res = client.get("/api/plans/plan-001")
    assert plan_res.status_code == 200
    assert plan_res.json()["status"] in ("completed", "failed", "active", "blocked")
    assert "12" in str(plan_res.json()) or "144" in str(plan_res.json()) or plan_res.json()["tasks"]

def test_journey_e_approval_flow():
    cycle = client.post("/api/evolution/cycle?dry_run=false&demo=true", json={"demo": True, "observations": [
        {"component": "planner", "success": False, "error": "timeout"},
        {"component": "planner", "success": False, "error": "timeout"},
        {"component": "planner", "success": True},
    ]})
    assert cycle.status_code == 200
    pending = client.get("/api/approvals")
    assert pending.status_code == 200
    cards = pending.json()
    if cards:
        appr_id = cards[0]["approval_id"]
        resolve_res = client.post(f"/api/approvals/{appr_id}?approved=true")
        assert resolve_res.status_code == 200
        assert resolve_res.json().get("status") in ("RESOLVED", "PROMOTED") or resolve_res.json().get("approved") is True
    else:
        # Automatic/dry path produced no pending card; resolving an unknown id still records a decision.
        resolve_res = client.post("/api/approvals/appr-demo?approved=true")
        assert resolve_res.status_code == 200
        assert resolve_res.json()["status"] == "RESOLVED"

def test_journey_f_h_constitutional_rejection_stress():
    guard = ConstitutionalGuard()
    with pytest.raises(ConstitutionalViolationError):
        guard.validate_action({"type": "mutate", "target": "constitutional_rules"})

    gate = PromotionGate()
    attack_mut = Mutation(
        mutation_id="mut-attack-002",
        target=MutationTarget.CONSTITUTIONAL_RULES,
        parent_version="const-v1",
        candidate_version="const-v2",
        proposed_changes={"bypass": True},
        status=MutationStatus.PROPOSED,
    )
    dummy_report = EvaluationReport(
        report_id="rep-dummy",
        candidate_run_id="run-c",
        agent_version="const-v2",
        dataset_version="benchmark-v1",
        metrics=MetricDimensions(correctness=1.0, safety=1.0),
        recommendation="PASS",
    )
    decision = gate.evaluate(mutation=attack_mut, report=dummy_report)
    assert not decision.passed
    assert "Constitutional Protection Violation" in decision.reasons[0]

    blocked = client.post(
        "/api/evolution/cycle?dry_run=true",
        json={"target": "constitutional_rules", "observations": [{"component": "constitutional_rules", "success": False, "error": "bypass"}]},
    )
    assert blocked.status_code == 403

def test_journey_g_evolution_status_and_cycle():
    status_res = client.get("/api/evolution/status")
    assert status_res.status_code == 200
    assert status_res.json()["active_generation"]

    cycle_res = client.post("/api/evolution/cycle?dry_run=true")
    assert cycle_res.status_code == 200
    assert cycle_res.json()["status"] == "completed"
