"""
Canary Manager for Monitoring Candidate Deployments under Shadow/Traffic Splitting.
"""

from typing import Dict, Any, Optional
from agent.evolution.models import Mutation, CanaryStatus, MutationStatus
from agent.logging import get_logger

logger = get_logger("agent.evolution.canary")

class CanaryManager:
    """
    Manages canary phase for approved candidate mutations before full promotion.
    """

    def __init__(self) -> None:
        pass

    def start_canary(self, mutation: Mutation, duration_steps: int = 10, traffic_percentage: float = 0.1) -> Mutation:
        """
        Initializes canary monitoring on an approved candidate.
        """
        mutation.status = MutationStatus.CANARY
        mutation.canary_status = CanaryStatus.HEALTHY
        mutation.canary_metrics = {
            "traffic_percentage": traffic_percentage,
            "target_steps": duration_steps,
            "completed_steps": 0,
            "successes": 0,
            "failures": 0,
            "error_rate": 0.0,
            "avg_latency_ms": 0.0,
        }
        logger.info(f"Canary started for '{mutation.mutation_id}' ({mutation.candidate_version}) with {traffic_percentage*100}% traffic over {duration_steps} steps.")
        return mutation

    def record_canary_step(self, mutation: Mutation, success: bool, latency_ms: float = 0.0) -> CanaryStatus:
        """
        Records a step result in the canary phase and re-evaluates canary status.
        """
        if mutation.status != MutationStatus.CANARY:
            raise ValueError(f"Mutation '{mutation.mutation_id}' is not in CANARY status.")

        metrics = mutation.canary_metrics
        metrics["completed_steps"] += 1
        if success:
            metrics["successes"] += 1
        else:
            metrics["failures"] += 1

        total = metrics["completed_steps"]
        metrics["error_rate"] = metrics["failures"] / total if total > 0 else 0.0

        # Simple rolling avg latency
        prev_avg = metrics["avg_latency_ms"]
        metrics["avg_latency_ms"] = prev_avg + (latency_ms - prev_avg) / total

        return self.evaluate_canary_health(mutation)

    def evaluate_canary_health(self, mutation: Mutation, max_error_rate: float = 0.05) -> CanaryStatus:
        """
        Evaluates canary health against error rate thresholds and target duration.
        """
        metrics = mutation.canary_metrics
        error_rate = metrics.get("error_rate", 0.0)
        completed = metrics.get("completed_steps", 0)
        target = metrics.get("target_steps", 10)

        if error_rate > max_error_rate:
            mutation.canary_status = CanaryStatus.FAILED
            logger.warning(f"Canary failed for '{mutation.mutation_id}': error_rate={error_rate:.2f} > threshold={max_error_rate}")
        elif completed >= target:
            mutation.canary_status = CanaryStatus.COMPLETED
            logger.info(f"Canary completed successfully for '{mutation.mutation_id}'")
        else:
            mutation.canary_status = CanaryStatus.HEALTHY

        return mutation.canary_status
