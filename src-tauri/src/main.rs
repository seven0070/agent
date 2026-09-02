// Sovereign Agent OS Tauri 2 Desktop Shell Main Entrypoint
// Desktop Runtime Supervisor managing Python FastAPI backend sidecar lifecycle,
// localhost binding, health readiness contract polling, and clean termination.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;
use tauri::{State, Manager};

struct BackendSupervisor {
    process: Mutex<Option<Child>>,
    port: u16,
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
            return Ok(()); // Already running
        }

        println!("[Desktop Shell] Starting Agent backend sidecar process on 127.0.0.1:{}...", self.port);
        let child = Command::new("python")
            .arg("scripts/run_agent_backend.py")
            .arg("--port")
            .arg(self.port.to_string())
            .spawn()
            .or_else(|_| {
                Command::new("python3")
                    .arg("scripts/run_agent_backend.py")
                    .arg("--port")
                    .arg(self.port.to_string())
                    .spawn()
            })
            .map_err(|e| format!("Failed to spawn Agent backend sidecar process: {}", e))?;

        *guard = Some(child);
        Ok(())
    }

    fn stop_backend(&self) {
        if let Ok(mut guard) = self.process.lock() {
            if let Some(mut child) = guard.take() {
                println!("[Desktop Shell] Terminating Agent backend sidecar process...");
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
}

#[tauri::command]
async fn get_backend_status(state: State<'_, BackendSupervisor>) -> Result<String, String> {
    let client = reqwest::Client::new();
    let health_url = format!("http://127.0.0.1:{}/health", state.port);

    match client.get(&health_url).timeout(Duration::from_secs(2)).send().await {
        Ok(res) if res.status().is_success() => Ok(format!("READY:127.0.0.1:{}", state.port)),
        _ => Ok("STARTING".to_string()),
    }
}

fn main() {
    let supervisor = BackendSupervisor::new(8000);
    let _ = supervisor.start_backend();

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
