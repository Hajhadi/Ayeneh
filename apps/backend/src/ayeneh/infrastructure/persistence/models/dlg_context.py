"""DLG Context persistence model."""

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


class DLGContextModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """DLG-03 context records — assembled context snapshots."""

    __tablename__ = "dlg_contexts"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    intent_type: Mapped[str] = mapped_column(String(50), default="")
    intent_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    dialogue_phase: Mapped[str] = mapped_column(String(30), default="")
    working_memory_entities: Mapped[str] = mapped_column(Text, default="[]")
    relevant_episodes: Mapped[str] = mapped_column(Text, default="[]")
    relevant_beliefs: Mapped[str] = mapped_column(Text, default="[]")
    engagement_level: Mapped[float] = mapped_column(Float, default=0.5)
    turn_number: Mapped[int] = mapped_column(Integer, default=0)
    completeness: Mapped[float] = mapped_column(Float, default=0.0)
