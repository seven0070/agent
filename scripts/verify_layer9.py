"""
Layer 9 Verification Script — Evolution Controller & Metamorphosis Control Plane Engine.
"""

import asyncio
import os
import tempfile
import sys

from agent.evolution.models import (
    Mutation, MutationTarget, MutationStatus, EvolutionMode, CanaryStatus
)
from agent.evolution.observer import EvolutionObserver
from agent.evolution.proposer import MutationProposer
from agent.evolution.registry import MutationRegistry
from agent.evolution.gate import PromotionGate
from agent.evolution.canary import CanaryManager
from agent.evolution.rollback import RollbackEngine
from agent.evolution.controller import EvolutionController
from agent.evaluation.models import EvaluationReport, MetricDimensions

async def main() -> int:
    print("=== Layer 9 Verification: Evolution Controller & Metamorphosis Engine ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "verify_evo.db")

        # 1. Verify Domain Models & Proposer
        print("[1/5] Verifying Mutation Registry and Proposer...")
        registry = MutationRegistry(db_path=db_path)
        proposer = MutationProposer(registry=registry)

        mut = proposer.propose_mutation(
            target=MutationTarget.PLANNER_STRATEGY,
            proposed_changes={"algorithm": "mcts_v2"},
            rationale="Optimize multi-step decomposition accuracy",
        )
        assert mut.mutation_id.startswith("mut-"), "Mutation ID should start with mut-"
        assert registry.get_mutation(mut.mutation_id) is not None, "Mutation should be saved in registry"
        print(f"  ✓ Created and persisted mutation '{mut.mutation_id}' for '{mut.target.value}'")

        # 2. Verify Observer & Weakness Detection
        print("[2/5] Verifying Evolution Observer & Weakness Analysis...")
        observer = EvolutionObserver()
        for _ in range(3):
            observer.record_observation(component="planner", success=False, error="Planner deadlock")
        observer.record_observation(component="planner", success=True)

        weaknesses = observer.identify_weaknesses(failure_threshold=0.5)
        assert len(weaknesses) == 1, f"Expected 1 weakness, got {len(weaknesses)}"
        assert weaknesses[0]["target"] == "planner_strategy", "Target should map to planner_strategy"
        print(f"  ✓ Identified weakness in '{weaknesses[0]['target']}' (failure rate: {weaknesses[0]['failure_rate']:.2f})")

        # 3. Verify Layer -1 Constitutional Protection in Promotion Gate
        print("[3/5] Verifying Promotion Gate Constitutional Rejection...")
        gate = PromotionGate()
        attack_mut = Mutation(
            mutation_id="mut-attack-001",
            target=MutationTarget.CONSTITUTIONAL_RULES,
            parent_version="const-v1",
            candidate_version="const-v2",
            proposed_changes={"bypass_gate": True},
            status=MutationStatus.PROPOSED,
        )
        dummy_report = EvaluationReport(
            report_id="rep-dummy",
            candidate_run_id="run-c",
            agent_version="const-v2",
            dataset_version="benchmark-v1",
            metrics=MetricDimensions(accuracy=1.0, safety=1.0),
            recommendation="PASS",
        )
        gate_decision = gate.evaluate(mutation=attack_mut, report=dummy_report)
        assert not gate_decision.passed, "Promotion Gate must reject attack on constitutional rules"
        print(f"  ✓ Promotion Gate rejected constitutional attack: {gate_decision.reasons[0]}")

        # 4. Verify Canary & Rollback Engine
        print("[4/5] Verifying Canary Management & Rollback Engine...")
        registry.set_active_generation("agent-v1")
        canary_mgr = CanaryManager()
        rollback_engine = RollbackEngine(registry=registry)

        valid_mut = Mutation(
            mutation_id="mut-valid-001",
            target=MutationTarget.MODEL_ROUTING,
            parent_version="agent-v1",
            candidate_version="agent-v2-canary",
            proposed_changes={"primary": "ollama/qwen2.5:14b"},
            status=MutationStatus.APPROVED,
        )

        canary_mgr.start_canary(mutation=valid_mut, duration_steps=5, traffic_percentage=0.1)
        for _ in range(2):
            canary_mgr.record_canary_step(mutation=valid_mut, success=False)

        assert valid_mut.canary_status == CanaryStatus.FAILED, "Canary should mark status FAILED on errors"
        rollback_engine.rollback_mutation(mutation=valid_mut, reason="Excessive canary latency and errors")
        assert valid_mut.status == MutationStatus.ROLLED_BACK, "Mutation should be marked ROLLED_BACK"
        assert registry.get_active_generation() == "agent-v1", "Active generation should remain parent baseline"
        print("  ✓ Canary failure accurately triggered Rollback Engine to parent baseline 'agent-v1'")

        # 5. Verify End-to-End Control Plane Cycle
        print("[5/5] Verifying End-to-End Evolution Control Plane Cycle (Dry Run)...")
        controller = EvolutionController(db_path=db_path, mode=EvolutionMode.AUTOMATIC)
        observations = [
            {"component": "planner", "success": False, "error": "timeout"},
            {"component": "planner", "success": False, "error": "timeout"},
            {"component": "planner", "success": True},
        ]

        cycle_mutations = await controller.run_evolution_cycle(observations=observations, dry_run=True)
        assert len(cycle_mutations) > 0, "Controller cycle should propose mutation for observed failure"
        assert cycle_mutations[0].status == MutationStatus.APPROVED, "Mutation should be approved in dry_run"
        print(f"  ✓ End-to-End evolution cycle successfully ran: proposed candidate '{cycle_mutations[0].candidate_version}'")

    print("\n=== LAYER 9 VERIFICATION SUCCESSFUL ===")
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
