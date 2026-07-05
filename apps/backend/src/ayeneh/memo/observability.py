"""MEMO observability — metrics and tracing for memory engines.

Provides a lightweight in-memory metrics collector that individual engines
can use to record execution counts, durations, LLM call outcomes, and errors
without depending on any external monitoring stack.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class MEMOMetrics:
    """Immutable snapshot of metrics for a single engine."""

    engine_name: str
    executions: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    objects_extracted: int = 0
    llm_calls: int = 0
    llm_fallbacks: int = 0
    errors: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class MEMOMetricsCollector:
    """Collects per-engine metrics in memory.

    Designed to be shared across engine instances as a lightweight
    observability layer.  Thread-safety is not guaranteed — this is
    intended for single-process use with async engines.
    """

    def __init__(self) -> None:
        self._metrics: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_execution(self, engine_name: str, duration_ms: float, objects_extracted: int = 0) -> None:
        """Record a single engine execution."""
        bucket = self._get_bucket(engine_name)
        bucket['executions'] = bucket.get('executions', 0) + 1
        bucket['total_duration_ms'] = bucket.get('total_duration_ms', 0.0) + duration_ms
        bucket['avg_duration_ms'] = bucket['total_duration_ms'] / bucket['executions']
        bucket['objects_extracted'] = bucket.get('objects_extracted', 0) + objects_extracted
        logger.debug(
            'memo_metrics.execution_recorded',
            engine=engine_name,
            duration_ms=duration_ms,
            objects=objects_extracted,
        )

    def record_llm_call(self, engine_name: str, success: bool) -> None:
        """Record an LLM call attempt (success or fallback)."""
        bucket = self._get_bucket(engine_name)
        bucket['llm_calls'] = bucket.get('llm_calls', 0) + 1
        if not success:
            bucket['llm_fallbacks'] = bucket.get('llm_fallbacks', 0) + 1

    def record_error(self, engine_name: str) -> None:
        """Record an engine error."""
        bucket = self._get_bucket(engine_name)
        bucket['errors'] = bucket.get('errors', 0) + 1
        logger.warning('memo_metrics.error_recorded', engine=engine_name)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_snapshot(self, engine_name: str) -> MEMOMetrics:
        """Return an immutable snapshot of metrics for *engine_name*."""
        bucket = self._get_bucket(engine_name)
        return MEMOMetrics(
            engine_name=engine_name,
            executions=bucket.get('executions', 0),
            total_duration_ms=bucket.get('total_duration_ms', 0.0),
            avg_duration_ms=bucket.get('avg_duration_ms', 0.0),
            objects_extracted=bucket.get('objects_extracted', 0),
            llm_calls=bucket.get('llm_calls', 0),
            llm_fallbacks=bucket.get('llm_fallbacks', 0),
            errors=bucket.get('errors', 0),
        )

    def get_all_snapshots(self) -> dict[str, MEMOMetrics]:
        """Return snapshots for every engine that has been recorded."""
        return {
            name: self.get_snapshot(name)
            for name in self._metrics
        }

    def reset(self, engine_name: str | None = None) -> None:
        """Reset metrics for a single engine or all engines."""
        if engine_name is None:
            self._metrics.clear()
        else:
            self._metrics.pop(engine_name, None)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_bucket(self, engine_name: str) -> dict[str, Any]:
        """Return (or create) the metric bucket for *engine_name*."""
        if engine_name not in self._metrics:
            self._metrics[engine_name] = {}
        return self._metrics[engine_name]


# ------------------------------------------------------------------
# Convenience: a module-level singleton
# ------------------------------------------------------------------

_default_collector: MEMOMetricsCollector | None = None


def get_metrics_collector() -> MEMOMetricsCollector:
    """Return the module-level singleton collector."""
    global _default_collector
    if _default_collector is None:
        _default_collector = MEMOMetricsCollector()
    return _default_collector


def reset_metrics() -> None:
    """Reset the module-level singleton."""
    global _default_collector
    _default_collector = None
