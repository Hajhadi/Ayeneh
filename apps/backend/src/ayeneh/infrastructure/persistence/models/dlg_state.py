"""DLG State persistence model."""

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


class DLGStateModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """DLG-02 conversation state records — state machine tracking."""

    __tablename__ = "dlg_states"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    state_type: Mapped[str] = mapped_column(String(50), default="")
    state_name: Mapped[str] = mapped_column(String(100), default="")
    previous_state: Mapped[str] = mapped_column(String(50), default="")
    transition_type: Mapped[str] = mapped_column(String(30), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    turn_number: Mapped[int] = mapped_column(Integer, default=0)
    depth_level: Mapped[int] = mapped_column(Integer, default=0)
    open_questions: Mapped[str] = mapped_column(Text, default="[]")
    exit_conditions: Mapped[str] = mapped_column(Text, default="[]")
