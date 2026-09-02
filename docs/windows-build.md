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

## 3. Production installer

```bash
python scripts/build_backend_sidecar.py --triple x86_64-pc-windows-msvc
npx --prefix ui tauri build
```

The Windows installer is emitted under `src-tauri/target/release/bundle/` as `Agent_0.1.0_x64_en-US.msi` (and NSIS). The bundled sidecar is `agent-backend-x86_64-pc-windows-msvc.exe`. The installed application does not use `scripts/run_agent_backend.py` or a system Python.

## 4. Verification

- Linux CI: pytest, layer verification, PyInstaller sidecar, Linux Tauri bundle (deb/AppImage)
- Windows CI: pytest, PyInstaller sidecar, MSI/NSIS Tauri bundle
- macOS is not built or claimed
