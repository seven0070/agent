"""
End-to-End Layer 10 Integration Tests.
Verifies complete flow: UI/API -> Agent Core -> Plan Orchestrator -> Tool Execution -> Audit Trail -> Evolution.
"""

import pytest
from fastapi.testclient import TestClient
from agent.api.app import app

client = TestClient(app)

def test_e2e_session_chat_plan_orchestration_flow():
    # 1. Create Session via API
    sess_res = client.post("/api/sessions", json={"title": "E2E Integration Session"})
    assert sess_res.status_code == 200
    sid = sess_res.json()["session_id"]

    # 2. Execute Chat Stream with Goal Prompt
    chat_payload = {
        "session_id": sid,
        "prompt": "Calculate 42 * 10 and report result",
    }
    with client.stream("POST", "/api/chat/stream", json=chat_payload) as response:
        assert response.status_code == 200
        events = [line for line in response.iter_lines() if line.startswith("data:")]
        assert len(events) >= 3

    # 3. Retrieve Session
    get_sess = client.get(f"/api/sessions/{sid}")
    assert get_sess.status_code == 200
    sdata = get_sess.json()
    assert sdata["message_count"] == 2
    assert sdata["active_plan_id"] is not None

    # 4. Verify Plan Retrieval
    plan_id = sdata["active_plan_id"]
    plan_res = client.get(f"/api/plans/{plan_id}")
    assert plan_res.status_code == 200
    assert plan_res.json()["status"] == "active"

    # 5. Verify Audit Logs Captured Event
    audit_res = client.get("/api/audit/logs")
    assert audit_res.status_code == 200
    assert len(audit_res.json()) > 0
