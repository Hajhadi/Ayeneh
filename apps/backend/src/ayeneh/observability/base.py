"""Shared observability primitives — MetricCounter, MetricHistogram, MetricsPublisher, MetricsSnapshot.

All counter and histogram operations are thread-safe.
MetricsPublisher is the abstract base for per-module metrics classes.
"""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Thread-safe primitives
# ---------------------------------------------------------------------------


class MetricCounter:
    """Thread-safe atomic counter."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._lock = threading.Lock()
        self._value: int = 0

    def inc(self, n: int = 1) -> None:
        with self._lock:
            self._value += n

    def dec(self, n: int = 1) -> None:
        with self._lock:
            self._value -= n

    def get(self) -> int:
        with self._lock:
            return self._value

    def reset(self) -> None:
        with self._lock:
            self._value = 0


class MetricHistogram:
    """Thread-safe bounded histogram with percentile queries."""

    def __init__(self, name: str, max_size: int = 1000) -> None:
        self.name = name
        self._lock = threading.Lock()
        self._values: list[float] = []
        self._max_size = max_size
        self._sum: float = 0.0
        self._count: int = 0

    def observe(self, value: float) -> None:
        with self._lock:
            self._values.append(value)
            self._sum += value
            self._count += 1
            if len(self._values) > self._max_size:
                self._values = self._values[-self._max_size:]

    def avg(self) -> float:
        with self._lock:
            if not self._values:
                return 0.0
            return sum(self._values) / len(self._values)

    def p50(self) -> float:
        return self._percentile(50)

    def p95(self) -> float:
        return self._percentile(95)

    def p99(self) -> float:
        return self._percentile(99)

    def count(self) -> int:
        with self._lock:
            return self._count

    def total(self) -> float:
        with self._lock:
            return self._sum

    def reset(self) -> None:
        with self._lock:
            self._values.clear()
            self._sum = 0.0
            self._count = 0

    def _percentile(self, pct: float) -> float:
        with self._lock:
            if not self._values:
                return 0.0
            sorted_vals = sorted(self._values)
            idx = int(len(sorted_vals) * pct / 100)
            idx = min(idx, len(sorted_vals) - 1)
            return sorted_vals[idx]


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetricsSnapshot:
    """Immutable snapshot of all metrics at a point in time."""

    module: str
    counters: dict[str, int] = field(default_factory=dict)
    histograms: dict[str, dict[str, float]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Publisher (ABC)
# ---------------------------------------------------------------------------


class MetricsPublisher(ABC):
    """Abstract base for per-module metrics publishers.

    Each module subclasses this and implements export_prometheus_text().
    """

    def __init__(self, module_name: str) -> None:
        self._module = module_name
        self._counters: dict[str, MetricCounter] = {}
        self._histograms: dict[str, MetricHistogram] = {}

    def _counter(self, name: str) -> MetricCounter:
        if name not in self._counters:
            self._counters[name] = MetricCounter(f"{self._module}_{name}")
        return self._counters[name]

    def _histogram(self, name: str) -> MetricHistogram:
        if name not in self._histograms:
            self._histograms[name] = MetricHistogram(f"{self._module}_{name}")
        return self._histograms[name]

    def inc(self, name: str, n: int = 1) -> None:
        self._counter(name).inc(n)

    def dec(self, name: str, n: int = 1) -> None:
        self._counter(name).dec(n)

    def observe(self, name: str, value: float) -> None:
        self._histogram(name).observe(value)

    def snapshot(self) -> MetricsSnapshot:
        counters = {name: c.get() for name, c in self._counters.items()}
        histograms = {
            name: {
                "avg": h.avg(),
                "p50": h.p50(),
                "p95": h.p95(),
                "p99": h.p99(),
                "count": h.count(),
                "total": h.total(),
            }
            for name, h in self._histograms.items()
        }
        return MetricsSnapshot(
            module=self._module,
            counters=counters,
            histograms=histograms,
        )

    def get_summary(self) -> dict[str, Any]:
        snap = self.snapshot()
        return {
            "module": snap.module,
            "timestamp": snap.timestamp.isoformat(),
            "counters": snap.counters,
            "histograms": snap.histograms,
        }

    @abstractmethod
    def export_prometheus_text(self) -> str:
        """Export metrics in Prometheus text format."""
        ...
