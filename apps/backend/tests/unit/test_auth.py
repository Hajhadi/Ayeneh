"""Comprehensive tests for the Authentication & Authorization subsystem."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest

from ayeneh.auth.models import (
    AuthenticatedUser,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    Role,
    TokenPair,
)
from ayeneh.auth.password import generate_api_key, hash_password, needs_rehash, verify_password
from ayeneh.auth.service import (
    AuditSink,
    AuthService,
    EmailAlreadyExistsError,
    InvalidPasswordError,
    InvalidRefreshTokenError,
    RevocationStore,
    TokenRevokedError,
    UserRepository,
)
from ayeneh.auth.tokens import (
    create_refresh_token,
    create_token_pair,
    decode_access_token,
    decode_refresh_token,
)

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class InMemoryUserRepo(UserRepository):
    def __init__(self) -> None:
        self._users: dict[str, dict[str, Any]] = {}

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        for u in self._users.values():
            if u["email"] == email:
                return u
        return None

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        return self._users.get(user_id)

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        user = {"id": str(uuid.uuid4()), **data, "created_at": datetime.now(UTC).isoformat()}
        self._users[user["id"]] = user
        return user

    async def update(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        if user_id in self._users:
            self._users[user_id].update(data)
        return self._users.get(user_id, {})

    async def update_password(self, user_id: str, hashed_password: str) -> None:
        if user_id in self._users:
            self._users[user_id]["password_hash"] = hashed_password


class InMemoryRevocationStore(RevocationStore):
    def __init__(self) -> None:
        self._revoked: dict[str, datetime] = {}

    async def revoke(self, jti: str, expires_at: datetime) -> None:
        self._revoked[jti] = expires_at

    async def is_revoked(self, jti: str) -> bool:
        return jti in self._revoked


class InMemoryAuditSink(AuditSink):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def record(self, event: dict[str, Any]) -> None:
        self.events.append(event)


@pytest.fixture
def user_repo() -> InMemoryUserRepo:
    return InMemoryUserRepo()


@pytest.fixture
def revocation_store() -> InMemoryRevocationStore:
    return InMemoryRevocationStore()


@pytest.fixture
def audit_sink() -> InMemoryAuditSink:
    return InMemoryAuditSink()


@pytest.fixture
def auth_service(
    user_repo: InMemoryUserRepo,
    revocation_store: InMemoryRevocationStore,
    audit_sink: InMemoryAuditSink,
) -> AuthService:
    return AuthService(
        user_repo=user_repo,
        revocation_store=revocation_store,
        audit_sink=audit_sink,
    )


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_and_verify(self) -> None:
        password = "secure_password_123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self) -> None:
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes(self) -> None:
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2

    def test_needs_rehash(self) -> None:
        hashed = hash_password("test")
        assert needs_rehash(hashed) is False

    def test_generate_api_key(self) -> None:
        key = generate_api_key()
        assert len(key) > 20
        assert key != generate_api_key()


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

class TestJWTTokens:
    def test_create_and_decode_access_token(self) -> None:
        tokens = create_token_pair("user-1", "test@example.com", Role.USER)
        payload = decode_access_token(tokens.access_token)
        assert payload is not None
        assert payload.sub == "user-1"
        assert payload.email == "test@example.com"
        assert payload.role == Role.USER
        assert payload.type == "access"

    def test_invalid_token_returns_none(self) -> None:
        assert decode_access_token("invalid.token.here") is None

    def test_create_refresh_token(self) -> None:
        token, payload = create_refresh_token("user-1")
        assert isinstance(token, str)
        assert payload.sub == "user-1"
        assert payload.type == "refresh"
        assert payload.family

    def test_decode_refresh_token(self) -> None:
        token, _ = create_refresh_token("user-1")
        decoded = decode_refresh_token(token)
        assert decoded is not None
        assert decoded.sub == "user-1"

    def test_token_pair_structure(self) -> None:
        tokens = create_token_pair("u1", "e@e.com", Role.ADMIN)
        assert tokens.token_type == "bearer"
        assert tokens.expires_in > 0
        assert len(tokens.access_token) > 50
        assert len(tokens.refresh_token) > 50


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegistration:
    @pytest.mark.asyncio
    async def test_register_success(self, auth_service: AuthService) -> None:
        req = RegisterRequest(email="new@example.com", password="password123", display_name="Test User")
        tokens = await auth_service.register(req)
        assert isinstance(tokens, TokenPair)
        assert tokens.access_token
        assert tokens.refresh_token

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, auth_service: AuthService) -> None:
        req = RegisterRequest(email="dup@example.com", password="password123", display_name="User")
        await auth_service.register(req)
        with pytest.raises(EmailAlreadyExistsError):
            await auth_service.register(req)

    @pytest.mark.asyncio
    async def test_register_audit_logged(self, auth_service: AuthService, audit_sink: InMemoryAuditSink) -> None:
        req = RegisterRequest(email="audit@example.com", password="password123", display_name="Auditor")
        await auth_service.register(req, ip="127.0.0.1")
        assert any(e["action"] == "register" for e in audit_sink.events)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, auth_service: AuthService, user_repo: InMemoryUserRepo) -> None:
        hashed = hash_password("mypassword")
        await user_repo.create({"email": "login@example.com", "password_hash": hashed, "role": "user"})

        req = LoginRequest(email="login@example.com", password="mypassword")
        tokens = await auth_service.login(req)
        assert tokens.access_token
        assert tokens.refresh_token

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, auth_service: AuthService, user_repo: InMemoryUserRepo) -> None:
        await user_repo.create({"email": "p@e.com", "password_hash": hash_password("correct"), "role": "user"})
        req = LoginRequest(email="p@e.com", password="wrong")
        with pytest.raises(InvalidPasswordError):
            await auth_service.login(req)

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, auth_service: AuthService) -> None:
        from ayeneh.auth.service import UserNotFoundError
        req = LoginRequest(email="ghost@example.com", password="password")
        with pytest.raises(UserNotFoundError):
            await auth_service.login(req)

    @pytest.mark.asyncio
    async def test_login_audit_logged(self, auth_service: AuthService, user_repo: InMemoryUserRepo, audit_sink: InMemoryAuditSink) -> None:
        await user_repo.create({"email": "a@b.com", "password_hash": hash_password("pass"), "role": "user"})
        await auth_service.login(LoginRequest(email="a@b.com", password="pass"), ip="10.0.0.1")
        assert any(e["action"] == "login_success" for e in audit_sink.events)

    @pytest.mark.asyncio
    async def test_login_failed_audit(self, auth_service: AuthService, audit_sink: InMemoryAuditSink) -> None:
        from ayeneh.auth.service import UserNotFoundError
        try:
            await auth_service.login(LoginRequest(email="x@x.com", password="wrong"))
        except UserNotFoundError:
            pass
        except InvalidPasswordError:
            pass
        assert any(e["action"] == "login_failed" for e in audit_sink.events)


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

class TestTokenRefresh:
    @pytest.mark.asyncio
    async def test_refresh_success(self, auth_service: AuthService) -> None:
        tokens = await auth_service.register(RegisterRequest(email="r@e.com", password="password123", display_name="R"))
        req = RefreshRequest(refresh_token=tokens.refresh_token)
        new_tokens = await auth_service.refresh(req)
        assert new_tokens.access_token != tokens.access_token

    @pytest.mark.asyncio
    async def test_refresh_revokes_old_token(self, auth_service: AuthService, revocation_store: InMemoryRevocationStore) -> None:
        tokens = await auth_service.register(RegisterRequest(email="rr@e.com", password="password123", display_name="RR"))
        old_refresh_payload = decode_refresh_token(tokens.refresh_token)
        assert old_refresh_payload is not None
        old_jti = old_refresh_payload.jti
        await auth_service.refresh(RefreshRequest(refresh_token=tokens.refresh_token))
        assert await revocation_store.is_revoked(old_jti)

    @pytest.mark.asyncio
    async def test_refresh_replay_detected(self, auth_service: AuthService, revocation_store: InMemoryRevocationStore) -> None:
        tokens = await auth_service.register(RegisterRequest(email="rp@e.com", password="password123", display_name="RP"))
        req = RefreshRequest(refresh_token=tokens.refresh_token)
        await auth_service.refresh(req)
        with pytest.raises(TokenRevokedError):
            await auth_service.refresh(req)

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, auth_service: AuthService) -> None:
        with pytest.raises(InvalidRefreshTokenError):
            await auth_service.refresh(RefreshRequest(refresh_token="garbage"))


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_revokes_token(self, auth_service: AuthService, revocation_store: InMemoryRevocationStore) -> None:
        tokens = await auth_service.register(RegisterRequest(email="lo@e.com", password="password123", display_name="LO"))
        payload = decode_access_token(tokens.access_token)
        assert payload is not None
        await auth_service.logout("user-1", payload.jti, payload.exp)
        assert await revocation_store.is_revoked(payload.jti)

    @pytest.mark.asyncio
    async def test_logout_audit(self, auth_service: AuthService, audit_sink: InMemoryAuditSink) -> None:
        tokens = await auth_service.register(RegisterRequest(email="la@e.com", password="password123", display_name="LA"))
        payload = decode_access_token(tokens.access_token)
        await auth_service.logout("user-1", payload.jti, payload.exp)
        assert any(e["action"] == "logout" for e in audit_sink.events)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class TestAuthMiddleware:
    def test_decode_valid_token(self) -> None:
        tokens = create_token_pair("u1", "e@e.com", Role.USER)
        payload = decode_access_token(tokens.access_token)
        assert payload is not None
        assert payload.sub == "u1"

    def test_decode_expired_token(self) -> None:
        from ayeneh.config import get_settings
        settings = get_settings()
        now = datetime.now(UTC)
        expired = {
            "sub": "u1", "email": "e@e.com", "role": "user",
            "jti": "expired-jti", "type": "access",
            "exp": (now - timedelta(hours=1)).isoformat(),
            "iat": (now - timedelta(hours=2)).isoformat(),
        }
        token = jwt.encode(expired, settings.auth_secret_key, algorithm="HS256")
        assert decode_access_token(token) is None


# ---------------------------------------------------------------------------
# Permission guards
# ---------------------------------------------------------------------------

class TestPermissionGuards:
    @pytest.mark.asyncio
    async def test_require_role_allows(self) -> None:
        from ayeneh.auth.dependencies import RequireRole
        guard = RequireRole(Role.USER)
        user = AuthenticatedUser(id="u1", email="e@e.com", role=Role.USER, jti="j")
        result = await guard(user)
        assert result.id == "u1"

    @pytest.mark.asyncio
    async def test_require_role_denies(self) -> None:
        from fastapi import HTTPException

        from ayeneh.auth.dependencies import RequireRole
        guard = RequireRole(Role.ADMIN)
        user = AuthenticatedUser(id="u1", email="e@e.com", role=Role.USER, jti="j")
        with pytest.raises(HTTPException) as exc_info:
            await guard(user)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_register_empty_email(self, auth_service: AuthService) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            await auth_service.register(RegisterRequest(email="", password="pass1234", display_name="X"))

    @pytest.mark.asyncio
    async def test_login_empty_password(self, auth_service: AuthService) -> None:
        from ayeneh.auth.service import UserNotFoundError
        with pytest.raises(UserNotFoundError):
            await auth_service.login(LoginRequest(email="e@e.com", password=""))

    def test_role_values(self) -> None:
        assert Role.USER == "user"
        assert Role.ADMIN == "admin"
