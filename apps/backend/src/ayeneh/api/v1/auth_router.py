"""Auth API endpoints — register, login, logout, refresh."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Request

if TYPE_CHECKING:
    from ayeneh.auth.dependencies import CurrentUser
    from ayeneh.auth.models import LoginRequest, RefreshRequest, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_auth_service() -> Any:
    """Get AuthService — wired through dependency injection in production."""
    from ayeneh.auth.service import AuthService

    class _StubRevocation:
        async def revoke(self, jti: str, exp: datetime) -> None:
            pass

        async def is_revoked(self, jti: str) -> bool:
            return False

    return AuthService(
        user_repo=_StubUserRepo(),
        revocation_store=_StubRevocation(),
        audit_sink=None,
    )


class _StubUserRepo:
    """Stub for route registration — replaced by real repo in production."""

    async def get_by_email(self, email: str) -> dict | None:
        return None

    async def get_by_id(self, user_id: str) -> dict | None:
        return None

    async def create(self, data: dict) -> dict:
        return {"id": str(uuid.uuid4()), **data, "role": "user", "status": "active"}

    async def update(self, user_id: str, data: dict) -> dict:
        return {"id": user_id, **data}

    async def update_password(self, user_id: str, hashed_password: str) -> None:
        pass


@router.post("/register")
async def register(request: Request, body: RegisterRequest) -> dict:
    """Register a new user."""
    auth = _get_auth_service()
    ip = request.client.host if request.client else None
    tokens = await auth.register(body, ip=ip)
    return tokens.model_dump()


@router.post("/login")
async def login(request: Request, body: LoginRequest) -> dict:
    """Authenticate and return tokens."""
    auth = _get_auth_service()
    ip = request.client.host if request.client else None
    tokens = await auth.login(body, ip=ip)
    return tokens.model_dump()


@router.post("/refresh")
async def refresh(request: Request, body: RefreshRequest) -> dict:
    """Rotate refresh token and get new pair."""
    auth = _get_auth_service()
    ip = request.client.host if request.client else None
    tokens = await auth.refresh(body, ip=ip)
    return tokens.model_dump()


@router.post("/logout")
async def logout(user: CurrentUser, request: Request) -> dict:
    """Revoke current token."""
    auth = _get_auth_service()
    jti = getattr(request.state, "user_jti", "")
    exp = getattr(request.state, "token_exp", datetime.now(UTC))
    await auth.logout(user.id, jti, exp, ip=request.client.host if request.client else None)
    return {"message": "Logged out"}
