"""V1 API router — aggregates all endpoint routers."""

from __future__ import annotations

from fastapi import APIRouter

from ayeneh.api.v1.endpoints import (
    act,
    blind_spots,
    cog,
    conversations,
    dec,
    diagnostics,
    dlg,
    health,
    inf,
    integration,
    library,
    memo,
    memories,
    patterns,
    reflections,
    runtime,
    self_arch,
    users,
    wizard,
)
from ayeneh.goal import api as goal_api
from ayeneh.product import api as product_api

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(wizard.router, tags=["wizard"])
api_router.include_router(diagnostics.router, tags=["diagnostics"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(memories.router, prefix="/memories", tags=["memories"])
api_router.include_router(patterns.router, prefix="/patterns", tags=["patterns"])
api_router.include_router(reflections.router, prefix="/reflections", tags=["reflections"])
api_router.include_router(blind_spots.router, prefix="/blind-spots", tags=["blind-spots"])
api_router.include_router(library.router, prefix="/library", tags=["library"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(runtime.router, prefix="/runtime", tags=["runtime"])
api_router.include_router(memo.router, prefix="/memo", tags=["memo"])
api_router.include_router(cog.router, tags=["cognitive"])
api_router.include_router(inf.router, prefix="/inf", tags=["inference"])
api_router.include_router(goal_api.router, prefix="/goals", tags=["goals"])
api_router.include_router(product_api.router, prefix="/products", tags=["products"])
api_router.include_router(dlg.router, prefix="/dlg", tags=["dialogue"])
api_router.include_router(dec.router, tags=["decision"])
api_router.include_router(act.router, tags=["action_architecture"])
api_router.include_router(integration.router, prefix="/integration", tags=["integration"])
api_router.include_router(self_arch.router, prefix="/self", tags=["self_architecture"])
