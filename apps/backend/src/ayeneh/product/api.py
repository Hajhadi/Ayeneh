"""Product Profile API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["products"])


@router.get("/")
async def list_products(request: Request) -> dict[str, Any]:
    registry = _get_registry(request)
    return {"data": registry.list_profiles(), "total": len(registry)}


@router.get("/{product_id}")
async def get_product(request: Request, product_id: str) -> dict[str, Any]:
    registry = _get_registry(request)
    profile = registry.get(product_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return profile.to_dict()


@router.get("/metrics/summary")
async def get_product_metrics(request: Request) -> dict[str, Any]:
    container = getattr(request.app.state, "container", None)
    if container and hasattr(container, "product_metrics"):
        return container.product_metrics.get_summary()
    return {}


def _get_registry(request: Any) -> Any:
    container = getattr(request.app.state, "container", None)
    if container and hasattr(container, "product_registry"):
        return container.product_registry
    from ayeneh.product.registry import ProductRegistry, load_default_profiles
    registry = ProductRegistry.get_instance()
    if len(registry) == 0:
        load_default_profiles()
    return registry
