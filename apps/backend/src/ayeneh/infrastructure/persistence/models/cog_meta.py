"""Cognitive Meta-Object persistence model."""

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


class CognitiveMetaObjectModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Meta-objects table — cognitive objects about one's own cognitive processes."""

    __tablename__ = "cognitive_meta_objects"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    observed_process: Mapped[str] = mapped_column(Text, nullable=False)
    awareness_description: Mapped[str] = mapped_column(Text, nullable=True)
    awareness_level: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    stability: Mapped[float] = mapped_column(Float, default=0.0)
    lifecycle_state: Mapped[str] = mapped_column(String(30), default="candidate")
