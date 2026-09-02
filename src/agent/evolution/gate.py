"""
Promotion Gate Enforcing Layer -1 Constitutional Invariants and Layer 8 Evaluation Thresholds.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from agent.evolution.models import Mutation, MutationStatus, MutationTarget
from agent.evolution.protection import PROTECTED_TARGETS, is_protected_target
from agent.evaluation.models import EvaluationReport
from agent.evaluation.metrics import EvaluationThresholds
from agent.constitution import ConstitutionalGuard, ConstitutionalViolationError
from agent.logging import get_logger

logger = get_logger("agent.evolution.gate")


class GateDecision(BaseModel):
    """Structured decision card returned by PromotionGate."""
    passed: bool = Field(..., description="Whether mutation passed promotion gate")
    decision_status: MutationStatus = Field(..., description="Resulting status (APPROVED, CANARY, REJECTED)")
    reasons: List[str] = Field(default_factory=list, description="List of decision reasons or violation messages")


class PromotionGate:
    """
    Control-plane promotion gate enforcing Layer -1 constitutional protections and Layer 8 evaluation thresholds.
    """

    PROTECTED_TARGETS = list(PROTECTED_TARGETS)

    def __init__(
        self,
        guard: Optional[ConstitutionalGuard] = None,
        thresholds: Optional[EvaluationThresholds] = None,
    ) -> None:
        self.guard = guard or ConstitutionalGuard()
        self.thresholds = thresholds or EvaluationThresholds()

    def evaluate(self, mutation: Mutation, report: EvaluationReport) -> GateDecision:
        """
        Evaluates mutation proposal and Layer 8 report against constitutional invariants and thresholds.
        """
        reasons: List[str] = []
        target_str = mutation.target.value if isinstance(mutation.target, MutationTarget) else str(mutation.target)

        if is_protected_target(target_str) or target_str in self.PROTECTED_TARGETS or "constitutional" in target_str:
            msg = f"Layer -1 Constitutional Protection Violation: Mutation '{mutation.mutation_id}' attempted unauthorized modification of protected category '{target_str}'."
            logger.error(msg)
            return GateDecision(passed=False, decision_status=MutationStatus.REJECTED, reasons=[msg])

        try:
            self.guard.validate_action({"type": "mutate", "target": target_str})
        except ConstitutionalViolationError as cve:
            msg = f"Layer -1 Constitutional Violation: {str(cve)}"
            logger.error(msg)
            return GateDecision(passed=False, decision_status=MutationStatus.REJECTED, reasons=[msg])

        metrics = report.metrics
        if metrics.safety < self.thresholds.min_safety:
            msg = f"PROMOTION REJECTED: Safety score ({metrics.safety}) below required threshold ({self.thresholds.min_safety})."
            reasons.append(msg)

        if len(report.regressions) > self.thresholds.max_allowed_regressions:
            msg = f"PROMOTION REJECTED: Candidate introduced {len(report.regressions)} regressions."
            reasons.append(msg)

        if metrics.correctness < self.thresholds.min_correctness:
            msg = f"PROMOTION REJECTED: Candidate correctness ({metrics.correctness}) below threshold ({self.thresholds.min_correctness})."
            reasons.append(msg)

        if report.recommendation == "FAIL" or reasons:
            if not reasons:
                reasons.append("PROMOTION REJECTED: Layer 8 report recommendation is FAIL.")
            logger.error(f"Promotion gate rejected mutation '{mutation.mutation_id}': {reasons}")
            return GateDecision(passed=False, decision_status=MutationStatus.REJECTED, reasons=reasons)

        if mutation.risk_level == "HIGH" or report.recommendation == "REVIEW":
            msg = f"PROMOTION APPROVED FOR CANARY: Mutation '{mutation.mutation_id}' requires canary deployment."
            logger.info(msg)
            return GateDecision(passed=True, decision_status=MutationStatus.CANARY, reasons=[msg])

        msg = f"PROMOTION APPROVED: Mutation '{mutation.mutation_id}' passed all constitutional and performance checks."
        logger.info(msg)
        return GateDecision(passed=True, decision_status=MutationStatus.APPROVED, reasons=[msg])

    def evaluate_promotion(self, mutation: Mutation, report: EvaluationReport) -> MutationStatus:
        decision = self.evaluate(mutation=mutation, report=report)
        return decision.decision_status
