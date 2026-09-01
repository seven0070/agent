# Layer Specification

This document defines the scope, responsibilities, and current status of each layer in the architecture.

| Layer | Name | Description | Status |
|---|---|---|---|
| **Layer -1** | Constitution | Immutable safety constraints, identity, audit integrity, and human approval rules. | DEFINED (Foundation Invariants) |
| **Layer 0** | Foundation | Project structure, environment config, structured logging, component versioning specifications, verification suite. | **IMPLEMENTED** |
| **Layer 1** | Agent Core | AgentScope agent lifecycle, base session management, message passing. | PLANNED |
| **Layer 2** | Intelligence / Models | Model adapters, LLM routing, token management, model failovers. | PLANNED |
| **Layer 3** | Memory / RAG | Ephemeral context window management, long-term vector/graph memory, memory index. | PLANNED |
| **Layer 4** | Tools / Skills / MCP | Executable tools, reusable skill library, Model Context Protocol (MCP) servers. | PLANNED |
| **Layer 5** | Planning / Orchestration | Multi-step reasoning planners, reactive execution graphs, multi-agent teams. | PLANNED |
| **Layer 6** | Jcode Coding Engine | Specialized coding agent subsystem for software tasks (read, edit, run tests). | PLANNED |
| **Layer 7** | Runtime / Sandbox | Process isolation, environment containerization, filesystem/network permission control. | PLANNED |
| **Layer 8** | Evaluation / Verification | Automated benchmark execution, safety regression tests, fitness metrics. | PLANNED |
| **Layer 9** | Evolution Control Plane | Out-of-band observer, mutation proposal engine, candidate generator, promotion/rollback controller. | PLANNED |
| **Layer 10** | UI / Desktop | Native Windows application interface for human user interaction and approval. | PLANNED |
