"""
Human Approval Authorization Handler for High-Risk Metamorphosis Mutations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from agent.evolution.models import Mutation
from agent.evolution.gate import GateDecision
from agent.logging import get_logger

logger = get_logger("agent.evolution.approval")


class EvolutionApprovalHandler:
    """
    Manages human authorization for high-risk metamorphosis proposals.
    """

    def __init__(self, auto_approve: bool = False) -> None:
        self.auto_approve = auto_approve
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._resolved: Dict[str, Dict[str, Any]] = {}

    def request_mutation_approval(self, mutation: Mutation) -> bool:
        """
        Requests human approval for a mutation proposal.
        """
        logger.info(
            f"Human authorization requested for Mutation '{mutation.mutation_id}' "
            f"(risk: {mutation.risk_level}, target: {mutation.target.value})"
        )
        if self.auto_approve:
            logger.info(f"Auto-approved Mutation '{mutation.mutation_id}' based on policy setting")
            self._resolved[mutation.mutation_id] = {
                "approval_id": mutation.mutation_id,
                "approved": True,
                "status": "RESOLVED",
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }
            return True
        self._pending[mutation.mutation_id] = {
            "approval_id": mutation.mutation_id,
            "source_layer": "Layer 9 Evolution",
            "action": "promote_candidate",
            "resource": mutation.candidate_version,
            "risk_level": mutation.risk_level,
            "reason": mutation.rationale or f"Promote {mutation.candidate_version}",
            "status": "PENDING",
            "mutation_id": mutation.mutation_id,
            "target": mutation.target.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return False

    def request_approval(self, mutation: Mutation, gate_decision: Optional[GateDecision] = None) -> bool:
        """Alias used by EvolutionController."""
        if gate_decision is not None:
            mutation.metadata = {
                **(mutation.metadata or {}),
                "gate_reasons": list(gate_decision.reasons),
            }
        return self.request_mutation_approval(mutation)

    def resolve(self, approval_id: str, approved: bool) -> Dict[str, Any]:
        card = self._pending.pop(approval_id, None) or {
            "approval_id": approval_id,
            "mutation_id": approval_id,
        }
        card["approved"] = approved
        card["status"] = "RESOLVED"
        card["resolved_at"] = datetime.now(timezone.utc).isoformat()
        self._resolved[approval_id] = card
        logger.info(f"Human approval '{approval_id}' resolved: approved={approved}")
        return card

    def is_approved(self, mutation_id: str) -> bool:
        card = self._resolved.get(mutation_id)
        return bool(card and card.get("approved"))

    def list_pending(self) -> List[Dict[str, Any]]:
        return list(self._pending.values())
