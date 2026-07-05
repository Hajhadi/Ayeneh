"""INF Contradiction persistence model."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class INFContradictionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """INF-04 contradictions — detected conflicts between cognitive objects."""

    __tablename__ = "inf_contradictions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    context_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    conflict_type: Mapped[str] = mapped_column(String(50), nullable=False)
    conflicting_objects: Mapped[str] = mapped_column(Text, default="[]")
    supporting_evidence: Mapped[str] = mapped_column(Text, default="[]")
    contradictory_evidence: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[float] = mapped_column(Float, default=0.0)
    current_status: Mapped[str] = mapped_column(String(30), default="detected")
    resolution_strategy: Mapped[str] = mapped_column(String(50), default="")
    potential_resolution_paths: Mapped[str] = mapped_column(Text, default="[]")
    version: Mapped[int] = mapped_column(Integer, default=1)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
