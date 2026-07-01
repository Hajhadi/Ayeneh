"""EpistemicProfile model — persisted epistemic identity for knowledge sources."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from ayeneh.infrastructure.persistence.types import JSONBCompat


class EpistemicProfileModel(Base, UUIDPrimaryKeyMixin, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "epistemic_profiles"

    book_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("books.id"), nullable=False, unique=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Identity
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    tradition: Mapped[str] = mapped_column(String(255), nullable=False)
    framework: Mapped[str] = mapped_column(String(30), nullable=False)
    discipline: Mapped[str] = mapped_column(String(30), nullable=False)

    # Topics
    primary_topics: Mapped[list] = mapped_column(JSONBCompat, nullable=False, default=list)
    secondary_topics: Mapped[list] = mapped_column(JSONBCompat, nullable=False, default=list)

    # Question support
    supported_questions: Mapped[list] = mapped_column(JSONBCompat, nullable=False, default=list)
    unsupported_questions: Mapped[list] = mapped_column(JSONBCompat, nullable=False, default=list)

    # Epistemic properties
    evidence_level: Mapped[str] = mapped_column(String(30), nullable=False)
    reasoning_style: Mapped[str] = mapped_column(String(30), nullable=False)
    authority: Mapped[str] = mapped_column(String(30), nullable=False)
    claim_types: Mapped[list] = mapped_column(JSONBCompat, nullable=False, default=list)

    # Scope
    applicability: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    limitations: Mapped[list] = mapped_column(JSONBCompat, nullable=False, default=list)
    scope_boundary: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)

    # Policy
    citation_policy: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    confidence_policy: Mapped[str] = mapped_column(JSONBCompat, nullable=False, default=str)
    conflict_policy: Mapped[str] = mapped_column(JSONBCompat, nullable=False, default=str)
    priority_hints: Mapped[list] = mapped_column(JSONBCompat, nullable=False, default=list)

    # Source metadata
    source_reliability: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    historical_period: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    translation_metadata: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)

    __table_args__ = (
        UniqueConstraint("book_id", name="uq_epistemic_profiles_book_id"),
    )
