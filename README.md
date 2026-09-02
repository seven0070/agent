# Agent — Governed Self-Evolving Local-First AI

This repository is a local-first AI agent with a complete layered architecture through Layer 10. Layer 9 is a real Evolution Control Plane: observations become isolated candidates, Jcode implements them, Layer 7 sandboxes tests, Layer 8 evaluates, and a constitutional promotion gate decides promote or rollback.

## Layer Architecture

```text
LAYER -1 — CONSTITUTION (Immutable Boundaries)
        ↓
LAYER 0 — FOUNDATION
        ↓
LAYER 1 — AGENT CORE (AgentScope 2.x)
        ↓
LAYER 2 — INTELLIGENCE / MODELS
        ↓
LAYER 3 — MEMORY / KNOWLEDGE
        ↓
LAYER 4 — TOOLS / SKILLS / MCP
        ↓
LAYER 5 — PLANNING / ORCHESTRATION
        ↓
LAYER 6 — JCODE CODING ENGINE
        ↓
LAYER 7 — RUNTIME / SANDBOX
        ↓
LAYER 8 — EVALUATION / VERIFICATION
        ↓
LAYER 9 — EVOLUTION CONTROL PLANE
        ↓
LAYER 10 — UI / DESKTOP
```

There are no Layers 11–15. Agent may evolve *how* it accomplishes objectives. It cannot autonomously redefine *what* it is allowed to do.

## Requirements

- Python 3.11 or 3.12
- Node.js 20+ for the desktop UI
- Rust stable for Tauri packaging

## Installation

```bash
python -m pip install -e ".[dev]"
```

## Running the Agent CLI

```bash
python -m agent --session my-session-1 "Create python module and test"
```

## Running the local API

```bash
python -m agent.api.main --port 8000
```

Development UI:

```bash
cd ui && npm install && npm run dev
```

## Tests

```bash
PYTHONPATH=src pytest
python scripts/verify_layer9.py
python scripts/verify_layer10.py
python scripts/verify_packaging.py
```

## Evolution Control Plane

The live cycle is:

Observe → Trigger → Proposal → Isolated candidate → Jcode → Layer 7 sandbox → Layer 8 evaluation → Promotion gate → Human approval (semi-automatic) → Canary → Promote or rollback

Candidates are written under `data/candidates/`. Promoted artifacts live under `data/generations/`. Source under `src/agent/constitution.py` and `src/agent/evolution/` cannot be rewritten by evolution.

## Desktop packaging

Packaged releases do not require a user Python install or a source checkout. CI builds a PyInstaller sidecar named `agent-backend-<target-triple>` and Tauri bundles it.

```bash
python scripts/build_backend_sidecar.py
npx --prefix ui tauri build
```

Verified desktop targets: Windows x64 and Linux x64. macOS is not claimed.

## Layer verification scripts

```bash
python scripts/verify_layer0.py
python scripts/verify_layer1.py
python scripts/verify_layer2.py
python scripts/verify_layer3.py
python scripts/verify_layer4.py
python scripts/verify_layer5.py
python scripts/verify_layer6.py
python scripts/verify_layer7.py
python scripts/verify_layer8.py
python scripts/verify_layer9.py
python scripts/verify_layer10.py
python scripts/verify_packaging.py
```
