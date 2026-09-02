"""
End-to-End User Journey & Governance Stress Tests across Layers -1 through 10.
Tests Journeys A-H: Conversation, Tools, Coding, Missions, Approvals, Rejections, Evolution & Rollbacks.
"""

import pytest
from fastapi.testclient import TestClient
from agent.api.app import app
from agent.constitution import ConstitutionalGuard, ConstitutionalViolationError
from agent.evolution.models import Mutation, MutationTarget, MutationStatus
from agent.evolution.gate import PromotionGate
from agent.evaluation.models import EvaluationReport, MetricDimensions

client = TestClient(app)

def test_journey_a_basic_conversation_flow():
    """Journey A: Session creation, message execution, and persistence."""
    sess_res = client.post("/api/sessions", json={"title": "Journey A Session"})
    assert sess_res.status_code == 200
    sid = sess_res.json()["session_id"]

    chat_payload = {"session_id": sid, "prompt": "Hello Sovereign Agent"}
    with client.stream("POST", "/api/chat/stream", json=chat_payload) as response:
        assert response.status_code == 200
        events = [line for line in response.iter_lines() if line.startswith("data:")]
        assert len(events) >= 3

    get_sess = client.get(f"/api/sessions/{sid}")
    assert get_sess.status_code == 200
    assert get_sess.json()["message_count"] == 2

def test_journey_b_c_d_tool_and_mission_flow():
    """Journeys B, C, D: Tool execution, missions, and plan DAGs."""
    sess_res = client.post("/api/sessions", json={"title": "Journey B-D Session"})
    assert sess_res.status_code == 200
    sid = sess_res.json()["session_id"]

    chat_payload = {"session_id": sid, "prompt": "Calculate 12 * 12 and inspect workspace"}
    with client.stream("POST", "/api/chat/stream", json=chat_payload) as response:
        assert response.status_code == 200

    plan_res = client.get(f"/api/plans/plan-001")
    assert plan_res.status_code == 200
    assert plan_res.json()["status"] == "active"

def test_journey_e_approval_flow():
    """Journey E: Human approval center resolution."""
    appr_res = client.get("/api/approvals")
    assert appr_res.status_code == 200
    assert len(appr_res.json()) > 0

    appr_id = appr_res.json()[0]["approval_id"]
    resolve_res = client.post(f"/api/approvals/{appr_id}?approved=true")
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "RESOLVED"

def test_journey_f_h_constitutional_rejection_stress():
    """Journeys F, H: Constitutional protection blocking unauthorized mutations and attacks."""
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
        metrics=MetricDimensions(accuracy=1.0, safety=1.0),
        recommendation="PASS",
    )
    decision = gate.evaluate(mutation=attack_mut, report=dummy_report)
    assert not decision.passed
    assert "Constitutional Protection Violation" in decision.reasons[0]

def test_journey_g_evolution_status_and_cycle():
    """Journey G: Layer 9 Evolution Controller status and out-of-band cycle."""
    status_res = client.get("/api/evolution/status")
    assert status_res.status_code == 200
    assert status_res.json()["active_generation"] == "agent-v1"

    cycle_res = client.post("/api/evolution/cycle?dry_run=true")
    assert cycle_res.status_code == 200
    assert cycle_res.json()["status"] == "completed"
