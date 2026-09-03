#!/usr/bin/env python3
"""Run the deterministic real-world Agent benchmark against the current implementation."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from tests.benchmark.cases import BenchmarkCase, build_cases, build_open_ended_cases  # noqa: E402


def _seed(workspace: Path, files: list[tuple[str, str]]) -> None:
    for rel, content in files:
        path = workspace / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _tools_from_plan(plan: Any) -> list[str]:
    if plan is None:
        return []
    return [t.required_tool_id for t in plan.tasks.values() if t.required_tool_id]


def _output_from_plan(plan: Any) -> str:
    if plan is None:
        return ""
    parts = []
    for task in plan.tasks.values():
        if task.outputs is not None:
            parts.append(str(task.outputs))
        if task.error:
            parts.append(str(task.error))
    return "\n".join(parts)


def run_core(case: BenchmarkCase) -> Dict[str, Any]:
    from agent.capabilities.broker import CapabilityBroker
    from agent.capabilities.models import PermissionLevel
    from agent.orchestration.orchestrator import PlanOrchestrator
    from agent.orchestration.planner import RuleBasedPlanner

    workspace = Path(tempfile.mkdtemp(prefix=f"bench-{case.case_id}-"))
    broker = CapabilityBroker(workspace_dir=str(workspace))
    sandbox_ws = Path(broker.workspace_manager.workspace_dir)
    _seed(sandbox_ws, case.setup_files)
    broker.permission_policy.set_permission("write_file-v1", PermissionLevel.ALLOW)
    broker.permission_policy.set_permission("coding-engine-v1", PermissionLevel.ALLOW)
    planner = RuleBasedPlanner()
    orchestrator = PlanOrchestrator(broker=broker)
    started = time.perf_counter()
    plan = planner.create_plan(case.prompt, workspace_dir=str(sandbox_ws))
    completed = orchestrator.execute_plan(plan)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    retries = sum(t.retry_count for t in completed.tasks.values())
    replanned = completed.version != "plan-v1"
    return {
        "workspace": str(sandbox_ws),
        "plan": completed,
        "plan_status": completed.status,
        "tools": _tools_from_plan(completed),
        "output": _output_from_plan(completed),
        "error": None,
        "elapsed_ms": elapsed_ms,
        "retries": retries,
        "replanned": replanned,
        "human_intervention": False,
    }


def run_pipeline(case: BenchmarkCase) -> Dict[str, Any]:
    import asyncio

    from agent.capabilities.broker import CapabilityBroker
    from agent.capabilities.models import PermissionLevel
    from agent.core.pipeline import AgentPipeline
    from agent.evolution.controller import EvolutionController
    from agent.evolution.models import EvolutionMode
    from agent.integrations.agentscope.adapter import AgentScopeAdapter
    from agent.memory.context import ContextBuilder
    from agent.memory.session import SessionMemoryManager
    from agent.memory.sqlite import SQLiteMemoryBackend
    from agent.orchestration.orchestrator import PlanOrchestrator
    from agent.orchestration.planner import RuleBasedPlanner

    workspace = Path(tempfile.mkdtemp(prefix=f"bench-{case.case_id}-"))
    broker = CapabilityBroker(workspace_dir=str(workspace))
    sandbox_ws = Path(broker.workspace_manager.workspace_dir)
    _seed(sandbox_ws, case.setup_files)
    session_manager = SessionMemoryManager()
    memory = SQLiteMemoryBackend(db_path=str(workspace / "memory.db"))
    adapter = AgentScopeAdapter(
        planner=RuleBasedPlanner(),
        broker=broker,
        orchestrator=PlanOrchestrator(broker=broker),
        context_builder=ContextBuilder(session_manager=session_manager, long_term_memory=memory),
    )
    evolution = EvolutionController(
        db_path=str(workspace / "evolution.db"),
        data_dir=str(workspace),
        mode=EvolutionMode.SEMI_AUTOMATIC,
    )
    pipeline = AgentPipeline(adapter=adapter, evolution=evolution, broker=broker)
    started = time.perf_counter()
    outcome = asyncio.run(pipeline.execute(session_id="bench-session", prompt=case.prompt))
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    plan = outcome.get("plan")
    result = outcome.get("result")
    evaluation = outcome.get("evaluation") or {}
    return {
        "workspace": str(sandbox_ws),
        "plan": plan,
        "plan_status": getattr(plan, "status", None),
        "tools": _tools_from_plan(plan),
        "output": getattr(result, "output", "") if result is not None else "",
        "error": None,
        "elapsed_ms": elapsed_ms,
        "retries": sum(t.retry_count for t in plan.tasks.values()) if plan else 0,
        "replanned": bool(plan and plan.version != "plan-v1"),
        "human_intervention": False,
        "evaluation": evaluation,
        "memory_turns": len(session_manager.get_session_history("bench-session", limit=20)),
    }


def run_evolution(case: BenchmarkCase) -> Dict[str, Any]:
    import asyncio

    from agent.constitution import ConstitutionalViolationError
    from agent.evolution.controller import EvolutionController
    from agent.evolution.models import EvolutionMode
    from agent.evolution.protection import is_protected_target

    workspace = Path(tempfile.mkdtemp(prefix=f"bench-{case.case_id}-"))
    controller = EvolutionController(
        db_path=str(workspace / "evolution.db"),
        data_dir=str(workspace),
        mode=EvolutionMode.AUTOMATIC,
        auto_approve=True,
    )
    started = time.perf_counter()
    details: Dict[str, Any] = {}
    error = None
    if case.case_id == "evolution-reject-protected":
        blocked = is_protected_target("constitutional_rules")
        try:
            controller.guard.validate_action(
                {"type": "promote_candidate", "target": "constitutional_rules", "human_approved": True}
            )
            raised = False
        except ConstitutionalViolationError as exc:
            raised = True
            error = str(exc)
        src = ROOT / "src" / "agent" / "constitution.py"
        details["protected"] = blocked and raised and src.exists()
        output = "protected-blocked" if details["protected"] else "not-blocked"
        status = "completed" if details["protected"] else "failed"
    else:
        observations = [
            {"component": "planner", "success": False, "error": "timeout"},
            {"component": "planner", "success": False, "error": "timeout"},
            {"component": "planner", "success": True},
        ]
        mutations = asyncio.run(controller.run_evolution_cycle(observations=observations, dry_run=False))
        active = controller.registry.get_active_generation()
        if mutations:
            mutation = mutations[0]
            before = src_text = (ROOT / "src" / "agent" / "constitution.py").read_bytes()
            if mutation.status.value in {"PROMOTED", "CANARY", "APPROVED"}:
                controller.rollback(mutation.mutation_id, reason="benchmark rollback")
            after = (ROOT / "src" / "agent" / "constitution.py").read_bytes()
            details["status"] = mutation.status.value
            details["active"] = controller.registry.get_active_generation()
            details["constitution_intact"] = before == after
            details["candidates_isolated"] = (workspace / "candidates").exists()
            output = f"{mutation.status.value}:{details['active']}"
            status = "completed" if details["constitution_intact"] else "failed"
        else:
            output = f"no-mutations:{active}"
            status = "completed"
            details["constitution_intact"] = True
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "workspace": str(workspace),
        "plan": None,
        "plan_status": status,
        "tools": [],
        "output": output,
        "error": error,
        "elapsed_ms": elapsed_ms,
        "retries": 0,
        "replanned": False,
        "human_intervention": False,
        "details": details,
    }


def evaluate_case(case: BenchmarkCase, ctx: Dict[str, Any]) -> Dict[str, Any]:
    check_results = []
    passed = True
    if case.path == "evolution":
        details = ctx.get("details") or {}
        if case.case_id == "evolution-reject-protected":
            ok = bool(details.get("protected"))
            check_results.append({"check": "protected-target-blocked", "passed": ok, "detail": str(details)})
            passed = ok
        else:
            ok = bool(details.get("constitution_intact", False))
            check_results.append({"check": "constitution-intact", "passed": ok, "detail": str(details)})
            passed = ok
        return {"passed": passed, "checks": check_results}
    for check in case.checks:
        try:
            ok, detail = check(ctx)
        except Exception as exc:  # noqa: BLE001
            ok, detail = False, f"check error: {exc}"
        check_results.append({"check": check.__name__ if hasattr(check, "__name__") else detail, "passed": ok, "detail": detail})
        if not ok:
            passed = False
    return {"passed": passed, "checks": check_results}


def _run_suite(name: str, cases: List[BenchmarkCase]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for case in cases:
        started = time.perf_counter()
        try:
            if case.path == "pipeline":
                ctx = run_pipeline(case)
            elif case.path == "evolution":
                ctx = run_evolution(case)
            else:
                ctx = run_core(case)
            verdict = evaluate_case(case, ctx)
            failure_reason = None
            if not verdict["passed"]:
                failure_reason = "; ".join(c["detail"] for c in verdict["checks"] if not c["passed"])
        except Exception as exc:  # noqa: BLE001
            ctx = {
                "workspace": "",
                "plan_status": "error",
                "tools": [],
                "output": "",
                "error": str(exc),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "retries": 0,
                "replanned": False,
                "human_intervention": False,
            }
            verdict = {"passed": False, "checks": []}
            failure_reason = f"exception: {exc}\n{traceback.format_exc(limit=4)}"
        rows.append(
            {
                "id": case.case_id,
                "category": case.category,
                "passed": verdict["passed"],
                "elapsed_ms": ctx.get("elapsed_ms"),
                "retries": ctx.get("retries"),
                "replanned": ctx.get("replanned"),
                "human_intervention": ctx.get("human_intervention"),
                "tools": ctx.get("tools"),
                "plan_status": ctx.get("plan_status"),
                "failure": failure_reason,
                "checks": verdict["checks"],
            }
        )

    passed = sum(1 for r in rows if r["passed"])
    total = len(rows)
    print(f"=== {name.upper()} BENCHMARK ===")
    print(f"score {passed}/{total} ({(passed / total * 100) if total else 0:.1f}%)")
    print("")
    print(f"{'ID':<28} {'CAT':<22} {'RES':<6} {'MS':>8} {'RETRY':>5}  FAIL")
    for row in rows:
        mark = "PASS" if row["passed"] else "FAIL"
        fail = (row["failure"] or "")[:90]
        print(f"{row['id']:<28} {row['category']:<22} {mark:<6} {row['elapsed_ms'] or 0:8.1f} {row['retries'] or 0:5}  {fail}")

    failed = [r for r in rows if not r["passed"]]
    categories: Dict[str, int] = {}
    for row in failed:
        key = row["category"]
        categories[key] = categories.get(key, 0) + 1
    print("\nFailure categories:")
    if not categories:
        print("  none")
    for cat_name, count in sorted(categories.items(), key=lambda kv: -kv[1]):
        print(f"  {cat_name}: {count}")
    print("")
    return {"name": name, "passed": passed, "total": total, "rows": rows}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run Agent real-world benchmarks")
    parser.add_argument(
        "--suite",
        choices=["core", "open-ended", "all"],
        default="all",
        help="Which benchmark suite to run (default: all)",
    )
    args = parser.parse_args()
    suites = []
    if args.suite in ("core", "all"):
        suites.append(("real-world", build_cases()))
    if args.suite in ("open-ended", "all"):
        suites.append(("open-ended", build_open_ended_cases()))

    reports = [_run_suite(name, cases) for name, cases in suites]
    report_path = ROOT / "tests" / "benchmark" / "last_report.json"
    report_path.write_text(json.dumps({"suites": reports}, indent=2), encoding="utf-8")
    print(f"Wrote {report_path}")
    return 0 if all(item["passed"] == item["total"] for item in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
