"""
Layer -1 / Layer 9 protection: evolvable vs forbidden mutation surfaces.

The Evolution Control Plane may change HOW the agent accomplishes objectives.
It must not autonomously redefine WHAT it is allowed to do, and it must not
rewrite its own governance implementation.
"""

from __future__ import annotations

import os
from typing import FrozenSet, Iterable

from agent.constitution import ConstitutionalGuard, ConstitutionalViolationError
from agent.evolution.models import MutationTarget

PROTECTED_TARGETS: FrozenSet[str] = frozenset(
    {
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
    }
)

EVOLVABLE_TARGETS: FrozenSet[str] = frozenset(
    {
        MutationTarget.PLANNER_STRATEGY.value,
        MutationTarget.AGENT_ROUTING.value,
        MutationTarget.TOOL_SELECTION_POLICY.value,
        MutationTarget.SKILL_DEFINITIONS.value,
        MutationTarget.MEMORY_RETRIEVAL_STRATEGY.value,
        MutationTarget.MODEL_ROUTING.value,
        MutationTarget.AGENT_COMPOSITION.value,
    }
)

# Source fragments that candidate implementation is forbidden to write.
PROTECTED_PATH_FRAGMENTS: tuple[str, ...] = (
    f"{os.sep}constitution.py",
    f"{os.sep}evolution{os.sep}",
    "/constitution.py",
    "/evolution/",
    "\\constitution.py",
    "\\evolution\\",
    "agent/constitution.py",
    "agent\\constitution.py",
    "agent/evolution/",
    "agent\\evolution\\",
)


def normalize_target(target: str | MutationTarget) -> str:
    if isinstance(target, MutationTarget):
        return target.value
    return str(target)


def is_protected_target(target: str | MutationTarget) -> bool:
    value = normalize_target(target)
    if value in PROTECTED_TARGETS:
        return True
    if "constitutional" in value or "evolution_controller" in value:
        return True
    return False


def is_evolvable_target(target: str | MutationTarget) -> bool:
    value = normalize_target(target)
    return value in EVOLVABLE_TARGETS and not is_protected_target(value)


def is_protected_path(path: str) -> bool:
    lowered = path.replace("\\", "/").lower()
    for fragment in PROTECTED_PATH_FRAGMENTS:
        needle = fragment.replace("\\", "/").lower()
        if needle and needle in lowered:
            return True
    return False


def assert_target_evolvable(target: str | MutationTarget) -> None:
    value = normalize_target(target)
    if is_protected_target(value) or not is_evolvable_target(value):
        raise ConstitutionalViolationError(
            f"Constitutional Violation: Evolution cannot mutate protected or non-evolvable target '{value}'."
        )


def assert_candidate_write_allowed(path: str, candidate_root: str) -> None:
    """
    Candidate writes must stay inside the isolated candidate workspace and
    must not target protected governance source.
    """
    real_path = os.path.realpath(os.path.abspath(path))
    real_root = os.path.realpath(os.path.abspath(candidate_root))
    try:
        common = os.path.commonpath([real_root, real_path])
    except ValueError as exc:
        raise ConstitutionalViolationError(
            f"Evolution write escapes candidate workspace: {path}"
        ) from exc
    if common != real_root:
        raise ConstitutionalViolationError(
            f"Evolution write escapes candidate workspace: {path}"
        )
    if is_protected_path(real_path):
        raise ConstitutionalViolationError(
            f"Evolution Controller self-protection: refusing write to '{path}'."
        )


def validate_evolution_action(
    action_type: str,
    target: str | MutationTarget,
    human_approved: bool = False,
    guard: ConstitutionalGuard | None = None,
) -> None:
    value = normalize_target(target)
    active_guard = guard or ConstitutionalGuard()
    if is_protected_target(value):
        raise ConstitutionalViolationError(
            f"Constitutional Violation: Action '{action_type}' on protected target '{value}' is forbidden."
        )
    payload = {
        "type": action_type,
        "target": value,
        "human_approved": human_approved,
    }
    active_guard.validate_action(payload)


def forbidden_source_relpaths() -> Iterable[str]:
    return (
        "src/agent/constitution.py",
        "src/agent/evolution/controller.py",
        "src/agent/evolution/gate.py",
        "src/agent/evolution/protection.py",
        "src/agent/evolution/approval.py",
    )
