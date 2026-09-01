"""
Agent Domain Layer (Agent-v1 Specification).
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from agent.core.models import AgentTask, AgentResult

class BaseAgent(ABC):
    """Abstract base class for domain agents."""

    def __init__(self, agent_version: str = "agent-v1") -> None:
        self.agent_version = agent_version

    @abstractmethod
    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Executes the given task and returns a structured AgentResult."""
        pass

class AgentV1(BaseAgent):
    """
    Agent-v1: First verified AgentScope implementation identity.
    Delegates task execution through an AgentScope adapter.
    """

    def __init__(self, adapter: Optional[Any] = None) -> None:
        super().__init__(agent_version="agent-v1")
        self.adapter = adapter

    async def execute_task(self, task: AgentTask) -> AgentResult:
        if self.adapter is None:
            raise RuntimeError("AgentV1 initialized without an execution adapter.")
        return await self.adapter.execute(task)
