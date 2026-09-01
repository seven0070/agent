"""
Test configuration loading and environment setting overrides.
"""

from agent.config import get_settings, Settings

def test_default_settings() -> None:
    settings = get_settings()
    assert settings.agent_env == "development"
    assert settings.log_level == "INFO"
    assert settings.agent_version == "0.1.0"

def test_settings_override(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("AGENT_VERSION", "0.2.0")

    settings = Settings()
    assert settings.agent_env == "test"
    assert settings.log_level == "DEBUG"
    assert settings.agent_version == "0.2.0"
