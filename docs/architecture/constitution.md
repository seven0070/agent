# Layer -1: Immutable Constitution Specification

## Concept & Purpose
The Constitution (Layer -1) establishes immutable operational boundaries and security invariants. The evolving agent software is strictly prohibited from modifying these rules or bypassing their enforcement.

## Core Constitutional Invariants

1. **Identity & Primary Purpose Invariant**: The agent must remain aligned with its defined persona and user-assigned objectives.
2. **Human Approval Authority**: High-risk actions (code commits, file deletion, credentials access, live deployment) require explicit human confirmation.
3. **Audit Integrity**: Execution logs, trace logs, and evolution histories must be append-only and immutable to runtime agents.
4. **Sandbox & Permission Ceiling**: Runtime execution cannot exceed sandboxed permission boundaries.
5. **Evolution Controller Boundary**: The agent cannot alter the candidate evaluation logic, baseline tests, or promotion criteria of the Evolution Controller.
6. **Rollback Authority**: The system must maintain a guaranteed pathway to revert any component or system state to a prior verified version.

## Enforcement Mechanism
- **Layer 0**: Programmatic checks via `src/agent/constitution.py` enforcing immutable invariant checks and raising `ConstitutionalViolationError` upon violation.
- **Future Layers**: Hardened OS-level file permissions, read-only policy engines, cryptographic signatures, and sandboxed isolation.
