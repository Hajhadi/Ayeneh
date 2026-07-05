"""Diagnostics collector — aggregates health from all subsystems.

Each subsystem registers a health check function. The collector runs all
checks and produces a unified diagnostic report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable


@dataclass(frozen=True)
class SubsystemHealth:
    """Health status for a single subsystem."""

    name: str
    status: str  # "healthy" | "degraded" | "unhealthy" | "not_configured"
    version: str = ""
    message: str = ""
    latency_ms: float = 0.0
    counters: dict[str, int] = field(default_factory=dict)
    last_check: datetime = field(default_factory=lambda: datetime.now(UTC))


class DiagnosticsCollector:
    """Aggregates health from all registered subsystems.

    Usage:
        collector = DiagnosticsCollector()
        collector.register("database", check_db_health)
        report = await collector.collect_all()
        overall = collector.overall_status()
    """

    def __init__(self) -> None:
        self._subsystems: dict[str, Callable[[], SubsystemHealth | None]] = {}

    def register(self, name: str, check_fn: Callable[[], SubsystemHealth | None]) -> None:
        """Register a subsystem health check function."""
        self._subsystems[name] = check_fn

    def collect_all(self) -> dict[str, SubsystemHealth]:
        """Run all registered health checks and return results."""
        results: dict[str, SubsystemHealth] = {}
        for name, check_fn in self._subsystems.items():
            try:
                health = check_fn()
                if health is not None:
                    results[name] = health
                else:
                    results[name] = SubsystemHealth(
                        name=name, status="not_configured",
                        message="Check function returned None",
                    )
            except Exception as exc:
                results[name] = SubsystemHealth(
                    name=name, status="unhealthy",
                    message=str(exc),
                )
        return results

    def overall_status(self, results: dict[str, SubsystemHealth] | None = None) -> str:
        """Return the worst status across all subsystems."""
        if results is None:
            results = self.collect_all()
        if not results:
            return "not_configured"

        status_order = {"healthy": 0, "degraded": 1, "unhealthy": 2, "not_configured": 3}
        worst = "healthy"
        for health in results.values():
            if status_order.get(health.status, 3) > status_order.get(worst, 0):
                worst = health.status
        return worst

    def export(self, results: dict[str, SubsystemHealth] | None = None) -> dict[str, Any]:
        """Export diagnostic report as JSON-serializable dict."""
        if results is None:
            results = self.collect_all()
        return {
            "overall_status": self.overall_status(results),
            "subsystems": {
                name: {
                    "status": h.status,
                    "version": h.version,
                    "message": h.message,
                    "latency_ms": h.latency_ms,
                    "counters": h.counters,
                    "last_check": h.last_check.isoformat(),
                }
                for name, h in results.items()
            },
            "total_subsystems": len(results),
            "timestamp": datetime.now(UTC).isoformat(),
        }
