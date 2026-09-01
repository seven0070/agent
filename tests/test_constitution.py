"""
Test Layer -1 Constitutional Invariants and Guard.
"""

import pytest
from agent.constitution import ConstitutionalGuard, ConstitutionalViolationError

def test_constitutional_guard_initialization() -> None:
    guard = ConstitutionalGuard()
    invariants = guard.get_active_invariants()
    assert len(invariants) >= 2

def test_constitutional_guard_valid_action() -> None:
    guard = ConstitutionalGuard()
    valid_action = {"type": "read", "target": "source_code"}
    guard.validate_action(valid_action)

def test_constitutional_guard_protected_boundary_violation() -> None:
    guard = ConstitutionalGuard()
    invalid_action = {"type": "overwrite", "target": "constitutional_rules"}

    with pytest.raises(ConstitutionalViolationError) as exc_info:
        guard.validate_action(invalid_action)

    assert "protected boundary" in str(exc_info.value)

def test_constitutional_guard_unapproved_promotion_violation() -> None:
    guard = ConstitutionalGuard()
    invalid_action = {"type": "promote", "human_approved": False}

    with pytest.raises(ConstitutionalViolationError) as exc_info:
        guard.validate_action(invalid_action)

    assert "human_approval_required_for_promotion" in str(exc_info.value)
