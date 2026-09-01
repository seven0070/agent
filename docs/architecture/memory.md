# Layer 3 — Memory & Knowledge System Specification

## Overview
Layer 3 provides persistent memory, session working memory, document RAG, embedding management, and bounded context construction for the self-evolving AI agent system.

## AgentScope 2.x Memory & RAG Analysis

### Verified Modules in AgentScope 2.0.7.post1

| Component | Module Path | Purpose |
|---|---|---|
| **Knowledge Base** | `agentscope.rag.KnowledgeBase` | Document RAG retrieval container using vector stores. |
| **Vector Record** | `agentscope.rag.VectorRecord` | Record structure containing embedding vector, document ID, and text chunk. |
| **Document Chunker** | `agentscope.rag.ApproxTokenChunker` | Text chunking utility for document ingestion. |
| **Embedding Base** | `agentscope.embedding.EmbeddingModelBase` | Abstract base class for embedding generators. |
| **Embeddings** | `OpenAIEmbeddingModel`, `OllamaEmbeddingModel`, `DashScopeEmbeddingModel` | Concrete embedding model adapters. |
| **Agent State** | `agentscope.state.AgentState` | Session state container. |
| **ReMe Ecosystem** | `reme` (PyPI `reme>=1.0.0`) | Advanced memory management ecosystem (integrated via adapter boundary). |

## Memory Architecture

```text
                     AGENT CORE (`AgentV1`)
                               │
                               ▼
               CONTEXT BUILDER (`ContextBuilder`)
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
SESSION MEMORY         LONG-TERM MEMORY            RAG KNOWLEDGE
(`SessionMemory`)    (`SQLiteMemoryBackend`)    (`RAGEngine` / `KnowledgeBase`)
  (Ephemeral)            (Persistent DB)          (Document Vectors)
```

## Taxonomy of Memory Types
Memory entries (`MemoryItem`) support a clean, extensible taxonomy:
- `conversation`: Dialog turns between user and agent
- `fact`: Extracted factual assertions about the domain or user
- `preference`: User configuration and operational preferences
- `task`: Task execution history, goals, and outcomes
- `decision`: Strategic decisions and rationale made by planners
- `knowledge`: Ingested domain knowledge and documentation

## Storage Backends & Persistence Strategy
1. **Session Memory (`SessionMemoryManager`)**: In-memory working buffer per `session_id`, storing active message history and context window state. Ensures strict session isolation.
2. **Long-Term Memory (`SQLiteMemoryBackend`)**: Persistent SQLite database storage (`data/memory.db`) storing structured memory cards. Supports CRUD operations, metadata filtering, keyword search, transaction safety, and explicit deletion (`delete_memory`, `delete_session`).

## RAG & Embedding Abstraction
- Provider-agnostic embedding interface (`EmbeddingModelInterface`) wrapping cloud and local providers (`OpenAIEmbeddingModel`, `OllamaEmbeddingModel`, or deterministic test mocks).
- RAG Engine (`RAGEngine`) leveraging `ApproxTokenChunker` and vector search for document indexing and retrieval.

## Bounded Context Builder
The `ContextBuilder` gathers:
1. Current user task prompt
2. Active session history (bounded by recent messages)
3. Relevant long-term memories retrieved via query search
4. Relevant RAG knowledge chunks

It formats these components into a clean, token-bounded prompt context, preventing token limit exhaustion.

## Memory Strategy Versioning Readiness
Memory strategies are tagged with explicit version specs (`MemoryStrategySpec`):
- `memory-v1`: Standard SQLite + Session working buffer
- `retrieval-v1`: Keyword and metadata filtering
- `context-builder-v1`: Bounded prompt context builder

Enables future Evolution Controller (Layer 9) evaluation between version candidates.

## Security & Privacy Rules
- **No Secret Persistence**: API keys, tokens, or private credentials must NEVER be stored as plain-text memory entries.
- **Redaction Enforcement**: Auto-scrubbing applies before committing entries to database.
- **Deletion Authority**: Exposes explicit deletion APIs (`delete_memory`, `delete_session`, `clear_all`).
