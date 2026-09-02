"""
Pydantic Request & Response Schemas for Layer 10 REST & SSE API.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

# --- Session Schemas ---
class SessionCreateRequest(BaseModel):
    title: Optional[str] = Field(default=None, description="Optional custom session title")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")

class SessionResponse(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0
    active_plan_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

# --- Chat & Messaging Schemas ---
class ChatMessageRequest(BaseModel):
    session_id: str
    prompt: str
    model_version: Optional[str] = Field(default="mock-model-v1")
    enable_planning: bool = True
    enable_coding: bool = True

class ChatMessageResponse(BaseModel):
    message_id: str
    session_id: str
    role: str = "assistant"
    content: str
    tools_used: List[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    created_at: str

# --- Event Stream Schema ---
class StreamEventFrame(BaseModel):
    event_type: str  # MESSAGE_DELTA, PLAN_UPDATED, TOOL_EXECUTED, APPROVAL_REQUIRED, SYSTEM_ERROR
    session_id: str
    payload: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
