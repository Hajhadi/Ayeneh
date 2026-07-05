"""Cognitive Evidence persistence model — COG-02 evidence objects."""

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


class CognitiveEvidenceModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Evidence table — individual evidence objects from cognitive analysis."""

    __tablename__ = "cognitive_evidence"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    epistemic_classification: Mapped[str] = mapped_column(String(50), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=True)
    speaker: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence_strength_directness: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_strength_specificity: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_strength_temporal_proximity: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_strength_consistency: Mapped[float] = mapped_column(Float, default=0.5)
    conversation_id: Mapped[str] = mapped_column(String(100), nullable=True)
    segment_id: Mapped[str] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    temporal_scope: Mapped[str] = mapped_column(String(20), default="momentary")
    validation_status: Mapped[str] = mapped_column(String(20), default="pending")
