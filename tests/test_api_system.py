"""
Unit Tests for Layer 10 FastAPI Core & Session/Chat API Endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from agent.api.app import app

client = TestClient(app)

def test_system_health_endpoint():
    response = client.get("/api/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "layers" in data
    assert data["layers"]["constitution"] == "active"

def test_session_lifecycle_api():
    # 1. Create Session
    create_res = client.post("/api/sessions", json={"title": "Test API Session"})
    assert create_res.status_code == 200
    sess = create_res.json()
    sid = sess["session_id"]
    assert sid.startswith("sess-")
    assert sess["title"] == "Test API Session"

    # 2. List Sessions
    list_res = client.get("/api/sessions")
    assert list_res.status_code == 200
    sessions = list_res.json()
    assert any(s["session_id"] == sid for s in sessions)

    # 3. Get Session
    get_res = client.get(f"/api/sessions/{sid}")
    assert get_res.status_code == 200
    assert get_res.json()["session_id"] == sid

    # 4. Delete Session
    del_res = client.delete(f"/api/sessions/{sid}")
    assert del_res.status_code == 200

    get_after_del = client.get(f"/api/sessions/{sid}")
    assert get_after_del.status_code == 404

def test_chat_stream_endpoint():
    payload = {
        "session_id": "test-stream-sess",
        "prompt": "Calculate 5 + 10 and write report",
    }
    with client.stream("POST", "/api/chat/stream", json=payload) as response:
        assert response.status_code == 200
        lines = list(response.iter_lines())
        assert len(lines) > 0
        events = [line for line in lines if line.startswith("data:")]
        assert len(events) >= 3
        assert "MESSAGE_STARTED" in events[0]
        assert "MESSAGE_COMPLETED" in events[-1]


def test_domain_api_endpoints():
    # 1. Plan Endpoint
    plan_res = client.get("/api/plans/plan-001")
    assert plan_res.status_code == 200
    assert plan_res.json()["plan_id"] == "plan-001"

    # 2. Approvals & Tools
    appr_res = client.get("/api/approvals")
    assert appr_res.status_code == 200
    assert len(appr_res.json()) >= 1

    post_appr = client.post("/api/approvals/appr-001?approved=true")
    assert post_appr.status_code == 200
    assert post_appr.json()["approved"] is True

    tools_res = client.get("/api/tools")
    assert tools_res.status_code == 200

    # 3. Jcode Workspace
    coding_res = client.get("/api/coding/workspace")
    assert coding_res.status_code == 200
    assert coding_res.json()["status"] == "idle"

    # 4. Evolution Controller Status
    evo_res = client.get("/api/evolution/status")
    assert evo_res.status_code == 200
    assert evo_res.json()["active_generation"] == "agent-v1"

    # 5. Audit Logs
    audit_res = client.get("/api/audit/logs")
    assert audit_res.status_code == 200
    assert len(audit_res.json()) >= 1
