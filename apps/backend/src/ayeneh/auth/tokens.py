"""JWT token creation, verification, and rotation."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from ayeneh.auth.models import AccessTokenPayload, RefreshTokenPayload, Role, TokenPair
from ayeneh.config import get_settings


def create_token_pair(user_id: str, email: str, role: Role) -> TokenPair:
    """Create a new access + refresh token pair."""
    settings = get_settings()
    now = datetime.now(UTC)
    access_jti = secrets.token_urlsafe(16)
    refresh_jti = secrets.token_urlsafe(16)
    family = secrets.token_urlsafe(8)

    access_payload = AccessTokenPayload(
        sub=user_id,
        email=email,
        role=role,
        jti=access_jti,
        exp=now + timedelta(minutes=settings.auth_access_token_ttl_minutes),
        iat=now,
        type="access",
    )

    refresh_payload = RefreshTokenPayload(
        sub=user_id,
        jti=refresh_jti,
        exp=now + timedelta(days=settings.auth_refresh_token_ttl_days),
        iat=now,
        type="refresh",
        family=family,
    )

    access_token = jwt.encode(
        _to_numeric_payload(access_payload),
        settings.auth_secret_key,
        algorithm="HS256",
    )
    refresh_token = jwt.encode(
        _to_numeric_payload(refresh_payload),
        settings.auth_refresh_secret_key,
        algorithm="HS256",
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.auth_access_token_ttl_minutes * 60,
    )


def create_access_token_from_refresh(
    refresh_payload: RefreshTokenPayload,
) -> tuple[str, RefreshTokenPayload]:
    """Rotate refresh token and create new access token.

    Returns (new_access_token, new_refresh_payload).
    """
    settings = get_settings()
    now = datetime.now(UTC)

    new_access_jti = secrets.token_urlsafe(16)
    new_access = jwt.encode(
        {
            "sub": refresh_payload.sub,
            "email": "",
            "role": Role.USER,
            "jti": new_access_jti,
            "exp": (now + timedelta(minutes=settings.auth_access_token_ttl_minutes)).isoformat(),
            "iat": now.isoformat(),
            "type": "access",
        },
        settings.auth_secret_key,
        algorithm="HS256",
    )

    new_refresh_jti = secrets.token_urlsafe(16)
    new_refresh = RefreshTokenPayload(
        sub=refresh_payload.sub,
        jti=new_refresh_jti,
        exp=now + timedelta(days=settings.auth_refresh_token_ttl_days),
        iat=now,
        type="refresh",
        family=refresh_payload.family,
    )

    return new_access, new_refresh


def decode_access_token(token: str) -> AccessTokenPayload | None:
    """Decode and verify an access token. Returns None on any failure."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.auth_secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "jti", "iat"]},
        )
        payload["exp"] = _parse_timestamp(payload["exp"])
        payload["iat"] = _parse_timestamp(payload["iat"])
        return AccessTokenPayload(**payload)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, ValueError):
        return None


def decode_refresh_token(token: str) -> RefreshTokenPayload | None:
    """Decode and verify a refresh token. Returns None on any failure."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.auth_refresh_secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "jti", "iat"]},
        )
        payload["exp"] = _parse_timestamp(payload["exp"])
        payload["iat"] = _parse_timestamp(payload["iat"])
        return RefreshTokenPayload(**payload)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, ValueError):
        return None


def _parse_timestamp(value: Any) -> datetime:
    """Convert a JWT timestamp (numeric or string) to datetime."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def create_refresh_token(user_id: str) -> tuple[str, RefreshTokenPayload]:
    """Create a standalone refresh token (for initial login)."""
    settings = get_settings()
    now = datetime.now(UTC)
    jti = secrets.token_urlsafe(16)
    family = secrets.token_urlsafe(8)

    payload = RefreshTokenPayload(
        sub=user_id,
        jti=jti,
        exp=now + timedelta(days=settings.auth_refresh_token_ttl_days),
        iat=now,
        type="refresh",
        family=family,
    )

    token = jwt.encode(
        _to_numeric_payload(payload),
        settings.auth_refresh_secret_key,
        algorithm="HS256",
    )

    return token, payload


def _to_numeric_payload(payload: Any) -> dict[str, Any]:
    """Convert Pydantic model to dict with numeric timestamps for PyJWT."""
    data = payload.model_dump(mode="json")
    if isinstance(data.get("exp"), str):
        data["exp"] = int(datetime.fromisoformat(data["exp"]).timestamp())
    if isinstance(data.get("iat"), str):
        data["iat"] = int(datetime.fromisoformat(data["iat"]).timestamp())
    return data
