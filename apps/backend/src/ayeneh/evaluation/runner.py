"""Evaluation runner — executes benchmark cases and produces reports."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

import structlog

from ayeneh.evaluation.benchmarks.golden import get_all_benchmarks, get_benchmarks
from ayeneh.evaluation.core import EvalCase, EvalReport, EvalResult, QualityThreshold
from ayeneh.evaluation.evaluators import (
    BlindSpotEvaluator,
    ConversationEvaluator,
    MemoryEvaluator,
    PatternEvaluator,
    ReflectionEvaluator,
)

logger = structlog.get_logger(__name__)


EVALUATOR_MAP = {
    "conversation": ConversationEvaluator(),
    "memory": MemoryEvaluator(),
    "pattern": PatternEvaluator(),
    "reflection": ReflectionEvaluator(),
    "blind_spot": BlindSpotEvaluator(),
}


@dataclass
class EvalRunConfig:
    agent_type: str | None = None
    thresholds: list[QualityThreshold] = field(default_factory=list)
    custom_cases: list[EvalCase] = field(default_factory=list)
    regression_baseline: dict[str, float] | None = None
    regression_tolerance: float = 0.1


class EvaluationRunner:
    """Runs evaluations and produces reports with regression detection."""

    def __init__(self) -> None:
        self._history: list[EvalReport] = []

    def run(
        self,
        agent_fn: Callable[[dict[str, Any]], dict[str, Any]],
        config: EvalRunConfig | None = None,
    ) -> EvalReport:
        cfg = config or EvalRunConfig()
        cases = cfg.custom_cases or (
            get_benchmarks(cfg.agent_type) if cfg.agent_type else get_all_benchmarks()
        )

        results: list[EvalResult] = []
        for case in cases:
            evaluator = EVALUATOR_MAP.get(case.agent_type)
            if evaluator is None:
                continue

            start = time.monotonic()
            try:
                actual = agent_fn(case.input_data)
            except Exception as exc:
                actual = {"error": str(exc)}

            duration = (time.monotonic() - start) * 1000
            result = evaluator.evaluate(case, actual)
            result.duration_ms = duration
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed

        metrics_summary = self._aggregate_metrics(results)
        regression_detected = False
        regression_details = ""

        if cfg.regression_baseline:
            regression_detected, regression_details = self._check_regression(
                metrics_summary, cfg.regression_baseline, cfg.regression_tolerance
            )

        agent_type = cfg.agent_type or "all"
        report = EvalReport(
            agent_type=agent_type,
            total_cases=len(results),
            passed_cases=passed,
            failed_cases=failed,
            metrics_summary=metrics_summary,
            results=results,
            regression_detected=regression_detected,
            regression_details=regression_details,
        )

        self._history.append(report)
        logger.info(
            "evaluation_complete",
            agent_type=agent_type,
            total=len(results),
            passed=passed,
            failed=failed,
        )
        return report

    def get_history(self, limit: int = 10) -> list[EvalReport]:
        return self._history[-limit:]

    def check_thresholds(
        self, report: EvalReport, thresholds: list[QualityThreshold]
    ) -> list[str]:
        violations = []
        for threshold in thresholds:
            value = report.metrics_summary.get(threshold.metric_name)
            if value is None:
                violations.append(f"{threshold.metric_name}: not computed")
                continue
            if value < threshold.min_value:
                violations.append(
                    f"{threshold.metric_name}: {value:.3f} < {threshold.min_value}"
                )
            if threshold.max_value and value > threshold.max_value:
                violations.append(
                    f"{threshold.metric_name}: {value:.3f} > {threshold.max_value}"
                )
        return violations

    def _aggregate_metrics(self, results: list[EvalResult]) -> dict[str, float]:
        all_keys: set[str] = set()
        for r in results:
            all_keys |= r.metrics.keys()

        summaries: dict[str, list[float]] = {k: [] for k in all_keys}
        for r in results:
            for k, v in r.metrics.items():
                summaries[k].append(v)

        return {
            k: sum(vals) / len(vals) if vals else 0.0
            for k, vals in summaries.items()
        }

    def _check_regression(
        self,
        current: dict[str, float],
        baseline: dict[str, float],
        tolerance: float,
    ) -> tuple[bool, str]:
        regressions = []
        for metric, base_val in baseline.items():
            curr_val = current.get(metric)
            if curr_val is not None and base_val - curr_val > tolerance:
                regressions.append(
                    f"{metric}: {curr_val:.3f} (baseline {base_val:.3f})"
                )
        return len(regressions) > 0, "; ".join(regressions)
