# Layer 10 — Desktop Development & Interface Guide

## 1. Overview
The Agent desktop interface consists of:
- **Tauri 2 Desktop Shell** (`src-tauri/`): Native window wrapper and sidecar supervisor.
- **React + TypeScript SPA** (`ui/`): Sovereign Chat, Session Manager, Plan Visualizer, Evolution Dashboard, Jcode Workspace, and Audit Viewer.
- **Local FastAPI Service** (`src/agent/api/`): Binds to `127.0.0.1` and exposes Layers 0–9.

Packaged releases launch `agent-backend-<target-triple>` next to the application binary. They do not require the user's Python installation or a source checkout. Python/`scripts/run_agent_backend.py` is a development-only path.

---

## 2. Local Development Workflow

From the repository root:

```bash
pip install -e ".[dev]"
python -m agent.api.main --port 8000
```

In another terminal:

```bash
cd ui && npm install && npm run dev
```

The UI is available at `http://localhost:1420` and talks to `http://127.0.0.1:8000`.

Tauri development (uses the Python fallback only in debug builds):

```bash
npx --prefix ui tauri dev
```

---

## 3. Production packaging

```bash
python scripts/build_backend_sidecar.py
npx --prefix ui tauri build
```

Verified targets: Windows x64 (MSI/NSIS) and Linux x64 (deb/AppImage). macOS is not claimed.

Installers land under `src-tauri/target/release/bundle/`.
