"""
Plan Domain Models, Task State Machine, and Orchestration Event Schemas.
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class TaskState(str, Enum):
    """Task execution state in orchestration graph."""
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

# Valid state transitions matrix
_VALID_TRANSITIONS: Dict[TaskState, List[TaskState]] = {
    TaskState.PENDING: [TaskState.READY, TaskState.CANCELLED, TaskState.BLOCKED],
    TaskState.READY: [TaskState.RUNNING, TaskState.CANCELLED, TaskState.BLOCKED],
    TaskState.RUNNING: [TaskState.SUCCEEDED, TaskState.FAILED, TaskState.READY, TaskState.BLOCKED, TaskState.CANCELLED],
    TaskState.BLOCKED: [TaskState.READY, TaskState.CANCELLED, TaskState.FAILED],
    TaskState.FAILED: [TaskState.READY, TaskState.CANCELLED],
    TaskState.SUCCEEDED: [],
    TaskState.CANCELLED: [],
}

def transition_task_state(current_state: TaskState, new_state: TaskState) -> TaskState:
    """
    Validates state transitions according to the task state machine.
    Raises ValueError on invalid state transition.
    """
    if current_state == new_state:
        return new_state
    valid_next = _VALID_TRANSITIONS.get(current_state, [])
    if new_state not in valid_next:
        raise ValueError(
            f"Invalid TaskState transition: Cannot transition from {current_state.value} to {new_state.value}."
        )
    return new_state

class PlanTask(BaseModel):
    """
    Task unit within an execution plan.
    """
    id: str = Field(..., description="Unique task ID within plan")
    description: str = Field(..., description="Human-readable task goal")
    dependencies: List[str] = Field(default_factory=list, description="IDs of prerequisite tasks")
    status: TaskState = Field(default=TaskState.PENDING, description="Current task execution state")
    required_tool_id: Optional[str] = Field(default=None, description="Capability/Tool ID required for execution")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Task execution parameters")
    outputs: Optional[Any] = Field(default=None, description="Task execution output result")
    retry_count: int = Field(default=0, description="Current retry attempt count")
    max_retries: int = Field(default=2, description="Maximum retry attempts allowed")
    error: Optional[str] = Field(default=None, description="Error details if task failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

class Plan(BaseModel):
    """
    Versioned execution plan containing task graph.
    """
    id: str = Field(..., description="Unique plan ID")
    goal: str = Field(..., description="User goal or objective")
    version: str = Field(default="plan-v1", description="Plan version string (e.g. plan-v1, plan-v2)")
    tasks: Dict[str, PlanTask] = Field(default_factory=dict, description="Task dictionary keyed by task ID")
    status: str = Field(default="active", description="Plan status (active, completed, failed, revised)")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom plan metadata")

class OrchestrationEvent(BaseModel):
    """
    Structured orchestration audit event.
    """
    event_type: str = Field(..., description="Event classification (e.g. PLAN_CREATED, TASK_COMPLETED)")
    plan_id: str = Field(..., description="Associated plan ID")
    plan_version: str = Field(..., description="Plan version string")
    task_id: Optional[str] = Field(default=None, description="Associated task ID if applicable")
    status: str = Field(..., description="Status payload")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 event timestamp",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")
