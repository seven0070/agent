# Self-Evolving AI Agent — Layer 7 (Runtime / Sandbox)

This repository contains the foundational architecture for a local-first, self-evolving AI agent system.

## Layer Architecture Overview

```text
LAYER -1 — CONSTITUTION (Immutable Boundaries)
        ↓
LAYER 0 — FOUNDATION (Implemented)
        ↓
LAYER 1 — AGENT CORE (Implemented — AgentScope 2.x Core Adapter)
        ↓
LAYER 2 — INTELLIGENCE / MODELS (Implemented — ModelRouter & Fallback Engine)
        ↓
LAYER 3 — MEMORY / KNOWLEDGE (Implemented — SQLite Long-Term Memory & RAG Engine)
        ↓
LAYER 4 — TOOLS / SKILLS / MCP (Implemented — CapabilityBroker & Permission Policies)
        ↓
LAYER 5 — PLANNING / ORCHESTRATION (Implemented — RuleBasedPlanner & PlanOrchestrator DAG Engine)
        ↓
LAYER 6 — JCODE CODING ENGINE (Implemented — JcodeAdapter @1jehuang/jcode-sdk Integration)
        ↓
LAYER 7 — RUNTIME / SANDBOX (Implemented — LocalAgentScopeRuntime & RuntimeSandbox Execution Engine)
        ↓
LAYER 8 — EVALUATION / VERIFICATION (Planned)
        ↓
LAYER 9 — EVOLUTION CONTROL PLANE (Planned)
        ↓
LAYER 10 — UI / DESKTOP (Planned)
```

## Getting Started

### Installation

```bash
python -m pip install -e .[dev]
```

### Running the Agent CLI

Execute complex multi-step goals or software engineering tasks inside sandboxed runtime sessions:

```bash
python -m agent --session my-session-1 "Create python module and test"
```

### Running Tests

```bash
PYTHONPATH=src pytest
```

### Layer Verification Scripts

```bash
# Verify Layer 0 Foundation
python scripts/verify_layer0.py

# Verify Layer 1 AgentScope Core
python scripts/verify_layer1.py

# Verify Layer 2 Intelligence/Models
python scripts/verify_layer2.py

# Verify Layer 3 Memory & Knowledge
python scripts/verify_layer3.py

# Verify Layer 4 Tools/Skills/MCP
python scripts/verify_layer4.py

# Verify Layer 5 Planning/Orchestration
python scripts/verify_layer5.py

# Verify Layer 6 Jcode Coding Engine
python scripts/verify_layer6.py

# Verify Layer 7 Runtime/Sandbox
python scripts/verify_layer7.py
```
