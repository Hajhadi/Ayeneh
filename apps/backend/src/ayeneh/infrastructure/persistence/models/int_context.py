"""INT Context persistence model."""

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


class INTContextModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """INT-02 global context records."""

    __tablename__ = "int_contexts"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    context_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    current_goals: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    active_workflows: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    relevant_memory_references: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    dialogue_state: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    environmental_context: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    temporal_context: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    task_context: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    priority_map: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    known_constraints: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    version_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
