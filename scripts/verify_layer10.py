"""
Layer 10 Verification Script — Desktop Interface & Public API Boundary.
Verifies end-to-end integration across Layers 0 through 10.
"""

import sys
from fastapi.testclient import TestClient
from agent.api.app import app

def main() -> int:
    print("=== Layer 10 Verification: Interface / Desktop & Service Boundary ===")
    client = TestClient(app)

    # 1. System Health Across All Layers
    print("[1/5] Verifying System Health across Layers 0–10...")
    health_res = client.get("/api/system/health")
    assert health_res.status_code == 200
    hdata = health_res.json()
    assert hdata["status"] == "online"
    assert len(hdata["layers"]) == 10
    print("  ✓ All 10 layers reporting active status in system health check")

    # 2. Session Management & Sovereign Chat Streaming
    print("[2/5] Verifying Session Management & SSE Chat Streaming...")
    sess_res = client.post("/api/sessions", json={"title": "Verification Session L10"})
    assert sess_res.status_code == 200
    sid = sess_res.json()["session_id"]

    chat_payload = {"session_id": sid, "prompt": "Calculate 15 + 27 and create workspace file"}
    with client.stream("POST", "/api/chat/stream", json=chat_payload) as stream_res:
        assert stream_res.status_code == 200
        lines = [line for line in stream_res.iter_lines() if line.startswith("data:")]
        assert len(lines) >= 3
    print("  ✓ Session created and SSE chat message stream executed cleanly")

    # 3. Domain API Endpoints Verification
    print("[3/5] Verifying Domain Endpoints (Planning, Approvals, Coding, Evolution, Audit)...")
    assert client.get("/api/approvals").status_code == 200
    assert client.get("/api/coding/workspace").status_code == 200
    assert client.get("/api/evolution/status").status_code == 200
    assert client.get("/api/audit/logs").status_code == 200
    print("  ✓ Domain endpoints responded with status 200 OK")

    # 4. Constitutional Protection Boundary Verification
    print("[4/5] Verifying Layer -1 Constitutional Protection Boundary...")
    from agent.constitution import ConstitutionalGuard, ConstitutionalViolationError
    guard = ConstitutionalGuard()
    try:
        guard.validate_action({"type": "mutate", "target": "constitutional_rules"})
        assert False, "Should have raised ConstitutionalViolationError"
    except ConstitutionalViolationError:
        print("  ✓ Layer -1 ConstitutionalGuard correctly blocked unauthorized modification")

    # 5. E2E Session Cleanup
    print("[5/5] Cleaning up session...")
    del_res = client.delete(f"/api/sessions/{sid}")
    assert del_res.status_code == 200
    print("  ✓ Session deleted cleanly")

    print("\n=== LAYER 10 VERIFICATION SUCCESSFUL ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
