"""
Evolution Domain Models, Enums, and Mutation Schemas.
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class MutationTarget(str, Enum):
    """Target component categories eligible for evolution."""
    PLANNER_STRATEGY = "planner_strategy"
    AGENT_ROUTING = "agent_routing"
    TOOL_SELECTION_POLICY = "tool_selection_policy"
    SKILL_DEFINITIONS = "skill_definitions"
    MEMORY_RETRIEVAL_STRATEGY = "memory_retrieval_strategy"
    MODEL_ROUTING = "model_routing"
    AGENT_COMPOSITION = "agent_composition"
    PROTECTED_CONSTITUTION = "constitutional_rules"  # Target used for testing constitutional attack rejection
    CONSTITUTIONAL_RULES = "constitutional_rules"

class MutationStatus(str, Enum):
    """Lifecycle state of a proposed mutation."""
    PROPOSED = "PROPOSED"
    EVALUATING = "EVALUATING"
    APPROVED = "APPROVED"
    CANARY = "CANARY"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"

class EvolutionMode(str, Enum):
    """Operational mode governing metamorphosis automation level."""
    OBSERVE_ONLY = "OBSERVE_ONLY"
    PROPOSE_ONLY = "PROPOSE_ONLY"
    SIMULATE = "SIMULATE"
    CANARY = "CANARY"
    SEMI_AUTOMATIC = "SEMI_AUTOMATIC"
    AUTOMATIC = "AUTOMATIC"
    AUTOMATED = "AUTOMATED"

class CanaryStatus(str, Enum):
    """Status of active canary monitoring."""
    PENDING = "PENDING"
    HEALTHY = "HEALTHY"
    REGRESSED = "REGRESSED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"

class Mutation(BaseModel):
    """
    Structured versioned mutation proposal card.
    """
    mutation_id: str = Field(..., description="Unique mutation ID (e.g. mut-001)")
    target: MutationTarget = Field(..., description="Target component category")
    parent_version: str = Field(default="agent-v1", description="Parent active version string")
    candidate_version: str = Field(..., description="Proposed candidate version string (e.g. agent-v2)")
    proposed_changes: Dict[str, Any] = Field(default_factory=dict, description="Proposed architectural or parameter changes")
    rationale: str = Field(default="", description="Rationale for mutation based on observed evidence")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Observed evidence metrics or failure logs")
    risk_level: str = Field(default="LOW", description="Assessed risk classification (LOW, MEDIUM, HIGH)")
    author: str = Field(default="evolution_proposer", description="Author or generator identifier")
    status: MutationStatus = Field(default=MutationStatus.PROPOSED, description="Mutation lifecycle status")
    canary_status: Optional[CanaryStatus] = Field(default=None, description="Current canary deployment status")
    canary_metrics: Dict[str, Any] = Field(default_factory=dict, description="Canary deployment performance metrics")
    requires_human_approval: bool = Field(default=False, description="Whether human approval is required for promotion")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")
