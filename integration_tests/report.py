"""Report generator — produces INTEGRATION_REPORT.md from test results."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TestOutcome:
    """Result of a single test."""

    name: str
    status: str = "pending"  # pass, fail, error, skip
    duration_ms: float = 0.0
    details: str = ""
    errors: list[str] = field(default_factory=list)


@dataclass
class IntegrationReport:
    """Aggregated integration test report."""

    # Metadata
    generated_at: str = ""
    total_duration_ms: float = 0.0

    # Module execution
    modules_executed: list[str] = field(default_factory=list)
    pipeline_stages_executed: list[str] = field(default_factory=list)

    # Test outcomes
    test_outcomes: list[TestOutcome] = field(default_factory=list)

    # Statistics
    confidence_stats: dict[str, float] = field(default_factory=dict)
    graph_stats: dict[str, int] = field(default_factory=dict)
    reasoning_stats: dict[str, Any] = field(default_factory=dict)
    safety_stats: dict[str, Any] = field(default_factory=dict)
    performance_stats: dict[str, float] = field(default_factory=dict)

    # Verification results
    determinism_verified: bool = False
    traceability_verified: bool = False
    architecture_valid: bool = False

    # Overall
    overall_health_score: float = 0.0
    passed: bool = False

    @property
    def passed_count(self) -> int:
        return sum(1 for t in self.test_outcomes if t.status == "pass")

    @property
    def failed_count(self) -> int:
        return sum(1 for t in self.test_outcomes if t.status == "fail")

    @property
    def error_count(self) -> int:
        return sum(1 for t in self.test_outcomes if t.status == "error")

    @property
    def total_count(self) -> int:
        return len(self.test_outcomes)


def generate_report(report: IntegrationReport) -> str:
    """Generate INTEGRATION_REPORT.md content."""
    lines: list[str] = []

    lines.append("# Ayeneh Integration Report")
    lines.append("")
    lines.append(f"Generated: {report.generated_at}")
    lines.append(f"Total Duration: {report.total_duration_ms:.0f}ms")
    lines.append("")

    # Overall Status
    status_emoji = "PASS" if report.passed else "FAIL"
    lines.append(f"## Overall Status: {status_emoji}")
    lines.append("")
    lines.append(f"Health Score: {report.overall_health_score:.1f}%")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Tests Run**: {report.total_count}")
    lines.append(f"- **Passed**: {report.passed_count}")
    lines.append(f"- **Failed**: {report.failed_count}")
    lines.append(f"- **Errors**: {report.error_count}")
    lines.append("")

    # Modules Executed
    lines.append("## Modules Executed")
    lines.append("")
    for module in report.modules_executed:
        lines.append(f"- {module}")
    lines.append("")

    # Pipeline Stages
    lines.append("## Pipeline Stages")
    lines.append("")
    for stage in report.pipeline_stages_executed:
        lines.append(f"- {stage}")
    lines.append("")

    # Test Results
    lines.append("## Test Results")
    lines.append("")
    lines.append("| Test | Status | Duration |")
    lines.append("|------|--------|----------|")
    for test in report.test_outcomes:
        status = test.status.upper()
        lines.append(f"| {test.name} | {status} | {test.duration_ms:.0f}ms |")
    lines.append("")

    # Failed Tests
    failed = [t for t in report.test_outcomes if t.status in ("fail", "error")]
    if failed:
        lines.append("## Failed Tests")
        lines.append("")
        for test in failed:
            lines.append(f"### {test.name}")
            lines.append(f"- Status: {test.status}")
            lines.append(f"- Details: {test.details}")
            for error in test.errors:
                lines.append(f"  - {error}")
            lines.append("")

    # Confidence Statistics
    lines.append("## Confidence Statistics")
    lines.append("")
    for key, value in report.confidence_stats.items():
        lines.append(f"- **{key}**: {value:.3f}")
    lines.append("")

    # Graph Statistics
    lines.append("## Graph Statistics")
    lines.append("")
    for key, value in report.graph_stats.items():
        lines.append(f"- **{key}**: {value}")
    lines.append("")

    # Reasoning Statistics
    lines.append("## Reasoning Statistics")
    lines.append("")
    for key, value in report.reasoning_stats.items():
        lines.append(f"- **{key}**: {value}")
    lines.append("")

    # Safety Statistics
    lines.append("## Safety Statistics")
    lines.append("")
    for key, value in report.safety_stats.items():
        lines.append(f"- **{key}**: {value}")
    lines.append("")

    # Performance Statistics
    lines.append("## Performance Statistics")
    lines.append("")
    for key, value in report.performance_stats.items():
        lines.append(f"- **{key}**: {value:.1f}ms")
    lines.append("")

    # Verification Results
    lines.append("## Verification Results")
    lines.append("")
    lines.append(f"- **Determinism Verified**: {'Yes' if report.determinism_verified else 'No'}")
    lines.append(f"- **Traceability Verified**: {'Yes' if report.traceability_verified else 'No'}")
    lines.append(f"- **Architecture Valid**: {'Yes' if report.architecture_valid else 'No'}")
    lines.append("")

    # Coverage
    lines.append("## Coverage")
    lines.append("")
    lines.append(f"- **Stage Coverage**: {len(report.pipeline_stages_executed)}/13 stages executed")
    lines.append(f"- **Module Coverage**: {len(report.modules_executed)} modules executed")
    lines.append(f"- **Test Coverage**: {report.passed_count}/{report.total_count} tests passed")
    lines.append("")

    # Warnings
    warnings = []
    for test in report.test_outcomes:
        if test.status == "fail":
            warnings.append(f"FAILED: {test.name}")
    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("---")
    lines.append(f"*Report generated by Ayeneh Integration Testing Framework*")

    return "\n".join(lines)
