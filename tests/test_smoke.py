"""
Smoke test verifying basic project initialization and component integration.
"""

from agent.config import get_settings
from agent.logging import get_logger
from agent.constitution import ConstitutionalGuard
from agent.versioning import VersionRegistry, ComponentVersionSpec

def test_smoke_initialization() -> None:
    settings = get_settings()
    assert settings.agent_version == "0.1.0"

    logger = get_logger("smoke.test")
    assert logger is not None

    guard = ConstitutionalGuard()
    assert len(guard.get_active_invariants()) > 0

    registry = VersionRegistry()
    registry.register(
        ComponentVersionSpec(component_type="core", name="foundation", version=settings.agent_version)
    )
    assert len(registry.list_components()) == 1
