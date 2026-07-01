"""FastAPI dependencies — CurrentUser, RequireRole, permission guards."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ayeneh.auth.models import AuthenticatedUser, Role
from ayeneh.auth.tokens import decode_access_token

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),  # noqa: B008
) -> AuthenticatedUser:
    """Extract and verify the current user from the Bearer token."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authentication credentials")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return AuthenticatedUser(
        id=payload.sub,
        email=payload.email,
        role=Role(payload.role),
        jti=payload.jti,
    )


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


class RequireRole:
    """Permission guard — restricts access to specific roles."""

    def __init__(self, *allowed_roles: Role) -> None:
        self._allowed = set(allowed_roles)

    async def __call__(self, user: CurrentUser) -> AuthenticatedUser:
        if user.role not in self._allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role: {', '.join(r.value for r in self._allowed)}",
            )
        return user


RequireUser = RequireRole(Role.USER)
RequireAdmin = RequireRole(Role.ADMIN, Role.USER)
