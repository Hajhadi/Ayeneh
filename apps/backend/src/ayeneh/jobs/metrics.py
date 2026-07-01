"""Job system metrics — tracks queue depth, throughput, latency, worker utilization."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JobMetrics:
    """Tracks comprehensive job system metrics for observability."""

    total_enqueued: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_retried: int = 0
    total_dead_lettered: int = 0
    total_cancelled: int = 0

    latencies_ms: list[float] = field(default_factory=list)
    retry_delays_ms: list[float] = field(default_factory=list)

    job_type_counts: dict[str, int] = field(default_factory=dict)
    job_type_latencies: dict[str, list[float]] = field(default_factory=dict)
    job_type_failures: dict[str, int] = field(default_factory=dict)

    worker_count: int = 0
    active_workers: int = 0

    def record_enqueue(self, job_type: str) -> None:
        self.total_enqueued += 1
        self.job_type_counts[job_type] = self.job_type_counts.get(job_type, 0) + 1

    def record_completion(self, job_type: str, duration_ms: float) -> None:
        self.total_completed += 1
        self.latencies_ms.append(duration_ms)
        if len(self.latencies_ms) > 10000:
            self.latencies_ms = self.latencies_ms[-5000:]
        self.job_type_latencies.setdefault(job_type, []).append(duration_ms)

    def record_failure(self, job_type: str) -> None:
        self.total_failed += 1
        self.job_type_failures[job_type] = self.job_type_failures.get(job_type, 0) + 1

    def record_retry(self) -> None:
        self.total_retried += 1

    def record_dead_letter(self) -> None:
        self.total_dead_lettered += 1

    def record_cancel(self) -> None:
        self.total_cancelled += 1

    def get_summary(self) -> dict[str, Any]:
        avg_latency = (
            sum(self.latencies_ms[-100:]) / len(self.latencies_ms[-100:])
            if self.latencies_ms else 0
        )
        total = self.total_completed + self.total_failed
        return {
            "total_enqueued": self.total_enqueued,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "total_retried": self.total_retried,
            "total_dead_lettered": self.total_dead_lettered,
            "success_rate": self.total_completed / max(total, 1),
            "retry_rate": self.total_retried / max(total, 1),
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(self._percentile(self.latencies_ms, 0.95), 2),
            "p99_latency_ms": round(self._percentile(self.latencies_ms, 0.99), 2),
        }

    def export_prometheus_text(self) -> str:
        lines = []
        lines.append(f"ayeneh_jobs_enqueued_total {self.total_enqueued}")
        lines.append(f"ayeneh_jobs_completed_total {self.total_completed}")
        lines.append(f"ayeneh_jobs_failed_total {self.total_failed}")
        lines.append(f"ayeneh_jobs_retried_total {self.total_retried}")
        lines.append(f"ayeneh_jobs_dead_lettered_total {self.total_dead_lettered}")
        avg = sum(self.latencies_ms[-100:]) / max(len(self.latencies_ms[-100:]), 1)
        lines.append(f"ayeneh_job_latency_ms_avg {avg:.2f}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _percentile(values: list[float], pct: float) -> float:
        if not values:
            return 0.0
        sorted_v = sorted(values)
        idx = int(len(sorted_v) * pct)
        return sorted_v[min(idx, len(sorted_v) - 1)]
