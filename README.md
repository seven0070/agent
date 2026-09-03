# Agent — Governed Self-Evolving Local-First AI

Agent is a local-first autonomous AI desktop application. A submitted goal
runs a single pipeline:

```text
USER GOAL → CORE → MODEL → MEMORY → PLANNER → CAPABILITY BROKER
         → TOOLS / JCODE → SANDBOX → EVALUATION → RESULT
```

Layer 9 is a real Evolution Control Plane beside that pipeline: observations
become isolated candidates, Jcode implements them, Layer 7 sandboxes tests,
Layer 8 evaluates, and a constitutional promotion gate decides promote or
rollback. Agent may evolve *how* it accomplishes objectives. It cannot
autonomously redefine *what* it is allowed to do.

There are no Layers 11–15. There is no OpenHands runtime.

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

## What is implemented

- Governed execution through `AgentPipeline` (API, CLI, and evaluation share it)
- Model abstraction with a **mock default**; OpenAI / Anthropic / DashScope / local
  hosts are optional and read from the environment
- Session + SQLite memory (conversation turns persist under the OS data directory)
- Rule-based planner, retries, and replanning (`plan-v1` → `plan-v2`)
- Capability Broker with ALLOW / REQUIRE_APPROVAL / DENY
- Jcode coding workspace restricted to the sandbox
- RuntimeSandbox with path-traversal guards and `NetworkPolicy.DENY`
- Deterministic evaluation on every live goal
- Isolated candidates under `data/candidates/`; promoted artifacts under `data/generations/`
- Native desktop UI (Workspace, Activity, Evolution, Trust, Settings)
- Rollback / versioning with audit records
- Tauri 2 + PyInstaller packaging contract

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

The backend binds `127.0.0.1` only. Development UI:

```bash
cd ui && npm install && npm run dev
```

The Vite dev server on port 1420 proxies `/api` and `/health` to the backend.
Packaged Tauri builds talk to `http://127.0.0.1:8000` directly. They do not
use Vite.

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

The desktop **Run demonstration cycle** button uses a deterministic planner-gap
fixture so the loop is reproducible. Live pipeline observations can drive a
cycle with `{"use_live_observations": true}` after goals have been executed.

Candidates are written under `data/candidates/`. Promoted artifacts live under
`data/generations/`. Source under `src/agent/constitution.py` and
`src/agent/evolution/` cannot be rewritten by evolution.

Default API mode is `SEMI_AUTOMATIC`: a gate pass still requires human approval.

## Desktop packaging

Packaged releases do not require a user Python install or a source checkout.
CI builds a PyInstaller sidecar named `agent-backend-<target-triple>` and Tauri
bundles it.

```bash
python scripts/build_backend_sidecar.py
cd ui && npx tauri build
```

Data directory:

- Windows: `%APPDATA%\Agent`
- Packaged POSIX: `~/.local/share/agent`
- Development: `./data` (or `AGENT_DATA_DIR`)

## Verification status

| Surface | Status |
|---|---|
| Python unit / integration / E2E tests | Implemented and run in CI (Ubuntu + Windows, Python 3.11/3.12) |
| Layer 0–10 verification scripts | Implemented and run in CI |
| Packaging contract (`verify_packaging.py`) | Implemented and run in CI |
| Frontend `ui` production build (`tsc` + Vite) | Implemented and run in CI |
| Linux PyInstaller sidecar + `/health` smoke | CI job (`Packaged Runtime Smoke (Linux)`) |
| Windows PyInstaller sidecar + `/health` smoke | CI job (`Packaged Runtime Smoke (Windows)`). Not executed in the Linux audit environment. |
| Tauri installer (Windows MSI/NSIS, Linux deb/AppImage) | CI `build-tauri` job after tests pass. Not built in the Linux audit environment (GTK/WebKit sysroot is unavailable here). |
| Packaged desktop window launch / click-through | **Not experimentally verified** in this environment. Supervised by `src-tauri/src/main.rs` (sidecar spawn, health poll, clean shutdown). |
| macOS | Not built. Not claimed. |

Windows CI previously failed only on Unicode `✓` prints under cp1252. Verification
scripts now emit ASCII `[OK]`, and the test job sets `PYTHONUTF8=1`.

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
