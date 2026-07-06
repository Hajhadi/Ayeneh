"""SELF-03 Self-Knowledge persistence model."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from ayeneh.infrastructure.persistence.types import JSONBCompat


class SelfKnowledgeModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """SELF-03 self-knowledge records."""

    __tablename__ = "self_knowledge"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    knowledge_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    statement: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    evidence_sources: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    associated_modules: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    revision_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    known_exceptions: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    applicable_contexts: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    future_validation_targets: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
