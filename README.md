# Self-Evolving AI Agent — Layer 1 (AgentScope Core)

This repository contains the foundational architecture for a local-first, self-evolving AI agent system.

## Layer Architecture Overview

```text
LAYER -1 — CONSTITUTION (Immutable Boundaries)
        ↓
LAYER 0 — FOUNDATION (Implemented)
        ↓
LAYER 1 — AGENT CORE (Implemented — AgentScope 2.x Core Adapter)
        ↓
LAYER 2 — INTELLIGENCE / MODELS (Planned)
        ↓
LAYER 3 — MEMORY / RAG (Planned)
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

Execute tasks via the CLI entrypoint:

```bash
python -m agent "Explain what this project does."
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
```
