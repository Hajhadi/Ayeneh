"""Cognitive Narrative persistence model."""

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


class CognitiveNarrativeModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Narratives table — life narratives and self-story structures."""

    __tablename__ = "cognitive_narratives"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    narrative_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    template: Mapped[str] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    influence_score: Mapped[float] = mapped_column(Float, default=0.0)
    core_assumptions: Mapped[str] = mapped_column(Text, default="[]")
    implicit_rules: Mapped[str] = mapped_column(Text, default="[]")
    behavioral_consequences: Mapped[str] = mapped_column(Text, default="[]")
    lifecycle_state: Mapped[str] = mapped_column(String(30), default="candidate")
    version: Mapped[int] = mapped_column(Integer, default=1)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
