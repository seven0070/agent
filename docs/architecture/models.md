# Layer 2 — Intelligence / Model System Specification

## Overview
Layer 2 builds a clean, provider-agnostic intelligence and model routing layer above AgentScope 2.x. It abstracts model identity, provider configuration, capability matching, routing policy, error handling, health tracking, and fallback execution.

## AgentScope 2.0.7.post1 Model API Analysis

### Verified Model Classes & Credential Objects

| Provider | Model Adapter Class | Credential Class | Supported Features |
|---|---|---|---|
| **OpenAI** | `agentscope.model.OpenAIChatModel` | `agentscope.credential.OpenAICredential` | Cloud LLM, Streaming, Structured Output, Tool Calls |
| **DashScope** | `agentscope.model.DashScopeChatModel` | `agentscope.credential.DashScopeCredential` | Cloud LLM, Streaming, Tool Calls |
| **Ollama (Local)** | `agentscope.model.OllamaChatModel` | `agentscope.credential.OllamaCredential` | Local LLM, Offline execution |
| **Anthropic** | `agentscope.model.AnthropicChatModel` | `agentscope.credential.AnthropicCredential` | Cloud LLM, Streaming, Vision |
| **Gemini** | `agentscope.model.GeminiChatModel` | `agentscope.credential.GeminiCredential` | Cloud LLM, Multimodal |
| **Mock (Test)** | `agent.integrations.agentscope.MockChatModel` | N/A | Deterministic non-interactive testing |

## Target Model Architecture

```text
                     AGENT CORE (`agent.core.AgentV1`)
                                     │
                                     ▼
                     MODEL ROUTER (`agent.models.ModelRouter`)
                                     │
                      ┌──────────────┴──────────────┐
                      ▼                             ▼
            PRIMARY MODEL SELECTION         FALLBACK SELECTION
            (e.g., openai / qwen)           (e.g., ollama / mock)
                      │                             │
                      └──────────────┬──────────────┘
                                     ▼
                     MODEL FACTORY (`agent.models.ModelFactory`)
                                     │
                                     ▼
            AGENTSCOPE MODEL ADAPTER (`agentscope.model.ChatModelBase`)
```

## Model Registry Specification
Models are registered with explicit specification cards (`ModelSpec`):
- `id`: Symbolic identifier (e.g. `primary`, `fallback`, `local`)
- `provider`: Provider type (`openai`, `dashscope`, `ollama`, `mock`)
- `model_name`: Provider model string (e.g. `gpt-4o-mini`, `qwen-max`, `llama3.2`)
- `capabilities`: Feature flags (`supports_tools`, `supports_vision`, `supports_streaming`)
- `context_window`: Maximum context token size
- `health_status`: In-process health state (`AVAILABLE`, `DEGRADED`, `UNAVAILABLE`, `DISABLED`)
- `enabled`: Global toggle
- `priority`: Selection priority order (lower number = higher priority)

## Credential Handling & Security
Credentials are strictly decoupled from model definitions:
- Environment variables (`OPENAI_API_KEY`, `DASHSCOPE_API_KEY`, `OLLAMA_HOST`) are loaded at runtime.
- Credential string representations are auto-redacted (`***REDACTED***`).
- Serialized configuration and log outputs are guaranteed to contain no plain-text secret tokens.

## Controlled Fallback Policy
When an active model invocation fails due to retryable network or provider errors:
1. The error is logged, and the failed model's health state transitions to `DEGRADED` or `UNAVAILABLE`.
2. The router checks the configured fallback models in priority order.
3. Up to `max_attempts` total attempts are executed across primary and fallback models.
4. If all candidate models fail, a normalized `ModelExecutionError` is returned safely without crashing the execution loop.

## Local Model Readiness
- Ollama is supported via `OllamaChatModel` and `OllamaCredential` (`host="http://localhost:11434"`).
- Enables offline local execution without cloud API dependencies.
