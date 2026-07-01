"""User API endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class UserProfileResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    created_at: datetime
    last_active_at: datetime | None = None


class UpdateProfileRequest(BaseModel):
    display_name: str | None = None
    email: str | None = None


class UserStatsResponse(BaseModel):
    user_id: str
    conversations_count: int = 0
    messages_count: int = 0
    memories_count: int = 0
    patterns_count: int = 0
    reflections_count: int = 0
    books_count: int = 0


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user(user: Any = None) -> dict:
    return {
        "id": getattr(user, "id", "anon"),
        "email": getattr(user, "email", ""),
        "display_name": "",
        "role": getattr(user, "role", "user"),
        "created_at": datetime.utcnow(),
    }


@router.patch("/me", response_model=UserProfileResponse)
async def update_profile(body: UpdateProfileRequest, user: Any = None) -> dict:
    return {
        "id": getattr(user, "id", "anon"),
        "email": getattr(user, "email", ""),
        "display_name": body.display_name or "",
        "role": getattr(user, "role", "user"),
        "created_at": datetime.utcnow(),
    }


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_user_stats(user: Any = None) -> dict:
    return {"user_id": getattr(user, "id", "anon")}
