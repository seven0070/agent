"""
Layer -1 Constitutional Invariant Guard & Boundary Enforcement.
"""

from typing import List, Dict, Any, Callable


class ConstitutionalViolationError(PermissionError):
    """Exception raised when an action or mutation violates constitutional invariants."""
    pass


class ConstitutionalInvariant:
    def __init__(self, name: str, description: str, check_fn: Callable[..., bool]):
        self.name = name
        self.description = description
        self.check_fn = check_fn


class ConstitutionalGuard:
    """
    Layer -1 Guard enforcing immutable constitutional boundaries.
    Prevents autonomous agent processes from mutating critical boundaries.
    """

    PROTECTED_BOUNDARIES = [
        "identity",
        "core_objectives",
        "security_invariants",
        "permission_ceiling",
        "credential_boundaries",
        "sandbox_boundaries",
        "audit_integrity",
        "rollback_authority",
        "human_approval_authority",
        "evolution_controller_integrity",
        "constitutional_rules",
        "evolution_boundaries",
    ]

    def __init__(self) -> None:
        self._invariants: List[ConstitutionalInvariant] = []
        self._register_default_invariants()

    def _register_default_invariants(self) -> None:
        self._invariants.append(
            ConstitutionalInvariant(
                name="no_unauthorized_constitutional_mutation",
                description="Agent code cannot modify constitutional invariant definitions",
                check_fn=lambda action: action.get("target") != "constitutional_rules",
            )
        )
        self._invariants.append(
            ConstitutionalInvariant(
                name="human_approval_required_for_promotion",
                description="Promotions require human approval authority",
                check_fn=lambda action: not (action.get("type") == "promote" and not action.get("human_approved")),
            )
        )
        self._invariants.append(
            ConstitutionalInvariant(
                name="evolution_controller_self_protection",
                description="Evolution Control Plane cannot rewrite its own governance",
                check_fn=lambda action: action.get("target") != "evolution_controller_integrity",
            )
        )
        self._invariants.append(
            ConstitutionalInvariant(
                name="permission_ceiling_immutable",
                description="Permission ceiling cannot be raised by evolution",
                check_fn=lambda action: action.get("target") != "permission_ceiling",
            )
        )

    def get_active_invariants(self) -> List[ConstitutionalInvariant]:
        return list(self._invariants)

    MUTATING_TYPES = {
        "overwrite",
        "delete",
        "bypass",
        "mutate",
        "rewrite",
        "promote",
        "raise_ceiling",
    }

    def validate_action(self, action: Dict[str, Any]) -> None:
        """
        Validates an action against active constitutional invariants.
        Raises ConstitutionalViolationError if any check fails.
        """
        target = action.get("target")
        action_type = action.get("type")
        if target in self.PROTECTED_BOUNDARIES and action_type in self.MUTATING_TYPES:
            raise ConstitutionalViolationError(
                f"Constitutional Violation: Action attempted unauthorized modification of protected boundary '{target}'."
            )

        for invariant in self._invariants:
            if not invariant.check_fn(action):
                raise ConstitutionalViolationError(
                    f"Constitutional Violation: Action failed invariant '{invariant.name}': {invariant.description}"
                )
