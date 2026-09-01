"""
Baseline Storage and Regression Comparator Engine.
Compares candidate evaluation runs against baselines and evaluates threshold policies.
"""

from typing import Dict, List, Optional, Any
from agent.evaluation.models import EvaluationRun, EvaluationReport, CaseResult
from agent.evaluation.metrics import MetricDimensions, EvaluationThresholds
from agent.logging import get_logger

logger = get_logger("agent.evaluation.comparator")

class BaselineStore:
    """
    In-memory / persistent baseline run store.
    """

    def __init__(self) -> None:
        self._baselines: Dict[str, EvaluationRun] = {}

    def set_baseline(self, key: str, run: EvaluationRun) -> None:
        """Sets an evaluation run as a named baseline."""
        self._baselines[key] = run
        logger.info(f"Saved baseline '{key}' for agent version '{run.agent_version}' ({len(run.case_results)} cases)")

    def get_baseline(self, key: str) -> Optional[EvaluationRun]:
        """Retrieves a named baseline run."""
        return self._baselines.get(key)

class RegressionComparator:
    """
    Compares candidate evaluation run against baseline run and evaluates against thresholds.
    """

    def __init__(self, thresholds: Optional[EvaluationThresholds] = None) -> None:
        self.thresholds = thresholds or EvaluationThresholds()

    def compare(self, candidate_run: EvaluationRun, baseline_run: Optional[EvaluationRun] = None) -> EvaluationReport:
        """
        Compares candidate_run against baseline_run, identifies case regressions/improvements,
        and generates structured EvaluationReport with recommendation (PASS, FAIL, REVIEW).
        """
        report_id = f"report-{candidate_run.run_id}"
        regressions: List[str] = []
        improvements: List[str] = []
        safety_passed = True

        # Index baseline results by case_id if baseline is available
        baseline_cases: Dict[str, CaseResult] = {}
        if baseline_run:
            baseline_cases = {cr.case_id: cr for cr in baseline_run.case_results}

        # Compare individual cases
        for cand_res in candidate_run.case_results:
            cid = cand_res.case_id

            if cand_res.safety_violation:
                safety_passed = False

            if cid in baseline_cases:
                base_res = baseline_cases[cid]
                if base_res.passed and not cand_res.passed:
                    regressions.append(cid)
                    logger.warning(f"Case REGRESSION detected: '{cid}' passed in baseline ({baseline_run.agent_version}) but failed in candidate ({candidate_run.agent_version})")
                elif not base_res.passed and cand_res.passed:
                    improvements.append(cid)
                    logger.info(f"Case IMPROVEMENT detected: '{cid}' failed in baseline ({baseline_run.agent_version}) but passed in candidate ({candidate_run.agent_version})")

        cand_metrics = candidate_run.summary_metrics

        # Determine Recommendation based on EvaluationThresholds
        recommendation = "PASS"
        if not safety_passed or cand_metrics.safety < self.thresholds.min_safety:
            recommendation = "FAIL"
            logger.error("Evaluation Recommendation FAIL: Safety threshold violation.")
        elif len(regressions) > self.thresholds.max_allowed_regressions:
            recommendation = "FAIL"
            logger.error(f"Evaluation Recommendation FAIL: {len(regressions)} regressions exceeded threshold max allowed ({self.thresholds.max_allowed_regressions}).")
        elif cand_metrics.correctness < self.thresholds.min_correctness:
            recommendation = "REVIEW"
            logger.warning(f"Evaluation Recommendation REVIEW: Correctness ({cand_metrics.correctness}) below threshold ({self.thresholds.min_correctness}).")

        return EvaluationReport(
            report_id=report_id,
            candidate_run_id=candidate_run.run_id,
            baseline_run_id=baseline_run.run_id if baseline_run else None,
            agent_version=candidate_run.agent_version,
            dataset_version=candidate_run.dataset_version,
            metrics=cand_metrics,
            regressions=regressions,
            improvements=improvements,
            safety_passed=safety_passed,
            recommendation=recommendation,
            metadata={
                "candidate_cases_count": len(candidate_run.case_results),
                "baseline_cases_count": len(baseline_cases),
            },
        )
