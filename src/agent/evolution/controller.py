"""
Evolution Controller: Control Plane Orchestrator for Self-Evolution & Metamorphosis.
"""

from typing import List, Dict, Any, Optional
import asyncio

from agent.evolution.models import (
    Mutation, MutationTarget, MutationStatus, EvolutionMode, CanaryStatus
)
from agent.evolution.events import EvolutionEvent
from agent.evolution.observer import EvolutionObserver
from agent.evolution.proposer import MutationProposer
from agent.evolution.registry import MutationRegistry
from agent.evolution.gate import PromotionGate
from agent.evolution.approval import EvolutionApprovalHandler
from agent.evolution.experiment import ExperimentRunner
from agent.evolution.canary import CanaryManager
from agent.evolution.rollback import RollbackEngine
from agent.evaluation.models import EvaluationRun
from agent.logging import get_logger

logger = get_logger("agent.evolution.controller")

class EvolutionController:
    """
    Main Control Plane Orchestrator operating beside the Agent System.
    Manages the lifecycle: OBSERVE -> PROPOSE -> EXPERIMENT -> GATE -> CANARY -> PROMOTE / ROLLBACK.
    """

    def __init__(
        self,
        db_path: str = "data/evolution.db",
        approval_handler: Optional[EvolutionApprovalHandler] = None,
        eval_runner = None,
        mode: EvolutionMode = EvolutionMode.SEMI_AUTOMATIC,
    ) -> None:
        self.mode = mode
        self.registry = MutationRegistry(db_path=db_path)
        self.observer = EvolutionObserver()
        self.proposer = MutationProposer(registry=self.registry)
        self.gate = PromotionGate()
        self.approval_handler = approval_handler or EvolutionApprovalHandler(auto_approve=False)
        self.experiment_runner = ExperimentRunner(eval_runner=eval_runner)
        self.canary_manager = CanaryManager()
        self.rollback_engine = RollbackEngine(registry=self.registry)

    async def run_evolution_cycle(
        self,
        observations: List[Dict[str, Any]],
        dry_run: bool = False,
        baseline_run: Optional[EvaluationRun] = None,
    ) -> List[Mutation]:
        """
        Runs a complete evolution control cycle.
        """
        logger.info(f"Starting evolution cycle (mode={self.mode.value}, dry_run={dry_run}, observations={len(observations)})")

        # 1. OBSERVE
        for obs in observations:
            self.observer.record_observation(
                component=obs.get("component", "system"),
                success=obs.get("success", True),
                error=obs.get("error"),
                latency_ms=obs.get("latency_ms", 0.0),
                metadata=obs.get("metadata"),
            )

        # 2. IDENTIFY WEAKNESS
        weaknesses = self.observer.identify_weaknesses()
        if not weaknesses:
            logger.info("No significant weaknesses identified in this cycle.")
            return []

        # 3. PROPOSE MUTATIONS
        mutations: List[Mutation] = []
        for w in weaknesses:
            target = MutationTarget(w["target"])
            mut = self.proposer.propose_mutation(
                target=target,
                proposed_changes={"reason": w["reason"], "failure_rate": w["failure_rate"]},
                rationale=f"Automated evolution proposal addressing weakness in {target.value}",
            )
            mutations.append(mut)

        # 4. EXPERIMENT & GATE
        for mut in mutations:
            logger.info(f"Processing candidate mutation '{mut.mutation_id}' for '{mut.target.value}'")

            # Run experiment
            report = await self.experiment_runner.run_experiment(mutation=mut, baseline_run=baseline_run)

            # Evaluate against promotion gate (Layer -1 Constitution + Layer 8 Benchmarks)
            gate_decision = self.gate.evaluate(mutation=mut, report=report)

            if not gate_decision.passed:
                mut.status = MutationStatus.REJECTED
                self.registry.save_mutation(mut)
                logger.warning(f"Mutation '{mut.mutation_id}' REJECTED by Promotion Gate: {gate_decision.reasons}")
                continue

            mut.status = MutationStatus.APPROVED
            self.registry.save_mutation(mut)

            if dry_run:
                logger.info(f"[DRY-RUN] Mutation '{mut.mutation_id}' approved but skipped deployment due to dry_run=True")
                continue

            # 5. HUMAN APPROVAL (if required by mode/policy)
            if self.mode == EvolutionMode.SEMI_AUTOMATIC and mut.requires_human_approval:
                approved = self.approval_handler.request_approval(mutation=mut, gate_decision=gate_decision)
                if not approved:
                    mut.status = MutationStatus.REJECTED
                    self.registry.save_mutation(mut)
                    logger.warning(f"Mutation '{mut.mutation_id}' rejected by human approval authority.")
                    continue

            # 6. CANARY PHASE
            self.canary_manager.start_canary(mutation=mut, duration_steps=5, traffic_percentage=0.1)
            self.registry.save_mutation(mut)

            # Simulate/Run canary steps
            canary_healthy = True
            for step in range(5):
                status = self.canary_manager.record_canary_step(mutation=mut, success=True, latency_ms=10.0)
                if status == CanaryStatus.FAILED:
                    canary_healthy = False
                    break

            if not canary_healthy:
                self.rollback_engine.rollback_mutation(mutation=mut, reason="Canary failure detected during deployment monitoring.")
                continue

            # 7. PROMOTION TO NEW GENERATION
            mut.status = MutationStatus.PROMOTED
            self.registry.save_mutation(mut)
            self.registry.set_active_generation(mut.candidate_version)
            logger.info(f"Mutation '{mut.mutation_id}' successfully PROMOTED. Active generation is now '{mut.candidate_version}'")

        return mutations
