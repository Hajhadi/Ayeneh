"""Shared observability layer for Ayeneh.

Provides thread-safe metrics, structured traces, diagnostics, and
configuration controls shared across all runtime modules.
"""

from ayeneh.observability.base import (
    MetricCounter,
    MetricHistogram,
    MetricsPublisher,
    MetricsSnapshot,
)
from ayeneh.observability.config import ObservabilityConfig
from ayeneh.observability.diagnostics import DiagnosticsCollector, SubsystemHealth
from ayeneh.observability.trace_registry import TraceRegistry
from ayeneh.observability.trace_types import (
    ExecutionTiming,
    RuntimeTrace,
    TraceBase,
)

__all__ = [
    "DiagnosticsCollector",
    "ExecutionTiming",
    "MetricCounter",
    "MetricHistogram",
    "MetricsPublisher",
    "MetricsSnapshot",
    "ObservabilityConfig",
    "RuntimeTrace",
    "SubsystemHealth",
    "TraceBase",
    "TraceRegistry",
]
