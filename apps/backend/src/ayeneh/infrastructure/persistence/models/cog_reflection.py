"""Cognitive Reflection persistence model."""

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


class CognitiveReflectionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Reflections table — cognitive reflection records."""

    __tablename__ = "cognitive_reflections"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    reflection_statement: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(String(50), nullable=True)
    granularity: Mapped[str] = mapped_column(String(20), default="session")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    lifecycle_state: Mapped[str] = mapped_column(String(30), default="candidate")
    version: Mapped[int] = mapped_column(Integer, default=1)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
