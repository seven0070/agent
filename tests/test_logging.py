"""
Test structured log formatting and context setting.
"""

import logging
import json
from io import StringIO
from agent.logging import get_logger, set_log_context, StructuredJSONFormatter

def test_structured_json_formatter() -> None:
    set_log_context(
        task_id="test-task-123",
        session_id="test-session-456",
        agent_version="0.1.0",
        component_version="planner-v1",
    )

    logger = get_logger("test.logger", level="INFO")

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredJSONFormatter())

    orig_handlers = logger.handlers
    logger.handlers = [handler]

    try:
        logger.info("Test message", extra={"event_type": "unit_test"})
        output = stream.getvalue()
        log_json = json.loads(output)

        assert log_json["severity"] == "INFO"
        assert log_json["message"] == "Test message"
        assert log_json["task_id"] == "test-task-123"
        assert log_json["session_id"] == "test-session-456"
        assert log_json["agent_version"] == "0.1.0"
        assert log_json["component_version"] == "planner-v1"
        assert log_json["event_type"] == "unit_test"
    finally:
        logger.handlers = orig_handlers
