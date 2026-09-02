# Layer 10 Interface Security Specification

## 1. Local Service Binding
The API server binds exclusively to `127.0.0.1` and restricts CORS origins to the local desktop shell (`tauri://localhost`, `http://localhost:1420`).

## 2. Security Boundaries & Non-Bypass Principles
- **Layer -1 Protection**: No API endpoint allows modifying constitutional rules or protected boundaries.
- **Layer 4 Capabilities**: Tool execution passes through `CapabilityBroker` and `ToolPermissionPolicy`.
- **Layer 7 Sandbox**: Workspace file operations are strictly restricted to `data/workspace` with path-traversal guards.
- **Layer 9 Evolution**: The UI acts as an observer/controller and cannot bypass `PromotionGate` or execute unapproved mutations.
- **Credential Protection**: Plain-text keys/passwords are never stored in memory or exposed via API responses (`***REDACTED***`).
