"""
Human Approval Authorization Handler for High-Risk Metamorphosis Mutations.
"""

from typing import Dict, Any, Optional
from agent.evolution.models import Mutation
from agent.logging import get_logger

logger = get_logger("agent.evolution.approval")

class EvolutionApprovalHandler:
    """
    Manages human authorization for high-risk metamorphosis proposals.
    """

    def __init__(self, auto_approve: bool = False) -> None:
        self.auto_approve = auto_approve

    def request_mutation_approval(self, mutation: Mutation) -> bool:
        """
        Requests human approval for a mutation proposal.
        """
        logger.info(f"Human authorization requested for Mutation '{mutation.id}' (risk: {mutation.risk_level}, target: {mutation.target.value})")
        if self.auto_approve:
            logger.info(f"Auto-approved Mutation '{mutation.id}' based on policy setting")
            return True
        return False
