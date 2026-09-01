"""
Abstract Memory Backend Interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from agent.memory.models import MemoryItem

class BaseMemoryBackend(ABC):
    """
    Abstract Base Class defining the contract for memory storage backends.
    """

    @abstractmethod
    def store_memory(self, item: MemoryItem) -> str:
        """Stores a memory item and returns its memory ID."""
        pass

    @abstractmethod
    def retrieve_memories(
        self,
        query: str,
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[MemoryItem]:
        """Retrieves relevant memory items matching optional filter criteria."""
        pass

    @abstractmethod
    def update_memory(self, memory_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Updates content or metadata of an existing memory item."""
        pass

    @abstractmethod
    def delete_memory(self, memory_id: str) -> bool:
        """Deletes a single memory item by ID."""
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> int:
        """Deletes all memory items associated with a session ID."""
        pass

    @abstractmethod
    def clear_all(self) -> None:
        """Clears all stored memory items."""
        pass
