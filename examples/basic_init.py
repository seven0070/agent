"""
Example showing basic Layer 0 initialization.
"""

from agent.config import get_settings
from agent.logging import get_logger, set_log_context
from agent.constitution import ConstitutionalGuard
from agent.versioning import VersionRegistry, ComponentVersionSpec

def run_example() -> None:
    settings = get_settings()
    logger = get_logger("example.basic_init")

    set_log_context(
        task_id="example-task-1",
        session_id="example-session-1",
        agent_version=settings.agent_version,
        component_version="foundation-v0.1.0",
    )

    logger.info("Starting Basic Layer 0 Initialization Example")

    guard = ConstitutionalGuard()
    logger.info(f"Guard initialized with {len(guard.get_active_invariants())} active invariants")

    registry = VersionRegistry()
    spec = ComponentVersionSpec(
        component_type="foundation",
        name="layer0-base",
        version="0.1.0",
        metadata={"author": "Jules"},
    )
    registry.register(spec)

    logger.info(f"Registered Component: {spec.get_full_identifier()}")
    print("Layer 0 Basic Initialization Example completed successfully.")

if __name__ == "__main__":
    run_example()
