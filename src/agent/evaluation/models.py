"""
Evaluation Domain Models and Report Schemas.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from agent.evaluation.metrics import MetricDimensions

class EvaluationCase(BaseModel):
    """
    Structured benchmark test case card.
    """
    id: str = Field(..., description="Unique case ID (e.g. eval-math-1, eval-safety-traversal)")
    category: str = Field(default="general", description="Category (coding, planning, tool, safety)")
    task_prompt: str = Field(..., description="Input prompt or goal given to agent")
    expected_behavior: str = Field(..., description="Expected execution behavior description")
    expected_output: Optional[str] = Field(default=None, description="Expected output text substring if applicable")
    expected_tool_ids: List[str] = Field(default_factory=list, description="Expected capability tool IDs")
    tags: List[str] = Field(default_factory=list, description="Classification tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom case metadata")

class CaseResult(BaseModel):
    """
    Evaluation result for a single test case.
    """
    case_id: str = Field(..., description="Associated evaluation case ID")
    passed: bool = Field(..., description="Case pass/fail status")
    score: float = Field(default=1.0 if True else 0.0, description="Case score (0.0 to 1.0)")
    actual_output: str = Field(default="", description="Actual output produced")
    tools_used: List[str] = Field(default_factory=list, description="Tool IDs invoked during execution")
    safety_violation: bool = Field(default=False, description="Whether a safety/permission breach occurred")
    error: Optional[str] = Field(default=None, description="Error message if case failed")
    duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")

class EvaluationRun(BaseModel):
    """
    Run record for a full evaluation benchmark suite execution.
    """
    run_id: str = Field(..., description="Unique evaluation run ID")
    agent_version: str = Field(default="agent-v1", description="Target agent version evaluated")
    model_version: str = Field(default="mock-model-v1", description="Model version used during run")
    dataset_version: str = Field(default="benchmark-v1", description="Evaluation dataset version ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp",
    )
    case_results: List[CaseResult] = Field(default_factory=list, description="Individual case results")
    summary_metrics: MetricDimensions = Field(default_factory=MetricDimensions, description="Aggregated metric card")

class EvaluationReport(BaseModel):
    """
    Comprehensive evaluation report comparing candidate performance.
    """
    report_id: str = Field(..., description="Unique evaluation report ID")
    candidate_run_id: str = Field(..., description="Candidate evaluation run ID")
    baseline_run_id: Optional[str] = Field(default=None, description="Baseline evaluation run ID if comparing")
    agent_version: str = Field(..., description="Candidate agent version")
    dataset_version: str = Field(..., description="Dataset version evaluated")
    metrics: MetricDimensions = Field(..., description="Candidate aggregated metrics")
    regressions: List[str] = Field(default_factory=list, description="IDs of cases that regressed from baseline")
    improvements: List[str] = Field(default_factory=list, description="IDs of cases that improved over baseline")
    safety_passed: bool = Field(default=True, description="Whether all safety benchmark cases passed")
    recommendation: str = Field(default="REVIEW", description="Evaluation recommendation (PASS, FAIL, REVIEW)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Report metadata")
