"""
Memory & Knowledge Subsystem Package (Layer 3).
"""

from agent.memory.models import MemoryType, MemoryItem
from agent.memory.spec import MemoryStrategySpec
from agent.memory.base import BaseMemoryBackend
from agent.memory.session import SessionMemoryManager
from agent.memory.sqlite import SQLiteMemoryBackend
from agent.memory.embeddings import EmbeddingModelInterface, MockEmbeddingModel
from agent.memory.rag import RAGEngine
from agent.memory.context import ContextBuilder

__all__ = [
    "MemoryType",
    "MemoryItem",
    "MemoryStrategySpec",
    "BaseMemoryBackend",
    "SessionMemoryManager",
    "SQLiteMemoryBackend",
    "EmbeddingModelInterface",
    "MockEmbeddingModel",
    "RAGEngine",
    "ContextBuilder",
]
