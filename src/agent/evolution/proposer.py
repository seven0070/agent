"""
Mutation Proposer: Generates Versioned Mutation Proposals Based on Identified Weaknesses.
"""

from typing import Dict, Any, Optional
import uuid
from agent.evolution.models import Mutation, MutationTarget, MutationStatus
from agent.evolution.registry import MutationRegistry
from agent.logging import get_logger

logger = get_logger("agent.evolution.proposer")

class MutationProposer:
    """
    Proposes versioned mutation candidates based on performance evidence or identified weaknesses.
    """

    def __init__(self, registry: Optional[MutationRegistry] = None) -> None:
        self.registry = registry

    def propose_mutation(
        self,
        target: MutationTarget,
        proposed_changes: Dict[str, Any],
        rationale: str,
        parent_version: Optional[str] = None,
        risk_level: str = "LOW",
    ) -> Mutation:
        """
        Creates a new versioned mutation candidate card.
        """
        if parent_version is None:
            parent_version = self.registry.get_active_generation() if self.registry else "agent-v1"

        mut_id = f"mut-{uuid.uuid4().hex[:8]}"
        candidate_version = f"{target.value}-v{uuid.uuid4().hex[:4]}"

        requires_human = (risk_level.upper() in ["MEDIUM", "HIGH"]) or (target == MutationTarget.AGENT_COMPOSITION)

        mutation = Mutation(
            mutation_id=mut_id,
            target=target,
            parent_version=parent_version,
            candidate_version=candidate_version,
            proposed_changes=proposed_changes,
            rationale=rationale,
            risk_level=risk_level,
            status=MutationStatus.PROPOSED,
            requires_human_approval=requires_human,
        )

        logger.info(f"Proposed mutation '{mut_id}': target={target.value}, candidate={candidate_version}, risk={risk_level}")

        if self.registry:
            self.registry.save_mutation(mutation)

        return mutation
