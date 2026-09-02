# Windows Build & Packaging Instructions — Sovereign Agent OS

## 1. Prerequisites (Windows Machine)
To build the native Windows installer `.msi` or `.exe` for Sovereign Agent OS:

1. **Node.js**: Install Node.js v20+ and `npm` or `pnpm`.
2. **Rust & Cargo**: Install Rust via rustup.rs (x86_64-pc-windows-msvc target).
3. **C++ Build Tools**: Install Microsoft Visual Studio C++ Build Tools.
4. **Python**: Install Python 3.10+ (x64) and ensure `python` / `pip` are on PATH.

---

## 2. Windows Development Build Steps

1. Clone repository & install Python agent package:
   pip install -e .

2. Install UI dependencies:
   cd ui && npm install

3. Start local API backend service:
   python -m uvicorn agent.api.app:app --port 8000

4. Run Tauri desktop app in dev mode:
   cd ui && npm run tauri dev

---

## 3. Production Installer Packaging (Windows)

Build standalone Windows installer package (.msi):
cd ui && npm run tauri build

The resulting installer package will be output to: `src-tauri/target/release/bundle/msi/SovereignAgentOS_0.1.0_x64_en-US.msi`.

---

## 4. Verification & Validation Requirements (Linux VM vs Windows Native)
- **Linux VM Validation (Jules Environment)**:
  - Backend FastAPI endpoints and SSE streaming verified (`pytest tests/`).
  - React SPA structure verified.
  - Tauri config schemas verified against Tauri 2 specs.
- **Windows Native Machine Validation**:
  - Launch `.msi` installer on Windows 11 x64.
  - Verify local sidecar process startup for Python backend service.
  - Verify native WebView2 rendering and local SSE stream connection.
