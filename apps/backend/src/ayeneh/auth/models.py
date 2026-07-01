"""Auth domain models — Pydantic schemas for authentication and authorization."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class Role(StrEnum):
    """User roles for RBAC."""

    USER = "user"
    ADMIN = "admin"


class TokenPair(BaseModel):
    """JWT access + refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token TTL in seconds")


class AccessTokenPayload(BaseModel):
    """Decoded JWT access token payload."""

    sub: str = Field(description="User ID")
    email: str = Field(description="User email")
    role: Role = Field(description="User role")
    jti: str = Field(description="Unique token ID for revocation")
    exp: datetime = Field(description="Expiration time")
    iat: datetime = Field(description="Issued at time")
    type: str = Field(default="access", description="Token type marker")


class RefreshTokenPayload(BaseModel):
    """Decoded JWT refresh token payload."""

    sub: str = Field(description="User ID")
    jti: str = Field(description="Unique token ID")
    exp: datetime = Field(description="Expiration time")
    iat: datetime = Field(description="Issued at time")
    type: str = Field(default="refresh", description="Token type marker")
    family: str = Field(description="Token family for rotation tracking")


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class AuthenticatedUser(BaseModel):
    """Authenticated user context injected into requests."""

    id: str
    email: str
    role: Role
    jti: str


class AuditEvent(BaseModel):
    """Audit trail entry."""

    timestamp: datetime
    actor_id: str
    actor_email: str
    action: str
    resource: str
    resource_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
