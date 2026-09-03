# Layer 10 — Desktop Development & Interface Guide

## 1. Overview
The Agent desktop interface consists of:
- **Tauri 2 Desktop Shell** (`src-tauri/`): Native window wrapper and sidecar supervisor.
- **React + TypeScript SPA** (`ui/`): Workspace (goal + plan + live activity), Activity, Evolution, Trust, Settings.
- **Local FastAPI Service** (`src/agent/api/`): Binds to `127.0.0.1` and exposes Layers 0–9 through `AgentPipeline`.

Packaged releases launch `agent-backend-<target-triple>` next to the application binary. They do not require the user's Python installation or a source checkout. Python/`scripts/run_agent_backend.py` is a development-only path (`cfg(debug_assertions)`).

There is no OpenHands dependency.

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

The UI is available at `http://localhost:1420` and talks to `http://127.0.0.1:8000` through the Vite proxy.

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

`npx --prefix ui tauri build` must run from the repository root so Tauri discovers `src-tauri/tauri.conf.json`. `beforeBuildCommand` is `npm --prefix ui run build` so the frontend package.json is found without `cwd=ui/`. CI passes `--bundles msi,nsis` on Windows and `--bundles deb,appimage` on Linux.

CI targets: Windows x64 (MSI/NSIS) and Linux x64 (deb/AppImage). macOS is not claimed.

Installers land under `src-tauri/target/release/bundle/`.

A full installer click-through is **not** claimed from the Linux audit environment. GitHub Actions is the platform verification path.
