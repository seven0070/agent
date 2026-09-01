"""
Unit and Integration Tests for Layer 9 — Evolution Controller & Metamorphosis Engine.
"""

import pytest
import os
import tempfile
import asyncio

from agent.evolution.models import (
    Mutation, MutationTarget, MutationStatus, EvolutionMode, CanaryStatus
)
from agent.evolution.observer import EvolutionObserver
from agent.evolution.proposer import MutationProposer
from agent.evolution.registry import MutationRegistry
from agent.evolution.gate import PromotionGate
from agent.evolution.approval import EvolutionApprovalHandler
from agent.evolution.canary import CanaryManager
from agent.evolution.rollback import RollbackEngine
from agent.evolution.controller import EvolutionController
from agent.evaluation.models import EvaluationReport, MetricDimensions, EvaluationRun, CaseResult

@pytest.mark.asyncio
async def test_evolution_domain_and_proposer():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_evo.db")
        registry = MutationRegistry(db_path=db_path)
        proposer = MutationProposer(registry=registry)

        mutation = proposer.propose_mutation(
            target=MutationTarget.PLANNER_STRATEGY,
            proposed_changes={"algorithm": "mcts"},
            rationale="Improve planning accuracy",
        )

        assert mutation.mutation_id.startswith("mut-")
        assert mutation.target == MutationTarget.PLANNER_STRATEGY
        assert mutation.candidate_version == "planner_strategy-v" + mutation.candidate_version.split("-v")[-1]
        assert mutation.status == MutationStatus.PROPOSED

        registry.save_mutation(mutation)
        retrieved = registry.get_mutation(mutation.mutation_id)
        assert retrieved is not None
        assert retrieved.mutation_id == mutation.mutation_id

@pytest.mark.asyncio
async def test_evolution_observer_and_weakness_identification():
    observer = EvolutionObserver()
    for _ in range(3):
        observer.record_observation(component="planner", success=False, error="Cycle detected")
    observer.record_observation(component="planner", success=True)

    weaknesses = observer.identify_weaknesses(failure_threshold=0.5)
    assert len(weaknesses) == 1
    assert weaknesses[0]["target"] == "planner_strategy"
    assert weaknesses[0]["failure_rate"] == 0.75

@pytest.mark.asyncio
async def test_promotion_gate_constitutional_protection():
    gate = PromotionGate()

    # Attempt illegal attack mutation on constitutional rules
    attack_mutation = Mutation(
        mutation_id="mut-attack",
        target=MutationTarget.CONSTITUTIONAL_RULES,
        parent_version="const-v1",
        candidate_version="const-v2",
        proposed_changes={"bypass_approval": True},
        status=MutationStatus.PROPOSED,
    )

    dummy_run = EvaluationRun(
        run_id="run-001",
        agent_version="const-v2",
        model_version="mock-v1",
        dataset_version="benchmark-v1",
        total_cases=1,
        passed_cases=1,
        failed_cases=0,
        unaggregated_scores=MetricDimensions(accuracy=1.0, safety=1.0),
        results=[],
    )

    report = EvaluationReport(
        report_id="rep-001",
        candidate_run_id="run-001",
        baseline_run_id="run-000",
        agent_version="const-v2",
        baseline_version="const-v1",
        dataset_version="benchmark-v1",
        metrics=MetricDimensions(accuracy=1.0, safety=1.0),
        candidate_scores=MetricDimensions(accuracy=1.0, safety=1.0),
        baseline_scores=MetricDimensions(accuracy=1.0, safety=1.0),
        recommendation="PASS",
    )

    decision = gate.evaluate(mutation=attack_mutation, report=report)
    assert decision.passed is False
    assert any("Layer -1 Constitutional Protection Violation" in r for r in decision.reasons)

@pytest.mark.asyncio
async def test_canary_and_rollback_engine():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_evo.db")
        registry = MutationRegistry(db_path=db_path)
        registry.set_active_generation("agent-v1")

        rollback_engine = RollbackEngine(registry=registry)
        canary_mgr = CanaryManager()

        mutation = Mutation(
            mutation_id="mut-123",
            target=MutationTarget.AGENT_ROUTING,
            parent_version="agent-v1",
            candidate_version="agent-v2",
            proposed_changes={},
            status=MutationStatus.APPROVED,
        )

        canary_mgr.start_canary(mutation=mutation, duration_steps=5, traffic_percentage=0.2)
        assert mutation.status == MutationStatus.CANARY

        # Simulate failures during canary
        for _ in range(3):
            canary_mgr.record_canary_step(mutation=mutation, success=False)

        assert mutation.canary_status == CanaryStatus.FAILED

        # Trigger rollback
        rollback_engine.rollback_mutation(mutation=mutation, reason="High canary error rate")
        assert mutation.status == MutationStatus.ROLLED_BACK
        assert registry.get_active_generation() == "agent-v1"

@pytest.mark.asyncio
async def test_evolution_controller_dry_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_evo.db")
        controller = EvolutionController(
            db_path=db_path,
            mode=EvolutionMode.AUTOMATIC,
        )

        observations = [
            {"component": "planner", "success": False, "error": "timeout"},
            {"component": "planner", "success": False, "error": "timeout"},
            {"component": "planner", "success": True},
        ]

        mutations = await controller.run_evolution_cycle(
            observations=observations,
            dry_run=True,
        )

        assert len(mutations) > 0
        assert mutations[0].status == MutationStatus.APPROVED
