# Layer 10 — Desktop Development & Interface Guide

## 1. Overview
The Sovereign Agent OS desktop interface consists of:
- **Tauri 2 Desktop Shell** (`src-tauri/`): Lightweight Rust native window wrapper.
- **React + TypeScript SPA** (`ui/`): Sovereign Chat, Session Manager, Plan Visualizer, Evolution Dashboard, Jcode Workspace, and Audit Viewer.
- **Local FastAPI Service** (`src/agent/api/`): Binds locally to expose backend Layers 0–9.

---

## 2. Local Development Workflow

Step 1: Start Python API service:
`python -m uvicorn agent.api.app:app --host 127.0.0.1 --port 8000`

Step 2: Run UI frontend in Vite dev mode:
`cd ui && npm start`

The UI will be accessible at `http://localhost:1420`.
