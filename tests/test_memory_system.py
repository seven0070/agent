"""
Unit and Integration Tests for Layer 3 Memory & Knowledge Subsystem.
"""

import pytest
import os
import tempfile
from agent.memory import (
    MemoryType,
    MemoryItem,
    MemoryStrategySpec,
    SessionMemoryManager,
    WorkingMemory,
    SQLiteMemoryBackend,
    MockEmbeddingModel,
    RAGEngine,
    ContextBuilder,
)
from agent.core import AgentTask, AgentResult, AgentV1
from agent.integrations.agentscope import AgentScopeAdapter

def test_session_memory_isolation() -> None:
    """Tests session memory working buffer and strict session isolation."""
    mgr = SessionMemoryManager()
    mgr.add_turn(session_id="session-A", role="user", content="Hello from Session A")
    mgr.add_turn(session_id="session-B", role="user", content="Hello from Session B")

    hist_a = mgr.get_session_history("session-A")
    hist_b = mgr.get_session_history("session-B")

    assert len(hist_a) == 1
    assert len(hist_b) == 1
    assert hist_a[0].content == "Hello from Session A"
    assert hist_b[0].content == "Hello from Session B"

    mgr.clear_session("session-A")
    assert len(mgr.get_session_history("session-A")) == 0
    assert len(mgr.get_session_history("session-B")) == 1


def test_working_memory_round_trips_through_sqlite() -> None:
    from agent.integrations.agentscope.adapter import AgentScopeAdapter
    from agent.orchestration import PlanOrchestrator, RuleBasedPlanner

    backend = SQLiteMemoryBackend(db_path=":memory:")
    live = SessionMemoryManager()
    live.record_step("s-restart", "Evaluate calculation", tool_id="calculator-v1", output="42")
    adapter = AgentScopeAdapter(
        planner=RuleBasedPlanner(),
        orchestrator=PlanOrchestrator(),
        context_builder=ContextBuilder(session_manager=live, long_term_memory=backend),
    )
    adapter._persist_working_memory("s-restart")
    restored = SessionMemoryManager()
    adapter.context_builder.session_manager = restored
    adapter._hydrate_working_memory("s-restart")
    wm = restored.get_working_memory("s-restart")
    assert wm.last_outputs.get("calculator-v1") == "42"


def test_follow_up_value_prefers_calculator_over_coding_summary() -> None:
    wm = WorkingMemory()
    wm.last_outputs["coding-engine-v1"] = "Jcode completed task 'coding-task-auto'. Created/edited 1 files."
    wm.last_outputs["calculator-v1"] = "42"
    assert wm.follow_up_value() == "42"


def test_working_memory_retrieves_relevant_artifacts_only() -> None:
    mgr = SessionMemoryManager()
    mgr.update_working_memory("s1", goal="Calculate 12 + 30")
    mgr.record_artifact("s1", "sum.txt", "42")
    mgr.record_artifact("s1", "noise.txt", "ignore-me")
    mgr.record_step("s1", "Evaluate calculation", tool_id="calculator-v1", output="42")
    relevant = mgr.get_working_memory("s1").relevant_for("Read sum.txt and write status.txt")
    assert relevant["artifacts"].get("sum.txt") == "42"
    assert "noise.txt" not in relevant["artifacts"]
    assert isinstance(WorkingMemory(), WorkingMemory)

def test_sqlite_memory_crud() -> None:
    """Tests CRUD operations in persistent SQLite memory backend."""
    backend = SQLiteMemoryBackend(db_path=":memory:")

    item = MemoryItem(
        id="mem-crud-1",
        content="User prefers dark theme mode",
        memory_type=MemoryType.PREFERENCE,
        session_id="s-crud",
    )
    backend.store_memory(item)

    # Retrieve
    retrieved = backend.retrieve_memories(query="theme", session_id="s-crud")
    assert len(retrieved) == 1
    assert retrieved[0].content == "User prefers dark theme mode"

    # Update
    updated = backend.update_memory("mem-crud-1", content="User prefers system theme mode")
    assert updated is True
    retrieved_updated = backend.retrieve_memories(query="theme", session_id="s-crud")
    assert retrieved_updated[0].content == "User prefers system theme mode"

    # Delete
    deleted = backend.delete_memory("mem-crud-1")
    assert deleted is True
    assert len(backend.retrieve_memories(query="theme", session_id="s-crud")) == 0

