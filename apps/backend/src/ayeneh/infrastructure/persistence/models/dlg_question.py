"""DLG Question persistence model."""

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


class DLGQuestionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """DLG-05 question records — generated Socratic questions."""

    __tablename__ = "dlg_questions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, default="")
    question_type: Mapped[str] = mapped_column(String(30), default="")
    socratic_step: Mapped[str] = mapped_column(String(30), default="")
    objective: Mapped[str] = mapped_column(String(50), default="")
    target_uncertainty: Mapped[str] = mapped_column(Text, default="")
    expected_information_gain: Mapped[float] = mapped_column(Float, default=0.0)
    cognitive_load: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    asked: Mapped[bool] = mapped_column(default=False)
