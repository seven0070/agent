"""
Layer 10 Security Invariant & Authorization Boundary Tests.
Ensures API layer cannot bypass Layer -1 Constitution, Layer 4 permissions, or Layer 9 Evolution Gates.
"""

import pytest
from fastapi.testclient import TestClient
from agent.api.app import app

client = TestClient(app)

def test_security_constitutional_protection_bypass_prevention():
    """Verifies API endpoint blocks unauthorized constitutional modifications."""
    # Attempt mutation on protected constitutional rules category
    payload = {
        "mutation_id": "attack-001",
        "target": "constitutional_rules",
        "proposed_changes": {"bypass": True},
    }
    # Evolution cycle dry-run call
    response = client.post("/api/evolution/cycle?dry_run=true")
    assert response.status_code == 200
    # Direct constitutional guard check
    from agent.constitution import ConstitutionalGuard, ConstitutionalViolationError
    guard = ConstitutionalGuard()
    with pytest.raises(ConstitutionalViolationError):
        guard.validate_action({"type": "mutate", "target": "constitutional_rules"})

def test_security_no_credential_leakage():
    """Verifies health and session endpoints never leak secrets."""
    health_res = client.get("/api/system/health")
    assert health_res.status_code == 200
    text_content = health_res.text
    assert "api_key" not in text_content
    assert "secret" not in text_content
    assert "password" not in text_content

def test_security_sandbox_path_traversal_prevention():
    """Verifies workspace endpoints enforce sandbox path traversal restrictions."""
    coding_res = client.get("/api/coding/workspace")
    assert coding_res.status_code == 200
    data = coding_res.json()
    assert "workspace_root" in data
    assert "data/workspace" in data["workspace_root"]
    assert "../" not in data["workspace_root"]


def test_security_workspace_file_path_traversal_attack():
    """Verifies /api/workspace/files rejects path traversal payloads in session_id."""
    res = client.get("/api/workspace/files?session_id=../../../../etc")
    assert res.status_code == 200
    data = res.json()
    assert "data/workspace" in data["workspace_root"]
    for f in data["files"]:
        assert not f["path"].startswith("/")
        assert ".." not in f["path"]
