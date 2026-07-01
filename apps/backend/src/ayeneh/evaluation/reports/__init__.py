"""Evaluation report generation — JSON and text formats."""

from __future__ import annotations

from typing import Any

from ayeneh.evaluation.core import EvalReport


def generate_json_report(report: EvalReport) -> dict[str, Any]:
    return {
        "agent_type": report.agent_type,
        "total_cases": report.total_cases,
        "passed_cases": report.passed_cases,
        "failed_cases": report.failed_cases,
        "pass_rate": report.passed_cases / max(report.total_cases, 1),
        "metrics_summary": report.metrics_summary,
        "regression_detected": report.regression_detected,
        "regression_details": report.regression_details,
        "created_at": report.created_at,
        "results": [
            {
                "case_id": r.case_id,
                "passed": r.passed,
                "metrics": r.metrics,
                "duration_ms": r.duration_ms,
            }
            for r in report.results
        ],
    }


def generate_text_report(report: EvalReport) -> str:
    lines = [
        f"{'=' * 60}",
        f"EVALUATION REPORT — {report.agent_type.upper()}",
        f"{'=' * 60}",
        f"Date: {report.created_at}",
        f"Cases: {report.total_cases} total, {report.passed_cases} passed, {report.failed_cases} failed",
        f"Pass rate: {report.passed_cases / max(report.total_cases, 1):.1%}",
        "",
        "Metrics Summary:",
    ]

    for metric, value in report.metrics_summary.items():
        lines.append(f"  {metric}: {value:.3f}")

    if report.regression_detected:
        lines.extend([
            "",
            "⚠ REGRESSION DETECTED:",
            f"  {report.regression_details}",
        ])

    lines.extend(["", "Case Details:"])
    for r in report.results:
        status = "PASS" if r.passed else "FAIL"
        metrics_str = ", ".join(f"{k}={v:.3f}" for k, v in r.metrics.items())
        lines.append(f"  [{status}] {r.case_id}: {metrics_str} ({r.duration_ms:.1f}ms)")

    lines.append(f"{'=' * 60}")
    return "\n".join(lines)


def generate_dashboard_data(report: EvalReport) -> dict[str, Any]:
    return {
        "agent_type": report.agent_type,
        "pass_rate": report.passed_cases / max(report.total_cases, 1),
        "total_cases": report.total_cases,
        "metrics": report.metrics_summary,
        "regression": report.regression_detected,
        "avg_duration_ms": (
            sum(r.duration_ms for r in report.results) / max(len(report.results), 1)
        ),
    }
