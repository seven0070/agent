"""
Evaluation & Verification Engine Subsystem Package (Layer 8).
"""

from agent.evaluation.models import EvaluationCase, CaseResult, EvaluationRun, EvaluationReport
from agent.evaluation.metrics import MetricDimensions, EvaluationThresholds
from agent.evaluation.spec import DatasetSpec

__all__ = [
    "EvaluationCase",
    "CaseResult",
    "EvaluationRun",
    "EvaluationReport",
    "MetricDimensions",
    "EvaluationThresholds",
    "DatasetSpec",
]
