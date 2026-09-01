# Layer 4 — Tools / Skills / MCP System Specification

## Overview
Layer 4 builds a secure, extensible capability management system above AgentScope 2.x. It introduces a `CapabilityBroker` to enforce permission policies (`ALLOW`, `REQUIRE_APPROVAL`, `DENY`), a `ToolRegistry` for versioned tools, workspace path-traversal safeguards, skill abstractions, and MCP client integration.

## AgentScope 2.0.7.post1 Capability API Analysis

### Verified Capabilities Modules

| Component | Module Path | Description |
|---|---|---|
| **FunctionTool** | `agentscope.tool.FunctionTool` | Wraps Python callable with JSON schema inspection. |
| **ToolBase** | `agentscope.tool.ToolBase` | Abstract base class for executable tools. |
| **Toolkit** | `agentscope.tool.Toolkit` | Container registering tools, skills, and MCP clients with AgentScope `Agent`. |
| **Skill** | `agentscope.skill.Skill` | Composed, reusable multi-tool procedural instructions. |
| **MCPClient** | `agentscope.mcp.MCPClient` | Model Context Protocol client (`StdioMCPConfig`, `HttpMCPConfig`). |

## Capability Architecture

```text
                           LLM / AGENT
                                │
                        requests tool call
                                │
                                ▼
                   CAPABILITY BROKER (`CapabilityBroker`)
                                │
                    evaluates permission policy
                   (`ALLOW` / `REQUIRE_APPROVAL` / `DENY`)
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
  SAFE TOOLS                 SKILLS                 MCP SERVERS
(calculator, file)   (file-management-v1)       (external MCP client)
       │                        │                        │
       └────────────────────────┴────────────────────────┘
                                │
                                ▼
                       `CapabilityResult`
                  (success, output, error, ms)
```

## Security & Permission Model

### Permission Levels
1. `ALLOW`: Executed immediately by the capability broker.
2. `REQUIRE_APPROVAL`: Suspended/flagged for human approval before execution.
3. `DENY`: Rejected immediately with a normalized `PermissionDeniedError`.

### Tool Risk Taxonomy
- `LOW`: Deterministic, read-only or pure computations (e.g. `calculator`, `read_file` in workspace).
- `MEDIUM`: Workspace file mutations (e.g. `write_file` in workspace).
- `HIGH`: External network access, workspace structural changes.
- `CRITICAL`: Unrestricted shell execution, OS administration, credential modifications (**STRICTLY PROHIBITED** in Layer 4).

### Workspace Isolation & Path Traversal Safeguards
Filesystem tools (`read_file`, `write_file`) are strictly scoped to a configured workspace directory (`data/workspace` by default). Any attempt to read or write files outside this directory (e.g., `../../etc/passwd` or absolute path traversal) is caught and denied by path resolution checks.

## Development Toolset
- `calculator-v1`: Evaluates basic mathematical expressions (`add`, `sub`, `mul`, `div`, `pow`).
- `read_file-v1`: Workspace-restricted file reading tool.
- `write_file-v1`: Workspace-restricted file writing tool.

## Skill Abstraction & Versioning
Skills (`SkillSpec`) represent higher-level composed procedures using underlying tools (e.g., `file-management-skill-v1` combining file reading, writing, and verification).

## MCP Integration Foundation
The `MCPClientWrapper` wraps AgentScope's `MCPClient`, enabling external MCP server capabilities subject to broker permission policy checks.
