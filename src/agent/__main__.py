"""
CLI / Main Entrypoint for Layer 0 Agent System.
"""

import sys
from agent.config import get_settings
from agent.logging import get_logger, set_log_context
from agent.constitution import ConstitutionalGuard

def main() -> None:
    settings = get_settings()
    logger = get_logger("agent.main")

    set_log_context(
        task_id="init-task-0",
        session_id="init-session-0",
        agent_version=settings.agent_version,
        component_version="foundation-v0.1.0",
    )

    logger.info("Initializing Agent System — Layer 0 Foundation", extra={"event_type": "system_startup"})

    # Initialize Layer -1 Constitutional Guard
    guard = ConstitutionalGuard()
    invariants = guard.get_active_invariants()
    logger.info(f"Constitutional Guard initialized with {len(invariants)} invariants", extra={"event_type": "constitution_check"})

    print(f"Agent Framework Layer 0 (v{settings.agent_version}) initialized successfully.")
    print(f"Active Environment: {settings.agent_env}")
    print(f"Constitutional Rules Enforced: {len(invariants)}")

if __name__ == "__main__":
    main()
