# Layer 9 — Evolution Controller / Metamorphosis Engine Specification

## Overview
Layer 9 implements the core metamorphosis control plane (`EvolutionController`). It operates as an **independent control plane beside the agent system**—observing performance, identifying weaknesses, generating structured mutation proposals, testing candidate generations through Layer 8 sandboxed benchmarks, enforcing Layer -1 constitutional protections, and governing promotion, canary monitoring, or automatic rollback.

## Core Architectural Principle
The Evolution Controller is **NOT** an execution or reasoning layer inside the agent.
- **Agent System**: Performs user tasks using active component versions.
- **Evolution Controller**: Observes execution evidence, generates candidate generations (`agent-v1` -> `agent-v2`), evaluates candidates in sandboxes, and controls promotion or rollback.
- **Security Invariant**: The evaluated agent CANNOT modify the mutation registry, evaluation results, promotion gate rules, or constitutional boundaries.

## Metamorphosis Lifecycle & Control Flow

```text
                               CONSTITUTION
                                    │
                                    │ governs
                                    ▼
                          EVOLUTION CONTROLLER
                             │      │      │
                          observe propose evaluate
                             │      │      │
                             └──────┼──────┘
                                    │
                                    ▼
                         ACTIVE AGENT SYSTEM
                                    │
                            (executes tasks)
                                    │
                                    ▼
                      OBSERVER (`EvolutionObserver`)
                   (analyzes audit events & traces)
                                    │
                                    ▼
                      PROPOSER (`MutationProposer`)
                     (generates structured `Mutation`)
                                    │
                                    ▼
                   PERSISTENT MUTATION REGISTRY (`MutationRegistry`)
                     (SQLite DB with file lock concurrency)
                                    │
                                    ▼
                    EXPERIMENT RUNNER (`ExperimentRunner`)
                      (evaluates candidate via Layer 8)
                                    │
                                    ▼
                      PROMOTION GATE (`PromotionGate`)
                 (enforces Constitutional Guard & thresholds)
                ┌───────────────────┴───────────────────┐
                ▼                                       ▼
             REJECT                                  CANARY
        (candidate discarded)                   (canary workload)
                                                        │
                                                   ┌────┴────┐
                                                   ▼         ▼
                                                ROLLBACK  PROMOTE
                                              (restore V1) (V2 active)
```

## Evolvable Targets vs Protected Categories

### Evolvable Component Targets
1. `planner_strategy`: Goal decomposition rules and task templates
2. `agent_routing`: Model selection and tool routing policy
3. `tool_selection_policy`: Capability permission levels and risk classifications
4. `skill_definitions`: Composed workflow procedures
5. `memory_retrieval_strategy`: Memory ranking, search limits, and context prompt formatting
6. `model_routing`: Provider fallback order and temperature settings

### Protected Categories (**STRICTLY PROHIBITED FROM MUTATION**)
Attempts to mutate any of the following categories raise `ConstitutionalViolationError` and result in immediate `REJECT`:
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

## Evolution Modes
- `OBSERVE_ONLY`: Records observations without generating proposals.
- `PROPOSE_ONLY` (Default): Generates proposals and candidates without active promotion.
- `SIMULATE`: Runs dry-run experiments without promoting candidates.
- `CANARY`: Deploys candidate to canary workloads prior to promotion.
- `AUTOMATED`: Full automated metamorphosis pipeline with strict safety gates.

## Canary Deployment & Guaranteed Rollback
- **Canary Manager (`CanaryManager`)**: Deploys candidate version to canary tasks (e.g. 10% workload or test tasks).
- **Rollback Manager (`RollbackManager`)**: If canary monitoring detects regressions or safety failures, the system executes an automatic rollback, resetting the active generation pointer to the parent baseline version without depending on candidate code.
