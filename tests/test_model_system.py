"""
Unit and Integration Tests for Layer 2 Intelligence / Model System.
"""

import pytest
import os
from agent.models import (
    ModelSpec,
    ModelCapabilities,
    ModelHealthStatus,
    ModelRegistry,
    ProviderCredentials,
    load_provider_credentials,
    check_local_model_readiness,
    ModelFactory,
    ModelRouter,
    MockChatModel,
)
from agent.core import AgentTask, AgentResult, AgentV1
from agent.integrations.agentscope import AgentScopeAdapter

def test_model_registry_operations() -> None:
    """Tests model registration, filtering, priority sorting, and health state updates."""
    registry = ModelRegistry()

    primary = ModelSpec(
        id="primary",
        provider="mock",
        model_name="mock-p1",
        priority=1,
    )
    fallback = ModelSpec(
        id="fallback-1",
        provider="mock",
        model_name="mock-f1",
        priority=2,
    )

    registry.register(fallback)
    registry.register(primary)

    # Priority sorting check (primary priority=1 comes before fallback priority=2)
    all_models = registry.list_all()
    assert len(all_models) == 2
    assert all_models[0].id == "primary"
    assert all_models[1].id == "fallback-1"

    # Disable model test
    registry.set_enabled("fallback-1", False)
    enabled_models = registry.list_enabled()
    assert len(enabled_models) == 1
    assert enabled_models[0].id == "primary"

    # Health status update test
    registry.update_health("primary", ModelHealthStatus.DEGRADED)
    assert registry.get("primary").health_status == ModelHealthStatus.DEGRADED

def test_provider_credentials_redaction(monkeypatch) -> None:
    """Verifies that provider credentials automatically redact secret values."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-key-12345")
    creds = load_provider_credentials()

    assert creds.get_key_value("openai") == "sk-secret-key-12345"

    safe_dict = creds.to_safe_dict()
    assert safe_dict["openai_api_key"] == "***REDACTED***"
    assert "sk-secret-key-12345" not in str(safe_dict)
    assert "sk-secret-key-12345" not in repr(creds)

def test_model_router_deterministic_selection() -> None:
    """Tests deterministic model selection based on capabilities and priority."""
    registry = ModelRegistry()

    m_standard = ModelSpec(
        id="standard",
        provider="mock",
        model_name="std-1",
        capabilities=ModelCapabilities(supports_vision=False),
        priority=1,
    )
    m_vision = ModelSpec(
        id="vision",
        provider="mock",
        model_name="vis-1",
        capabilities=ModelCapabilities(supports_vision=True),
        priority=2,
    )

    registry.register(m_standard)
    registry.register(m_vision)

    router = ModelRouter(registry=registry)

    # Without vision requirement -> selects standard (priority 1)
    selected_std = router.select_model()
    assert selected_std.id == "standard"

    # With vision requirement -> selects vision model
    selected_vis = router.select_model(required_capabilities={"supports_vision": True})
    assert selected_vis.id == "vision"

@pytest.mark.asyncio
async def test_fallback_engine_primary_succeeds() -> None:
    """Tests fallback engine when primary model succeeds directly."""
    registry = ModelRegistry()
    registry.register(ModelSpec(id="primary", provider="mock", model_name="p1", priority=1))
    registry.register(ModelSpec(id="fallback", provider="mock", model_name="f1", priority=2))

    router = ModelRouter(registry=registry)

    async def executor(spec: ModelSpec) -> str:
        return f"Response from {spec.id}"

    task = AgentTask(task_id="t-succ", prompt="Test Prompt")
    res = await router.execute_with_fallback(task, executor)

    assert res.status == "success"
    assert res.model_id == "primary"
    assert res.is_fallback is False
    assert res.output == "Response from primary"

@pytest.mark.asyncio
async def test_fallback_engine_primary_fails_fallback_succeeds() -> None:
    """Tests fallback engine when primary fails and fallback model succeeds."""
    registry = ModelRegistry()
    registry.register(ModelSpec(id="failing-primary", provider="mock", model_name="p1", priority=1))
    registry.register(ModelSpec(id="working-fallback", provider="mock", model_name="f1", priority=2))

    router = ModelRouter(registry=registry)

    async def executor(spec: ModelSpec) -> str:
        if spec.id == "failing-primary":
            raise ConnectionError("Simulated primary connection error")
        return "Response from working-fallback"

    task = AgentTask(task_id="t-fall", prompt="Test Prompt")
    res = await router.execute_with_fallback(task, executor)

    assert res.status == "success"
    assert res.model_id == "working-fallback"
    assert res.is_fallback is True
    assert res.output == "Response from working-fallback"
    assert registry.get("failing-primary").health_status == ModelHealthStatus.DEGRADED

@pytest.mark.asyncio
async def test_fallback_engine_all_fail() -> None:
    """Tests fallback engine when all primary and fallback candidates fail."""
    registry = ModelRegistry()
    registry.register(ModelSpec(id="fail-1", provider="mock", model_name="f1", priority=1))
    registry.register(ModelSpec(id="fail-2", provider="mock", model_name="f2", priority=2))

    router = ModelRouter(registry=registry, max_attempts=2)

    async def executor(spec: ModelSpec) -> str:
        raise RuntimeError(f"Failure on {spec.id}")

    task = AgentTask(task_id="t-all-fail", prompt="Test Prompt")
    res = await router.execute_with_fallback(task, executor)

    assert res.status == "error"
    assert "Failure on fail-2" in res.error

def test_local_model_readiness() -> None:
    """Tests local model endpoint readiness check."""
    status = check_local_model_readiness(host="http://localhost:11434")
    assert status["provider"] == "ollama"
    assert status["host"] == "http://localhost:11434"
    assert status["configured"] is True

@pytest.mark.asyncio
async def test_adapter_layer2_integration() -> None:
    """Tests AgentScopeAdapter integration with Layer 2 ModelRouter."""
    router = ModelRouter()
    adapter = AgentScopeAdapter(name="layer2-adapter-test", router=router)
    agent = AgentV1(adapter=adapter)

    task = AgentTask(task_id="t-layer2-integration", prompt="Integration Prompt")
    result: AgentResult = await agent.execute_task(task)

    assert result.status == "success"
    assert result.model_execution is not None
    assert result.model_execution.model_id == "primary"
    assert result.metadata["is_fallback"] is False
