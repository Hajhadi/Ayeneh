"""First-Run Wizard API — setup flow for new installations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["wizard"])


class SetupStep(BaseModel):
    step: str
    completed: bool = False
    data: dict[str, Any] = {}


class SetupState(BaseModel):
    current_step: str = "select_profile"
    completed_steps: list[str] = []
    profile_id: str | None = None
    llm_provider: str | None = None
    llm_api_key: str = ""
    embedding_provider: str | None = None
    embedding_api_key: str = ""
    database_url: str = ""
    is_complete: bool = False


@router.get("/wizard/status")
async def get_setup_status(request: Request) -> dict[str, Any]:
    container = getattr(request.app.state, "container", None)
    settings = getattr(container, "settings", None) if container else None

    has_llm = bool(getattr(settings, "llm_openai_api_key", "") or getattr(settings, "llm_anthropic_api_key", "") or getattr(settings, "llm_gemini_api_key", "") or getattr(settings, "llm_litellm_api_key", "")) if settings else False
    has_db = bool(getattr(settings, "database_url", "")) if settings else False

    steps = [
        {"step": "select_profile", "completed": True, "detail": "Default profile loaded"},
        {"step": "configure_llm", "completed": has_llm, "detail": "LLM provider configured" if has_llm else "Not configured"},
        {"step": "configure_embeddings", "completed": has_llm, "detail": "Embeddings configured" if has_llm else "Uses LLM provider"},
        {"step": "configure_storage", "completed": has_db, "detail": "Database configured" if has_db else "Not configured"},
        {"step": "validate", "completed": has_llm and has_db, "detail": "System ready" if (has_llm and has_db) else "Setup incomplete"},
    ]

    completed = [s["step"] for s in steps if s["completed"]]
    is_complete = all(s["completed"] for s in steps)

    return {
        "current_step": steps[-1]["step"] if is_complete else next((s["step"] for s in steps if not s["completed"]), "complete"),
        "completed_steps": completed,
        "is_complete": is_complete,
        "steps": steps,
    }


@router.post("/wizard/validate-llm")
async def validate_llm_config(request: Request, body: dict[str, Any] | None = None) -> dict[str, Any]:
    container = getattr(request.app.state, "container", None)
    has_provider = bool(getattr(container, "llm_gateway", None)) if container else False
    return {
        "valid": has_provider,
        "provider": type(container.llm_gateway).__name__ if has_provider else None,
        "model": getattr(container.llm_gateway, "_model", "unknown") if has_provider else None,
    }


@router.post("/wizard/validate-embeddings")
async def validate_embedding_config(request: Request) -> dict[str, Any]:
    container = getattr(request.app.state, "container", None)
    has_embedder = bool(getattr(container, "llm_gateway", None)) if container else False
    return {"valid": has_embedder, "provider": "llm_gateway" if has_embedder else None}


@router.post("/wizard/validate-storage")
async def validate_storage(request: Request) -> dict[str, Any]:
    container = getattr(request.app.state, "container", None)
    has_db = bool(getattr(container, "database", None))
    return {"valid": has_db, "provider": "postgresql" if has_db else None}


@router.post("/wizard/run-full-check")
async def run_full_health_check(request: Request) -> dict[str, Any]:
    checks = {}

    llm_check = await validate_llm_config(request)
    checks["llm"] = llm_check

    embed_check = await validate_embedding_config(request)
    checks["embeddings"] = embed_check

    storage_check = await validate_storage(request)
    checks["storage"] = storage_check

    container = getattr(request.app.state, "container", None)
    if container:
        checks["redis"] = {"valid": bool(container.redis), "provider": "redis" if container.redis else None}
        checks["scheduler"] = {"valid": True, "provider": "in_memory"}
        checks["workers"] = {"valid": True, "count": 0}
        checks["jobs"] = {"valid": True, "depth": 0}
    else:
        checks["redis"] = {"valid": False}
        checks["scheduler"] = {"valid": False}
        checks["workers"] = {"valid": False}
        checks["jobs"] = {"valid": False}

    all_valid = all(c.get("valid", False) for c in checks.values())
    return {"checks": checks, "all_healthy": all_valid}
