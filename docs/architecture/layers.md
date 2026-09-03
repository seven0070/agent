# Layer Specification

This document defines the scope, responsibilities, and current status of each layer in the architecture.

| Layer | Name | Description | Status |
|---|---|---|---|
| **Layer -1** | Constitution | Immutable safety constraints, identity, audit integrity, and human approval rules. | **IMPLEMENTED** |
| **Layer 0** | Foundation | Project structure, environment config, structured logging, component versioning specifications, verification suite. | **IMPLEMENTED** |
| **Layer 1** | Agent Core | AgentScope 2.x agent lifecycle, adapter boundary, session management, structured AgentResult, agent-v1. | **IMPLEMENTED** |
| **Layer 2** | Intelligence / Models | Model adapters, LLM routing, token management, model failovers, ModelRouter. | **IMPLEMENTED** |
| **Layer 3** | Memory / Knowledge | Session working memory, persistent SQLite long-term storage, embedding interface, RAG engine, ContextBuilder. | **IMPLEMENTED** |
| **Layer 4** | Tools / Skills / MCP | CapabilityBroker, ToolPermissionPolicy, calculator, workspace file I/O tools, path traversal safeguards, BasicFileManagementSkill, MCPClientWrapper. | **IMPLEMENTED** |
| **Layer 5** | Planning / Orchestration | RuleBasedPlanner, versioned Plan DAG, TaskState machine, PlanOrchestrator, retries, replanning (plan-v1 -> plan-v2), OrchestrationEvents. | **IMPLEMENTED** |
| **Layer 6** | Jcode Coding Engine | JcodeAdapter (@1jehuang/jcode-sdk v1.1.0), CodingTask, CodingResult, CodingWorkspaceRestrictor, JcodePermissionInterceptor, JcodeBridge, coding-engine-v1 tool. | **IMPLEMENTED** |
| **Layer 7** | Runtime / Sandbox | LocalAgentScopeRuntime, RuntimeSession lifecycle, RuntimeSandbox, path traversal guards, ResourceLimits, NetworkPolicy (DENY/ALLOWLIST), RuntimeEvent audit. | **IMPLEMENTED** |
| **Layer 8** | Evaluation / Verification | DeterministicEvaluator, MetricDimensions, EvaluationThresholds, BaselineStore, RegressionComparator, EvaluationRunner, EvaluationReport. | **IMPLEMENTED** |
| **Layer 9** | Evolution Control Plane | Observer, trigger, structured proposals, isolated candidates, Jcode implementation, Layer 7 sandbox, Layer 8 evaluation, promotion gate, versioning, rollback, audit. | **IMPLEMENTED** |
| **Layer 10** | UI / Desktop | Tauri 2 shell, React UI, local FastAPI API, packaged PyInstaller sidecar for Windows x64 and Linux x64. CI builds installers; a packaged window click-through is not claimed from the Linux audit environment. | **IMPLEMENTED** |

Layers 11–15 do not exist and must not be added.
