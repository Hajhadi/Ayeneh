"""Reasoning observability — metrics and tracking for the reasoning engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ayeneh.observability.base import MetricsPublisher


@dataclass
class ReasoningMetrics(MetricsPublisher):
    """Tracks reasoning engine metrics for observability."""

    def __post_init__(self) -> None:
        MetricsPublisher.__init__(self, "reasoning")

    total_sessions: int = 0
    total_evidence_evaluated: int = 0
    total_hypotheses_generated: int = 0
    total_conflicts_detected: int = 0
    total_alternatives_considered: int = 0
    avg_confidence: float = 0.0
    avg_latency_ms: float = 0.0
    reasoning_failures: int = 0

    latencies_ms: list[float] = field(default_factory=list)
    confidence_values: list[float] = field(default_factory=list)
    hypothesis_counts: list[int] = field(default_factory=list)

    def record_session(
        self, latency_ms: float, confidence: float,
        evidence_count: int, hypothesis_count: int,
        conflict_count: int, alternative_count: int,
    ) -> None:
        self.total_sessions += 1
        self.total_evidence_evaluated += evidence_count
        self.total_hypotheses_generated += hypothesis_count
        self.total_conflicts_detected += conflict_count
        self.total_alternatives_considered += alternative_count

        self.latencies_ms.append(latency_ms)
        self.confidence_values.append(confidence)
        self.hypothesis_counts.append(hypothesis_count)

        if len(self.latencies_ms) > 1000:
            self.latencies_ms = self.latencies_ms[-500:]
        if len(self.confidence_values) > 1000:
            self.confidence_values = self.confidence_values[-500:]

        n = self.total_sessions
        self.avg_confidence = (self.avg_confidence * (n - 1) + confidence) / n
        self.avg_latency_ms = sum(self.latencies_ms[-100:]) / max(len(self.latencies_ms[-100:]), 1)

    def record_failure(self) -> None:
        self.reasoning_failures += 1

    def get_summary(self) -> dict[str, Any]:
        return {
            "total_sessions": self.total_sessions,
            "total_evidence_evaluated": self.total_evidence_evaluated,
            "total_hypotheses_generated": self.total_hypotheses_generated,
            "total_conflicts_detected": self.total_conflicts_detected,
            "total_alternatives": self.total_alternatives_considered,
            "avg_confidence": round(self.avg_confidence, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "failures": self.reasoning_failures,
        }

    def export_prometheus_text(self) -> str:
        s = self.get_summary()
        lines = [
            f"ayeneh_reasoning_sessions_total {s['total_sessions']}",
            f"ayeneh_reasoning_evidence_total {s['total_evidence_evaluated']}",
            f"ayeneh_reasoning_hypotheses_total {s['total_hypotheses_generated']}",
            f"ayeneh_reasoning_conflicts_total {s['total_conflicts_detected']}",
            f"ayeneh_reasoning_alternatives_total {s['total_alternatives']}",
            f"ayeneh_reasoning_avg_confidence {s['avg_confidence']:.4f}",
            f"ayeneh_reasoning_avg_latency_ms {s['avg_latency_ms']:.2f}",
            f"ayeneh_reasoning_failures_total {s['failures']}",
        ]
        return "\n".join(lines) + "\n"
