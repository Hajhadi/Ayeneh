"""Semantic memory model for MEMO subsystem."""



import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class MEMSemanticModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "mem_semantic"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    knowledge_statement: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    importance: Mapped[float] = mapped_column(Float, default=0.0)
    temporal_stability: Mapped[str] = mapped_column(String(20), default="stable")
    supporting_evidence: Mapped[str] = mapped_column(Text, default="[]")
    supporting_episodes: Mapped[str] = mapped_column(Text, default="[]")
    contradictory_evidence: Mapped[str] = mapped_column(Text, default="[]")
    lifecycle_state: Mapped[str] = mapped_column(String(30), default="candidate")
    version: Mapped[int] = mapped_column(Integer, default=1)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
