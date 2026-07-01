"""Health, readiness, liveness, and metrics endpoints."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["health"])

_start_time = time.monotonic()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Liveness — confirms the process is running."""
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime_seconds": round(time.monotonic() - _start_time, 1),
    }


@router.get("/ready")
async def readiness_check(request: Request) -> dict[str, Any]:
    """Readiness — confirms the service can handle requests."""
    checks: dict[str, str] = {}
    container = getattr(request.app.state, "container", None)

    if container and container.database:
        try:
            from sqlalchemy import text
            async with container.database.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {exc}"
    else:
        checks["database"] = "not_configured"

    if container and getattr(container, "redis", None):
        try:
            await container.redis.ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
    else:
        checks["redis"] = "not_configured"

    overall = "ready" if all(
        v in ("ok", "not_configured") for v in checks.values()
    ) else "not_ready"
    return {"status": overall, "checks": checks, "timestamp": datetime.now(UTC).isoformat()}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Liveness probe for kubernetes."""
    return {"status": "alive"}


@router.get("/metrics")
async def metrics_endpoint(request: Request) -> PlainTextResponse:
    """Prometheus-format metrics endpoint."""
    container = getattr(request.app.state, "container", None)
    if container and hasattr(container, "metrics"):
        return PlainTextResponse(container.metrics.export_prometheus_text())
    return PlainTextResponse("# no metrics configured\n")


@router.get("/circuit-breakers")
async def circuit_breaker_status(request: Request) -> dict[str, str]:
    """Current circuit breaker states."""
    container = getattr(request.app.state, "container", None)
    if container and hasattr(container, "circuit_breakers"):
        return container.circuit_breakers.get_all_states()
    return {}
