"""
Coding Engine Domain Models and Event Schemas.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class CodingTask(BaseModel):
    """
    Specification payload for a coding task assigned to Jcode.
    """
    task_id: str = Field(..., description="Unique task identifier")
    goal: str = Field(..., description="Coding objective or software engineering requirement")
    workspace_dir: str = Field(default="data/workspace", description="Explicit workspace root directory")
    test_command: Optional[str] = Field(default=None, description="Command to execute test suite (e.g. 'pytest')")
    constraints: List[str] = Field(default_factory=list, description="Architectural constraints or rules")
    max_turns: int = Field(default=5, description="Maximum agent execution turns")
    approval_policy: str = Field(default="ALLOW", description="Default permission policy level")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

class CodingResult(BaseModel):
    """
    Machine-readable result returned from Jcode execution.
    """
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(default="success", description="Execution status (success, failed, cancelled, error)")
    summary: str = Field(default="", description="Summary description of changes made")
    files_changed: List[str] = Field(default_factory=list, description="Relative paths of created or edited files")
    tests_run: int = Field(default=0, description="Total number of tests executed")
    tests_passed: int = Field(default=0, description="Total number of tests passed")
    tests_failed: int = Field(default=0, description="Total number of tests failed")
    tool_calls_count: int = Field(default=0, description="Total tool invocations during task")
    errors: List[str] = Field(default_factory=list, description="Error messages encountered during execution")
    duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

class JcodeEvent(BaseModel):
    """
    Structured Jcode execution audit event.
    """
    event_type: str = Field(..., description="Event classification (e.g. session_started, tool_executed)")
    session_id: str = Field(..., description="Associated Jcode session ID")
    task_id: Optional[str] = Field(default=None, description="Associated task ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp",
    )
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event detail payload")
