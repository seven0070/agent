"""
Session Memory Manager for Active Session History and Working State.
"""

from typing import List, Dict, Any, Optional
from agent.memory.models import MemoryItem, MemoryType

class SessionMemoryManager:
    """
    In-memory session manager maintaining working context per session_id.
    Ensures strict session isolation.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, List[MemoryItem]] = {}

    def add_turn(self, session_id: str, role: str, content: str) -> MemoryItem:
        """Appends a conversation turn to the given session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        memory_id = f"sess-{session_id}-{len(self._sessions[session_id]) + 1}"
        item = MemoryItem(
            id=memory_id,
            content=content,
            memory_type=MemoryType.CONVERSATION,
            source=role,
            session_id=session_id,
        )
        self._sessions[session_id].append(item)
        return item

    def get_session_history(self, session_id: str, limit: int = 10) -> List[MemoryItem]:
        """Retrieves recent conversation turns for a specific session."""
        items = self._sessions.get(session_id, [])
        return items[-limit:]

    def clear_session(self, session_id: str) -> bool:
        """Clears working memory for a specific session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
