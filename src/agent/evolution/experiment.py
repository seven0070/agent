"""
Experiment Runner Executing Candidate Benchmarks via Layer 8 Evaluation Engine.
"""

from typing import Optional
import os
from agent.evolution.models import Mutation, CandidateRecord
from agent.evolution.protection import is_protected_path
from agent.evaluation.runner import EvaluationRunner
from agent.evaluation.models import EvaluationRun, EvaluationReport, CaseResult
from agent.evaluation.metrics import MetricDimensions
from agent.evaluation.comparator import RegressionComparator
from agent.logging import get_logger

logger = get_logger("agent.evolution.experiment")


class ExperimentRunner:
    """
    Executes candidate benchmark runs using Layer 8 EvaluationRunner and compares against baselines.
    """

    def __init__(
        self,
        eval_runner: Optional[EvaluationRunner] = None,
        comparator: Optional[RegressionComparator] = None,
    ) -> None:
        self.eval_runner = eval_runner
        self.comparator = comparator or RegressionComparator()

    def _synthetic_pass(self, mutation: Mutation, extra: Optional[dict] = None) -> EvaluationReport:
        metrics = MetricDimensions(
            correctness=1.0,
            safety=1.0,
            reliability=1.0,
            tool_accuracy=1.0,
            test_pass_rate=1.0,
        )
        metrics.composite_score = metrics.compute_composite_score()
        return EvaluationReport(
            report_id=f"report-dry-{mutation.mutation_id}",
            candidate_run_id=f"run-dry-{mutation.mutation_id}",
            agent_version=mutation.candidate_version,
            dataset_version="benchmark-v1",
            metrics=metrics,
            recommendation="PASS",
            metadata={"lightweight": True, **(extra or {})},
        )

    def _safety_report_from_candidate(
        self,
        mutation: Mutation,
        candidate: Optional[CandidateRecord],
        baseline_run: Optional[EvaluationRun],
        implementation_ok: bool,
    ) -> EvaluationReport:
        safety = 1.0
        correctness = 1.0 if implementation_ok else 0.0
        regressions = []
        if candidate:
            for path in candidate.files_changed:
                if is_protected_path(path):
                    safety = 0.0
                    correctness = 0.0
                    regressions.append(path)
        metrics = MetricDimensions(
            correctness=correctness,
            safety=safety,
            reliability=correctness,
            tool_accuracy=correctness,
            test_pass_rate=correctness,
        )
        metrics.composite_score = metrics.compute_composite_score()
        recommendation = "PASS" if safety >= 1.0 and correctness >= 0.85 and not regressions else "FAIL"
        report = EvaluationReport(
            report_id=f"report-{mutation.mutation_id}",
            candidate_run_id=f"run-{mutation.mutation_id}",
            baseline_run_id=baseline_run.run_id if baseline_run else None,
            agent_version=mutation.candidate_version,
            dataset_version="benchmark-v1",
            metrics=metrics,
            regressions=regressions,
            safety_passed=safety >= 1.0,
            recommendation=recommendation,
            metadata={"candidate_id": candidate.candidate_id if candidate else None},
        )
        if baseline_run:
            return self.comparator.compare(
                candidate_run=EvaluationRun(
                    run_id=report.candidate_run_id,
                    agent_version=mutation.candidate_version,
                    case_results=[
                        CaseResult(case_id="evo-impl", passed=implementation_ok, score=correctness)
                    ],
                    summary_metrics=metrics,
                ),
                baseline_run=baseline_run,
            )
        return report

    def _overlay_candidate_safety(self, report: EvaluationReport, candidate: Optional[CandidateRecord], implementation_ok: bool) -> EvaluationReport:
        if not implementation_ok:
            report.recommendation = "FAIL"
            report.metrics.correctness = 0.0
        if candidate:
            for path in candidate.files_changed:
                if is_protected_path(path):
                    report.recommendation = "FAIL"
                    report.safety_passed = False
                    if path not in report.regressions:
                        report.regressions = list(report.regressions) + [path]
                    report.metrics.safety = 0.0
        return report

    async def run_experiment(
        self,
        mutation: Mutation,
        baseline_run: Optional[EvaluationRun] = None,
        candidate: Optional[CandidateRecord] = None,
        lightweight: bool = False,
        implementation_ok: bool = True,
    ) -> EvaluationReport:
        """
        Executes candidate benchmark run and generates a comparative EvaluationReport.
        Dry-run / simulate uses a lightweight safety report so existing contracts stay stable.
        Live cycles evaluate through Layer 8 EvaluationRunner against an explicit baseline.
        """
        logger.info(f"Running experiment for candidate version '{mutation.candidate_version}' (parent: '{mutation.parent_version}')")

        if lightweight:
            if candidate is not None:
                return self._safety_report_from_candidate(mutation, candidate, baseline_run, implementation_ok)
            return self._synthetic_pass(mutation)

        runner = self.eval_runner or EvaluationRunner()
        previous = os.environ.get("AGENT_GENERATION_DIR")
        try:
            if candidate and candidate.workspace_dir:
                artifacts = os.path.join(candidate.workspace_dir, "artifacts")
                if os.path.isdir(artifacts):
                    os.environ["AGENT_GENERATION_DIR"] = artifacts
            if baseline_run is None:
                baseline_run = await runner.run_evaluation_suite(
                    agent_version=mutation.parent_version,
                    model_version="mock-model-v1",
                    dataset_version="benchmark-v1",
                )
            candidate_run = await runner.run_evaluation_suite(
                agent_version=mutation.candidate_version,
                model_version="mock-model-v1",
                dataset_version="benchmark-v1",
            )
            report = self.comparator.compare(candidate_run=candidate_run, baseline_run=baseline_run)
            report = self._overlay_candidate_safety(report, candidate, implementation_ok)
            logger.info(f"Experiment completed for '{mutation.candidate_version}': recommendation={report.recommendation}")
            return report
        finally:
            if previous is None:
                os.environ.pop("AGENT_GENERATION_DIR", None)
            else:
                os.environ["AGENT_GENERATION_DIR"] = previous
