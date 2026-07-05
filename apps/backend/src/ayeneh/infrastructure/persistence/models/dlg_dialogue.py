"""DLG Dialogue persistence model."""

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


class DLGDialogueModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """DLG-01 dialogue records — dialogue management state per conversation."""

    __tablename__ = "dlg_dialogues"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    intent: Mapped[str] = mapped_column(String(50), default="")
    mode: Mapped[str] = mapped_column(String(50), default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    strategy: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.0)
    referenced_memories: Mapped[str] = mapped_column(Text, default="[]")
    referenced_evidence: Mapped[str] = mapped_column(Text, default="[]")
    follow_up_opportunities: Mapped[str] = mapped_column(Text, default="[]")
