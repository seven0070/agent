# Layer 10 Local API Reference

## Endpoints
- `GET /health` or `GET /api/system/health`: System health status across Layers 0–10.
- `GET /api/sessions`: List active/stored sessions.
- `POST /api/sessions`: Create new session.
- `GET /api/sessions/{id}`: Get session details.
- `DELETE /api/sessions/{id}`: Delete session.
- `POST /api/chat/stream`: SSE chat event stream (`MESSAGE_STARTED`, `PLAN_CREATED`, `MESSAGE_DELTA`, `MESSAGE_COMPLETED`).
- `GET /api/plans/{id}`: Retrieve plan DAG.
- `GET /api/approvals`: List pending human approvals.
- `POST /api/approvals/{id}`: Resolve human approval.
- `GET /api/tools`: List registered tools & risk levels.
- `GET /api/coding/workspace`: Get Jcode workspace status.
- `GET /api/memory/search`: Query Layer 3 memory entries.
- `GET /api/evolution/status`: Get Layer 9 Evolution Controller status.
- `POST /api/evolution/cycle`: Trigger out-of-band evolution cycle.
- `GET /api/audit/logs`: Query unified audit log event stream.
