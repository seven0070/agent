# Layer 9 — Evolution Control Plane

## Overview
Layer 9 implements the metamorphosis control plane (`EvolutionController`). It operates as an **independent control plane beside the agent system**—observing performance, identifying weaknesses, generating structured mutation proposals, implementing isolated candidates through Jcode, testing them in the Layer 7 sandbox, evaluating them with Layer 8, enforcing Layer -1 constitutional protections, and governing promotion, canary monitoring, or automatic rollback.

## Core Architectural Principle
The Evolution Controller is **NOT** an execution or reasoning layer inside the agent.
- **Agent System**: Performs user tasks using active component versions.
- **Evolution Controller**: Observes execution evidence, generates candidate generations, evaluates candidates in sandboxes, and controls promotion or rollback.
- **Security Invariant**: The evaluated agent CANNOT modify the mutation registry, evaluation results, promotion gate rules, or constitutional boundaries.

## Metamorphosis Lifecycle

```text
OBSERVE → TRIGGER → PROPOSE → CANDIDATE → JCODE → SANDBOX → EVAL → GATE → APPROVE → CANARY → PROMOTE / ROLLBACK
```

- Candidates are created under `data/candidates/<id>/`. Production `src/` is never mutated.
- Jcode writes versioned artifacts (`artifacts/<target>.json`) and tests inside the candidate workspace.
- Layer 7 `RuntimeSandbox` executes those tests with `NetworkPolicy.DENY`.
- Layer 8 `EvaluationRunner` / `RegressionComparator` compares the candidate against an explicit baseline.
- Promotion copies artifacts to `data/generations/<version>/` and updates the active generation pointer.
- Rollback restores the parent generation pointer and preserves the audit trail.

## Evolvable Targets vs Protected Categories

### Evolvable Component Targets
1. `planner_strategy`
2. `agent_routing`
3. `tool_selection_policy`
4. `skill_definitions`
5. `memory_retrieval_strategy`
6. `model_routing`
7. `agent_composition`

### Protected Categories
Attempts to mutate any of the following raise `ConstitutionalViolationError` and result in immediate `REJECT`:
- `identity`
- `core_objectives`
- `security_invariants`
- `permission_ceiling`
- `credential_boundaries`
- `sandbox_boundaries`
- `audit_integrity`
- `rollback_authority`
- `human_approval_authority`
- `evolution_controller_integrity`
- `constitutional_rules`
- `evolution_boundaries`

Layer 9 also refuses writes to `src/agent/constitution.py` and `src/agent/evolution/`.

## Evolution Modes
- `OBSERVE_ONLY`: Records observations without generating proposals.
- `PROPOSE_ONLY`: Generates proposals without implementing candidates.
- `SIMULATE` / `dry_run`: Evaluates without deploying.
- `SEMI_AUTOMATIC` (API default): Gate pass still requires human approval.
- `AUTOMATIC`: Promotes after gate + canary when tests pass.

## Version lineage

```text
agent-v1
 └── candidate planner_strategy-vxxxx
      └── promoted planner_strategy-vxxxx
```
