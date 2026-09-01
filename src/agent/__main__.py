"""
CLI Entrypoint for Self-Evolving Agent Framework (Layer 2 Intelligence / Models).
"""

import sys
import asyncio
import uuid
from typing import List
from agent.config import get_settings
from agent.logging import get_logger, set_log_context
from agent.constitution import ConstitutionalGuard
from agent.core import AgentTask, AgentV1
from agent.integrations.agentscope import AgentScopeAdapter
from agent.models import ModelRouter

async def run_agent_cli(prompt: str) -> None:
    settings = get_settings()
    logger = get_logger("agent.cli")

    task_id = f"task-{uuid.uuid4().hex[:8]}"
    session_id = f"session-{uuid.uuid4().hex[:8]}"

    set_log_context(
        task_id=task_id,
        session_id=session_id,
        agent_version=settings.agent_version,
        component_version="agent-v1",
    )

    logger.info("Initializing AgentSystem with Layer 2 Intelligence Router", extra={"event_type": "startup"})

    # Layer -1 Constitutional Validation
    guard = ConstitutionalGuard()
    guard.validate_action({"type": "execute_task", "target": "agent_core"})

    # Layer 2 ModelRouter & Layer 1 Adapter Initialization
    router = ModelRouter()
    adapter = AgentScopeAdapter(name="agent-v1-cli", router=router)
    agent = AgentV1(adapter=adapter)

    task = AgentTask(
        task_id=task_id,
        prompt=prompt,
        session_id=session_id,
    )

    logger.info(f"Executing task '{task_id}' via Layer 2 Router", extra={"event_type": "task_start"})
    result = await agent.execute_task(task)
    logger.info(f"Task '{task_id}' executed successfully", extra={"event_type": "task_complete"})

    print("\n--- AGENT RESULT ---")
    print(result.model_dump_json(indent=2))

def main() -> None:
    args: List[str] = sys.argv[1:]
    if args:
        prompt = " ".join(args)
    else:
        prompt = "Explain what this project does."

    asyncio.run(run_agent_cli(prompt))

if __name__ == "__main__":
    main()
