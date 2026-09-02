"""
Layer 9 Verification Script — Evolution Controller & Metamorphosis Control Plane Engine.
"""

import asyncio
import os
import tempfile
import sys

from agent.evolution.models import (
    Mutation, MutationTarget, MutationStatus, EvolutionMode, CanaryStatus, CandidateStatus
)
from agent.evolution.observer import EvolutionObserver
from agent.evolution.proposer import MutationProposer
from agent.evolution.registry import MutationRegistry
from agent.evolution.gate import PromotionGate
from agent.evolution.canary import CanaryManager
from agent.evolution.rollback import RollbackEngine
from agent.evolution.controller import EvolutionController
from agent.evolution.candidate import CandidateManager
from agent.evolution.implementer import EvolutionImplementer
from agent.evolution.protection import assert_target_evolvable, is_protected_target
from agent.evolution.models import EvolutionProposal
from agent.evaluation.models import EvaluationReport, MetricDimensions, EvaluationRun, CaseResult
from agent.constitution import ConstitutionalViolationError

class FakeEvalRunner:
    async def run_evaluation_suite(self, **kwargs):
        metrics = MetricDimensions(correctness=1.0, safety=1.0, reliability=1.0, tool_accuracy=1.0, test_pass_rate=1.0)
        metrics.composite_score = metrics.compute_composite_score()
        return EvaluationRun(
            run_id="verify-run",
            agent_version=kwargs.get("agent_version", "candidate"),
            case_results=[CaseResult(case_id="evo-1", passed=True, score=1.0)],
            summary_metrics=metrics,
        )

async def main() -> int:
    print("=== Layer 9 Verification: Evolution Controller & Metamorphosis Engine ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "verify_evo.db")

        # 1. Verify Domain Models & Proposer
        print("[1/8] Verifying Mutation Registry and Proposer...")
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
        print("[2/8] Verifying Evolution Observer & Weakness Analysis...")
        observer = EvolutionObserver()
        for _ in range(3):
            observer.record_observation(component="planner", success=False, error="Planner deadlock")
        observer.record_observation(component="planner", success=True)

        weaknesses = observer.identify_weaknesses(failure_threshold=0.5)
        assert len(weaknesses) == 1, f"Expected 1 weakness, got {len(weaknesses)}"
        assert weaknesses[0]["target"] == "planner_strategy", "Target should map to planner_strategy"
        print(f"  ✓ Identified weakness in '{weaknesses[0]['target']}' (failure rate: {weaknesses[0]['failure_rate']:.2f})")

        # 3. Verify Layer -1 Constitutional Protection in Promotion Gate
        print("[3/8] Verifying Promotion Gate Constitutional Rejection...")
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
        print("[4/8] Verifying Canary Management & Rollback Engine...")
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
        print("[5/8] Verifying End-to-End Evolution Control Plane Cycle (Dry Run)...")
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

        # 6. Isolated candidate + Jcode + sandbox
        print("[6/8] Verifying isolated candidate implementation through Jcode and Layer 7...")
        manager = CandidateManager(root_dir=os.path.join(tmpdir, "candidates"))
        impl_mut = Mutation(
            mutation_id="mut-verify-impl",
            target=MutationTarget.PLANNER_STRATEGY,
            parent_version="agent-v1",
            candidate_version="planner_strategy-vverify",
            proposed_changes={"strategy_patch": {"max_retries": 3}},
        )
        proposal = EvolutionProposal(
            proposal_id="prop-verify",
            mutation_id=impl_mut.mutation_id,
            detected_problem="timeouts",
            affected_capability="planner_strategy",
            proposed_change=impl_mut.proposed_changes,
        )
        candidate = manager.create_candidate(proposal, impl_mut, data_dir=tmpdir)
        manager.assert_isolated(candidate)
        coding = EvolutionImplementer().implement(impl_mut, candidate)
        assert coding.status == "success"
        assert candidate.status == CandidateStatus.IMPLEMENTED
        print(f"  ✓ Candidate '{candidate.candidate_id}' implemented in isolation with sandbox tests")

        # 7. Self-protection
        print("[7/8] Verifying Evolution Controller self-protection...")
        assert is_protected_target("evolution_controller_integrity")
        try:
            assert_target_evolvable("constitutional_rules")
            raise AssertionError("protected target must be rejected")
        except ConstitutionalViolationError:
            print("  ✓ Protected targets cannot be evolved")

        # 8. Live promote/rollback with Layer 8 stub
        print("[8/8] Verifying promotion, lineage, rollback, and audit trail...")
        live = EvolutionController(
            db_path=os.path.join(tmpdir, "live.db"),
            data_dir=os.path.join(tmpdir, "live"),
            mode=EvolutionMode.AUTOMATIC,
            eval_runner=FakeEvalRunner(),
        )
        live_mutations = await live.run_evolution_cycle(observations=observations, dry_run=False)
        assert live_mutations[0].status == MutationStatus.PROMOTED
        assert live.registry.get_active_generation() == live_mutations[0].candidate_version
        live.rollback(live_mutations[0].mutation_id, "verification rollback")
        assert live.registry.get_active_generation() == "agent-v1"
        event_types = {e.event_type for e in live.registry.list_audit(limit=50)}
        assert "PROMOTED" in event_types and "ROLLBACK" in event_types
        print("  ✓ Promotion, version lineage, rollback, and audit trail verified")

    print("\n=== LAYER 9 VERIFICATION SUCCESSFUL ===")
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
