"""
Persistent SQLite Memory Backend Implementation.
"""

import sqlite3
import json
import os
import uuid
from typing import List, Optional, Dict, Any
from agent.memory.base import BaseMemoryBackend
from agent.memory.models import MemoryItem, MemoryType

class SQLiteMemoryBackend(BaseMemoryBackend):
    """
    Persistent SQLite-backed long-term memory backend.
    """

    def __init__(self, db_path: str = "data/memory.db") -> None:
        self.db_path = db_path
        self._shared_conn: Optional[sqlite3.Connection] = None
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        else:
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                source TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                importance REAL NOT NULL,
                metadata_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)"
        )
        conn.commit()
        if self._shared_conn is None:
            conn.close()

    def _scrub_secrets(self, text: str) -> str:
        """Simple safety check scrubbing plain-text API key patterns."""
        if "sk-" in text or "bearer" in text.lower():
            return "[SECRET SCRUBBED]"
        return text

    def store_memory(self, item: MemoryItem) -> str:
        scrubbed_content = self._scrub_secrets(item.content)
        metadata_str = json.dumps(item.metadata)

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO memories
                (id, content, memory_type, source, timestamp, session_id, importance, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.id,
                    scrubbed_content,
                    item.memory_type.value if isinstance(item.memory_type, MemoryType) else str(item.memory_type),
                    item.source,
                    item.timestamp,
                    item.session_id,
                    item.importance,
                    metadata_str,
                ),
            )
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()
        return item.id

    def retrieve_memories(
        self,
        query: str,
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[MemoryItem]:
        keywords = [w.strip() for w in query.split() if len(w.strip()) > 3]

        def _fetch_rows(kw_filter: Optional[str] = None) -> List[sqlite3.Row]:
            query_sql = "SELECT * FROM memories WHERE 1=1"
            params: List[Any] = []

            if session_id:
                query_sql += " AND (session_id = ? OR session_id IS NULL)"
                params.append(session_id)

            if memory_type:
                query_sql += " AND memory_type = ?"
                params.append(memory_type)

            if kw_filter:
                query_sql += " AND content LIKE ?"
                params.append(f"%{kw_filter}%")

            query_sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                return cursor.execute(query_sql, params).fetchall()
            finally:
                if self._shared_conn is None:
                    conn.close()

        rows = _fetch_rows(kw_filter=None)
        if keywords and rows:
            def score_row(r: sqlite3.Row) -> int:
                c = r["content"].lower()
                return sum(1 for kw in keywords if kw.lower() in c)

            rows.sort(key=score_row, reverse=True)

        items: List[MemoryItem] = []
        for row in rows[:limit]:
            metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
            items.append(
                MemoryItem(
                    id=row["id"],
                    content=row["content"],
                    memory_type=MemoryType(row["memory_type"]),
                    source=row["source"],
                    timestamp=row["timestamp"],
                    session_id=row["session_id"],
                    importance=row["importance"],
                    metadata=metadata,
                )
            )
        return items

    def update_memory(self, memory_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        scrubbed_content = self._scrub_secrets(content)
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if metadata is not None:
                metadata_str = json.dumps(metadata)
                cursor.execute(
                    "UPDATE memories SET content = ?, metadata_json = ? WHERE id = ?",
                    (scrubbed_content, metadata_str, memory_id),
                )
            else:
                cursor.execute(
                    "UPDATE memories SET content = ? WHERE id = ?",
                    (scrubbed_content, memory_id),
                )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            if self._shared_conn is None:
                conn.close()

    def delete_memory(self, memory_id: str) -> bool:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            if self._shared_conn is None:
                conn.close()

    def delete_session(self, session_id: str) -> int:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE session_id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount
        finally:
            if self._shared_conn is None:
                conn.close()

    def clear_all(self) -> None:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories")
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()
