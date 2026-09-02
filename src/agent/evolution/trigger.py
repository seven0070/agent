"""
Evolution Trigger: decides when an observed weakness is strong enough to propose.

Avoids uncontrolled evolution loops by requiring evidence, limiting in-flight
candidates, and applying a cooldown between cycles.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from agent.evolution.protection import is_evolvable_target, is_protected_target
from agent.logging import get_logger

logger = get_logger("agent.evolution.trigger")


class EvolutionTrigger:
    def __init__(
        self,
        min_failures: int = 2,
        failure_threshold: float = 0.5,
        cooldown_seconds: float = 0.0,
        max_in_flight: int = 1,
    ) -> None:
        self.min_failures = min_failures
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.max_in_flight = max_in_flight
        self._last_trigger_monotonic: float = 0.0

    def select_trigger(
        self,
        weaknesses: List[Dict[str, Any]],
        in_flight_count: int = 0,
        now: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Returns the highest-priority weakness that is eligible for a proposal,
        or None if evolution should not fire.
        """
        if in_flight_count >= self.max_in_flight:
            logger.info("Evolution trigger suppressed: in-flight candidate limit reached")
            return None

        clock = now if now is not None else time.monotonic()
        if self.cooldown_seconds > 0 and (clock - self._last_trigger_monotonic) < self.cooldown_seconds:
            logger.info("Evolution trigger suppressed: cooldown active")
            return None

        eligible: List[Dict[str, Any]] = []
        for weakness in weaknesses:
            target = str(weakness.get("target", ""))
            failures = int(weakness.get("failures", 0))
            fail_rate = float(weakness.get("failure_rate", 0.0))
            if is_protected_target(target) or not is_evolvable_target(target):
                logger.warning(f"Ignoring non-evolvable weakness target '{target}'")
                continue
            if failures < self.min_failures:
                continue
            if fail_rate < self.failure_threshold:
                continue
            eligible.append(weakness)

        if not eligible:
            return None

        eligible.sort(key=lambda item: float(item.get("failure_rate", 0.0)), reverse=True)
        chosen = eligible[0]
        self._last_trigger_monotonic = clock
        logger.info(
            f"Evolution trigger armed for target '{chosen.get('target')}' "
            f"(failure_rate={chosen.get('failure_rate')})"
        )
        return chosen
