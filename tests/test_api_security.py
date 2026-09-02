"""
Layer 10 Security Invariant & Authorization Boundary Tests.
"""

import os
from fastapi.testclient import TestClient
from agent.api.app import app
from agent.api.main import main as standalone_main_exists  # noqa: F401
import agent.api.main as standalone_main
from agent.config import get_data_dir, get_settings
from agent.constitution import ConstitutionalGuard, ConstitutionalViolationError
import pytest

client = TestClient(app)


def test_security_constitutional_protection_bypass_prevention():
    payload = {
        "target": "constitutional_rules",
        "observations": [
            {"component": "constitutional_rules", "success": False, "error": "bypass"},
            {"component": "constitutional_rules", "success": False, "error": "bypass"},
        ],
        "proposed_changes": {"bypass": True},
    }
    response = client.post("/api/evolution/cycle?dry_run=true", json=payload)
    assert response.status_code == 403
    guard = ConstitutionalGuard()
    with pytest.raises(ConstitutionalViolationError):
        guard.validate_action({"type": "mutate", "target": "constitutional_rules"})


def test_security_no_credential_leakage():
    health_res = client.get("/api/system/health")
    assert health_res.status_code == 200
    text_content = health_res.text.lower()
    assert "api_key" not in text_content
    assert "secret" not in text_content
    assert "password" not in text_content


def test_security_sandbox_path_traversal_prevention():
    coding_res = client.get("/api/coding/workspace")
    assert coding_res.status_code == 200
    data = coding_res.json()
    assert "workspace_root" in data
    assert "workspace" in data["workspace_root"]
    assert "../" not in data["workspace_root"]


def test_security_workspace_file_path_traversal_attack():
    res = client.get("/api/workspace/files?session_id=../../../../etc")
    assert res.status_code == 200
    data = res.json()
    assert "workspace" in data["workspace_root"]
    for f in data["files"]:
        assert not f["path"].startswith("/")
        assert ".." not in f["path"]


def test_security_cross_platform_get_data_dir():
    d_dir = get_data_dir()
    assert d_dir is not None
    assert len(d_dir) > 0
    settings = get_settings()
    assert settings.data_dir == d_dir


def test_security_backend_localhost_binding_and_health_contract():
    source = open(os.path.join(os.path.dirname(__file__), "..", "src", "agent", "api", "main.py"), encoding="utf-8").read()
    assert 'host = "127.0.0.1"' in source
    settings = get_settings()
    assert settings.agent_version == "0.1.0"


def test_security_backend_health_wait_contract():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "online"


def test_security_standalone_main_entrypoint():
    assert hasattr(standalone_main, "main")


def test_security_live_cycle_requires_observations():
    res = client.post("/api/evolution/cycle?dry_run=false")
    assert res.status_code == 400
