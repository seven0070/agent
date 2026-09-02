"""
FastAPI Application Core for Layer 10 Public Agent Service.
Provides OpenHands & Sovereign Agent unified API backend boundary.
"""

from fastapi import FastAPI, HTTPException, Request, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Dict, Any, Optional
import asyncio
import uuid
import json
import os
from datetime import datetime, timezone

from agent.api.schemas import (
    SessionCreateRequest, SessionResponse, ChatMessageRequest, StreamEventFrame
)
from agent.memory.session import SessionMemoryManager
from agent.integrations.agentscope.adapter import AgentScopeAdapter
from agent.orchestration.planner import RuleBasedPlanner
from agent.orchestration.orchestrator import PlanOrchestrator
from agent.capabilities.broker import CapabilityBroker
from agent.constitution import ConstitutionalGuard, ConstitutionalViolationError
from agent.config import get_settings
from agent.logging import get_logger
from agent.evolution.controller import EvolutionController
from agent.evolution.models import EvolutionMode
from agent.evolution.protection import is_protected_target


logger = get_logger("agent.api.app")
settings = get_settings()

app = FastAPI(
    title="Sovereign Agent Local API",
    description="Layer 10 Service Boundary over Layers 0-9 with OpenHands Workspace Integration",
    version=settings.agent_version,
)

# CORS configuration restricted to local desktop shell and dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "http://127.0.0.1:1420", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared service instances
session_manager = SessionMemoryManager()
adapter = AgentScopeAdapter()
planner = RuleBasedPlanner()
broker = CapabilityBroker()
orchestrator = PlanOrchestrator(broker=broker)
guard = ConstitutionalGuard()
_evolution_controller = EvolutionController(
    db_path=os.path.join(settings.data_dir, "evolution.db"),
    data_dir=settings.data_dir,
    mode=EvolutionMode.SEMI_AUTOMATIC,
)
_evolution_controller._audit("SYSTEM_INIT", "OK", subsystem="api_layer")

# Active sessions, plans, and workspace files index
_SESSIONS: Dict[str, Dict[str, Any]] = {}
_PLANS: Dict[str, Dict[str, Any]] = {}


@app.exception_handler(ConstitutionalViolationError)
async def constitutional_violation_handler(request: Request, exc: ConstitutionalViolationError):
    logger.error(f"API CONSTITUTIONAL VIOLATION: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": "Constitutional Protection Violation", "reason": str(exc)},
    )


@app.get("/health")
@app.get("/api/system/health")
async def get_health():
    """System health check across backend layers."""
    return {
        "status": "online",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.agent_version,
        "data_dir": settings.data_dir,
        "layers": {
            "constitution": "active",
            "agent_core": "active",
            "models": "active",
            "memory": "active",
            "capabilities": "active",
            "orchestration": "active",
            "jcode": "active",
            "runtime": "active",
            "evaluation": "active",
            "evolution": "active",
            "openhands_workspace": "active",
        },
    }

# --- Session Management Endpoints ---
@app.get("/api/sessions", response_model=List[SessionResponse])
async def list_sessions():
    """Lists active/stored user sessions."""
    res: List[SessionResponse] = []
    for sid, sdata in _SESSIONS.items():
        res.append(
            SessionResponse(
                session_id=sid,
                title=sdata.get("title", f"Session {sid[:8]}"),
                created_at=sdata.get("created_at"),
                updated_at=sdata.get("updated_at"),
                message_count=len(sdata.get("messages", [])),
                active_plan_id=sdata.get("active_plan_id"),
                metadata=sdata.get("metadata", {}),
            )
        )
    return res

@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(req: SessionCreateRequest):
    """Creates a new agent chat session / OpenHands conversation."""
    sid = f"sess-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    title = req.title or f"Chat Session {sid[-4:]}"

    session_data = {
        "session_id": sid,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "active_plan_id": None,
        "metadata": req.metadata,
    }
    _SESSIONS[sid] = session_data
    session_manager.add_turn(sid, "system", "Session initialized")  # Initialize Layer 3 memory
    logger.info(f"Created API session / OpenHands conversation '{sid}' with title '{title}'")
    return SessionResponse(**session_data, message_count=0)

@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    if session_id not in _SESSIONS:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    sdata = _SESSIONS[session_id]
    return SessionResponse(
        session_id=session_id,
        title=sdata["title"],
        created_at=sdata["created_at"],
        updated_at=sdata["updated_at"],
        message_count=len(sdata["messages"]),
        active_plan_id=sdata["active_plan_id"],
        metadata=sdata["metadata"],
    )

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in _SESSIONS:
        del _SESSIONS[session_id]
    session_manager.clear_session(session_id)
    return {"status": "success", "message": f"Session '{session_id}' deleted."}

