# Layer Specification

This document defines the scope, responsibilities, and current status of each layer in the architecture.

| Layer | Name | Description | Status |
|---|---|---|---|
| **Layer -1** | Constitution | Immutable safety constraints, identity, audit integrity, and human approval rules. | DEFINED (Foundation Invariants) |
| **Layer 0** | Foundation | Project structure, environment config, structured logging, component versioning specifications, verification suite. | **IMPLEMENTED** |
| **Layer 1** | Agent Core | AgentScope 2.x agent lifecycle, adapter boundary, session management, structured AgentResult, agent-v1. | **IMPLEMENTED** |
| **Layer 2** | Intelligence / Models | Model adapters, LLM routing, token management, model failovers, ModelRouter. | **IMPLEMENTED** |
| **Layer 3** | Memory / Knowledge | Session working memory, persistent SQLite long-term storage, embedding interface, RAG engine, ContextBuilder. | **IMPLEMENTED** |
| **Layer 4** | Tools / Skills / MCP | CapabilityBroker, ToolPermissionPolicy, calculator, workspace file I/O tools, path traversal safeguards, BasicFileManagementSkill, MCPClientWrapper. | **IMPLEMENTED** |
| **Layer 5** | Planning / Orchestration | RuleBasedPlanner, versioned Plan DAG, TaskState machine, PlanOrchestrator, retries, replanning (plan-v1 -> plan-v2), OrchestrationEvents. | **IMPLEMENTED** |
| **Layer 6** | Jcode Coding Engine | JcodeAdapter (@1jehuang/jcode-sdk v1.1.0), CodingTask, CodingResult, CodingWorkspaceRestrictor, JcodePermissionInterceptor, JcodeBridge, coding-engine-v1 tool. | **IMPLEMENTED** |
| **Layer 7** | Runtime / Sandbox | LocalAgentScopeRuntime, RuntimeSession lifecycle, RuntimeSandbox, path traversal guards, ResourceLimits, NetworkPolicy (DENY/ALLOWLIST), RuntimeEvent audit. | **IMPLEMENTED** |
| **Layer 8** | Evaluation / Verification | DeterministicEvaluator, MetricDimensions, EvaluationThresholds, BaselineStore, RegressionComparator, EvaluationRunner, EvaluationReport. | **IMPLEMENTED** |
| **Layer 9** | Evolution Control Plane | Out-of-band observer, mutation proposal engine, candidate generator, promotion/rollback controller. | PLANNED |
| **Layer 10** | UI / Desktop | Native Windows application interface for human user interaction and approval. | PLANNED |
