"""Auth service — orchestrates registration, login, logout, token rotation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.auth.models import (
    AuthenticatedUser,
    LoginRequest,
    RefreshRequest,
    RefreshTokenPayload,
    RegisterRequest,
    Role,
    TokenPair,
)
from ayeneh.auth.password import hash_password, needs_rehash, verify_password
from ayeneh.auth.tokens import (
    create_access_token_from_refresh,
    create_token_pair,
    decode_access_token,
    decode_refresh_token,
)

logger = structlog.get_logger(__name__)


class AuthError(Exception):
    """Base auth error."""

    def __init__(self, message: str, code: str = "AUTH_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class UserNotFoundError(AuthError):
    def __init__(self) -> None:
        super().__init__("Invalid email or password", "INVALID_CREDENTIALS")


class InvalidPasswordError(AuthError):
    def __init__(self) -> None:
        super().__init__("Invalid email or password", "INVALID_CREDENTIALS")


class EmailAlreadyExistsError(AuthError):
    def __init__(self) -> None:
        super().__init__("Email already registered", "EMAIL_EXISTS")


class InvalidRefreshTokenError(AuthError):
    def __init__(self) -> None:
        super().__init__("Invalid or expired refresh token", "INVALID_REFRESH_TOKEN")


class TokenRevokedError(AuthError):
    def __init__(self) -> None:
        super().__init__("Token has been revoked", "TOKEN_REVOKED")


class UserRepository:
    """Abstract user persistence interface."""

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        raise NotImplementedError

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    async def update(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    async def update_password(self, user_id: str, hashed_password: str) -> None:
        raise NotImplementedError


class RevocationStore:
    """Abstract store for revoked token JTIs."""

    async def revoke(self, jti: str, expires_at: datetime) -> None:
        raise NotImplementedError

    async def is_revoked(self, jti: str) -> bool:
        raise NotImplementedError


class AuditSink:
    """Abstract audit event sink."""

    async def record(self, event: dict[str, Any]) -> None:
        raise NotImplementedError


class AuthService:
    """Production auth service — register, login, logout, refresh."""

    def __init__(
        self,
        user_repo: UserRepository,
        revocation_store: RevocationStore,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._revocation = revocation_store
        self._audit = audit_sink

    async def register(self, request: RegisterRequest, ip: str | None = None) -> TokenPair:
        """Register a new user and return tokens."""
        existing = await self._user_repo.get_by_email(request.email)
        if existing:
            raise EmailAlreadyExistsError()

        hashed = hash_password(request.password)
        user = await self._user_repo.create({
            "email": request.email,
            "password_hash": hashed,
            "display_name": request.display_name,
            "role": Role.USER,
            "status": "active",
        })

        tokens = create_token_pair(user["id"], user["email"], Role(user["role"]))

        await self._audit_event(
            "register", user["id"], user["email"], "user", user["id"], ip=ip
        )

        logger.info("user_registered", user_id=user["id"], email=user["email"])
        return tokens

    async def login(self, request: LoginRequest, ip: str | None = None) -> TokenPair:
        """Authenticate user and return tokens."""
        user = await self._user_repo.get_by_email(request.email)
        if not user:
            await self._audit_event(
                "login_failed", "unknown", request.email, "user", None,
                reason="user_not_found", ip=ip,
            )
            raise UserNotFoundError()

        if not verify_password(request.password, user["password_hash"]):
            await self._audit_event(
                "login_failed", user["id"], user["email"], "user", user["id"],
                reason="invalid_password", ip=ip,
            )
            raise InvalidPasswordError()

        if needs_rehash(user["password_hash"]):
            await self._user_repo.update_password(user["id"], user["password_hash"])

        tokens = create_token_pair(user["id"], user["email"], Role(user["role"]))

        await self._user_repo.update(user["id"], {"last_active_at": datetime.now(UTC)})
        await self._audit_event(
            "login_success", user["id"], user["email"], "user", user["id"], ip=ip,
        )

        logger.info("user_logged_in", user_id=user["id"])
        return tokens

    async def refresh(self, request: RefreshRequest, ip: str | None = None) -> TokenPair:
        """Rotate refresh token and issue new token pair."""
        payload = decode_refresh_token(request.refresh_token)
        if not payload:
            raise InvalidRefreshTokenError()

        if await self._revocation.is_revoked(payload.jti):
            await self._audit_event(
                "refresh_replayed", payload.sub, "", "token", payload.jti, ip=ip,
            )
            raise TokenRevokedError()

        await self._revocation.revoke(payload.jti, payload.exp)

        new_access, new_refresh = create_access_token_from_refresh(payload)

        await self._audit_event(
            "token_rotated", payload.sub, "", "token", payload.jti, ip=ip,
        )

        return TokenPair(
            access_token=new_access,
            refresh_token=new_refresh.model_dump(mode="json") if isinstance(new_refresh, dict) else _encode_refresh(new_refresh),
            expires_in=900,
        )

    async def logout(self, user_id: str, token_jti: str, token_exp: datetime, ip: str | None = None) -> None:
        """Revoke the current access token."""
        await self._revocation.revoke(token_jti, token_exp)
        await self._audit_event("logout", user_id, "", "token", token_jti, ip=ip)
        logger.info("user_logged_out", user_id=user_id)

    async def get_current_user(self, token_jti: str) -> AuthenticatedUser | None:
        """Look up user by token JTI (after JWT verification)."""
        payload = decode_access_token(token_jti) if len(token_jti) > 100 else None
        if payload and await self._revocation.is_revoked(payload.jti):
            return None
        return None

    async def _audit_event(
        self, action: str, actor_id: str, actor_email: str,
        resource: str, resource_id: str | None,
        ip: str | None = None, **kwargs: Any,
    ) -> None:
        if self._audit:
            await self._audit.record({
                "timestamp": datetime.now(UTC).isoformat(),
                "actor_id": actor_id,
                "actor_email": actor_email,
                "action": action,
                "resource": resource,
                "resource_id": resource_id,
                "ip_address": ip,
                **kwargs,
            })


def _encode_refresh(payload: RefreshTokenPayload) -> str:
    """Encode a RefreshTokenPayload back to a JWT string."""
    import jwt as _jwt

    from ayeneh.config import get_settings as _get_settings
    settings = _get_settings()
    data = payload.model_dump(mode="json")
    if isinstance(data.get("exp"), str):
        data["exp"] = int(datetime.fromisoformat(data["exp"]).timestamp())
    if isinstance(data.get("iat"), str):
        data["iat"] = int(datetime.fromisoformat(data["iat"]).timestamp())
    return _jwt.encode(data, settings.auth_refresh_secret_key, algorithm="HS256")