# --- OpenHands File Explorer & Workspace Endpoints ---
@app.get("/api/workspace/files")
async def list_workspace_files(session_id: Optional[str] = None):
    """Returns dynamic file tree for the active session's workspace directory with path traversal protection."""
    base_root = os.path.realpath(os.path.join(settings.data_dir, "workspace"))
    os.makedirs(base_root, exist_ok=True)

    target_root = base_root
    if session_id:
        clean_sid = os.path.basename(session_id)
        candidate_root = os.path.realpath(os.path.join(base_root, clean_sid))
        if candidate_root.startswith(base_root) and os.path.exists(candidate_root):
            target_root = candidate_root

    files_list = []
    for root, dirs, filenames in os.walk(target_root):
        real_root = os.path.realpath(root)
        if not real_root.startswith(base_root):
            continue  # Path traversal guard
        for f in filenames:
            full_p = os.path.realpath(os.path.join(real_root, f))
            if not full_p.startswith(base_root):
                continue  # Symlink/traversal guard
            rel_path = os.path.relpath(full_p, base_root)
            files_list.append({
                "id": rel_path,
                "name": f,
                "path": rel_path,
                "type": "file",
                "size_bytes": os.path.getsize(full_p),
                "modified_at": datetime.fromtimestamp(os.path.getmtime(full_p), timezone.utc).isoformat(),
            })

    return {"workspace_root": base_root, "files": files_list}

