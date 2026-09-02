"""
Evolution Observer Analyzing Audit Logs and Failure Signals.
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from agent.evolution.models import SignalType
from agent.evolution.protection import EVOLVABLE_TARGETS
from agent.logging import get_logger

logger = get_logger("agent.evolution.observer")

_COMPONENT_TARGET_MAP = {
    "planner": "planner_strategy",
    "orchestrator": "planner_strategy",
    "planning": "planner_strategy",
    "routing": "agent_routing",
    "agent_routing": "agent_routing",
    "tool": "tool_selection_policy",
    "tools": "tool_selection_policy",
    "broker": "tool_selection_policy",
    "skill": "skill_definitions",
    "skills": "skill_definitions",
    "memory": "memory_retrieval_strategy",
    "rag": "memory_retrieval_strategy",
    "model": "model_routing",
    "models": "model_routing",
    "router": "model_routing",
    "composition": "agent_composition",
    "agent": "agent_composition",
}


class EvolutionObserver:
    """
    Consumes evidence and audit events from agent, orchestration, runtime, and evaluation runs
    to detect repeated failure signals and performance bottlenecks.
    """

    def __init__(self, failure_threshold: float = 0.5) -> None:
        self.failure_threshold = failure_threshold
        self._observed_events: List[Dict[str, Any]] = []

    def observe_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Records an observed event from the execution pipeline."""
        entry = {"event_type": event_type, "payload": payload}
        self._observed_events.append(entry)

    def record_observation(
        self,
        component: str,
        success: bool,
        error: Optional[str] = None,
        latency_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        signal_type: Optional[str] = None,
    ) -> None:
        """Convenience method for recording structured observations per component."""
        inferred = signal_type or self._infer_signal_type(component, success, error, metadata or {})
        payload = {
            "component": component,
            "success": success,
            "error": error,
            "latency_ms": latency_ms,
            "metadata": metadata or {},
            "signal_type": inferred,
        }
        self.observe_event("component_observation", payload)

    def record_capability_gap(self, capability: str, evidence: Dict[str, Any]) -> None:
        self.record_observation(
            component=capability,
            success=False,
            error=str(evidence.get("reason") or "capability gap"),
            metadata=evidence,
            signal_type=SignalType.CAPABILITY_GAP.value,
        )

    def record_evaluation_regression(self, component: str, regressions: List[str]) -> None:
        self.record_observation(
            component=component,
            success=False,
            error=f"evaluation regressions: {regressions}",
            metadata={"regressions": regressions},
            signal_type=SignalType.EVALUATION_REGRESSION.value,
        )

    @staticmethod
    def _infer_signal_type(component: str, success: bool, error: Optional[str], metadata: Dict[str, Any]) -> str:
        if not success:
            if metadata.get("regressions"):
                return SignalType.EVALUATION_REGRESSION.value
            if component in {"tool", "tools", "broker"}:
                return SignalType.TOOL_FAILURE.value
            if component in {"planner", "orchestrator", "planning"}:
                return SignalType.PLANNING_FAILURE.value
            if error:
                return SignalType.TASK_FAILURE.value
            return SignalType.CAPABILITY_GAP.value
        if float(metadata.get("latency_ms") or 0) > 5000:
            return SignalType.PERFORMANCE_DEGRADATION.value
        return "ok"

    def map_component_to_target(self, component: str) -> str:
        mapped = _COMPONENT_TARGET_MAP.get(component, component)
        if mapped in EVOLVABLE_TARGETS:
            return mapped
        if component in {"planner", "orchestrator"}:
            return "planner_strategy"
        return mapped

    def identify_weaknesses(self, failure_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Analyzes recorded observations per component and identifies targets exceeding failure threshold.
        """
        thresh = failure_threshold if failure_threshold is not None else self.failure_threshold
        component_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"total": 0, "failures": 0, "errors": [], "signals": []}
        )

        for item in self._observed_events:
            payload = item.get("payload", {})
            comp = payload.get("component", "system")
            success = payload.get("success", True)

            component_stats[comp]["total"] += 1
            if not success:
                component_stats[comp]["failures"] += 1
                if payload.get("error"):
                    component_stats[comp]["errors"].append(payload.get("error"))
                component_stats[comp]["signals"].append(payload.get("signal_type"))

        weaknesses: List[Dict[str, Any]] = []
        for comp, stats in component_stats.items():
            total = stats["total"]
            failures = stats["failures"]
            fail_rate = failures / total if total > 0 else 0.0

            if fail_rate >= thresh:
                target = self.map_component_to_target(comp)
                signal = SignalType.REPEATED_FAILURE.value if failures >= 2 else SignalType.TASK_FAILURE.value
                weaknesses.append({
                    "component": comp,
                    "target": target,
                    "failure_rate": fail_rate,
                    "total_runs": total,
                    "failures": failures,
                    "errors": stats["errors"][:10],
                    "signal_type": signal,
                    "reason": f"Component '{comp}' exceeded failure threshold ({fail_rate:.2f} >= {thresh})",
                })

        logger.info(f"EvolutionObserver identified {len(weaknesses)} weaknesses across {len(component_stats)} components")
        return weaknesses
