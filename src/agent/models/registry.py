"""
In-Memory Model Registry for Managing Configured Models.
"""

from typing import Dict, List, Optional
from agent.models.spec import ModelSpec, ModelHealthStatus

class ModelRegistry:
    """
    Registry for managing model specifications, health states, and routing metadata.
    """

    def __init__(self) -> None:
        self._models: Dict[str, ModelSpec] = {}

    def register(self, spec: ModelSpec) -> None:
        """Registers or updates a model specification."""
        self._models[spec.id] = spec

    def get(self, model_id: str) -> Optional[ModelSpec]:
        """Retrieves a model specification by ID."""
        return self._models.get(model_id)

    def list_all(self) -> List[ModelSpec]:
        """Lists all registered models sorted by priority."""
        return sorted(self._models.values(), key=lambda m: m.priority)

    def list_enabled(self) -> List[ModelSpec]:
        """Lists enabled models that are not disabled or unavailable."""
        blocked = {ModelHealthStatus.DISABLED, ModelHealthStatus.UNAVAILABLE}
        return [
            m for m in sorted(self._models.values(), key=lambda m: m.priority)
            if m.enabled and m.health_status not in blocked
        ]

    def update_health(self, model_id: str, status: ModelHealthStatus) -> None:
        """Updates the health status of a registered model."""
        if model_id in self._models:
            self._models[model_id].health_status = status

    def set_enabled(self, model_id: str, enabled: bool) -> None:
        """Enables or disables a registered model."""
        if model_id in self._models:
            self._models[model_id].enabled = enabled
            if not enabled:
                self._models[model_id].health_status = ModelHealthStatus.DISABLED
            elif self._models[model_id].health_status == ModelHealthStatus.DISABLED:
                self._models[model_id].health_status = ModelHealthStatus.AVAILABLE
