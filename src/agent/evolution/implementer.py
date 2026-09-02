"""
Evolution implementation loop: Layer 6 Jcode applies proposed changes
inside an isolated candidate workspace. Layer 7 sandbox runs the tests.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from typing import Dict, Optional

from agent.coding.jcode.adapter import JcodeAdapter
from agent.coding.models import CodingTask, CodingResult
from agent.constitution import ConstitutionalViolationError
from agent.evolution.models import CandidateRecord, CandidateStatus, Mutation
from agent.evolution.protection import assert_candidate_write_allowed, is_protected_path
from agent.logging import get_logger
from agent.runtime.models import NetworkPolicy, RuntimeSession
from agent.runtime.policy import ResourceLimits
from agent.runtime.sandbox import RuntimeSandbox

logger = get_logger("agent.evolution.implementer")

_TEST_TEMPLATE = '''\
import json
import os

def test_artifact_exists_and_is_valid():
    path = os.path.join(os.path.dirname(__file__), "..", "artifacts", "{filename}")
    path = os.path.abspath(path)
    assert os.path.isfile(path), f"missing artifact {{path}}"
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    assert data.get("target") == "{target}"
    assert data.get("candidate_version")
    assert "proposed_changes" in data
'''


class EvolutionImplementer:
    """Uses Jcode to materialize a mutation as candidate artifacts + tests."""

    def __init__(self, adapter: Optional[JcodeAdapter] = None) -> None:
        self.adapter = adapter

    def implement(self, mutation: Mutation, candidate: CandidateRecord) -> CodingResult:
        workspace = candidate.workspace_dir
        artifacts_dir = os.path.join(workspace, "artifacts")
        tests_dir = os.path.join(workspace, "tests")
        os.makedirs(artifacts_dir, exist_ok=True)
        os.makedirs(tests_dir, exist_ok=True)

        target = mutation.target.value
        filename = f"{target}.json"
        artifact_rel = os.path.join("artifacts", filename)
        test_rel = os.path.join("tests", f"test_{target}.py")
        artifact_abs = os.path.join(workspace, artifact_rel)
        test_abs = os.path.join(workspace, test_rel)

        if is_protected_path(artifact_abs) or is_protected_path(test_abs):
            raise ConstitutionalViolationError(
                "Evolution Controller self-protection: refusing to implement into protected path."
            )
        assert_candidate_write_allowed(artifact_abs, workspace)
        assert_candidate_write_allowed(test_abs, workspace)

        payload = {
            "target": target,
            "parent_version": mutation.parent_version,
            "candidate_version": mutation.candidate_version,
            "mutation_id": mutation.mutation_id,
            "proposed_changes": mutation.proposed_changes,
            "rationale": mutation.rationale,
        }
        files = {
            artifact_rel.replace("\\", "/"): json.dumps(payload, indent=2) + "\n",
            test_rel.replace("\\", "/"): _TEST_TEMPLATE.format(filename=filename, target=target),
        }

        adapter = self.adapter or JcodeAdapter(workspace_dir=workspace)
        task = CodingTask(
            task_id=f"evo-{uuid.uuid4().hex[:8]}",
            goal=(
                f"Implement evolution of {target} for candidate {mutation.candidate_version}. "
                "Write the versioned strategy artifact and its validation test."
            ),
            workspace_dir=workspace,
            test_command=None,
            constraints=[
                "Do not modify constitution, evolution controller, or permission ceiling.",
                "Stay inside the candidate workspace.",
            ],
            metadata={"files": files, "evolution": True, "mutation_id": mutation.mutation_id},
        )
        result = adapter.execute_coding_task(task)
        if result.status not in ("success", "completed"):
            candidate.status = CandidateStatus.IMPLEMENTATION_FAILED
            return result

        sandbox_session = RuntimeSession(
            session_id=f"evo-sandbox-{candidate.candidate_id}",
            workspace_id=candidate.candidate_id,
            workspace_dir=workspace,
            network_policy=NetworkPolicy.DENY,
            limits=ResourceLimits(timeout_seconds=20.0, max_output_bytes=65536),
        )
        sandbox = RuntimeSandbox(session=sandbox_session)
        test_path = sandbox.resolve_and_validate_path(test_rel)
        proc = sandbox.execute_process(
            cmd=[sys.executable, "-m", "pytest", test_path, "-q"],
            cwd=".",
            env={**os.environ, "PYTHONPATH": workspace},
        )
        result.metadata = {
            **(result.metadata or {}),
            "sandbox_exit_code": proc.get("exit_code"),
            "sandbox_success": proc.get("success"),
            "sandbox_stderr": proc.get("stderr", "")[:2000],
        }
        if not proc.get("success"):
            result.status = "failed"
            result.errors = list(result.errors or []) + [
                proc.get("stderr") or "Candidate sandbox tests failed."
            ]
            candidate.status = CandidateStatus.IMPLEMENTATION_FAILED
            return result

        candidate.status = CandidateStatus.IMPLEMENTED
        candidate.files_changed = list(result.files_changed)
        logger.info(
            f"Jcode implemented mutation '{mutation.mutation_id}' in candidate '{candidate.candidate_id}'"
        )
        return result
