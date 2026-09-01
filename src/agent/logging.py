"""
Structured Logging Foundation for Layer 0.
Supports task_id, session_id, agent_version, component_version, event_type, timestamp, severity.
"""

import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_LOG_CONTEXT: Dict[str, Any] = {
    "task_id": None,
    "session_id": None,
    "agent_version": "0.1.0",
    "component_version": "0.1.0",
}

def set_log_context(
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    agent_version: Optional[str] = None,
    component_version: Optional[str] = None,
) -> None:
    """Sets global contextual identifiers for structured log records."""
    if task_id is not None:
        _LOG_CONTEXT["task_id"] = task_id
    if session_id is not None:
        _LOG_CONTEXT["session_id"] = session_id
    if agent_version is not None:
        _LOG_CONTEXT["agent_version"] = agent_version
    if component_version is not None:
        _LOG_CONTEXT["component_version"] = component_version

class StructuredJSONFormatter(logging.Formatter):
    """Formats log records as structured JSON strings."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "task_id": getattr(record, "task_id", _LOG_CONTEXT.get("task_id")),
            "session_id": getattr(record, "session_id", _LOG_CONTEXT.get("session_id")),
            "agent_version": getattr(record, "agent_version", _LOG_CONTEXT.get("agent_version")),
            "component_version": getattr(record, "component_version", _LOG_CONTEXT.get("component_version")),
            "event_type": getattr(record, "event_type", "general"),
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)

def get_logger(name: str = "agent", level: str = "INFO") -> logging.Logger:
    """Configures and returns a structured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger
