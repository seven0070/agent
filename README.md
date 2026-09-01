# Self-Evolving AI Agent — Layer 3 (Memory & Knowledge)

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
LAYER 4 — TOOLS / SKILLS / MCP (Planned)
        ↓
LAYER 5 — PLANNING / ORCHESTRATION (Planned)
        ↓
LAYER 6 — JCODE CODING ENGINE (Planned)
        ↓
LAYER 7 — RUNTIME / SANDBOX (Planned)
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

Execute tasks with optional persistent session history:

```bash
python -m agent --session my-session-1 "Explain what this project does."
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
```
