# Layer 10 — Interface / Desktop Architecture Specification

## 1. Overview & Architectural Principles

Layer 10 provides the presentation layer and desktop user experience for the local-first AI agent system. It exposes the underlying capabilities of Layers 0 through 9 to human operators through a desktop application shell (Tauri 2 + React/TypeScript) communicating with a local API service (`src/agent/api/`).

### Strict Architectural Rule
Layer 10 is **strictly a presentation and observation interface**. It is **NOT** another agent engine, authorization authority, or mutation executor.

```
                    USER / OPERATOR
                           │
                           ▼
            ┌──────────────────────────────┐
            │       LAYER 10 INTERFACE     │
            │   Tauri 2 Desktop Shell      │
            │   React + TypeScript UI      │
            └──────────────┬───────────────┘
                           │
                           ▼ (Local HTTP / SSE API)
            ┌──────────────────────────────┐
            │   PUBLIC API BOUNDARY        │
            │   FastAPI Service Handler    │
            └──────────────┬───────────────┘
                           │
                           ▼
                   LAYERS 0–9 BACKEND
   ┌─────────────────────────────────────────────────┐
   │ Layer -1: Constitutional Invariants Guard       │
   │ Layer 0: Foundation / Logging / Config / Ver    │
   │ Layer 1: Agent Core (AgentScope 2.x Adapter)   │
   │ Layer 2: Intelligence / Model Router           │
   │ Layer 3: Memory / SQLite & RAG Engine          │
   │ Layer 4: Capabilities Broker & Permission Policy│
   │ Layer 5: Planning & DAG Orchestrator           │
   │ Layer 6: Jcode Coding Engine Bridge            │
   │ Layer 7: Runtime Sandbox & Process Isolation    │
   │ Layer 8: Evaluation & Verification Engine      │
   │ Layer 9: Evolution Controller Control Plane    │
   └─────────────────────────────────────────────────┘
```

### Invariant Security Rules
The UI and API layer **MUST NEVER**:
1. Bypass Layer -1 `ConstitutionalGuard` or alter constitutional rules.
2. Bypass Layer 4 `CapabilityBroker` permissions or offer an ungoverned "allow all" switch.
3. Bypass Layer 7 `RuntimeSandbox` process timeout, path-traversal, or output limits.
4. Bypass Layer 9 `PromotionGate` or execute unapproved mutations.
5. Store or expose plain-text credentials or secret tokens (`***REDACTED***`).
6. Perform direct filesystem or command execution outside backend policies.

---

## 2. Desktop Stack & Service Boundary

### Technology Selection
- **Desktop Shell**: Tauri 2 (Rust) providing lightweight native desktop window management, low memory footprint, and cross-platform native OS integration (Windows, macOS, Linux).
- **Frontend SPA**: React 18 + TypeScript + Vite + Tailwind CSS.
- **Backend API**: FastAPI / Starlette local HTTP server (`127.0.0.1`) with SSE (Server-Sent Events) streaming.
- **Communication Protocol**: Local REST endpoints for CRUD/commands, SSE stream `/api/chat/stream` for real-time agent thoughts, plan step updates, tool execution cards, and system audit events.

---

## 3. Core UI Sections & Capabilities

1. **Sovereign Chat Interface**: Primary conversational view with streaming message cards, real-time thought processing, inline tool activity, plan visualization, and error handling.
2. **Session Manager**: Session creation, history list, resume, rename, archive, and clear, backed by Layer 3 memory.
3. **Plan / Task Visualizer**: Exposes Layer 5 Plan DAGs with status nodes (`PENDING`, `READY`, `RUNNING`, `SUCCEEDED`, `FAILED`), task retries, and replanning history.
4. **Tool Activity Stream**: Displays Layer 4 capability executions, parameters, and results with permission policy badges (`ALLOW`, `REQUIRE_APPROVAL`, `DENY`).
5. **Approval Center**: Human-in-the-Loop review center for Layer 4 tool executions, Layer 7 runtime requests, and Layer 9 evolution candidate promotions.
6. **Evolution / Metamorphosis Dashboard**: Displays Layer 9 active generation, proposed candidate mutations, evaluation metric comparisons (+/- %), canary health, rollback history, and human approval gates.
7. **Jcode Coding Workspace**: Visualizer for Layer 6 software engineering tasks, file change diffs, test execution results, and sandboxed sandbox terminal output.
8. **Memory / Knowledge Inspector**: Inspection and scrubbing interface for Layer 3 ephemeral session memory, persistent SQLite entries, and RAG document sources.
9. **System Status**: Real-time health monitoring of backend layers (Core, Models, Memory, Tools, Runtime, Jcode, Evaluation, Evolution).
10. **Audit Log Viewer**: Filterable audit trail viewer for `RuntimeEvent`, `OrchestrationEvent`, and `EvolutionEvent` streams.
11. **Settings**: Configuration editor for backend parameters mapping directly to safe `config.py` settings.

---

## 4. API Request & Event Streaming Protocol

### Key API Endpoints
- `GET /api/system/health` — Layer status checks.
- `GET /api/sessions`, `POST /api/sessions` — Session lifecycle management.
- `POST /api/chat/stream` — SSE streaming chat execution.
- `GET /api/plans/{session_id}` — Active plan DAG retrieval.
- `GET /api/approvals`, `POST /api/approvals/{approval_id}` — Human approval resolution.
- `GET /api/evolution/status`, `POST /api/evolution/cycle` — Evolution control plane status and cycle execution.
- `GET /api/coding/workspace` — Jcode workspace status and diff inspection.
- `GET /api/memory/search` — Layer 3 memory inspection.
- `GET /api/audit/logs` — Audit event logs query.

### Event Stream Protocol (SSE)
Event streams send JSON-formatted event frames matching backend audit types:
`MESSAGE_DELTA`, `PLAN_UPDATED`, `TASK_STATUS`, `TOOL_EXECUTION`, `APPROVAL_REQUIRED`, `EVOLUTION_MUTATION_PROPOSED`, `SYSTEM_ERROR`.

---

## 5. Security Invariants & Review

- **Binding**: Local API binds exclusively to `127.0.0.1` (or local IPC pipe in Tauri production).
- **Sanitisation**: All agent outputs and markdown renderings are sanitized against HTML/script injection.
- **Immutability**: Audit logs and constitutional rules remain immutable and read-only.
