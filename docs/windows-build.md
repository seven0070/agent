# Windows Build & Packaging Instructions

## 1. Prerequisites (Windows Machine)

1. **Node.js** v20+
2. **Rust** via rustup (`x86_64-pc-windows-msvc`)
3. **C++ Build Tools** (Visual Studio)
4. **Python 3.11+** — required to *build* the sidecar, not to *run* the installed app

## 2. Development

```bash
pip install -e ".[dev]"
cd ui && npm install
python -m agent.api.main --port 8000
npx --prefix ui tauri dev
```

`tauri dev` may fall back to `scripts/run_agent_backend.py` only in debug
builds. Release builds never spawn Python.

## 3. Production installer

```bash
python scripts/build_backend_sidecar.py --triple x86_64-pc-windows-msvc
npx --prefix ui tauri build
```

The Windows installer is emitted under `src-tauri/target/release/bundle/` as
`Agent_0.1.0_x64_en-US.msi` (and NSIS). The bundled sidecar is
`agent-backend-x86_64-pc-windows-msvc.exe`. The installed application does not
use `scripts/run_agent_backend.py`, a system Python, or Vite.

Runtime data lives in `%APPDATA%\Agent`. The backend binds `127.0.0.1` only.
The UI addresses `http://127.0.0.1:8000` from the Tauri webview.

## 4. Verification

What is verified:

- **This Linux audit environment**: Python tests, layer scripts, packaging
  contract, frontend `tsc`/`vite build`. GTK/WebKit are not available, so a
  Tauri installer is **not** produced here. A Windows `.msi` is **not**
  launched here.
- **GitHub Actions**: pytest + layer scripts on `windows-latest` (Python 3.11
  and 3.12); PyInstaller sidecar build; sidecar `/health` smoke; Tauri MSI/NSIS
  bundle after tests pass.

macOS is not built or claimed.
