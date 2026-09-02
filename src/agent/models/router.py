"""
Model Router & Controlled Fallback Execution Engine.
"""

import time
from typing import List, Optional, Dict, Any, Callable, Awaitable
from agent.models.spec import ModelSpec, ModelHealthStatus
from agent.models.registry import ModelRegistry
from agent.models.factory import ModelFactory
from agent.core.models import ModelExecutionResult, AgentTask
from agent.logging import get_logger

logger = get_logger("agent.models.router")

class ModelRouter:
    """
    Deterministic Model Router & Controlled Fallback Engine.
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        factory: Optional[ModelFactory] = None,
        max_attempts: int = 3,
    ) -> None:
        self.registry = registry or self._create_default_registry()
        self.factory = factory or ModelFactory()
        self.max_attempts = max_attempts

    def _create_default_registry(self) -> ModelRegistry:
        reg = ModelRegistry()
        reg.register(
            ModelSpec(
                id="primary",
                provider="mock",
                model_name="mock-primary-v1",
                priority=1,
            )
        )
        reg.register(
            ModelSpec(
                id="fallback-1",
                provider="mock",
                model_name="mock-fallback-v1",
                priority=2,
            )
        )
        return reg

    def select_model(self, required_capabilities: Optional[Dict[str, bool]] = None) -> ModelSpec:
        """
        Selects the best available model matching requested capabilities sorted by priority.
        Promoted evolution artifacts may pin a preferred model id.
        """
        try:
            from agent.evolution.generation import load_artifact
            routing = load_artifact("model_routing") or {}
            preferred = (routing.get("proposed_changes") or {}).get("preferred_model_id")
            if preferred:
                for spec in self.registry.list_enabled():
                    if spec.id == preferred:
                        return spec
        except Exception:
            pass

        candidates = self.registry.list_enabled()
        if not candidates:
            raise RuntimeError("No enabled models available in ModelRegistry.")

        if required_capabilities:
            matching = []
            for spec in candidates:
                caps = spec.capabilities.model_dump()
                if all(caps.get(req_cap, False) for req_cap, required in required_capabilities.items() if required):
                    matching.append(spec)
            if matching:
                return matching[0]

        return candidates[0]

    def select_fallback_chain(self, primary_id: str) -> List[ModelSpec]:
        """Returns ordered fallback specs excluding the primary model."""
        all_enabled = self.registry.list_enabled()
        return [m for m in all_enabled if m.id != primary_id]

    async def execute_with_fallback(
        self,
        task: AgentTask,
        executor_fn: Callable[[ModelSpec], Awaitable[str]],
    ) -> ModelExecutionResult:
        """
        Executes model invocation function `executor_fn` with primary model and automatic fallback chain.
        Tracks execution latency, health status changes, and returns ModelExecutionResult.
        """
        primary_spec = self.select_model(task.required_capabilities)
        candidate_chain = [primary_spec] + self.select_fallback_chain(primary_spec.id)

        attempts = 0
        last_error: Optional[Exception] = None

        for spec in candidate_chain:
            if attempts >= self.max_attempts:
                logger.warning(
                    f"Max attempts ({self.max_attempts}) reached for task '{task.task_id}'. Stopping fallback chain."
                )
                break

            attempts += 1
            is_fallback = (spec.id != primary_spec.id)
            start_time = time.perf_counter()

            logger.info(
                f"Attempt {attempts}: Executing model '{spec.id}' ({spec.provider}/{spec.model_name}) [fallback={is_fallback}]"
            )

            try:
                output = await executor_fn(spec)
                latency_ms = (time.perf_counter() - start_time) * 1000

                # Restore health to AVAILABLE on successful execution
                if spec.health_status in [ModelHealthStatus.DEGRADED, ModelHealthStatus.UNAVAILABLE]:
                    self.registry.update_health(spec.id, ModelHealthStatus.AVAILABLE)

                return ModelExecutionResult(
                    model_id=spec.id,
                    provider=spec.provider,
                    output=output,
                    status="success",
                    latency_ms=round(latency_ms, 2),
                    is_fallback=is_fallback,
                )

            except Exception as exc:
                latency_ms = (time.perf_counter() - start_time) * 1000
                last_error = exc
                logger.error(
                    f"Model '{spec.id}' failed on attempt {attempts}: {str(exc)}. Degrading health state."
                )

                # Update health state of failing model
                new_status = ModelHealthStatus.DEGRADED if spec.health_status == ModelHealthStatus.AVAILABLE else ModelHealthStatus.UNAVAILABLE
                self.registry.update_health(spec.id, new_status)

        # If all candidates/attempts failed:
        error_msg = str(last_error) if last_error else "All candidate models failed."
        return ModelExecutionResult(
            model_id=primary_spec.id,
            provider=primary_spec.provider,
            output="",
            status="error",
            error=error_msg,
            is_fallback=False,
        )
