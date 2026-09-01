# AGENTS.md — Repository Engineering & Architecture Specification

Welcome agent. This file specifies the persistent architecture, development guidelines, boundaries, and rules for this repository.

## 1. Project Purpose & Long-Term Vision
We are building a local-first AI agent for Windows capable of controlled **metamorphosis**: evolving internal capabilities, strategies, skills, routing, memory strategies, and agent composition through a tested versioning pipeline while preserving immutable constitutional boundaries.

## 2. Layered Architecture
The system is built strictly layer-by-layer:

- **LAYER -1 — CONSTITUTION**: Immutable boundaries & invariants (identity, security, human approval, authority boundaries).
- **LAYER 0 — FOUNDATION (Current)**: Environment, structure, config, structured logging, component versioning specifications, verification tools.
- **LAYER 1 — AGENT CORE (Planned)**: Base AgentScope runtime integration, session lifecycle, message schema.
- **LAYER 2 — INTELLIGENCE / MODELS (Planned)**: Model API routing, fallback logic, prompt template engines.
- **LAYER 3 — MEMORY / RAG (Planned)**: Short-term context & long-term vector/graph memory retrieval.
- **LAYER 4 — TOOLS / SKILLS / MCP (Planned)**: Tool execution registry, skill management, MCP integration.
- **LAYER 5 — PLANNING / ORCHESTRATION (Planned)**: Dynamic planner, multi-agent workflow orchestration.
- **LAYER 6 — JCODE CODING ENGINE (Planned)**: Specialized coding subsystem for repository analysis, editing, and local verifications.
- **LAYER 7 — RUNTIME / SANDBOX (Planned)**: Controlled sandboxed execution environment.
- **LAYER 8 — EVALUATION / VERIFICATION (Planned)**: Benchmark execution, regression checks, safety evaluations.
- **LAYER 9 — EVOLUTION CONTROL PLANE (Planned)**: Independent control plane observing agent runs, generating candidates, testing mutations, managing rollbacks/promotions.
- **LAYER 10 — UI / DESKTOP (Planned)**: Desktop user interface for Windows.

## 3. Strict Development Rules & Directives

### A. Layer Discipline
- **DO NOT** implement future layers prematurely.
- Build strictly **layer by layer**: Research → Design → Implement → Test → Verify → Document → Commit.
- Never claim a layer is complete merely because code imports without error.
- Stop after completing the assigned layer. Do not proceed to the next layer automatically.

### B. Constitutional Invariants (Layer -1)
- The agent framework and runtime code **CANNOT** modify constitutional rules, audit trails, human approval authority, or Evolution Controller boundaries.
- Any attempt to bypass or overwrite constitutional constraints must raise a `ConstitutionalViolationError`.

### C. Evolution Controller Separation
- The **Evolution Controller** is **NOT** an internal execution layer within the agent.
- It operates as an external control plane beside the agent.
- Agent performs tasks; Evolution Controller observes, evaluates, and governs version candidate promotion or rollback.

### D. Component Versioning Policy
- All evolvable components (planners, memory strategies, skills, tools) must be explicitly versioned (e.g. `planner-v1`, `planner-v2`).
- Mutations must generate new versioned candidates rather than overwriting existing source files directly.

### E. Jcode & AgentScope Roles
- **AgentScope** acts as the core multi-agent infrastructure (agents, models, messaging, context).
- **Jcode** acts as a specialized coding subsystem invoked for software-engineering tasks (read, edit, test, verify).

## 4. Engineering & Testing Practices
- Use `pytest` for unit and integration tests.
- Maintain minimal dependencies specified in `pyproject.toml`.
- All tests must run non-interactively without requiring external services or long-running daemons.
- Never commit secrets, API keys, or private tokens.
