# Layer 8 — Evaluation / Verification Engine System Specification

## Overview
Layer 8 provides an objective, versioned evaluation system (`EvaluationEngine`) that measures agent, plan, tool, coding task, and candidate version performance. It generates multi-dimensional metric cards, compares candidates against established baselines (`baseline: agent-v1`), detects regressions, enforces configurable promotion thresholds, and produces machine-readable `EvaluationReport`s.

Layer 9 (Evolution Controller) consumes Layer 8 evaluation reports to make empirical promotion or rollback decisions.

## Evaluation Engine Architecture

```text
                           EVALUATION DATASET (`EvaluationCase`)
                                     │
                                     ▼
                           EVALUATION RUNNER (`EvaluationRunner`)
                             (runs inside Layer 7 Sandbox)
                                     │
                                     ▼
                      DETERMINISTIC EVALUATORS (`DeterministicEvaluator`)
            ┌────────────────────────┼────────────────────────┐
            ▼                        ▼                        ▼
     CODING EVALUATION      PLANNING EVALUATION       SAFETY BENCHMARK
   (pytest, file edits)    (DAG, task execution)    (path escape, permissions)
            │                        │                        │
            └────────────────────────┼────────────────────────┘
                                     │
                                     ▼
                     MULTI-DIMENSIONAL METRICS (`MetricDimensions`)
                   (correctness, safety, reliability, latency)
                                     │
                                     ▼
                   REGRESSION COMPARATOR (`RegressionComparator`)
                     (candidate vs baseline comparison)
                                     │
                                     ▼
                    EVALUATION REPORT (`EvaluationReport`)
                         (recommendation: PASS / FAIL / REVIEW)
```

## Multi-Dimensional Metrics
Rather than reducing evaluation to a single lossy score, raw dimensions are preserved to prevent optimizing one metric while degrading another:
- `correctness`: Task completion and test suite pass rate (0.0 to 1.0)
- `safety`: Security policy compliance (1.0 = zero permission/path violations; 0.0 = safety breach)
- `reliability`: Execution success rate without unexpected errors (0.0 to 1.0)
- `latency_ms`: Execution duration in milliseconds
- `tool_accuracy`: Rate of valid tool selections and parameter schema compliance
- `test_pass_rate`: Percentage of workspace unit tests passing

## Baseline & Regression Comparison
- **Baseline Store (`BaselineStore`)**: Persists benchmark runs for verified baseline agent versions (e.g., `baseline: agent-v1`).
- **Regression Comparator (`RegressionComparator`)**: Compares candidate runs (`candidate: agent-v2`) against baseline runs on identical evaluation datasets (`benchmark-v1`).
- Categorizes performance per metric and case: `IMPROVED`, `UNCHANGED`, `REGRESSED`.

## Configurable Evaluation Thresholds (`EvaluationThresholds`)
- `min_correctness`: Minimum acceptable correctness score (default 0.90)
- `min_safety`: Minimum acceptable safety score (default 1.00 — zero safety regressions)
- `max_allowed_regressions`: Maximum allowed test case regressions (default 0)
- `max_latency_increase_ratio`: Maximum allowed latency increase ratio (default 0.25 — 20% latency buffer)

## Deterministic Evaluators
1. **Coding Evaluator**: Ingests workspace, executes unit test suites (`pytest`), verifies file creation and structural correctness.
2. **Planning Evaluator**: Verifies task dependency ordering, task completion, and state transition validity.
3. **Tool Evaluator**: Verifies tool selection, argument schema validity, and tool execution status.
4. **Safety Evaluator**: Deliberately executes path traversal attacks (`../../`), permission bypass requests, and unapproved tool actions. Verifies the runtime and capability broker reject unauthorized actions.

## Security Boundary & Immutable Reports
- The evaluated agent runs inside an isolated Layer 7 `RuntimeSandbox`.
- The evaluated agent has **READ-ONLY** access and CANNOT modify evaluation datasets, baselines, promotion thresholds, or report recommendations.
- Evaluators and reports are generated in the trusted control-plane context.
