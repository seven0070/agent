"""
Bounded Context Builder Assembling Prompts from Session Memory, Long-Term Memory, and RAG Knowledge.
"""

from typing import List, Optional, Dict, Any
from agent.memory.models import MemoryItem
from agent.memory.session import SessionMemoryManager
from agent.memory.base import BaseMemoryBackend
from agent.memory.rag import RAGEngine

class ContextBuilder:
    """
    Assembles bounded agent prompts combining session history, long-term memory, and RAG knowledge.
    """

    def __init__(
        self,
        session_manager: Optional[SessionMemoryManager] = None,
        long_term_memory: Optional[BaseMemoryBackend] = None,
        rag_engine: Optional[RAGEngine] = None,
        max_long_term_items: int = 5,
        max_rag_items: int = 3,
    ) -> None:
        self.session_manager = session_manager or SessionMemoryManager()
        self.long_term_memory = long_term_memory
        self.rag_engine = rag_engine
        self.max_long_term_items = max_long_term_items
        self.max_rag_items = max_rag_items

    def build_context_prompt(self, task_prompt: str, session_id: Optional[str] = None) -> str:
        """
        Assembles task prompt with relevant long-term memories, RAG knowledge, and recent session turns.
        """
        context_sections: List[str] = []

        # 1. Retrieve Relevant Long-Term Memory
        if self.long_term_memory:
            relevant_memories = self.long_term_memory.retrieve_memories(
                query=task_prompt,
                session_id=session_id,
                limit=self.max_long_term_items,
            )
            if relevant_memories:
                mem_lines = [f"- [{m.memory_type.value}] {m.content}" for m in relevant_memories]
                context_sections.append("### Relevant Long-Term Memory:\n" + "\n".join(mem_lines))

        # 2. Retrieve Relevant Knowledge from RAG Engine
        if self.rag_engine:
            rag_chunks = self.rag_engine.retrieve_knowledge(query=task_prompt, top_k=self.max_rag_items)
            if rag_chunks:
                rag_lines = [f"- [{chunk['title']}] {chunk['content']}" for chunk in rag_chunks]
                context_sections.append("### Relevant Knowledge / Documentation:\n" + "\n".join(rag_lines))

        # 3. Retrieve Session Conversation History
        if session_id and self.session_manager:
            session_turns = self.session_manager.get_session_history(session_id, limit=5)
            if session_turns:
                turn_lines = [f"{m.source.capitalize()}: {m.content}" for m in session_turns]
                context_sections.append("### Recent Conversation History:\n" + "\n".join(turn_lines))

        # 4. Append Task Prompt
        context_sections.append(f"### Current User Prompt:\n{task_prompt}")

        return "\n\n".join(context_sections)
