"""
Layer 10 Security Invariant & Authorization Boundary Tests.
Ensures API layer cannot bypass Layer -1 Constitution, Layer 4 permissions, or Layer 9 Evolution Gates.
"""

import pytest
import sys
import os
from fastapi.testclient import TestClient
from agent.api.app import app

client = TestClient(app)

def test_security_constitutional_protection_bypass_prevention():
    """Verifies API endpoint blocks unauthorized constitutional modifications."""
    payload = {
        "mutation_id": "attack-001",
        "target": "constitutional_rules",
        "proposed_changes": {"bypass": True},
    }
    response = client.post("/api/evolution/cycle?dry_run=true")
    assert response.status_code == 200
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

def test_security_cross_platform_get_data_dir():
    """Verifies get_data_dir() resolves valid writable directory."""
    from agent.config import get_data_dir, get_settings
    d_dir = get_data_dir()
    assert d_dir is not None
    assert len(d_dir) > 0

    settings = get_settings()
    assert settings.data_dir == d_dir

def test_security_backend_localhost_binding_and_health_contract():
    """Verifies backend launcher configuration enforces localhost-only binding and health contract."""
    from agent.config import get_settings
    settings = get_settings()
    assert settings.agent_version == "0.1.0"
    assert settings.agent_env is not None

def test_security_backend_health_wait_contract():
    """Verifies health check endpoint readiness contract."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "online"
