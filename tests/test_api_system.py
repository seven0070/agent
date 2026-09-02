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
    assert data["layers"]["evolution"] == "active"

def test_session_lifecycle_api():
    create_res = client.post("/api/sessions", json={"title": "Test API Session"})
    assert create_res.status_code == 200
    sess = create_res.json()
    sid = sess["session_id"]
    assert sid.startswith("sess-")
    assert sess["title"] == "Test API Session"

    list_res = client.get("/api/sessions")
    assert list_res.status_code == 200
    sessions = list_res.json()
    assert any(s["session_id"] == sid for s in sessions)

    get_res = client.get(f"/api/sessions/{sid}")
    assert get_res.status_code == 200
    assert get_res.json()["session_id"] == sid

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
        joined = "\n".join(events)
        assert "MESSAGE_STARTED" in joined
        assert "MESSAGE_COMPLETED" in joined
        assert "PLAN_CREATED" in joined


def test_domain_api_endpoints():
    chat_payload = {"session_id": "domain-sess", "prompt": "Calculate 9 + 1"}
    with client.stream("POST", "/api/chat/stream", json=chat_payload) as response:
        assert response.status_code == 200
        list(response.iter_lines())

    plan_res = client.get("/api/plans/plan-001")
    assert plan_res.status_code == 200
    assert plan_res.json()["plan_id"] == "plan-001"
    assert plan_res.json()["status"] in ("completed", "failed", "active", "blocked")

    appr_res = client.get("/api/approvals")
    assert appr_res.status_code == 200
    assert isinstance(appr_res.json(), list)

    tools_res = client.get("/api/tools")
    assert tools_res.status_code == 200
    assert any(t["tool_id"] == "calculator-v1" for t in tools_res.json())

    coding_res = client.get("/api/coding/workspace")
    assert coding_res.status_code == 200
    assert coding_res.json()["status"] == "idle"

    evo_res = client.get("/api/evolution/status")
    assert evo_res.status_code == 200
    assert evo_res.json()["active_generation"]

    audit_res = client.get("/api/audit/logs")
    assert audit_res.status_code == 200
    assert len(audit_res.json()) >= 1

    settings_res = client.get("/api/settings")
    assert settings_res.status_code == 200
    assert settings_res.json()["constitution_locked"] is True

    trust_res = client.get("/api/trust/constitution")
    assert trust_res.status_code == 200
    assert trust_res.json()["protected"] is True
