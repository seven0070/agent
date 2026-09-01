"""
Unit and Integration Tests for Layer 1 AgentScope Core Integration.
"""

import pytest
import json
import asyncio
from typing import Generator
from agentscope.message import Msg
from agent.core import AgentTask, AgentResult, AgentV1, ModelConfigInfo
from agent.integrations.agentscope import AgentScopeAdapter, MockChatModel

@pytest.mark.asyncio
async def test_a_agent_initialization() -> None:
    """Test A: AgentScope adapter and AgentV1 initialization."""
    adapter = AgentScopeAdapter(name="test-agent", system_prompt="Test system prompt")
    agent = AgentV1(adapter=adapter)

    assert agent.agent_version == "agent-v1"
    assert adapter.name == "test-agent"
    assert adapter._agentscope_agent.name == "test-agent"

def test_b_model_configuration() -> None:
    """Test B: Model configuration initialization without exposing credentials."""
    config_info = ModelConfigInfo(
        provider="mock",
        model_name="test-model-v1",
        temperature=0.2,
    )
    mock_model = MockChatModel(model_name=config_info.model_name)
    adapter = AgentScopeAdapter(model=mock_model, model_config_info=config_info)

    assert adapter.model_config_info.provider == "mock"
    assert adapter.model_config_info.model_name == "test-model-v1"
    assert adapter.model_config_info.temperature == 0.2

def test_c_message_conversion() -> None:
    """Test C: Message format conversion between domain models and AgentScope Msg."""
    adapter = AgentScopeAdapter()
    task = AgentTask(
        task_id="task-msg-1",
        prompt="Hello AgentScope!",
        session_id="session-msg-1",
    )

    msg: Msg = adapter.convert_task_to_msg(task)
    assert msg.role == "user"
    assert msg.name == "user"
    assert "Hello AgentScope!" in msg.get_text_content()

@pytest.mark.asyncio
async def test_d_agent_execution() -> None:
    """Test D: End-to-end agent task execution via AgentScope adapter and MockChatModel."""
    mock_model = MockChatModel(mock_response="Custom test response", model_name="mock-model-v1")
    adapter = AgentScopeAdapter(name="execution-agent", model=mock_model)
    agent = AgentV1(adapter=adapter)

    task = AgentTask(
        task_id="task-exec-100",
        prompt="Run integration test",
        session_id="session-exec-200",
    )

    result: AgentResult = await agent.execute_task(task)

    assert result.task_id == "task-exec-100"
    assert "Custom test response" in result.output
    assert result.agent_version == "agent-v1"
    assert result.status == "success"
    assert result.metadata["session_id"] == "session-exec-200"

def test_e_cli_smoke_execution(monkeypatch, capsys) -> None:
    """Test E: CLI entrypoint smoke test."""
    from agent.__main__ import main

    monkeypatch.setattr("sys.argv", ["agent", "Test CLI Execution Prompt"])

    main()

    captured = capsys.readouterr()
    assert "--- AGENT RESULT ---" in captured.out

    result_section = captured.out.split("--- AGENT RESULT ---")[1]
    json_start = result_section.find("{")
    json_end = result_section.rfind("}") + 1
    assert json_start != -1 and json_end != -1

    json_str = result_section[json_start:json_end]
    result_dict = json.loads(json_str)

    assert result_dict["agent_version"] == "agent-v1"
    assert result_dict["status"] == "success"
    assert "Mocked AgentScope response content" in result_dict["output"]
