"""
Comprehensive tests for Layer 9 Evolution Control Plane.

Covers observation, proposal, candidate isolation, Jcode implementation,
sandbox enforcement, Layer 8 evaluation, promotion gate, human approval,
rollback, version lineage, audit trail, constitution, self-protection,
API security, and concurrent cycle prevention.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from agent.coding.models import CodingResult
from agent.constitution import ConstitutionalGuard, ConstitutionalViolationError
from agent.evaluation.metrics import MetricDimensions
from agent.evaluation.models import CaseResult, EvaluationRun
from agent.evolution.candidate import CandidateManager
from agent.evolution.controller import EvolutionController
from agent.evolution.gate import PromotionGate
from agent.evolution.generation import load_artifact, promote_candidate_artifacts
from agent.evolution.implementer import EvolutionImplementer
from agent.evolution.models import (
    CandidateRecord,
    CandidateStatus,
    EvolutionMode,
    EvolutionProposal,
    Mutation,
    MutationStatus,
    MutationTarget,
    ProposalStatus,
)
from agent.evolution.observer import EvolutionObserver
from agent.evolution.protection import (
    assert_candidate_write_allowed,
    assert_target_evolvable,
    is_protected_path,
    is_protected_target,
)
from agent.evolution.proposer import MutationProposer
from agent.evolution.registry import MutationRegistry
from agent.evolution.trigger import EvolutionTrigger


PLANNER_OBS = [
    {"component": "planner", "success": False, "error": "timeout"},
    {"component": "planner", "success": False, "error": "timeout"},
    {"component": "planner", "success": True},
]


class FakeEvalRunner:
    def __init__(
        self,
        passed: bool = True,
        correctness: float = 1.0,
        safety: float = 1.0,
        case_id: str = "evo-1",
    ) -> None:
        self.passed = passed
        self.correctness = correctness
        self.safety = safety
        self.case_id = case_id
        self.calls = 0

    async def run_evaluation_suite(self, **kwargs: Any) -> EvaluationRun:
        self.calls += 1
        metrics = MetricDimensions(
            correctness=self.correctness,
            safety=self.safety,
            reliability=self.correctness,
            tool_accuracy=self.correctness,
            test_pass_rate=self.correctness,
        )
        metrics.composite_score = metrics.compute_composite_score()
        return EvaluationRun(
            run_id=f"run-fake-{self.calls}",
            agent_version=kwargs.get("agent_version", "candidate"),
            dataset_version=kwargs.get("dataset_version", "benchmark-v1"),
            case_results=[
                CaseResult(
                    case_id=self.case_id,
                    passed=self.passed,
                    score=self.correctness,
                    safety_violation=self.safety < 1.0,
                )
            ],
            summary_metrics=metrics,
        )


class FailingJcode:
    def execute_coding_task(self, task):  # noqa: ANN001
        return CodingResult(task_id=task.task_id, status="failed", errors=["implementation boom"])


def _controller(tmpdir: str, **kwargs: Any) -> EvolutionController:
    db_path = os.path.join(tmpdir, "evo.db")
    kwargs.setdefault("eval_runner", FakeEvalRunner())
    return EvolutionController(
        db_path=db_path,
        data_dir=tmpdir,
        **kwargs,
    )


def test_proposal_creation_from_capability_gap():
    observer = EvolutionObserver()
    observer.record_capability_gap("planner", {"reason": "cannot decompose nested tools"})
    observer.record_observation(component="planner", success=False, error="timeout")
    weaknesses = observer.identify_weaknesses(failure_threshold=0.5)
    assert weaknesses
    assert weaknesses[0]["target"] == "planner_strategy"
    trigger = EvolutionTrigger()
    chosen = trigger.select_trigger(weaknesses)
    assert chosen is not None
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = MutationRegistry(db_path=os.path.join(tmpdir, "evo.db"))
        proposer = MutationProposer(registry=registry)
        mutation = proposer.propose_mutation(
            target=MutationTarget(chosen["target"]),
            proposed_changes={"reason": chosen["reason"]},
            rationale="address capability gap",
        )
        assert mutation.mutation_id.startswith("mut-")
        assert mutation.status == MutationStatus.PROPOSED
        assert registry.get_mutation(mutation.mutation_id) is not None


def test_invalid_proposal_rejection_protected_target():
    with pytest.raises(ConstitutionalViolationError):
        assert_target_evolvable("constitutional_rules")
    with pytest.raises(ConstitutionalViolationError):
        assert_target_evolvable("evolution_controller_integrity")
    with pytest.raises(ConstitutionalViolationError):
        assert_target_evolvable("permission_ceiling")
    assert is_protected_target(MutationTarget.CONSTITUTIONAL_RULES)


@pytest.mark.asyncio
async def test_controller_rejects_constitutional_observations():
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = _controller(tmpdir, mode=EvolutionMode.AUTOMATIC)
        mutations = await controller.run_evolution_cycle(
            observations=[
                {"component": "constitutional_rules", "success": False, "error": "bypass"},
                {"component": "constitutional_rules", "success": False, "error": "bypass"},
            ],
            dry_run=True,
        )
        assert mutations == []
        audit = controller.registry.list_audit()
        assert any(e.event_type in ("PROPOSAL_REJECTED", "OBSERVATION") for e in audit)


def test_candidate_isolation_and_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = CandidateManager(root_dir=os.path.join(tmpdir, "candidates"))
        mutation = Mutation(
            mutation_id="mut-iso",
            target=MutationTarget.PLANNER_STRATEGY,
            parent_version="agent-v1",
            candidate_version="planner_strategy-vtest",
            proposed_changes={"strategy_patch": {"max_retries": 3}},
        )
        proposal = EvolutionProposal(
            proposal_id="prop-iso",
            mutation_id=mutation.mutation_id,
            detected_problem="planner timeout",
            affected_capability="planner_strategy",
            proposed_change=mutation.proposed_changes,
        )
        record = manager.create_candidate(proposal, mutation, data_dir=tmpdir)
        manager.assert_isolated(record)
        assert record.candidate_id.startswith("cand-")
        assert record.status == CandidateStatus.CREATED
        assert os.path.isdir(record.workspace_dir)
        src_root = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "src"))
        assert not os.path.realpath(record.workspace_dir).startswith(src_root + os.sep)
        assert os.path.isfile(os.path.join(record.workspace_dir, "MANIFEST.json"))
        cleaned = manager.cleanup(record)
        assert cleaned.status == CandidateStatus.CLEANED
        assert not os.path.isdir(record.workspace_dir)


def test_candidate_write_cannot_escape_or_hit_protected_paths():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = os.path.join(tmpdir, "candidates", "cand-x")
        os.makedirs(workspace, exist_ok=True)
        allowed = os.path.join(workspace, "artifacts", "planner_strategy.json")
        os.makedirs(os.path.dirname(allowed), exist_ok=True)
        assert_candidate_write_allowed(allowed, workspace)
        with pytest.raises(ConstitutionalViolationError):
            assert_candidate_write_allowed(os.path.join(tmpdir, "outside.json"), workspace)
        assert is_protected_path("/tmp/src/agent/constitution.py")
        assert is_protected_path("src/agent/evolution/controller.py")


def test_implementation_failure_marks_candidate_failed():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = CandidateManager(root_dir=os.path.join(tmpdir, "candidates"))
        mutation = Mutation(
            mutation_id="mut-fail",
            target=MutationTarget.PLANNER_STRATEGY,
            parent_version="agent-v1",
            candidate_version="planner_strategy-vfail",
            proposed_changes={"strategy_patch": {"max_retries": 3}},
        )
        proposal = EvolutionProposal(
            proposal_id="prop-fail",
            mutation_id="mut-fail",
            detected_problem="x",
            affected_capability="planner_strategy",
            proposed_change={},
        )
        candidate = manager.create_candidate(proposal, mutation, data_dir=tmpdir)
        implementer = EvolutionImplementer(adapter=FailingJcode())
        result = implementer.implement(mutation, candidate)
        assert result.status == "failed"
        assert candidate.status == CandidateStatus.IMPLEMENTATION_FAILED


def test_sandbox_enforced_jcode_implementation():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = CandidateManager(root_dir=os.path.join(tmpdir, "candidates"))
        mutation = Mutation(
            mutation_id="mut-impl",
            target=MutationTarget.PLANNER_STRATEGY,
            parent_version="agent-v1",
            candidate_version="planner_strategy-vimpl",
            proposed_changes={"strategy_patch": {"max_retries": 4}},
            rationale="raise retries",
        )
        proposal = EvolutionProposal(
            proposal_id="prop-impl",
            mutation_id="mut-impl",
            detected_problem="timeouts",
            affected_capability="planner_strategy",
            proposed_change=mutation.proposed_changes,
        )
        candidate = manager.create_candidate(proposal, mutation, data_dir=tmpdir)
        result = EvolutionImplementer().implement(mutation, candidate)
        assert result.status in ("success", "completed")
        assert candidate.status == CandidateStatus.IMPLEMENTED
        artifact = os.path.join(candidate.workspace_dir, "artifacts", "planner_strategy.json")
        assert os.path.isfile(artifact)
        assert result.metadata.get("sandbox_success") is True
        assert result.metadata.get("sandbox_exit_code") == 0


@pytest.mark.asyncio
async def test_evaluation_failure_and_regression_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        baseline = EvaluationRun(
            run_id="base-1",
            agent_version="agent-v1",
            case_results=[CaseResult(case_id="evo-1", passed=True, score=1.0)],
            summary_metrics=MetricDimensions(correctness=1.0, safety=1.0, reliability=1.0),
        )
        controller = _controller(
            tmpdir,
            mode=EvolutionMode.AUTOMATIC,
            eval_runner=FakeEvalRunner(passed=False, correctness=0.2, safety=1.0),
        )
        mutations = await controller.run_evolution_cycle(
            observations=PLANNER_OBS,
            dry_run=False,
            baseline_run=baseline,
        )
        assert mutations
        assert mutations[0].status == MutationStatus.REJECTED
        assert controller._last_gate["decision"] == "FAIL"


@pytest.mark.asyncio
async def test_promotion_approval_and_rejection():
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = _controller(tmpdir, mode=EvolutionMode.SEMI_AUTOMATIC)
        mutations = await controller.run_evolution_cycle(observations=PLANNER_OBS, dry_run=False)
        assert mutations
        mut = mutations[0]
        pending = controller.approval_handler.list_pending()
        assert any(p["mutation_id"] == mut.mutation_id for p in pending)

        rejected = controller.approve_and_promote(mut.mutation_id, approved=False)
        assert rejected["approved"] is False
        assert controller.registry.get_mutation(mut.mutation_id).status == MutationStatus.REJECTED

        controller2 = _controller(os.path.join(tmpdir, "c2"), mode=EvolutionMode.SEMI_AUTOMATIC)
        mutations = await controller2.run_evolution_cycle(observations=PLANNER_OBS, dry_run=False)
        mut = mutations[0]
        promoted = controller2.approve_and_promote(mut.mutation_id, approved=True)
        assert promoted["mutation_status"] == MutationStatus.PROMOTED.value
        assert controller2.registry.get_active_generation() == mut.candidate_version


@pytest.mark.asyncio
async def test_automatic_promote_versions_and_rollback():
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = _controller(tmpdir, mode=EvolutionMode.AUTOMATIC)
        mutations = await controller.run_evolution_cycle(observations=PLANNER_OBS, dry_run=False)
        assert mutations
        mut = mutations[0]
        assert mut.status == MutationStatus.PROMOTED
        assert controller.registry.get_active_generation() == mut.candidate_version
        lineage = controller.registry.lineage()
        assert any(row["version"] == mut.candidate_version for row in lineage)
        assert any(row["parent_version"] == "agent-v1" for row in lineage)
        artifact = load_artifact("planner_strategy", data_dir=tmpdir, version=mut.candidate_version)
        assert artifact.get("target") == "planner_strategy"

        rolled = controller.rollback(mut.mutation_id, "health regression")
        assert rolled.status == MutationStatus.ROLLED_BACK
        assert controller.registry.get_active_generation() == mut.parent_version


@pytest.mark.asyncio
async def test_audit_trail_records_full_cycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = _controller(tmpdir, mode=EvolutionMode.AUTOMATIC)
        await controller.run_evolution_cycle(observations=PLANNER_OBS, dry_run=False)
        events = {e.event_type for e in controller.registry.list_audit(limit=100)}
        assert "OBSERVATION" in events
        assert "MUTATION_PROPOSED" in events
        assert "CANDIDATE_CREATED" in events
        assert "IMPLEMENTATION" in events
        assert "EVALUATION" in events
        assert "PROMOTED" in events


def test_constitution_and_permission_enforcement():
    guard = ConstitutionalGuard()
    with pytest.raises(ConstitutionalViolationError):
        guard.validate_action({"type": "mutate", "target": "constitutional_rules"})
    with pytest.raises(ConstitutionalViolationError):
        guard.validate_action({"type": "promote", "human_approved": False})
    with pytest.raises(ConstitutionalViolationError):
        guard.validate_action({"type": "overwrite", "target": "permission_ceiling"})
    gate = PromotionGate()
    attack = Mutation(
        mutation_id="mut-attack-cp",
        target=MutationTarget.CONSTITUTIONAL_RULES,
        parent_version="const-v1",
        candidate_version="const-v2",
        proposed_changes={"bypass": True},
    )
    from agent.evaluation.models import EvaluationReport

    report = EvaluationReport(
        report_id="r",
        candidate_run_id="c",
        agent_version="const-v2",
        dataset_version="benchmark-v1",
        metrics=MetricDimensions(correctness=1.0, safety=1.0),
        recommendation="PASS",
    )
    decision = gate.evaluate(mutation=attack, report=report)
    assert decision.passed is False
    assert any("Layer -1 Constitutional Protection Violation" in r for r in decision.reasons)


def test_evolution_controller_self_protection():
    assert is_protected_target("evolution_controller_integrity")
    with pytest.raises(ConstitutionalViolationError):
        assert_target_evolvable("evolution_controller_integrity")
    guard = ConstitutionalGuard()
    names = [inv.name for inv in guard.get_active_invariants()]
    assert "evolution_controller_self_protection" in names
    with pytest.raises(ConstitutionalViolationError):
        guard.validate_action({"type": "mutate", "target": "evolution_controller_integrity"})


@pytest.mark.asyncio
async def test_concurrent_duplicate_evolution_prevention():
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = _controller(tmpdir, mode=EvolutionMode.AUTOMATIC)
        held = controller.registry.try_acquire_cycle_lock("external-holder")
        assert held is True
        mutations = await controller.run_evolution_cycle(observations=PLANNER_OBS, dry_run=True)
        assert mutations == []
        controller.registry.release_cycle_lock("external-holder")
        mutations = await controller.run_evolution_cycle(observations=PLANNER_OBS, dry_run=True)
        assert len(mutations) > 0


def test_trigger_suppresses_weak_signals():
    trigger = EvolutionTrigger(min_failures=2, failure_threshold=0.5)
    weak = [{"target": "planner_strategy", "failures": 1, "failure_rate": 0.2}]
    assert trigger.select_trigger(weak) is None
    protected = [{"target": "constitutional_rules", "failures": 9, "failure_rate": 0.9}]
    assert trigger.select_trigger(protected) is None
    assert trigger.select_trigger(
        [{"target": "planner_strategy", "failures": 3, "failure_rate": 0.75}],
        in_flight_count=1,
    ) is None


def test_api_security_blocks_protected_mutation_payload():
    from agent.api.app import app

    client = TestClient(app)
    res = client.post(
        "/api/evolution/cycle?dry_run=true",
        json={"target": "constitutional_rules", "proposed_changes": {"bypass": True}},
    )
    assert res.status_code == 403
    assert "Constitutional Protection Violation" in res.json()["detail"]

    res_ok = client.post("/api/evolution/cycle?dry_run=true")
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "completed"

    status = client.get("/api/evolution/status")
    assert status.status_code == 200
    assert "active_generation" in status.json()
    assert "candidates" in status.json()

    proposals = client.get("/api/evolution/proposals")
    assert proposals.status_code == 200
    assert isinstance(proposals.json(), list)

    lineage = client.get("/api/evolution/lineage")
    assert lineage.status_code == 200


def test_promote_candidate_artifacts_do_not_touch_src():
    with tempfile.TemporaryDirectory() as tmpdir:
        cand = os.path.join(tmpdir, "candidates", "cand-y")
        artifacts = os.path.join(cand, "artifacts")
        os.makedirs(artifacts, exist_ok=True)
        with open(os.path.join(artifacts, "planner_strategy.json"), "w", encoding="utf-8") as handle:
            handle.write('{"target": "planner_strategy", "candidate_version": "v2"}')
        dest = promote_candidate_artifacts(cand, "planner_strategy-v2", data_dir=tmpdir)
        assert dest.startswith(tmpdir)
        src_constitution = os.path.join(os.path.dirname(__file__), "..", "src", "agent", "constitution.py")
        original = open(src_constitution, "r", encoding="utf-8").read()
        assert "ConstitutionalGuard" in original
