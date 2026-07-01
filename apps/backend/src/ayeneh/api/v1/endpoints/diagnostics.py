"""Diagnostics API — system health checks and status."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["diagnostics"])


@router.get("/diagnostics")
async def get_diagnostics(request: Request) -> dict[str, Any]:
    container = getattr(request.app.state, "container", None)
    checks: dict[str, Any] = {}

    if container:
        checks["llm"] = {
            "status": "connected" if container.llm_gateway else "not_configured",
            "provider": type(container.llm_gateway).__name__ if container.llm_gateway else None,
        }
        checks["database"] = {
            "status": "connected" if container.database else "not_configured",
        }
        checks["redis"] = {
            "status": "connected" if container.redis else "not_configured",
        }
        checks["products"] = {
            "count": len(container.product_registry.list_ids()) if container.product_registry else 0,
            "default": container.product_registry.get_or_default().id if container.product_registry else None,
        }
        checks["goals"] = {"status": "initialized" if container.goal_service else "not_configured"}
        checks["circuit_breakers"] = {
            "states": container.circuit_breakers.get_all_states() if hasattr(container.circuit_breakers, "get_all_states") else {},
        }
        if hasattr(container, "metrics") and container.metrics:
            checks["metrics"] = container.metrics.get_summary()
        if hasattr(container, "product_metrics") and container.product_metrics:
            checks["product_metrics"] = container.product_metrics.get_summary()
    else:
        checks["llm"] = {"status": "not_configured"}
        checks["database"] = {"status": "not_configured"}
        checks["redis"] = {"status": "not_configured"}
        checks["products"] = {"count": 0, "default": None}
        checks["goals"] = {"status": "not_configured"}

    overall = "healthy" if checks.get("llm", {}).get("status") == "connected" else "degraded"
    return {"status": overall, "checks": checks}


@router.get("/diagnostics/metrics")
async def get_metrics(request: Request) -> PlainTextResponse:
    container = getattr(request.app.state, "container", None)
    lines = []
    if container:
        if hasattr(container, "metrics") and container.metrics:
            lines.append(container.metrics.export_prometheus_text())
        if hasattr(container, "product_metrics") and container.product_metrics:
            lines.append(container.product_metrics.export_prometheus_text())
        if hasattr(container, "goal_metrics") and container.goal_metrics:
            lines.append(container.goal_metrics.export_prometheus_text())
    return PlainTextResponse("".join(lines) or "# no metrics\n")
