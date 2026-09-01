# AgentScope Integration Research & Architectural Decisions

## Overview
This document records the research findings, dependency choices, and architectural decisions made when integrating **AgentScope** as Layer 1 (Agent Core) of the self-evolving AI agent system.

## Environment & Version Specification
- **AgentScope Release**: `2.0.7.post1`
- **Python Version**: `3.12.13`
- **Installation Package**: `agentscope>=2.0.0`

## AgentScope 2.x API Findings

### 1. Module Layout Changes in AgentScope 2.x
Compared to AgentScope 1.x, version 2.x introduces refined module structures:
- `agentscope.agent.Agent`: Core agent class (`Agent(name, system_prompt, model, ...)`) with async `reply()` method (`async def reply(inputs, ...)`).
- `agentscope.model.ChatModelBase`: Abstract base class for chat models (`async def __call__(messages, tools, ...)`).
- `agentscope.model.OpenAIChatModel`, `DashScopeChatModel`, `AnthropicChatModel`, `GeminiChatModel`, `OllamaChatModel`: Concrete model adapters.
- `agentscope.message.Msg`: Base message schema containing block-based content (`TextBlock`, `ToolCallBlock`, etc.).
- `agentscope.message.UserMsg`, `AssistantMsg`, `SystemMsg`: Helper constructors for message creation.

### 2. Selected Abstractions & Justification

| Abstraction | Package Path | Selection Justification |
|---|---|---|
| **Agent Base** | `agentscope.agent.Agent` | Provides core message handling, async step execution, and structured reply generation. |
| **Model Base** | `agentscope.model.ChatModelBase` | Clean contract for LLM invocation, enabling production models as well as deterministic test mock models. |
| **Message Schema** | `agentscope.message.Msg` | Rich content block support (`TextBlock`), standard metadata tracking (`role`, `name`, `id`). |

### 3. Application Adapter Boundary Pattern
To ensure the system remains decoupled from AgentScope internals, Layer 1 introduces an isolated adapter pattern:

```text
       OUR APPLICATION CORE (`agent.core`)
                      │
           uses domain `AgentTask` & returns `AgentResult`
                      │
                      ▼
       AGENTSCOPE ADAPTER (`agent.integrations.agentscope.adapter`)
                      │
           converts domain types ↔ AgentScope `Msg` & `Agent`
                      │
                      ▼
            AGENTSCOPE 2.x ENGINE (`agentscope.agent.Agent`)
```

### 4. Deterministic Mock Model Strategy for Testing
For unit tests, integration tests, and environments without live cloud credentials, Layer 1 provides a `MockChatModel` inheriting from `ChatModelBase`. It returns deterministic responses without making network requests, ensuring fast, reproducible non-interactive test suites.

## Future Layer Integration Placeholders
- **Tools/Skills (Layer 4)**: AgentScope `Toolkit` and tool call blocks are supported in `Agent.__init__` but omitted in Layer 1.
- **Planning/Orchestration (Layer 5)**: Multi-agent teams and pipeline workflows will attach to the adapter boundary in Layer 5.