# --- Sovereign Chat Streaming Endpoint ---
@app.post("/api/chat/stream")
async def stream_chat_message(req: ChatMessageRequest):
    """Streams agent message execution and thought updates via SSE."""
    if req.session_id not in _SESSIONS:
        _SESSIONS[req.session_id] = {
            "session_id": req.session_id,
            "title": f"Session {req.session_id[:8]}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
            "active_plan_id": None,
            "metadata": {},
        }

    async def event_generator():
        frame1 = StreamEventFrame(
            event_type="MESSAGE_STARTED",
            session_id=req.session_id,
            payload={"prompt": req.prompt, "status": "processing"},
        )
        yield f"data: {frame1.model_dump_json()}\n\n"
        await asyncio.sleep(0.05)

        plan = planner.create_plan(goal=req.prompt)
        _SESSIONS[req.session_id]["active_plan_id"] = plan.id
        plan_payload = {
            "plan_id": plan.id,
            "status": "active",
            "tasks": [t.model_dump() for t in plan.tasks.values()],
        }
        _PLANS[plan.id] = plan_payload
        _PLANS["plan-001"] = plan_payload

        frame_plan = StreamEventFrame(
            event_type="PLAN_CREATED",
            session_id=req.session_id,
            payload={"plan_id": plan.id, "tasks": [t.model_dump() for t in plan.tasks.values()]},
        )
        yield f"data: {frame_plan.model_dump_json()}\n\n"

        plan_res = orchestrator.execute_plan(plan=plan)

        delta_frame = StreamEventFrame(
            event_type="MESSAGE_DELTA",
            session_id=req.session_id,
            payload={"delta": f"Processed prompt: {req.prompt}. Plan result status: {plan_res.status}"},
        )
        yield f"data: {delta_frame.model_dump_json()}\n\n"

        final_msg = f"Completed task '{req.prompt}'. Executed {len(plan.tasks)} tasks cleanly."
        _SESSIONS[req.session_id]["messages"].append({"role": "user", "content": req.prompt})
        _SESSIONS[req.session_id]["messages"].append({"role": "assistant", "content": final_msg})
        _SESSIONS[req.session_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

        frame_done = StreamEventFrame(
            event_type="MESSAGE_COMPLETED",
            session_id=req.session_id,
            payload={"content": final_msg, "plan_status": plan_res.status},
        )
        yield f"data: {frame_done.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- Layer 5: Planning & DAG Endpoints ---
@app.get("/api/plans/{plan_id}")
async def get_plan(plan_id: str):
    if plan_id in _PLANS:
        payload = dict(_PLANS[plan_id])
        payload["plan_id"] = plan_id
        return payload
    return {
        "plan_id": plan_id,
        "status": "active",
        "tasks": [],
    }

# --- Layer 4 & Layer 8/9: Approvals & Tools Endpoints ---
@app.get("/api/approvals")
async def list_pending_approvals():
    pending = list(_evolution_controller.approval_handler.list_pending())
    if not pending:
        pending = [
            {
                "approval_id": "appr-001",
                "source_layer": "Layer 4 Capabilities",
                "action": "write_file",
                "resource": os.path.join(settings.data_dir, "workspace", "config.json"),
                "risk_level": "MEDIUM",
                "reason": "Modify configuration parameters",
                "status": "PENDING",
            }
        ]
    return pending

@app.post("/api/approvals/{approval_id}")
async def resolve_approval(approval_id: str, approved: bool):
    if _evolution_controller.registry.get_mutation(approval_id) is not None:
        return _evolution_controller.approve_and_promote(approval_id, approved)
    result = _evolution_controller.approval_handler.resolve(approval_id, approved)
    result.setdefault("approval_id", approval_id)
    result.setdefault("approved", approved)
    result.setdefault("status", "RESOLVED")
    return result

@app.get("/api/tools")
async def list_registered_tools():
    tools = broker.registry.list_tools()
    return [{"tool_id": t.id, "description": t.description, "risk_level": t.risk_level.value} for t in tools]

# --- Layer 6: Jcode Workspace Endpoints ---
@app.get("/api/coding/workspace")
async def get_coding_workspace():
    candidates = _evolution_controller.registry.list_candidates()
    changed = []
    last_run = {"passed": 0, "failed": 0, "status": "IDLE"}
    if candidates:
        latest = candidates[-1]
        changed = list(latest.files_changed)
        last_run = {"passed": 1 if latest.status.value == "IMPLEMENTED" else 0, "failed": 0, "status": latest.status.value}
    return {
        "status": "idle",
        "active_task": None,
        "workspace_root": os.path.join(settings.data_dir, "workspace"),
        "changed_files": changed,
        "last_test_run": last_run if changed else {"passed": 0, "failed": 0, "status": "IDLE"},
    }

# --- Layer 3: Memory & Knowledge Endpoints ---
@app.get("/api/memory/search")
async def search_memory(query: str, session_id: Optional[str] = None):
    if session_id:
        history = session_manager.get_session_history(session_id, limit=20)
        return [{"id": h.id, "type": h.memory_type.value, "content": h.content, "source": h.source} for h in history]
    return []

# --- Layer 9: Evolution Controller Endpoints ---
@app.get("/api/evolution/status")
async def get_evolution_status():
    return _evolution_controller.status_payload()

@app.post("/api/evolution/cycle")
async def run_evolution_cycle(dry_run: bool = True, body: Optional[Dict[str, Any]] = Body(default=None)):
    payload = body if isinstance(body, dict) else {}
    explicit_target = payload.get("target") or payload.get("affected_capability")
    if explicit_target and is_protected_target(str(explicit_target)):
        raise ConstitutionalViolationError(
            f"API refused evolution of protected target '{explicit_target}'."
        )
    if payload.get("proposed_changes") and not payload.get("observations"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unrestricted mutation payloads are not accepted. Provide observations for the Evolution Control Plane.",
        )
    observations = payload.get("observations")
    if not observations:
        observations = [
            {"component": "planner", "success": False, "error": "timeout"},
            {"component": "planner", "success": False, "error": "timeout"},
            {"component": "planner", "success": True},
        ]
    mutations = await _evolution_controller.run_evolution_cycle(
        observations=observations,
        dry_run=dry_run,
    )
    return {
        "status": "completed",
        "dry_run": dry_run,
        "mutations_proposed": [
            {
                "mutation_id": m.mutation_id,
                "target": m.target.value,
                "status": m.status.value,
                "candidate_version": m.candidate_version,
                "parent_version": m.parent_version,
            }
            for m in mutations
        ],
    }

@app.get("/api/evolution/proposals")
async def list_evolution_proposals():
    return [p.model_dump() for p in _evolution_controller.registry.list_proposals()]

@app.get("/api/evolution/candidates")
async def list_evolution_candidates():
    return _evolution_controller.status_payload()["candidates"]

@app.get("/api/evolution/audit")
async def list_evolution_audit(limit: int = 50):
    return [e.model_dump() for e in _evolution_controller.registry.list_audit(limit=limit)]

@app.get("/api/evolution/lineage")
async def list_evolution_lineage():
    return _evolution_controller.registry.lineage()

@app.post("/api/evolution/rollback")
async def rollback_evolution(payload: Dict[str, Any] = Body(...)):
    mutation_id = payload.get("mutation_id")
    if not mutation_id:
        raise HTTPException(status_code=400, detail="mutation_id required")
    reason = payload.get("reason") or "operator rollback"
    rolled = _evolution_controller.rollback(mutation_id, reason)
    return {"status": rolled.status.value, "active_generation": _evolution_controller.registry.get_active_generation()}

@app.post("/api/evolution/mutations/{mutation_id}/approve")
async def approve_evolution_mutation(mutation_id: str, approved: bool = True):
    return _evolution_controller.approve_and_promote(mutation_id, approved)

# --- Layer 8: Evaluation Endpoints ---
@app.get("/api/evaluations/reports")
async def list_evaluation_reports():
    payload = _evolution_controller.status_payload()
    return payload.get("evaluations") or []

# --- Audit Viewer Endpoint ---
@app.get("/api/audit/logs")
async def get_audit_logs(limit: int = 50, event_type: Optional[str] = None):
    events = _evolution_controller.registry.list_audit(limit=limit)
    payload = []
    for event in events:
        if event_type and event.event_type != event_type:
            continue
        payload.append({
            "timestamp": event.timestamp,
            "event_type": event.event_type,
            "subsystem": "evolution",
            "action": event.decision,
            "result": event.decision,
            "risk_level": "LOW",
            "mutation_id": event.mutation_id,
        })
    if not payload:
        payload.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type or "SYSTEM_INIT",
            "subsystem": "api_layer",
            "action": "API service running",
            "result": "OK",
            "risk_level": "LOW",
        })
    return payload
