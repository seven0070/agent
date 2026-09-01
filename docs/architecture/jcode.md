# Layer 6 — Jcode Coding Engine System Specification

## Overview
Layer 6 integrates Jcode (`@1jehuang/jcode-sdk` v1.1.0) as a specialized software-engineering agent engine inside our AgentScope-based AI agent system.

Jcode handles specialized repository code reading, file creation/editing, command execution, and test verification. Jcode operates strictly as a subsystem invoked by the main agent and does NOT replace the main AgentScope agent.

## Target Architecture

```text
                     MAIN AGENT CORE (`AgentV1`)
                               │
                               ▼
               PLAN ORCHESTRATOR (`PlanOrchestrator`)
                               │
                      coding task detected
                               │
                               ▼
                CODING ENGINE TOOL (`coding-engine-v1`)
                               │
                        CAPABILITY BROKER
                   (ToolPermissionPolicy checks)
                               │
                               ▼
                CODING ADAPTER (`JcodeAdapter`)
                               │
                               ▼
            IPC / HARNESS BRIDGE (`JcodeBridge`)
                               │
                               ▼
              JCODE SDK (`@1jehuang/jcode-sdk`)
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
   READ FILES              EDIT FILES             RUN TESTS
       │                       │                       │
       └───────────────────────┼───────────────────────┘
                               │
                               ▼
                   `CodingResult` / `JcodeEvent`
```

## Language & IPC Boundary
- **Core Agent**: Python 3.10+ (`src/agent/`)
- **Jcode Engine**: Node/TypeScript (`@1jehuang/jcode-sdk` / `@1jehuang/jcode-linux-x64` / `@1jehuang/jcode-win32-x64`)
- **IPC Protocol**: JSON-RPC IPC subprocess bridge (`JcodeBridge`) launching Node or fallback embedded execution harness.

## Working Directory Security Boundary
Jcode is explicitly scoped to an assigned workspace directory (`data/workspace` by default).
- File operations outside the assigned workspace are intercepted and rejected with `PermissionError`.
- Path traversal sequences (`../`, absolute path escapes) are prevented.

## Permission Mapping & Security Rules
Jcode tool requests are intercepted by `JcodePermissionInterceptor` and mapped to Layer 4 `ToolPermissionPolicy`:
- `read_file`: `ALLOW` (workspace scoped)
- `write_file` / `edit_file`: `ALLOW` or `REQUIRE_APPROVAL` (workspace scoped)
- `exec_command` / `run_test`: `ALLOW` within workspace test context
- `shell` / `system_admin`: `DENY` (prohibited in Layer 6)

## Event Stream & Audit Logging
Jcode execution emits structured events (`JcodeEvent`):
- `session_started`: Session created for `task_id`
- `tool_started` / `tool_executed`: File edits or test commands
- `permission_requested`: Security check
- `turn_completed`: Task execution complete
- `error`: Execution failure details

## Windows Platform Considerations
- `@1jehuang/jcode-win32-x64` and `@1jehuang/jcode-win32-arm64` binary packages exist on npm.
- Paths are handled using cross-platform path normalization (`os.path.abspath` and relative POSIX/Windows paths) to prevent Windows drive letter or backslash resolution issues.
