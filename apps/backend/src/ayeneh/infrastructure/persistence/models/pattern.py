"""Pattern, PatternEvidence, and PatternRelation models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class PatternModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Patterns table — recurring cognitive tendencies."""

    __tablename__ = "patterns"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)


class PatternEvidenceModel(Base):
    """Pattern evidence join table — links patterns to insights or memories."""

    __tablename__ = "pattern_evidence"

    pattern_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patterns.id"), primary_key=True)
    evidence_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    evidence_type: Mapped[str] = mapped_column(String(10), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PatternRelationModel(Base):
    """Pattern relations join table — links patterns to other patterns."""

    __tablename__ = "pattern_relations"

    pattern_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patterns.id"), primary_key=True)
    related_pattern_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patterns.id"), primary_key=True)
    relation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
