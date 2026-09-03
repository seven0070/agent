// Sovereign Agent OS Tauri 2 Desktop Shell
// Production packaged builds launch the PyInstaller sidecar next to the executable.
// Development builds may start the Python backend from the source tree.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;
use tauri::{Manager, State};

struct BackendSupervisor {
    process: Mutex<Option<Child>>,
    port: u16,
}

fn current_target_triple() -> String {
    if let Some(target) = option_env!("TARGET") {
        if !target.is_empty() {
            return target.to_string();
        }
    }
    match (std::env::consts::ARCH, std::env::consts::OS) {
        ("x86_64", "linux") => "x86_64-unknown-linux-gnu".to_string(),
        ("aarch64", "linux") => "aarch64-unknown-linux-gnu".to_string(),
        ("x86_64", "windows") => "x86_64-pc-windows-msvc".to_string(),
        ("aarch64", "windows") => "aarch64-pc-windows-msvc".to_string(),
        (arch, os) => format!("{arch}-unknown-{os}"),
    }
}

fn with_windows_exe(name: String) -> String {
    if cfg!(windows) && !name.ends_with(".exe") {
        format!("{name}.exe")
    } else {
        name
    }
}

fn sidecar_candidates(dir: &Path) -> Vec<PathBuf> {
    let triple = current_target_triple();
    let names = [
        with_windows_exe(format!("agent-backend-{triple}")),
        with_windows_exe("agent-backend".to_string()),
    ];
    names.into_iter().map(|name| dir.join(name)).collect()
}

fn resolve_packaged_sidecar() -> Result<PathBuf, String> {
    let exe = std::env::current_exe().map_err(|e| e.to_string())?;
    let dir = exe
        .parent()
        .ok_or_else(|| "unable to resolve application directory".to_string())?;
    let mut searched: Vec<String> = Vec::new();
    for candidate in sidecar_candidates(dir) {
        searched.push(candidate.display().to_string());
        if candidate.exists() {
            return Ok(candidate);
        }
    }
    Err(format!(
        "Packaged Agent backend sidecar was not found. The desktop application is not self-contained. Looked for: {}",
        searched.join(", ")
    ))
}

#[cfg(debug_assertions)]
fn spawn_development_backend(port: u16) -> Result<Child, String> {
    let script = PathBuf::from("scripts/run_agent_backend.py");
    if !script.exists() {
        return Err(
            "Development backend script scripts/run_agent_backend.py was not found. Run from the repository root."
                .to_string(),
        );
    }
    let mut attempts: Vec<String> = Vec::new();
    for python in ["python3", "python"] {
        attempts.push(python.to_string());
        match Command::new(python)
            .arg(&script)
            .arg("--port")
            .arg(port.to_string())
            .spawn()
        {
            Ok(child) => return Ok(child),
            Err(err) => attempts.push(format!("{python} failed: {err}")),
        }
    }
    Err(format!(
        "Failed to start development Agent backend via Python. Tried: {}",
        attempts.join("; ")
    ))
}

impl BackendSupervisor {
    fn new(port: u16) -> Self {
        Self {
            process: Mutex::new(None),
            port,
        }
    }

    fn start_backend(&self) -> Result<(), String> {
        let mut guard = self.process.lock().map_err(|e| e.to_string())?;
        if guard.is_some() {
            return Ok(());
        }

        println!(
            "[Desktop Shell Supervisor] Starting Agent backend on 127.0.0.1:{}...",
            self.port
        );

        let child = match resolve_packaged_sidecar() {
            Ok(path) => Command::new(&path)
                .arg("--port")
                .arg(self.port.to_string())
                .spawn()
                .map_err(|e| {
                    format!(
                        "Failed to launch packaged Agent backend sidecar '{}': {}",
                        path.display(),
                        e
                    )
                })?,
            Err(missing) => {
                #[cfg(debug_assertions)]
                {
                    println!("[Desktop Shell Supervisor] {missing}");
                    spawn_development_backend(self.port)?
                }
                #[cfg(not(debug_assertions))]
                {
                    return Err(missing);
                }
            }
        };

        *guard = Some(child);
        Ok(())
    }

    fn stop_backend(&self) {
        if let Ok(mut guard) = self.process.lock() {
            if let Some(mut child) = guard.take() {
                println!("[Desktop Shell Supervisor] Terminating Agent backend sidecar process...");
                let pid = child.id();
                // PyInstaller --onefile spawns a grandchild interpreter. Killing
                // only the bootloader leaves the API process bound to :8000.
                #[cfg(windows)]
                {
                    let _ = Command::new("taskkill")
                        .args(["/PID", &pid.to_string(), "/T", "/F"])
                        .status();
                }
                #[cfg(not(windows))]
                {
                    let _ = child.kill();
                }
                let _ = child.wait();
            }
        }
    }
}

#[tauri::command]
async fn get_backend_status(state: State<'_, BackendSupervisor>) -> Result<String, String> {
    let client = reqwest::Client::new();
    let health_url = format!("http://127.0.0.1:{}/health", state.port);

    match client
        .get(&health_url)
        .timeout(Duration::from_secs(2))
        .send()
        .await
    {
        Ok(res) if res.status().is_success() => Ok(format!("READY:127.0.0.1:{}", state.port)),
        _ => Ok("STARTING".to_string()),
    }
}

fn main() {
    let supervisor = BackendSupervisor::new(8000);
    if let Err(err) = supervisor.start_backend() {
        eprintln!("[Desktop Shell Supervisor] {err}");
        #[cfg(not(debug_assertions))]
        panic!("{err}");
    }

    tauri::Builder::default()
        .manage(supervisor)
        .invoke_handler(tauri::generate_handler![get_backend_status])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let state: State<'_, BackendSupervisor> = window.state();
                state.stop_backend();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
