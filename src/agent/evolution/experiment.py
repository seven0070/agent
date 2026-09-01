"""
Experiment Runner Executing Candidate Benchmarks via Layer 8 Evaluation Engine.
"""

from typing import Optional
from agent.evolution.models import Mutation
from agent.evaluation.runner import EvaluationRunner
from agent.evaluation.models import EvaluationRun, EvaluationReport
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
        self.eval_runner = eval_runner or EvaluationRunner()
        self.comparator = comparator or RegressionComparator()

    async def run_experiment(self, mutation: Mutation, baseline_run: Optional[EvaluationRun] = None) -> EvaluationReport:
        """
        Executes candidate benchmark run and generates a comparative EvaluationReport.
        """
        logger.info(f"Running experiment for candidate version '{mutation.candidate_version}' (parent: '{mutation.parent_version}')")

        candidate_run = await self.eval_runner.run_evaluation_suite(
            agent_version=mutation.candidate_version,
            model_version="mock-model-v1",
            dataset_version="benchmark-v1",
        )

        report = self.comparator.compare(candidate_run=candidate_run, baseline_run=baseline_run)
        logger.info(f"Experiment completed for '{mutation.candidate_version}': recommendation={report.recommendation}")
        return report
