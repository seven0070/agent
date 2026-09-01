"""
Multi-Agent Subagent Delegation Hooks & Human Approval Interfaces.
Establishes Layer 6+ integration boundaries without prematurely building complex multi-agent runtimes or desktop UI elements.
"""

from typing import Dict, Any, Optional, Callable
from agent.orchestration.models import PlanTask, TaskState
from agent.capabilities.models import PermissionLevel
from agent.logging import get_logger

logger = get_logger("agent.orchestration.preparation")

class SubagentDelegateHook:
    """
    Hook interface preparing for future subagent/specialist delegation (Layer 6+ Jcode/Specialist Agents).
    """

    def __init__(self) -> None:
        self._specialist_delegates: Dict[str, Callable[[PlanTask], Any]] = {}

    def register_delegate(self, specialist_type: str, delegate_fn: Callable[[PlanTask], Any]) -> None:
        """Registers a delegate function for a specialist agent type (e.g. 'coding_agent')."""
        self._specialist_delegates[specialist_type] = delegate_fn

    def can_delegate(self, specialist_type: str) -> bool:
        """Checks if a delegate function is registered for the specialist type."""
        return specialist_type in self._specialist_delegates

    def delegate_task(self, specialist_type: str, task: PlanTask) -> Any:
        """Delegates task execution to a registered specialist delegate function."""
        if not self.can_delegate(specialist_type):
            raise KeyError(f"No delegate registered for specialist type '{specialist_type}'.")
        logger.info(f"Delegating task '{task.id}' to specialist '{specialist_type}'")
        return self._specialist_delegates[specialist_type](task)

class HumanApprovalHandler:
    """
    Handler interface preparing for human-in-the-loop task approval (Layer 10 UI/Desktop).
    """

    def __init__(self) -> None:
        self._auto_approve: bool = False

    def set_auto_approve(self, auto_approve: bool) -> None:
        """Configures auto-approval toggle for testing or autonomous execution modes."""
        self._auto_approve = auto_approve

    def request_approval(self, task: PlanTask, permission_level: PermissionLevel) -> bool:
        """
        Requests human authorization for tasks with REQUIRE_APPROVAL permission level.
        Returns boolean approval status.
        """
        logger.info(f"Human approval requested for task '{task.id}' (permission level: {permission_level.value})")
        if self._auto_approve:
            logger.info(f"Auto-approved task '{task.id}' based on policy setting")
            return True
        return False
