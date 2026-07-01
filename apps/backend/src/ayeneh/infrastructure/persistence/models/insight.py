"""Insight model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import Base, SoftDeleteMixin, UUIDPrimaryKeyMixin
from ayeneh.infrastructure.persistence.types import ArrayCompat


class InsightModel(Base, UUIDPrimaryKeyMixin, SoftDeleteMixin):
    """Insights table — granular observations from messages."""

    __tablename__ = "insights"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    source_message_ids: Mapped[list] = mapped_column(
        ArrayCompat, nullable=False, default=list,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
