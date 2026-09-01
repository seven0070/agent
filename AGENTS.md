# AGENTS.md — Repository Engineering & Architecture Specification

Welcome agent. This file specifies the persistent architecture, development guidelines, boundaries, and rules for this repository.

## 1. Project Purpose & Long-Term Vision
We are building a local-first AI agent for Windows capable of controlled **metamorphosis**: evolving internal capabilities, strategies, skills, routing, memory strategies, and agent composition through a tested versioning pipeline while preserving immutable constitutional boundaries.

## 2. Layered Architecture
The system is built strictly layer-by-layer:

- **LAYER -1 — CONSTITUTION**: Immutable boundaries & invariants (identity, security, human approval, authority boundaries).
- **LAYER 0 — FOUNDATION (Implemented)**: Environment, structure, config, structured logging, component versioning specifications, verification tools.
- **LAYER 1 — AGENT CORE (Implemented)**: Base AgentScope 2.x runtime integration, session lifecycle, message schema, agent-v1.
- **LAYER 2 — INTELLIGENCE / MODELS (Implemented)**: Provider-agnostic model abstraction, ModelSpec registry, secure credential handling, deterministic router, health status tracking, fallback engine, local model readiness.
- **LAYER 3 — MEMORY / KNOWLEDGE (Implemented)**: Ephemeral session working memory, persistent SQLite long-term storage, embedding interface, document RAG engine, bounded context builder, secret scrubbing.
- **LAYER 4 — TOOLS / SKILLS / MCP (Implemented)**: CapabilityBroker, ToolPermissionPolicy (ALLOW, REQUIRE_APPROVAL, DENY), versioned ToolRegistry, calculator tool, workspace path-traversal prevention, BasicFileManagementSkill, MCPClientWrapper.
- **LAYER 5 — PLANNING / ORCHESTRATION (Implemented)**: RuleBasedPlanner, versioned Plan DAGs (`plan-v1`), TaskState machine (`PENDING`, `READY`, `RUNNING`, `SUCCEEDED`, `FAILED`), PlanOrchestrator, task retries, replanning (`plan-v1` -> `plan-v2`), structured `OrchestrationEvent`s.
- **LAYER 6 — JCODE CODING ENGINE (Implemented)**: `JcodeAdapter` (`@1jehuang/jcode-sdk` v1.1.0 harness protocol), `CodingTask`, `CodingResult`, `CodingWorkspaceRestrictor` path restriction, `JcodePermissionInterceptor`, `JcodeBridge`, `coding-engine-v1` tool wrapper.
- **LAYER 7 — RUNTIME / SANDBOX (Implemented)**: `LocalAgentScopeRuntime`, `RuntimeSession` lifecycle, `RuntimeSandbox` process controls, workspace path traversal guards, `ResourceLimits` (timeouts, output caps), `NetworkPolicy` (`DENY`, `ALLOWLIST`), structured `RuntimeEvent` audit stream.
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

### C. Intelligence & Model Layer Security (Layer 2)
- Models are infrastructure and must **NOT** have direct filesystem, shell, or credential mutation permissions.
- Secret credentials must be read from environment variables and redacted in all logs, representations, and serializations (`***REDACTED***`).

### D. Memory & Privacy Protection (Layer 3)
- API keys, tokens, or private credentials must **NEVER** be stored as plain-text memory entries.
- Scrubbing and deletion APIs (`delete_memory`, `delete_session`) must be provided at the memory abstraction level.

### E. Capability Broker & Permission Boundary (Layer 4)
- Unrestricted shell execution, arbitrary process spawning, package installation, network access, and system administration are strictly **PROHIBITED** without sandbox isolation.
- Tool requests must pass through `CapabilityBroker` permission policy checks (`ALLOW`, `REQUIRE_APPROVAL`, `DENY`).
- Filesystem tools must enforce workspace root isolation and path-traversal prevention.

### F. Orchestration & Planning Boundaries (Layer 5)
- All plan tasks requiring tool capability execution MUST pass through `CapabilityBroker.execute_tool()`.
- Plan dependency graphs must be validated against cycles using DFS cycle detection before execution.
- Plans and task failures must be versioned (`plan-v1` -> `plan-v2`) with failure rationale preserved for future evaluation.

### G. Jcode Coding Engine Boundaries (Layer 6)
- Jcode is a specialized coding subsystem invoked by the Main Agent and does NOT replace the main AgentScope agent.
- Jcode file operations and test executions MUST be restricted to the assigned workspace directory (`CodingWorkspaceRestrictor`).
- Tool actions requested by Jcode must pass through `JcodePermissionInterceptor` and `ToolPermissionPolicy`.

### H. Runtime & Sandbox Execution Boundaries (Layer 7)
- Process execution MUST occur inside `RuntimeSandbox` with strict timeout limits (`timeout_seconds`), output buffer capping (`max_output_bytes`), and network policy checks (`NetworkPolicy.DENY`).
- Path traversal outside sandbox workspace root (`data/workspace`) is strictly **PROHIBITED**.
- Runtime sessions must be properly closed and cleaned up to prevent orphaned processes or handles.

### I. Evolution Controller Separation
- The **Evolution Controller** is **NOT** an internal execution layer within the agent.
- It operates as an external control plane beside the agent.
- Agent performs tasks; Evolution Controller observes, evaluates, and governs version candidate promotion or rollback.

### J. Component Versioning Policy
- All evolvable components (plans, coding engines, tools, skills, memory strategies, planners) must be explicitly versioned (e.g. `coding-engine-v1`, `plan-v1`, `calculator-v1`, `memory-v1`).
- Mutations must generate new versioned candidates rather than overwriting existing source files directly.

## 4. Engineering & Testing Practices
- Use `pytest` for unit and integration tests (`PYTHONPATH=src pytest`).
- Execute layer verification tools (`python scripts/verify_layer7.py`).
- Maintain minimal dependencies specified in `pyproject.toml`.
- All tests must run non-interactively without requiring external cloud services or long-running daemons.
- Never commit secrets, API keys, or private tokens.
