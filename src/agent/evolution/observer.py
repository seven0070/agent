"""
Evolution Observer Analyzing Audit Logs and Failure Signals.
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from agent.logging import get_logger

logger = get_logger("agent.evolution.observer")

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
    ) -> None:
        """Convenience method for recording structured observations per component."""
        payload = {
            "component": component,
            "success": success,
            "error": error,
            "latency_ms": latency_ms,
            "metadata": metadata or {},
        }
        self.observe_event("component_observation", payload)

    def identify_weaknesses(self, failure_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Analyzes recorded observations per component and identifies targets exceeding failure threshold.
        """
        thresh = failure_threshold if failure_threshold is not None else self.failure_threshold
        component_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "failures": 0})

        for item in self._observed_events:
            payload = item.get("payload", {})
            comp = payload.get("component", "system")
            success = payload.get("success", True)

            component_stats[comp]["total"] += 1
            if not success:
                component_stats[comp]["failures"] += 1

        weaknesses: List[Dict[str, Any]] = []
        for comp, stats in component_stats.items():
            total = stats["total"]
            failures = stats["failures"]
            fail_rate = failures / total if total > 0 else 0.0

            if fail_rate >= thresh:
                # Map component name to MutationTarget string
                target = "planner_strategy" if comp in ["planner", "orchestrator"] else comp
                weaknesses.append({
                    "component": comp,
                    "target": target,
                    "failure_rate": fail_rate,
                    "total_runs": total,
                    "failures": failures,
                    "reason": f"Component '{comp}' exceeded failure threshold ({fail_rate:.2f} >= {thresh})",
                })

        logger.info(f"EvolutionObserver identified {len(weaknesses)} weaknesses across {len(component_stats)} components")
        return weaknesses
