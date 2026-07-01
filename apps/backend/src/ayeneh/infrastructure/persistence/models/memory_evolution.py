"""Memory evolution model — tracks every change to a memory over its lifetime."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import Base, UUIDPrimaryKeyMixin


class MemoryEvolutionEventModel(Base, UUIDPrimaryKeyMixin):
    """Records a single evolution event on a memory."""

    __tablename__ = "memory_evolution_events"

    memory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memories.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    old_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    old_importance: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_importance: Mapped[float | None] = mapped_column(Float, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MemoryLineageModel(Base, UUIDPrimaryKeyMixin):
    """Tracks parent/child/merge relationships between memories."""

    __tablename__ = "memory_lineage"

    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memories.id"), nullable=False)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memories.id"), nullable=False)
    relation: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
