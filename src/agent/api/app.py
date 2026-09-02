"""
FastAPI Application Core for Layer 10 Public Agent Service.
Single execution path: USER GOAL → CORE → MODEL → MEMORY → PLANNER → TOOLS/JCODE → RUNTIME → EVAL → RESULT.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from agent.api.schemas import ChatMessageRequest, SessionCreateRequest, SessionResponse, StreamEventFrame
from agent.capabilities.broker import CapabilityBroker
from agent.capabilities.models import PermissionLevel
from agent.config import get_settings
from agent.constitution import ConstitutionalGuard, ConstitutionalViolationError
from agent.core.pipeline import AgentPipeline
from agent.evolution.controller import EvolutionController
from agent.evolution.models import EvolutionMode
from agent.evolution.protection import is_protected_target
from agent.integrations.agentscope.adapter import AgentScopeAdapter
from agent.logging import get_logger
from agent.memory.session import SessionMemoryManager
from agent.orchestration.orchestrator import PlanOrchestrator
from agent.orchestration.planner import RuleBasedPlanner

logger = get_logger("agent.api.app")
settings = get_settings()

app = FastAPI(
    title="Agent Local API",
    description="Layer 10 service boundary over Layers -1 through 9",
    version=settings.agent_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_manager = SessionMemoryManager()
planner = RuleBasedPlanner()
broker = CapabilityBroker()
orchestrator = PlanOrchestrator(broker=broker)
guard = ConstitutionalGuard()
adapter = AgentScopeAdapter(planner=planner, broker=broker, orchestrator=orchestrator)
_evolution_controller = EvolutionController(
    db_path=os.path.join(settings.data_dir, "evolution.db"),
    data_dir=settings.data_dir,
    mode=EvolutionMode.SEMI_AUTOMATIC,
)
pipeline = AgentPipeline(
    adapter=adapter,
    evolution=_evolution_controller,
    broker=broker,
    guard=guard,
)
_evolution_controller._audit("SYSTEM_INIT", "OK", subsystem="api_layer")

_SESSIONS: Dict[str, Dict[str, Any]] = {}
_PLANS: Dict[str, Dict[str, Any]] = {}
_SETTINGS_PATH = os.path.join(settings.data_dir, "settings.json")

DEMO_OBSERVATIONS = [
    {"component": "planner", "success": False, "error": "timeout"},
    {"component": "planner", "success": False, "error": "timeout"},
    {"component": "planner", "success": True},
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_settings() -> Dict[str, Any]:
    defaults = {
        "model_provider": "mock",
        "model_name": "mock-primary-v1",
        "local_model_host": "http://127.0.0.1:11434",
        "runtime_timeout_seconds": 30,
        "data_dir": settings.data_dir,
        "evolution_mode": _evolution_controller.mode.value,
        "agent_version": settings.agent_version,
    }
    if os.path.isfile(_SETTINGS_PATH):
        try:
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as handle:
                stored = json.load(handle)
            if isinstance(stored, dict):
                defaults.update({k: v for k, v in stored.items() if k in defaults or k in {"model_provider", "model_name", "local_model_host", "runtime_timeout_seconds"}})
        except (OSError, json.JSONDecodeError):
            pass
    return defaults


def _save_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    current = _load_settings()
    forbidden = {"permission_ceiling", "constitution", "evolution_boundaries", "audit_integrity"}
    for key in forbidden:
        if key in payload:
            raise ConstitutionalViolationError(f"Settings cannot modify protected boundary '{key}'.")
    allowed = {"model_provider", "model_name", "local_model_host", "runtime_timeout_seconds"}
    for key, value in payload.items():
        if key in allowed:
            current[key] = value
    os.makedirs(os.path.dirname(_SETTINGS_PATH), exist_ok=True)
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as handle:
        json.dump(current, handle, indent=2)
    return current


def _store_plan(plan) -> Dict[str, Any]:
    payload = {
        "plan_id": plan.id,
        "status": plan.status,
        "goal": plan.goal,
        "version": plan.version,
        "tasks": [t.model_dump() for t in plan.tasks.values()],
    }
    _PLANS[plan.id] = payload
    _PLANS["plan-001"] = payload
    return payload


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
    evo = _evolution_controller.status_payload()
    return {
        "status": "online",
        "timestamp": _utcnow(),
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
            "desktop": "active",
        },
        "active_generation": evo.get("active_generation"),
        "pending_approvals": len(evo.get("pending_approvals") or []),
    }


@app.get("/api/sessions", response_model=List[SessionResponse])
async def list_sessions():
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
    sid = f"sess-{uuid.uuid4().hex[:8]}"
    now = _utcnow()
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
    session_manager.add_turn(sid, "system", "Session initialized")
    logger.info(f"Created API session '{sid}'")
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


@app.get("/api/workspace/files")
async def list_workspace_files(session_id: Optional[str] = None):
    base_root = os.path.realpath(os.path.join(settings.data_dir, "workspace"))
    os.makedirs(base_root, exist_ok=True)
    target_root = base_root
    if session_id:
        clean_sid = os.path.basename(session_id)
        candidate_root = os.path.realpath(os.path.join(base_root, clean_sid))
        try:
            common = os.path.commonpath([base_root, candidate_root])
        except ValueError:
            common = ""
        if common == base_root and os.path.exists(candidate_root):
            target_root = candidate_root

    files_list = []
    for root, dirs, filenames in os.walk(target_root):
        real_root = os.path.realpath(root)
        try:
            if os.path.commonpath([base_root, real_root]) != base_root:
                continue
        except ValueError:
            continue
        for f in filenames:
            full_p = os.path.realpath(os.path.join(real_root, f))
            try:
                if os.path.commonpath([base_root, full_p]) != base_root:
                    continue
            except ValueError:
                continue
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


@app.post("/api/chat/stream")
async def stream_chat_message(req: ChatMessageRequest):
    if req.session_id not in _SESSIONS:
        _SESSIONS[req.session_id] = {
            "session_id": req.session_id,
            "title": f"Session {req.session_id[:8]}",
            "created_at": _utcnow(),
            "updated_at": _utcnow(),
            "messages": [],
            "active_plan_id": None,
            "metadata": {},
        }

    queue: asyncio.Queue = asyncio.Queue()

    def sink(event_type: str, payload: Dict[str, Any]) -> None:
        frame = StreamEventFrame(event_type=event_type, session_id=req.session_id, payload=payload)
        queue.put_nowait(frame)

    async def runner():
        try:
            outcome = await pipeline.execute(session_id=req.session_id, prompt=req.prompt, sink=sink)
            plan = outcome.get("plan")
            result = outcome.get("result")
            if plan is not None:
                _store_plan(plan)
                _SESSIONS[req.session_id]["active_plan_id"] = plan.id
            content = result.output if result else ""
            _SESSIONS[req.session_id]["messages"].append({"role": "user", "content": req.prompt})
            _SESSIONS[req.session_id]["messages"].append({"role": "assistant", "content": content})
            _SESSIONS[req.session_id]["updated_at"] = _utcnow()
        except ConstitutionalViolationError as exc:
            sink("SYSTEM_ERROR", {"error": str(exc), "kind": "constitutional"})
        except Exception as exc:  # noqa: BLE001 — surface to the client
            logger.exception("Chat pipeline failed")
            sink("SYSTEM_ERROR", {"error": str(exc)})
        finally:
            queue.put_nowait(None)

    async def event_generator():
        task = asyncio.create_task(runner())
        try:
            while True:
                frame = await queue.get()
                if frame is None:
                    break
                yield f"data: {frame.model_dump_json()}\n\n"
        finally:
            await task

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/plans/{plan_id}")
async def get_plan(plan_id: str):
    if plan_id in _PLANS:
        payload = dict(_PLANS[plan_id])
        payload["plan_id"] = plan_id
        return payload
    raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found.")


@app.get("/api/approvals")
async def list_pending_approvals():
    return list(_evolution_controller.approval_handler.list_pending())


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
    return [
        {
            "tool_id": t.id,
            "description": t.description,
            "risk_level": t.risk_level.value,
            "permission": broker.permission_policy.get_permission(t.id, t.risk_level).value,
        }
        for t in tools
    ]


@app.get("/api/coding/workspace")
async def get_coding_workspace():
    candidates = _evolution_controller.registry.list_candidates()
    changed = []
    last_run = {"passed": 0, "failed": 0, "status": "IDLE"}
    if candidates:
        latest = candidates[-1]
        changed = list(latest.files_changed)
        last_run = {
            "passed": 1 if latest.status.value == "IMPLEMENTED" else 0,
            "failed": 0,
            "status": latest.status.value,
        }
    return {
        "status": "idle",
        "active_task": None,
        "workspace_root": os.path.join(settings.data_dir, "workspace"),
        "changed_files": changed,
        "last_test_run": last_run if changed else {"passed": 0, "failed": 0, "status": "IDLE"},
    }


@app.get("/api/memory/search")
async def search_memory(query: str, session_id: Optional[str] = None):
    if session_id:
        history = session_manager.get_session_history(session_id, limit=20)
        return [{"id": h.id, "type": h.memory_type.value, "content": h.content, "source": h.source} for h in history]
    if query:
        hits = []
        for sid, sdata in _SESSIONS.items():
            for msg in sdata.get("messages", []):
                if query.lower() in str(msg.get("content", "")).lower():
                    hits.append({"session_id": sid, "role": msg.get("role"), "content": msg.get("content")})
        return hits[:20]
    return []


@app.get("/api/activity")
async def get_activity(limit: int = 80, session_id: Optional[str] = None):
    return pipeline.recent_activity(limit=limit, session_id=session_id)


@app.get("/api/settings")
async def get_runtime_settings():
    payload = _load_settings()
    payload["permissions"] = {
        tool.id: broker.permission_policy.get_permission(tool.id, tool.risk_level).value
        for tool in broker.registry.list_tools()
    }
    payload["permissions"]["shell-v1"] = PermissionLevel.DENY.value
    payload["constitution_locked"] = True
    payload["data_dir"] = settings.data_dir
    return payload


@app.post("/api/settings")
async def update_runtime_settings(body: Dict[str, Any] = Body(...)):
    return _save_settings(body)


@app.get("/api/trust/constitution")
async def get_constitution_status():
    invariants = guard.get_active_invariants()
    return {
        "protected": True,
        "identity": True,
        "coreObjectives": True,
        "permissionCeiling": True,
        "credentialBoundary": True,
        "auditIntegrity": True,
        "rollbackAuthority": True,
        "evolutionBoundary": True,
        "invariants": [{"name": inv.name, "description": inv.description} for inv in invariants],
        "protected_boundaries": list(ConstitutionalGuard.PROTECTED_BOUNDARIES),
    }


@app.get("/api/evolution/status")
async def get_evolution_status():
    return _evolution_controller.status_payload()


@app.post("/api/evolution/cycle")
async def run_evolution_cycle(dry_run: bool = True, demo: bool = False, body: Optional[Dict[str, Any]] = Body(default=None)):
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
        if dry_run or demo or payload.get("demo"):
            observations = list(DEMO_OBSERVATIONS)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Observations are required for a live evolution cycle. Pass demo=true to run the deterministic capability-gap demonstration.",
            )
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
        "active_generation": _evolution_controller.registry.get_active_generation(),
        "pending_approvals": _evolution_controller.approval_handler.list_pending(),
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


@app.get("/api/evaluations/reports")
async def list_evaluation_reports():
    payload = _evolution_controller.status_payload()
    return payload.get("evaluations") or []


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
            "timestamp": _utcnow(),
            "event_type": event_type or "SYSTEM_INIT",
            "subsystem": "api_layer",
            "action": "API service running",
            "result": "OK",
            "risk_level": "LOW",
        })
    return payload
