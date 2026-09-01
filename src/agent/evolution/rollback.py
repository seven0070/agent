"""
Rollback Engine for Restoring Baseline Generations upon Regression.
"""

from typing import Optional
from agent.evolution.models import Mutation, MutationStatus, CanaryStatus
from agent.evolution.registry import MutationRegistry
from agent.logging import get_logger

logger = get_logger("agent.evolution.rollback")

class RollbackEngine:
    """
    Handles immediate rollback of canary or promoted candidates back to parent baseline.
    """

    def __init__(self, registry: MutationRegistry) -> None:
        self.registry = registry

    def rollback_mutation(self, mutation: Mutation, reason: str) -> Mutation:
        """
        Rolls back a mutation to its parent baseline version.
        """
        logger.warning(f"Initiating rollback for mutation '{mutation.mutation_id}' ({mutation.candidate_version}): {reason}")
        mutation.status = MutationStatus.ROLLED_BACK
        if mutation.canary_status == CanaryStatus.HEALTHY or mutation.canary_status == CanaryStatus.FAILED:
            mutation.canary_status = CanaryStatus.FAILED

        # Update registry
        self.registry.save_mutation(mutation)

        # Set active generation back to parent version if active was this candidate
        active = self.registry.get_active_generation()
        if active == mutation.candidate_version:
            self.registry.set_active_generation(mutation.parent_version)
            logger.info(f"Active generation restored to parent baseline '{mutation.parent_version}'")

        return mutation
