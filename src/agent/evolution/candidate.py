"""
Candidate Manager: isolated workspaces for proposed generations.

Never mutates the active production Agent source. Candidates live under
data/candidates/<candidate_id>/ and may only write evolvable artifacts.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Optional

from agent.constitution import ConstitutionalViolationError
from agent.evolution.generation import generation_path, get_active_generation_dir
from agent.evolution.models import CandidateRecord, CandidateStatus, EvolutionProposal, Mutation
from agent.evolution.protection import assert_candidate_write_allowed, is_protected_path
from agent.logging import get_logger

logger = get_logger("agent.evolution.candidate")


class CandidateManager:
    def __init__(self, root_dir: str) -> None:
        self.root_dir = os.path.abspath(root_dir)
        os.makedirs(self.root_dir, exist_ok=True)

    def create_candidate(
        self,
        proposal: EvolutionProposal,
        mutation: Mutation,
        data_dir: Optional[str] = None,
    ) -> CandidateRecord:
        candidate_id = f"cand-{uuid.uuid4().hex[:8]}"
        workspace = os.path.join(self.root_dir, candidate_id)
        artifacts = os.path.join(workspace, "artifacts")
        tests_dir = os.path.join(workspace, "tests")
        os.makedirs(artifacts, exist_ok=True)
        os.makedirs(tests_dir, exist_ok=True)

        parent_gen = get_active_generation_dir(data_dir=data_dir, version=mutation.parent_version)
        if parent_gen and os.path.isdir(parent_gen):
            for name in os.listdir(parent_gen):
                src = os.path.join(parent_gen, name)
                if os.path.isfile(src) and not is_protected_path(src):
                    shutil.copy2(src, os.path.join(artifacts, name))

        manifest = {
            "candidate_id": candidate_id,
            "proposal_id": proposal.proposal_id,
            "mutation_id": mutation.mutation_id,
            "parent_version": mutation.parent_version,
            "candidate_version": mutation.candidate_version,
            "target": mutation.target.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        manifest_path = os.path.join(workspace, "MANIFEST.json")
        assert_candidate_write_allowed(manifest_path, workspace)
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)

        record = CandidateRecord(
            candidate_id=candidate_id,
            proposal_id=proposal.proposal_id,
            mutation_id=mutation.mutation_id,
            parent_version=mutation.parent_version,
            candidate_version=mutation.candidate_version,
            workspace_dir=workspace,
            status=CandidateStatus.CREATED,
            metadata={"target": mutation.target.value},
        )
        logger.info(
            f"Created isolated candidate '{candidate_id}' for '{mutation.candidate_version}' "
            f"at '{workspace}'"
        )
        return record

    def cleanup(self, record: CandidateRecord) -> CandidateRecord:
        workspace = record.workspace_dir
        if workspace and os.path.isdir(workspace):
            real_root = os.path.realpath(self.root_dir)
            real_ws = os.path.realpath(workspace)
            if real_ws.startswith(real_root + os.sep) or real_ws == real_root:
                shutil.rmtree(real_ws, ignore_errors=True)
        record.status = CandidateStatus.CLEANED
        return record

    def assert_isolated(self, record: CandidateRecord) -> None:
        workspace = os.path.realpath(record.workspace_dir)
        src_root = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if workspace.startswith(src_root + os.sep):
            raise ConstitutionalViolationError(
                "Candidate workspace must not reside inside Agent source tree."
            )
        if not workspace.startswith(os.path.realpath(self.root_dir)):
            raise ConstitutionalViolationError(
                "Candidate workspace escaped candidate root."
            )
