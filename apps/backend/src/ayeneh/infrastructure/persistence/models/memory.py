"""Memory model."""

import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from ayeneh.infrastructure.persistence.types import ArrayCompat, JSONBCompat


class MemoryModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "memories"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    source_message_ids: Mapped[list] = mapped_column(ArrayCompat, nullable=False, default=list)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    embedding_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parent_memory_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("memories.id"), nullable=True)
    evolution_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    confidence_history: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)
    importance_history: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)
    last_evolved_at: Mapped[dict | None] = mapped_column(DateTime(timezone=True), nullable=True)
