"""Reflection model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import Base, SoftDeleteMixin, UUIDPrimaryKeyMixin
from ayeneh.infrastructure.persistence.types import JSONBCompat


class ReflectionModel(Base, UUIDPrimaryKeyMixin, SoftDeleteMixin):
    """Reflections table — longitudinal narrative documents."""

    __tablename__ = "reflections"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    evidence_snapshot: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
