"""Episodic memory model for MEMO subsystem."""

import uuid
from datetime import datetime
from typing import Optional, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class MEMEpisodeModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "mem_episodes"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True, default="")
    episode_type: Mapped[str] = mapped_column(String(50), nullable=False)
    state: Mapped[str] = mapped_column(String(20), default="candidate")
    start_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    estimated_duration_s: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    importance: Mapped[float] = mapped_column(Float, default=0.0)
    primary_context: Mapped[str] = mapped_column(String(100), nullable=True, default="")
    primary_project: Mapped[str] = mapped_column(String(100), nullable=True, default="")
    primary_people: Mapped[str] = mapped_column(Text, default="[]")
    primary_places: Mapped[str] = mapped_column(Text, default="[]")
    supporting_conversations: Mapped[str] = mapped_column(Text, default="[]")
    supporting_evidence: Mapped[str] = mapped_column(Text, default="[]")
    major_decisions: Mapped[str] = mapped_column(Text, default="[]")
    major_behaviors: Mapped[str] = mapped_column(Text, default="[]")
    major_reflections: Mapped[str] = mapped_column(Text, default="[]")
    associated_narratives: Mapped[str] = mapped_column(Text, default="[]")
    associated_beliefs: Mapped[str] = mapped_column(Text, default="[]")
    associated_goals: Mapped[str] = mapped_column(Text, default="[]")
    associated_identity: Mapped[str] = mapped_column(Text, default="[]")
    outcome: Mapped[str] = mapped_column(Text, default="[]")
    open_questions: Mapped[str] = mapped_column(Text, default="[]")
    version: Mapped[int] = mapped_column(Integer, default=1)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
