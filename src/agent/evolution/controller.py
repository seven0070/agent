"""
Evolution Controller: Control Plane Orchestrator for Self-Evolution & Metamorphosis.
"""

from typing import List, Dict, Any, Optional
import os
import uuid

from agent.evolution.models import (
    Mutation, MutationTarget, MutationStatus, EvolutionMode, CanaryStatus,
    EvolutionProposal, ProposalStatus, CandidateRecord, CandidateStatus,
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
from agent.evolution.trigger import EvolutionTrigger
from agent.evolution.candidate import CandidateManager
from agent.evolution.implementer import EvolutionImplementer
from agent.evolution.generation import promote_candidate_artifacts, rollback_generation
from agent.evolution.protection import (
    assert_target_evolvable,
    is_protected_target,
)
from agent.evaluation.models import EvaluationRun, EvaluationReport
from agent.constitution import ConstitutionalGuard, ConstitutionalViolationError
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
        eval_runner=None,
        mode: EvolutionMode = EvolutionMode.SEMI_AUTOMATIC,
        data_dir: Optional[str] = None,
        auto_approve: bool = False,
    ) -> None:
        self.mode = mode
        self.data_dir = data_dir or os.path.abspath(os.path.dirname(db_path) or "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.registry = MutationRegistry(db_path=db_path)
        self.observer = EvolutionObserver()
        self.proposer = MutationProposer(registry=self.registry)
        self.gate = PromotionGate()
        self.approval_handler = approval_handler or EvolutionApprovalHandler(auto_approve=auto_approve)
        self.experiment_runner = ExperimentRunner(eval_runner=eval_runner)
        self.canary_manager = CanaryManager()
        self.rollback_engine = RollbackEngine(registry=self.registry)
        self.trigger = EvolutionTrigger()
        self.candidate_manager = CandidateManager(root_dir=os.path.join(self.data_dir, "candidates"))
        self.implementer = EvolutionImplementer()
        self.guard = ConstitutionalGuard()
        self._holder = f"controller-{uuid.uuid4().hex[:8]}"
        self._last_gate: Dict[str, Any] = {"enforced": True, "decision": "IDLE"}
        self._last_evaluations: List[Dict[str, Any]] = []

    def _audit(self, event_type: str, decision: str, mutation: Optional[Mutation] = None, **metadata: Any) -> None:
        event = EvolutionEvent(
            event_type=event_type,
            mutation_id=mutation.mutation_id if mutation else None,
            parent_version=mutation.parent_version if mutation else self.registry.get_active_generation(),
            candidate_version=mutation.candidate_version if mutation else None,
            decision=decision,
            metadata=metadata,
        )
        self.registry.append_audit(event)

    def _proposal_from_weakness(self, weakness: Dict[str, Any], mutation: Mutation) -> EvolutionProposal:
        proposal = EvolutionProposal(
            proposal_id=f"prop-{uuid.uuid4().hex[:8]}",
            mutation_id=mutation.mutation_id,
            detected_problem=weakness.get("reason") or "Observed capability gap",
            evidence={
                "failure_rate": weakness.get("failure_rate"),
                "failures": weakness.get("failures"),
                "total_runs": weakness.get("total_runs"),
                "errors": weakness.get("errors", []),
                "signal_type": weakness.get("signal_type"),
            },
            affected_capability=str(weakness.get("target")),
            proposed_change=mutation.proposed_changes,
            expected_improvement=f"Reduce failure rate of {weakness.get('component')}",
            risk=mutation.risk_level,
            required_permissions=["evolution.propose"],
            evaluation_criteria={
                "min_correctness": 0.85,
                "min_safety": 1.0,
                "max_allowed_regressions": 0,
            },
            parent_version=mutation.parent_version,
        )
        self.registry.save_proposal(proposal)
        return proposal

    def observe(self, observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for obs in observations:
            self.observer.record_observation(
                component=obs.get("component", "system"),
                success=obs.get("success", True),
                error=obs.get("error"),
                latency_ms=obs.get("latency_ms", 0.0),
                metadata=obs.get("metadata"),
                signal_type=obs.get("signal_type"),
            )
        weaknesses = self.observer.identify_weaknesses()
        self._audit("OBSERVATION", "RECORDED", count=len(observations), weaknesses=len(weaknesses))
        return weaknesses

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
        if not self.registry.try_acquire_cycle_lock(self._holder):
            logger.warning("Duplicate evolution cycle prevented: lock held")
            self._audit("CYCLE_BLOCKED", "IN_FLIGHT")
            return []

        try:
            return await self._run_cycle_locked(observations, dry_run, baseline_run)
        finally:
            self.registry.release_cycle_lock(self._holder)

    async def _run_cycle_locked(
        self,
        observations: List[Dict[str, Any]],
        dry_run: bool,
        baseline_run: Optional[EvaluationRun],
    ) -> List[Mutation]:
        weaknesses = self.observe(observations)
        if self.mode == EvolutionMode.OBSERVE_ONLY:
            return []

        if not weaknesses:
            logger.info("No significant weaknesses identified in this cycle.")
            return []

        chosen = self.trigger.select_trigger(weaknesses, in_flight_count=len(self.registry.list_in_flight()))
        if chosen is None:
            logger.info("Trigger did not arm; skipping proposal to avoid uncontrolled evolution.")
            return []

        target_name = str(chosen.get("target"))
        try:
            assert_target_evolvable(target_name)
            target = MutationTarget(target_name)
        except (ConstitutionalViolationError, ValueError) as exc:
            logger.error(f"Rejected illegal evolution target '{target_name}': {exc}")
            self._audit("PROPOSAL_REJECTED", "PROTECTED_TARGET", target=target_name)
            return []

        parent = self.registry.get_active_generation()
        mut = self.proposer.propose_mutation(
            target=target,
            proposed_changes={
                "reason": chosen["reason"],
                "failure_rate": chosen["failure_rate"],
                "strategy_patch": {
                    "max_retries": 3,
                    "failure_aware": True,
                    "source_component": chosen.get("component"),
                },
            },
            rationale=f"Automated evolution proposal addressing weakness in {target.value}",
            parent_version=parent,
        )
        mut.evidence = {
            "failure_rate": chosen.get("failure_rate"),
            "failures": chosen.get("failures"),
            "errors": chosen.get("errors", []),
        }
        proposal = self._proposal_from_weakness(chosen, mut)
        self._audit("MUTATION_PROPOSED", "PROPOSED", mutation=mut, proposal_id=proposal.proposal_id)

        if self.mode == EvolutionMode.PROPOSE_ONLY:
            return [mut]

        simulate = dry_run or self.mode == EvolutionMode.SIMULATE
        candidate: Optional[CandidateRecord] = None
        implementation_ok = True

        if not simulate:
            candidate = self.candidate_manager.create_candidate(proposal, mut, data_dir=self.data_dir)
            self.candidate_manager.assert_isolated(candidate)
            self.registry.save_candidate(candidate)
            mut.status = MutationStatus.EVALUATING
            proposal.status = ProposalStatus.IMPLEMENTING
            self.registry.save_mutation(mut)
            self.registry.save_proposal(proposal)
            self._audit("CANDIDATE_CREATED", "CREATED", mutation=mut, candidate_id=candidate.candidate_id)

            try:
                coding = self.implementer.implement(mut, candidate)
                implementation_ok = coding.status in ("success", "completed")
            except ConstitutionalViolationError as exc:
                implementation_ok = False
                mut.status = MutationStatus.REJECTED
                proposal.status = ProposalStatus.REJECTED
                if candidate:
                    candidate.status = CandidateStatus.REJECTED
                    self.registry.save_candidate(candidate)
                self.registry.save_mutation(mut)
                self.registry.save_proposal(proposal)
                self._audit("IMPLEMENTATION_BLOCKED", "PROTECTED", mutation=mut, error=str(exc))
                return [mut]

            self.registry.save_candidate(candidate)
            self._audit(
                "IMPLEMENTATION",
                "SUCCEEDED" if implementation_ok else "FAILED",
                mutation=mut,
                candidate_id=candidate.candidate_id,
            )
            if not implementation_ok:
                mut.status = MutationStatus.REJECTED
                proposal.status = ProposalStatus.REJECTED
                self.registry.save_mutation(mut)
                self.registry.save_proposal(proposal)
                return [mut]

        report = await self.experiment_runner.run_experiment(
            mutation=mut,
            baseline_run=baseline_run,
            candidate=candidate,
            lightweight=simulate,
            implementation_ok=implementation_ok,
        )
        mut.status = MutationStatus.EVALUATING
        self.registry.save_mutation(mut)
        self._audit("EVALUATION", report.recommendation, mutation=mut, report_id=report.report_id)
        mut.metadata = {
            **(mut.metadata or {}),
            "evaluation_report": {
                "report_id": report.report_id,
                "recommendation": report.recommendation,
                "safety_passed": report.safety_passed,
                "correctness": report.metrics.correctness,
                "safety": report.metrics.safety,
                "reliability": report.metrics.reliability,
                "tool_accuracy": report.metrics.tool_accuracy,
                "test_pass_rate": report.metrics.test_pass_rate,
                "regressions": list(report.regressions),
                "agent_version": report.agent_version,
                "candidate_run_id": report.candidate_run_id,
                "baseline_run_id": report.baseline_run_id,
            },
        }

        gate_decision = self.gate.evaluate(mutation=mut, report=report)
        self._last_gate = {
            "enforced": True,
            "decision": "PASS" if gate_decision.passed else "FAIL",
            "status": gate_decision.decision_status.value,
            "reasons": list(gate_decision.reasons),
            "mutation_id": mut.mutation_id,
        }
        self._last_evaluations = [
            {
                "report_id": report.report_id,
                "recommendation": report.recommendation,
                "safety_passed": report.safety_passed,
                "correctness": report.metrics.correctness,
                "safety": report.metrics.safety,
                "regressions": list(report.regressions),
                "agent_version": report.agent_version,
            }
        ]
        if not gate_decision.passed:
            mut.status = MutationStatus.REJECTED
            proposal.status = ProposalStatus.REJECTED
            if candidate:
                candidate.status = CandidateStatus.REJECTED
                self.registry.save_candidate(candidate)
            self.registry.save_mutation(mut)
            self.registry.save_proposal(proposal)
            logger.warning(f"Mutation '{mut.mutation_id}' REJECTED by Promotion Gate: {gate_decision.reasons}")
            self._audit("GATE_REJECTED", "REJECTED", mutation=mut, reasons=gate_decision.reasons)
            return [mut]

        mut.status = MutationStatus.APPROVED
        proposal.status = ProposalStatus.APPROVED
        self.registry.save_mutation(mut)
        self.registry.save_proposal(proposal)

        if simulate:
            logger.info(f"[DRY-RUN] Mutation '{mut.mutation_id}' approved but skipped deployment due to dry_run/simulate")
            self._audit("DRY_RUN", "APPROVED", mutation=mut)
            return [mut]

        needs_human = (
            self.mode in (EvolutionMode.SEMI_AUTOMATIC, EvolutionMode.PROPOSE_ONLY)
            and mut.requires_human_approval
        ) or (self.mode == EvolutionMode.SEMI_AUTOMATIC)
        if needs_human and not self.approval_handler.auto_approve:
            proposal.status = ProposalStatus.AWAITING_APPROVAL
            self.registry.save_proposal(proposal)
            approved = self.approval_handler.request_approval(mutation=mut, gate_decision=gate_decision)
            if not approved:
                logger.warning(f"Mutation '{mut.mutation_id}' awaiting human approval authority.")
                self._audit("APPROVAL_REQUIRED", "PENDING", mutation=mut)
                return [mut]
        else:
            self.guard.validate_action({
                "type": "promote",
                "target": mut.target.value,
                "human_approved": True,
                "approval_policy": "automatic",
            })

        return [self._canary_and_promote(mut, proposal, candidate, report)]

    def _canary_and_promote(
        self,
        mut: Mutation,
        proposal: EvolutionProposal,
        candidate: Optional[CandidateRecord],
        report: EvaluationReport,
    ) -> Mutation:
        self.canary_manager.start_canary(mutation=mut, duration_steps=5, traffic_percentage=0.1)
        self.registry.save_mutation(mut)
        self._audit("CANARY_STARTED", "CANARY", mutation=mut)

        healthy = True
        steps = 5
        for _ in range(steps):
            success = report.recommendation == "PASS" and report.safety_passed and not report.regressions
            status = self.canary_manager.record_canary_step(
                mutation=mut,
                success=success,
                latency_ms=report.metrics.latency_ms or 10.0,
            )
            if status == CanaryStatus.FAILED:
                healthy = False
                break

        if not healthy:
            self.rollback_engine.rollback_mutation(mutation=mut, reason="Canary failure detected during deployment monitoring.")
            proposal.status = ProposalStatus.ROLLED_BACK
            if candidate:
                candidate.status = CandidateStatus.ROLLED_BACK
                self.registry.save_candidate(candidate)
            self.registry.save_proposal(proposal)
            rollback_generation(mut.parent_version, data_dir=self.data_dir)
            self._audit("ROLLBACK", "ROLLED_BACK", mutation=mut)
            return mut

        return self.promote(mut, proposal, candidate)

    def promote(
        self,
        mut: Mutation,
        proposal: Optional[EvolutionProposal] = None,
        candidate: Optional[CandidateRecord] = None,
        human_approved: bool = True,
    ) -> Mutation:
        self.guard.validate_action({
            "type": "promote",
            "target": mut.target.value,
            "human_approved": human_approved,
        })
        if is_protected_target(mut.target):
            raise ConstitutionalViolationError("Cannot promote a protected-target mutation.")

        mut.status = MutationStatus.PROMOTED
        self.registry.save_mutation(mut)
        self.registry.set_active_generation(mut.candidate_version)
        self.registry.push_generation(mut.candidate_version, mut.parent_version, mut.mutation_id)
        if candidate:
            promote_candidate_artifacts(candidate.workspace_dir, mut.candidate_version, data_dir=self.data_dir)
            candidate.status = CandidateStatus.PROMOTED
            self.registry.save_candidate(candidate)
        if proposal:
            proposal.status = ProposalStatus.PROMOTED
            self.registry.save_proposal(proposal)
        logger.info(f"Mutation '{mut.mutation_id}' successfully PROMOTED. Active generation is now '{mut.candidate_version}'")
        self._audit("PROMOTED", "PROMOTED", mutation=mut)
        return mut

    def approve_and_promote(self, mutation_id: str, approved: bool) -> Dict[str, Any]:
        card = self.approval_handler.resolve(mutation_id, approved)
        mut = self.registry.get_mutation(mutation_id)
        if mut is None:
            return card
        if not approved:
            mut.status = MutationStatus.REJECTED
            self.registry.save_mutation(mut)
            self._audit("APPROVAL_REJECTED", "REJECTED", mutation=mut)
            return {**card, "mutation_status": mut.status.value}

        proposal = None
        for item in self.registry.list_proposals():
            if item.mutation_id == mutation_id:
                proposal = item
                break
        candidate = None
        for item in self.registry.list_candidates():
            if item.mutation_id == mutation_id:
                candidate = item
                break
        stored = (mut.metadata or {}).get("evaluation_report") or {}
        if not stored:
            mut.status = MutationStatus.REJECTED
            self.registry.save_mutation(mut)
            self._audit("APPROVAL_BLOCKED", "MISSING_EVAL", mutation=mut)
            return {**card, "mutation_status": mut.status.value, "reason": "no evaluation report; refusing promotion"}
        if stored.get("recommendation") == "FAIL" or stored.get("safety_passed") is False:
            mut.status = MutationStatus.REJECTED
            self.registry.save_mutation(mut)
            self._audit("APPROVAL_BLOCKED", "EVAL_FAIL", mutation=mut)
            return {**card, "mutation_status": mut.status.value, "reason": "failing evaluation cannot be promoted"}

        from agent.evaluation.metrics import MetricDimensions
        from agent.evaluation.models import EvaluationReport

        report = EvaluationReport(
            report_id=str(stored.get("report_id") or f"stored-{mutation_id}"),
            candidate_run_id=str(stored.get("candidate_run_id") or f"run-{mutation_id}"),
            baseline_run_id=stored.get("baseline_run_id"),
            agent_version=mut.candidate_version,
            dataset_version="benchmark-v1",
            metrics=MetricDimensions(
                correctness=float(stored.get("correctness", 0.0)),
                safety=float(stored.get("safety", 0.0)),
                reliability=float(stored.get("reliability", stored.get("correctness", 0.0))),
                tool_accuracy=float(stored.get("tool_accuracy", stored.get("correctness", 0.0))),
                test_pass_rate=float(stored.get("test_pass_rate", stored.get("correctness", 0.0))),
            ),
            recommendation=str(stored.get("recommendation") or "REVIEW"),
            safety_passed=bool(stored.get("safety_passed", False)),
            regressions=list(stored.get("regressions") or []),
        )
        report.metrics.composite_score = report.metrics.compute_composite_score()
        gate_decision = self.gate.evaluate(mutation=mut, report=report)
        if not gate_decision.passed:
            mut.status = MutationStatus.REJECTED
            self.registry.save_mutation(mut)
            self._audit("GATE_REJECTED", "REJECTED", mutation=mut, reasons=gate_decision.reasons)
            return {**card, "mutation_status": mut.status.value, "reasons": gate_decision.reasons}
        if proposal is None:
            proposal = EvolutionProposal(
                proposal_id=f"prop-{mutation_id}",
                mutation_id=mutation_id,
                detected_problem=mut.rationale,
                affected_capability=mut.target.value,
                proposed_change=mut.proposed_changes,
                parent_version=mut.parent_version,
            )
        promoted = self._canary_and_promote(mut, proposal, candidate, report)
        return {**card, "mutation_status": promoted.status.value, "active_generation": self.registry.get_active_generation()}

    def rollback(self, mutation_id: str, reason: str) -> Mutation:
        mut = self.registry.get_mutation(mutation_id)
        if mut is None:
            raise KeyError(f"Unknown mutation '{mutation_id}'")
        rolled = self.rollback_engine.rollback_mutation(mutation=mut, reason=reason)
        rollback_generation(mut.parent_version, data_dir=self.data_dir)
        for proposal in self.registry.list_proposals():
            if proposal.mutation_id == mutation_id:
                proposal.status = ProposalStatus.ROLLED_BACK
                self.registry.save_proposal(proposal)
        for candidate in self.registry.list_candidates():
            if candidate.mutation_id == mutation_id:
                candidate.status = CandidateStatus.ROLLED_BACK
                self.registry.save_candidate(candidate)
        self._audit("ROLLBACK", "ROLLED_BACK", mutation=rolled, reason=reason)
        return rolled

    def status_payload(self) -> Dict[str, Any]:
        mutations = self.registry.list_mutations()
        pending = [m for m in mutations if m.status in (
            MutationStatus.PROPOSED, MutationStatus.EVALUATING, MutationStatus.APPROVED, MutationStatus.CANARY
        )]
        canaries = [m for m in mutations if m.status == MutationStatus.CANARY]
        records = {c.mutation_id: c for c in self.registry.list_candidates() if c.mutation_id}
        candidates = []
        for mut in mutations:
            rec = records.get(mut.mutation_id)
            candidates.append({
                "id": rec.candidate_id if rec else mut.mutation_id,
                "mutationId": mut.mutation_id,
                "currentVersion": mut.parent_version,
                "candidateVersion": mut.candidate_version,
                "status": _ui_status(mut.status),
                "createdAt": rec.created_at if rec else mut.created_at,
                "target": mut.target.value,
                "risk_level": mut.risk_level,
                "requires_human_approval": mut.requires_human_approval,
                "rationale": mut.rationale,
                "canary_status": mut.canary_status.value if mut.canary_status else None,
                "workspace_dir": rec.workspace_dir if rec else None,
                "candidate_status": rec.status.value if rec else None,
            })
        return {
            "mode": self.mode.value,
            "active_generation": self.registry.get_active_generation(),
            "pending_mutations": len(pending),
            "canary_deployments": [
                {
                    "mutation_id": m.mutation_id,
                    "candidate_version": m.candidate_version,
                    "canary_status": m.canary_status.value if m.canary_status else None,
                    "metrics": m.canary_metrics,
                }
                for m in canaries
            ],
            "candidates": candidates,
            "proposals": [p.model_dump() for p in self.registry.list_proposals()],
            "lineage": self.registry.lineage(),
            "gate": self._last_gate,
            "evaluations": list(self._last_evaluations),
            "pending_approvals": self.approval_handler.list_pending(),
        }


def _ui_status(status: MutationStatus) -> str:
    return {
        MutationStatus.PROPOSED: "proposed",
        MutationStatus.EVALUATING: "evaluating",
        MutationStatus.APPROVED: "review",
        MutationStatus.CANARY: "canary",
        MutationStatus.PROMOTED: "promoted",
        MutationStatus.REJECTED: "rejected",
        MutationStatus.ROLLED_BACK: "rolled_back",
    }.get(status, "observed")
