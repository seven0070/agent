"""
Persistent SQLite Mutation Registry with Concurrency File Locking.
"""

import sqlite3
import json
import os
import time
from contextlib import contextmanager
from typing import List, Optional, Dict, Any, Iterator
from agent.evolution.models import (
    Mutation,
    MutationStatus,
    MutationTarget,
    CanaryStatus,
    EvolutionProposal,
    ProposalStatus,
    CandidateRecord,
    CandidateStatus,
)
from agent.evolution.events import EvolutionEvent
from agent.logging import get_logger

logger = get_logger("agent.evolution.registry")


class MutationRegistry:
    """
    Persistent SQLite mutation registry tracking candidate versions, parent/child lineage,
    decision records, and active generation pointers.
    """

    def __init__(self, db_path: str = "data/evolution.db") -> None:
        self.db_path = db_path
        self._shared_conn: Optional[sqlite3.Connection] = None
        if db_path != ":memory:":
            parent = os.path.dirname(db_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
        else:
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @contextmanager
    def _locked(self) -> Iterator[sqlite3.Connection]:
        conn = self._get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if self._shared_conn is None:
                conn.close()

    def _init_db(self) -> None:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mutations (
                    mutation_id TEXT PRIMARY KEY,
                    target TEXT NOT NULL,
                    parent_version TEXT NOT NULL,
                    candidate_version TEXT NOT NULL,
                    proposed_changes_json TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    author TEXT NOT NULL,
                    status TEXT NOT NULL,
                    canary_status TEXT,
                    canary_metrics_json TEXT NOT NULL,
                    requires_human_approval INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS active_pointers (
                    pointer_key TEXT PRIMARY KEY,
                    active_version TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                "INSERT OR IGNORE INTO active_pointers (pointer_key, active_version, updated_at) VALUES ('main', 'agent-v1', datetime('now'))"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS proposals (
                    proposal_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS generation_stack (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    parent_version TEXT,
                    mutation_id TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS evolution_lock (
                    lock_key TEXT PRIMARY KEY,
                    holder TEXT,
                    acquired_at REAL
                )
                """
            )
            cursor.execute(
                "INSERT OR IGNORE INTO evolution_lock (lock_key, holder, acquired_at) VALUES ('cycle', NULL, 0)"
            )
            cursor.execute(
                "INSERT OR IGNORE INTO generation_stack (version, parent_version, mutation_id, created_at) VALUES ('agent-v1', NULL, NULL, datetime('now'))"
            )
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()

    def _row_to_mutation(self, row: sqlite3.Row) -> Mutation:
        return Mutation(
            mutation_id=row["mutation_id"],
            target=MutationTarget(row["target"]),
            parent_version=row["parent_version"],
            candidate_version=row["candidate_version"],
            proposed_changes=json.loads(row["proposed_changes_json"]) if row["proposed_changes_json"] else {},
            rationale=row["rationale"],
            evidence=json.loads(row["evidence_json"]) if row["evidence_json"] else {},
            risk_level=row["risk_level"],
            author=row["author"],
            status=MutationStatus(row["status"]),
            canary_status=CanaryStatus(row["canary_status"]) if row["canary_status"] else None,
            canary_metrics=json.loads(row["canary_metrics_json"]) if row["canary_metrics_json"] else {},
            requires_human_approval=bool(row["requires_human_approval"]),
            created_at=row["created_at"],
            metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
        )

    def save_mutation(self, mutation: Mutation) -> str:
        """Persists a new or updated mutation record."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO mutations
                (mutation_id, target, parent_version, candidate_version, proposed_changes_json, rationale, evidence_json, risk_level, author, status, canary_status, canary_metrics_json, requires_human_approval, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mutation.mutation_id,
                    mutation.target.value if isinstance(mutation.target, MutationTarget) else str(mutation.target),
                    mutation.parent_version,
                    mutation.candidate_version,
                    json.dumps(mutation.proposed_changes),
                    mutation.rationale,
                    json.dumps(mutation.evidence),
                    mutation.risk_level,
                    mutation.author,
                    mutation.status.value if isinstance(mutation.status, MutationStatus) else str(mutation.status),
                    mutation.canary_status.value if mutation.canary_status and isinstance(mutation.canary_status, CanaryStatus) else (str(mutation.canary_status) if mutation.canary_status else None),
                    json.dumps(mutation.canary_metrics),
                    1 if mutation.requires_human_approval else 0,
                    mutation.created_at,
                    json.dumps(mutation.metadata),
                ),
            )
            conn.commit()
            logger.info(f"Persisted Mutation '{mutation.mutation_id}' [{mutation.status.value}] in registry")
        finally:
            if self._shared_conn is None:
                conn.close()
        return mutation.mutation_id

    def store_mutation(self, mutation: Mutation) -> str:
        return self.save_mutation(mutation)

    def get_mutation(self, mutation_id: str) -> Optional[Mutation]:
        """Retrieves a mutation record by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            row = cursor.execute("SELECT * FROM mutations WHERE mutation_id = ?", (mutation_id,)).fetchone()
            if not row:
                return None
            return self._row_to_mutation(row)
        finally:
            if self._shared_conn is None:
                conn.close()

    def list_mutations(self) -> List[Mutation]:
        """Lists all stored mutation records."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            rows = cursor.execute("SELECT * FROM mutations ORDER BY created_at ASC").fetchall()
            return [self._row_to_mutation(row) for row in rows]
        finally:
            if self._shared_conn is None:
                conn.close()

    def list_in_flight(self) -> List[Mutation]:
        active = {
            MutationStatus.EVALUATING.value,
            MutationStatus.CANARY.value,
        }
        return [m for m in self.list_mutations() if m.status.value in active]

    def get_active_version(self) -> str:
        """Retrieves current active agent generation version."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            row = cursor.execute("SELECT active_version FROM active_pointers WHERE pointer_key = 'main'").fetchone()
            return row["active_version"] if row else "agent-v1"
        finally:
            if self._shared_conn is None:
                conn.close()

    def get_active_generation(self) -> str:
        return self.get_active_version()

    def set_active_version(self, version: str) -> None:
        """Updates main active agent generation pointer."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE active_pointers SET active_version = ?, updated_at = datetime('now') WHERE pointer_key = 'main'",
                (version,),
            )
            conn.commit()
            logger.info(f"Updated active agent generation pointer to '{version}'")
        finally:
            if self._shared_conn is None:
                conn.close()

    def set_active_generation(self, version: str) -> None:
        self.set_active_version(version)

    def save_proposal(self, proposal: EvolutionProposal) -> str:
        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO proposals (proposal_id, payload_json) VALUES (?, ?)",
                (proposal.proposal_id, proposal.model_dump_json()),
            )
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()
        return proposal.proposal_id

    def get_proposal(self, proposal_id: str) -> Optional[EvolutionProposal]:
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT payload_json FROM proposals WHERE proposal_id = ?",
                (proposal_id,),
            ).fetchone()
            if not row:
                return None
            return EvolutionProposal.model_validate_json(row["payload_json"])
        finally:
            if self._shared_conn is None:
                conn.close()

    def list_proposals(self) -> List[EvolutionProposal]:
        conn = self._get_connection()
        try:
            rows = conn.execute("SELECT payload_json FROM proposals").fetchall()
            return [EvolutionProposal.model_validate_json(r["payload_json"]) for r in rows]
        finally:
            if self._shared_conn is None:
                conn.close()

    def save_candidate(self, candidate: CandidateRecord) -> str:
        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO candidates (candidate_id, payload_json) VALUES (?, ?)",
                (candidate.candidate_id, candidate.model_dump_json()),
            )
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()
        return candidate.candidate_id

    def get_candidate(self, candidate_id: str) -> Optional[CandidateRecord]:
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT payload_json FROM candidates WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
            if not row:
                return None
            return CandidateRecord.model_validate_json(row["payload_json"])
        finally:
            if self._shared_conn is None:
                conn.close()

    def list_candidates(self) -> List[CandidateRecord]:
        conn = self._get_connection()
        try:
            rows = conn.execute("SELECT payload_json FROM candidates").fetchall()
            return [CandidateRecord.model_validate_json(r["payload_json"]) for r in rows]
        finally:
            if self._shared_conn is None:
                conn.close()

    def append_audit(self, event: EvolutionEvent) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT INTO audit_events (timestamp, payload_json) VALUES (?, ?)",
                (event.timestamp, event.model_dump_json()),
            )
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()

    def list_audit(self, limit: int = 50) -> List[EvolutionEvent]:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT payload_json FROM audit_events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [EvolutionEvent.model_validate_json(r["payload_json"]) for r in rows]
        finally:
            if self._shared_conn is None:
                conn.close()

    def push_generation(self, version: str, parent_version: Optional[str], mutation_id: Optional[str]) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT INTO generation_stack (version, parent_version, mutation_id, created_at) VALUES (?, ?, ?, datetime('now'))",
                (version, parent_version, mutation_id),
            )
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()

    def lineage(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT version, parent_version, mutation_id, created_at FROM generation_stack ORDER BY id ASC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            if self._shared_conn is None:
                conn.close()

    def try_acquire_cycle_lock(self, holder: str, ttl_seconds: float = 120.0) -> bool:
        now = time.time()
        with self._locked() as conn:
            row = conn.execute(
                "SELECT holder, acquired_at FROM evolution_lock WHERE lock_key = 'cycle'"
            ).fetchone()
            holder_val = row["holder"] if row else None
            acquired = float(row["acquired_at"] or 0) if row else 0.0
            if holder_val and holder_val != holder and (now - acquired) < ttl_seconds:
                return False
            conn.execute(
                "UPDATE evolution_lock SET holder = ?, acquired_at = ? WHERE lock_key = 'cycle'",
                (holder, now),
            )
            return True

    def release_cycle_lock(self, holder: str) -> None:
        with self._locked() as conn:
            conn.execute(
                "UPDATE evolution_lock SET holder = NULL, acquired_at = 0 WHERE lock_key = 'cycle' AND holder = ?",
                (holder,),
            )
