"""
Session Memory Manager for Active Session History and Working State.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from agent.memory.models import MemoryItem, MemoryType


@dataclass
class WorkingMemory:
    """Structured task context for a session. Not a conversation dump."""

    goal: str = ""
    active_plan_id: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)
    last_outputs: Dict[str, str] = field(default_factory=dict)
    decisions: List[str] = field(default_factory=list)

    def relevant_for(self, prompt: str, limit: int = 6) -> Dict[str, Any]:
        """Return only artifacts/outputs mentioned by the current prompt or recent steps."""
        lower = (prompt or "").lower()
        artifacts = {}
        for path, content in self.artifacts.items():
            name = path.replace("\\", "/").split("/")[-1].lower()
            if name in lower or path.lower() in lower:
                artifacts[path] = content
        if not artifacts and self.artifacts:
            # Keep the most recent artifact when the prompt refers to prior work.
            if any(token in lower for token in ("that", "result", "it", "previous", "last", "the file")):
                last_path = next(reversed(list(self.artifacts.keys())))
                artifacts[last_path] = self.artifacts[last_path]
        outputs = {}
        for tool_id, output in self.last_outputs.items():
            if tool_id.split("-")[0] in lower or "result" in lower or "that" in lower:
                outputs[tool_id] = output
        steps = [step for step in self.completed_steps[-limit:] if step]
        return {
            "goal": self.goal,
            "active_plan_id": self.active_plan_id,
            "completed_steps": steps,
            "artifacts": artifacts,
            "last_outputs": outputs,
            "decisions": self.decisions[-limit:],
        }

    def follow_up_value(self) -> str:
        """Prefer a real tool result over coding summaries when wiring the next step."""
        for tool_id in ("calculator-v1", "inspect_data-v1", "read_file-v1"):
            value = str(self.last_outputs.get(tool_id) or "").strip()
            if value:
                return value
        for tool_id, output in reversed(list(self.last_outputs.items())):
            text = str(output or "").strip()
            if tool_id == "coding-engine-v1" or not text:
                continue
            return text
        if self.artifacts:
            return str(list(self.artifacts.values())[-1])
        return ""


class SessionMemoryManager:
    """
    In-memory session manager maintaining working context per session_id.
    Ensures strict session isolation.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, List[MemoryItem]] = {}
        self._working: Dict[str, WorkingMemory] = {}

    def get_working_memory(self, session_id: str) -> WorkingMemory:
        if session_id not in self._working:
            self._working[session_id] = WorkingMemory()
        return self._working[session_id]

    def update_working_memory(self, session_id: str, **changes: Any) -> WorkingMemory:
        memory = self.get_working_memory(session_id)
        for key, value in changes.items():
            if hasattr(memory, key) and value is not None:
                setattr(memory, key, value)
        return memory

    def record_artifact(self, session_id: str, path: str, content: str) -> None:
        memory = self.get_working_memory(session_id)
        snippet = content if len(content) <= 500 else content[:500]
        memory.artifacts[path] = snippet

    def record_step(self, session_id: str, description: str, tool_id: Optional[str] = None, output: Any = None) -> None:
        memory = self.get_working_memory(session_id)
        if description:
            memory.completed_steps.append(description)
        if tool_id is not None and output is not None:
            memory.last_outputs[tool_id] = str(output)

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
        cleared = False
        if session_id in self._sessions:
            del self._sessions[session_id]
            cleared = True
        if session_id in self._working:
            del self._working[session_id]
            cleared = True
        return cleared
