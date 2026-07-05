"""COG observability — metrics and tracing for cognitive engines."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class COGMetrics:
    """Immutable snapshot of COG engine metrics."""

    engine_name: str
    executions: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    objects_extracted: int = 0
    llm_calls: int = 0
    llm_fallbacks: int = 0
    errors: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class COGMetricsCollector:
    """Collects metrics for all COG engines."""

    def __init__(self) -> None:
        self._metrics: dict[str, dict[str, Any]] = {}

    def record_execution(
        self,
        engine_name: str,
        duration_ms: float,
        objects_extracted: int = 0,
    ) -> None:
        if engine_name not in self._metrics:
            self._metrics[engine_name] = {
                'executions': 0,
                'total_duration_ms': 0.0,
                'objects_extracted': 0,
                'llm_calls': 0,
                'llm_fallbacks': 0,
                'errors': 0,
            }
        m = self._metrics[engine_name]
        m['executions'] += 1
        m['total_duration_ms'] += duration_ms
        m['objects_extracted'] += objects_extracted

    def record_llm_call(self, engine_name: str, success: bool) -> None:
        if engine_name not in self._metrics:
            return
        m = self._metrics[engine_name]
        m['llm_calls'] += 1
        if not success:
            m['llm_fallbacks'] += 1

    def record_error(self, engine_name: str) -> None:
        if engine_name not in self._metrics:
            return
        m = self._metrics[engine_name]
        m['errors'] += 1

    def get_snapshot(self, engine_name: str) -> COGMetrics:
        m = self._metrics.get(engine_name, {})
        executions = m.get('executions', 0)
        total = m.get('total_duration_ms', 0.0)
        return COGMetrics(
            engine_name=engine_name,
            executions=executions,
            total_duration_ms=total,
            avg_duration_ms=total / max(executions, 1),
            objects_extracted=m.get('objects_extracted', 0),
            llm_calls=m.get('llm_calls', 0),
            llm_fallbacks=m.get('llm_fallbacks', 0),
            errors=m.get('errors', 0),
        )

    def get_all_snapshots(self) -> dict[str, COGMetrics]:
        return {name: self.get_snapshot(name) for name in self._metrics}


class COGTrace:
    """Execution trace for a single COG pipeline run."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.stages: list[dict[str, Any]] = []
        self.start_time = time.monotonic()

    def record_stage(
        self,
        stage_name: str,
        duration_ms: float,
        input_count: int = 0,
        output_count: int = 0,
    ) -> None:
        self.stages.append({
            'stage': stage_name,
            'duration_ms': duration_ms,
            'input_count': input_count,
            'output_count': output_count,
            'timestamp': datetime.now(UTC).isoformat(),
        })

    def complete(self) -> dict[str, Any]:
        total_ms = (time.monotonic() - self.start_time) * 1000
        return {
            'run_id': self.run_id,
            'total_duration_ms': total_ms,
            'stages': self.stages,
            'stage_count': len(self.stages),
        }