def test_sqlite_memory_persistence_across_instances() -> None:
    """Tests SQLite database persistence across new backend connections."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        backend1 = SQLiteMemoryBackend(db_path=db_path)
        backend1.store_memory(
            MemoryItem(
                id="persist-1",
                content="Persistent fact about AgentScope",
                memory_type=MemoryType.FACT,
            )
        )

        backend2 = SQLiteMemoryBackend(db_path=db_path)
        retrieved = backend2.retrieve_memories(query="AgentScope")
        assert len(retrieved) == 1
        assert retrieved[0].id == "persist-1"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

def test_secret_scrubbing_in_memory() -> None:
    """Verifies plain-text secret keys are scrubbed before storage."""
    backend = SQLiteMemoryBackend(db_path=":memory:")
    item = MemoryItem(
        id="mem-secret-1",
        content="User provided sk-secret12345 key",
        memory_type=MemoryType.FACT,
    )
    backend.store_memory(item)

    retrieved = backend.retrieve_memories(query="key")
    assert len(retrieved) == 1
    assert "sk-secret12345" not in retrieved[0].content
    assert "[SECRET SCRUBBED]" in retrieved[0].content

def test_embedding_model_mock() -> None:
    """Tests deterministic MockEmbeddingModel vector output."""
    emb = MockEmbeddingModel(dimension=8)
    vec = emb.embed_text("test input string")

    assert len(vec) == 8
    assert all(isinstance(val, float) for val in vec)

    batch_vecs = emb.embed_batch(["text1", "text2"])
    assert len(batch_vecs) == 2

@pytest.mark.asyncio
async def test_rag_engine_ingestion_and_retrieval() -> None:
    """Tests RAG Engine document ingestion and chunk keyword retrieval."""
    rag = RAGEngine()
    chunks_count = await rag.ingest_document(
        doc_id="doc-rag-1",
        title="AgentScope Architecture Manual",
        content="AgentScope provides core agent runtime capabilities and memory management.",
    )
    assert chunks_count > 0

    results = rag.retrieve_knowledge(query="AgentScope runtime", top_k=2)
    assert len(results) > 0
    assert results[0]["doc_id"] == "doc-rag-1"
    assert "AgentScope" in results[0]["content"]

@pytest.mark.asyncio
async def test_context_builder_prompt_assembly() -> None:
    """Tests ContextBuilder prompt assembly with session, long-term memory, and RAG knowledge."""
    sess_mgr = SessionMemoryManager()
    sess_mgr.add_turn("s-ctx", "user", "Prior turn 1")
    sess_mgr.add_turn("s-ctx", "agent", "Prior turn response 1")

    lt_mem = SQLiteMemoryBackend(db_path=":memory:")
    lt_mem.store_memory(
        MemoryItem(id="m-ctx", content="User prefers concise responses", memory_type=MemoryType.PREFERENCE)
    )

    rag = RAGEngine()
    await rag.ingest_document("d-ctx", "Doc Title", "Knowledge chunk content regarding AgentScope")

    builder = ContextBuilder(session_manager=sess_mgr, long_term_memory=lt_mem, rag_engine=rag)
    prompt = builder.build_context_prompt("Explain AgentScope concise", session_id="s-ctx")

    assert "Relevant Long-Term Memory" in prompt
    assert "Relevant Knowledge" in prompt
    assert "Recent Conversation History" in prompt
    assert "Current User Prompt" in prompt

def test_memory_strategy_spec() -> None:
    """Tests MemoryStrategySpec versioning spec card."""
    spec = MemoryStrategySpec(strategy_id="memory-v1", backend_type="sqlite")
    assert spec.strategy_id == "memory-v1"
    assert spec.version == "1.0.0"

@pytest.mark.asyncio
async def test_adapter_layer3_memory_integration() -> None:
    """Tests AgentScopeAdapter end-to-end execution with Layer 3 ContextBuilder."""
    lt_mem = SQLiteMemoryBackend(db_path=":memory:")
    context_builder = ContextBuilder(
        session_manager=SessionMemoryManager(),
        long_term_memory=lt_mem,
    )

    adapter = AgentScopeAdapter(name="layer3-adapter-test", context_builder=context_builder)
    agent = AgentV1(adapter=adapter)

    task = AgentTask(task_id="t-l3", prompt="Memory test task", session_id="s-l3")
    result: AgentResult = await agent.execute_task(task)

    assert result.status == "success"
    # Verify memory was persisted
    stored = lt_mem.retrieve_memories(query="Memory test task", session_id="s-l3")
    assert len(stored) > 0
