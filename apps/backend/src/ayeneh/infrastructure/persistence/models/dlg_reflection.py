"""DLG Reflection persistence model."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class DLGReflectionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """DLG-04 reflection records — detected reflection opportunities."""

    __tablename__ = "dlg_reflections"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    pattern_type: Mapped[str] = mapped_column(String(50), default="")
    pattern_description: Mapped[str] = mapped_column(Text, default="")
    reflection_category: Mapped[str] = mapped_column(String(50), default="")
    suggested_reflection: Mapped[str] = mapped_column(Text, default="")
    urgency: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_benefit: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_risk: Mapped[float] = mapped_column(Float, default=0.0)
    delivered: Mapped[bool] = mapped_column(default=False)
