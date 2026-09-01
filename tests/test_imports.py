"""
Test package and module imports.
"""

def test_package_imports() -> None:
    import agent
    from agent.config import get_settings, Settings
    from agent.logging import get_logger, set_log_context
    from agent.versioning import ComponentVersionSpec, VersionRegistry
    from agent.constitution import ConstitutionalGuard, ConstitutionalViolationError

    assert agent.__version__ == "0.1.0"
    assert agent.__layer__ == 0
    assert agent.__layer_name__ == "Foundation"
