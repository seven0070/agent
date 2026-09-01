# Layer 7 — Runtime / Sandbox / Execution System Specification

## Overview
Layer 7 creates a controlled execution environment (`LocalAgentScopeRuntime` and `RuntimeSandbox`) bridging agent intent and host execution. It isolates agent and Jcode operations within explicit workspace boundaries (`data/workspace`), enforces process timeouts, caps output sizes, applies network access policies (`DENY`, `ALLOWLIST`, `FULL`), and manages session lifecycles with automatic resource cleanup.

## AgentScope 2.0 Runtime & Workspace Analysis

### Verified Modules in AgentScope 2.0.7.post1

| Component | Module Path | Description |
|---|---|---|
| **LocalWorkspace** | `agentscope.workspace.LocalWorkspace` | Local workspace container (`workdir`, filesystem isolation). |
| **DockerWorkspace** | `agentscope.workspace.DockerWorkspace` | Docker container sandbox for production/remote modes. |
| **BubblewrapWorkspace** | `agentscope.workspace.BubblewrapWorkspace` | Linux unprivileged user sandbox. |
| **LocalBackend** | `agentscope.tool.LocalBackend` | Execution backend for local process invocation. |

## Target Runtime Architecture

```text
                        MAIN AGENT CORE (`AgentV1`)
                                    │
                                    ▼
                    PLAN ORCHESTRATOR (`PlanOrchestrator`)
                                    │
                                    ▼
                    CAPABILITY BROKER (`CapabilityBroker`)
                                    │
                     SECURITY & PERMISSION POLICY
                                    │
                                    ▼
                     LOCAL RUNTIME (`LocalAgentScopeRuntime`)
                        (AgentScope `LocalWorkspace`)
                                    │
                                    ▼
                      RUNTIME SANDBOX (`RuntimeSandbox`)
                                    │
           ┌────────────────────────┼────────────────────────┐
           ▼                        ▼                        ▼
  FILESYSTEM BOUNDARY        PROCESS CONTROL           NETWORK POLICY
 (path traversal guard)   (timeout, output caps)     (`DENY`/`ALLOWLIST`)
           │                        │                        │
           └────────────────────────┴────────────────────────┘
                                    │
                                    ▼
                      AUDIT EVENTS (`RuntimeEvent`)
```

## Session Lifecycle State Machine
Runtime sessions (`RuntimeSession`) follow a deterministic lifecycle:
- `CREATED`: Session instantiated
- `INITIALIZED`: AgentScope workspace initialized
- `RUNNING`: Executing process or capability inside workspace
- `PAUSED`: Execution suspended
- `COMPLETED`: Execution completed
- `CANCELLED`: Process or session cancelled by user/timeout
- `CLOSED`: Session resources cleaned up and handles closed

## Security Boundaries & Safeguards

### 1. Workspace Root Isolation
All operations must be performed within an explicit workspace directory.
- Attempts to access absolute system paths (`/etc/passwd`, `C:\Windows`, `C:\Users\...\.ssh`) or path traversal relative escapes (`../../`) are caught and blocked with `PermissionError`.

### 2. Process & Resource Limits (`ResourceLimits`)
- `timeout_seconds`: Process execution timeout (default 10s). Long-running processes are forcibly killed (`SIGKILL` / process termination).
- `max_output_bytes`: Output buffer size cap (default 1MB). Large output streams are safely truncated.
- `max_processes`: Maximum concurrent process cap.

### 3. Network Access Policy (`NetworkPolicy`)
- `DENY`: Outbound network connections blocked (default for sandboxed test/eval tasks).
- `ALLOWLIST`: Outbound connections restricted to authorized domain lists.
- `FULL`: Full network access (requires explicit user authorization).

## Audit Event Stream
Every runtime operation emits structured audit events (`RuntimeEvent`):
- `SANDBOX_CREATED`, `EXECUTION_STARTED`, `EXECUTION_COMPLETED`, `EXECUTION_FAILED`, `PERMISSION_DENIED`, `RESOURCE_LIMIT`, `SANDBOX_CLEANUP`, `SESSION_CLOSED`.

## Windows Platform Considerations
- Windows path semantics (`C:\`, `D:\`, case-insensitivity, backslashes vs forward slashes, UNC paths) are handled using `os.path.abspath` and `os.path.commonpath`.
- Path traversal tests verify Windows drive letter escapes and relative path traversals are blocked.
