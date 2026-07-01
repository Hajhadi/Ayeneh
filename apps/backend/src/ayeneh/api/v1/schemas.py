"""Shared Pydantic schemas for API request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ── Pagination ──

class PaginationParams(BaseModel):
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class PageInfo(BaseModel):
    total_count: int
    has_next: bool
    next_cursor: str | None = None
    has_prev: bool
    prev_cursor: str | None = None


class PaginatedResponse(BaseModel):
    data: list[Any] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


# ── Standard response envelope ──

class DataResponse(BaseModel):
    data: Any = None
    meta: dict[str, Any] = Field(default_factory=dict)
    links: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    data: None = None
    error: dict[str, Any] = Field(default_factory=dict)


# ── Timestamps mixin ──

class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
