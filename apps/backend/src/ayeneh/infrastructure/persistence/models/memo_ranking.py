"""Ranking memory model for MEMO subsystem."""



import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class MEMRankingModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "mem_ranking"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    target_memory_id: Mapped[str] = mapped_column(String(100), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    importance_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    centrality_score: Mapped[float] = mapped_column(Float, default=0.0)
    recency_score: Mapped[float] = mapped_column(Float, default=0.0)
    behavioral_impact: Mapped[float] = mapped_column(Float, default=0.0)
    identity_impact: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_quality: Mapped[float] = mapped_column(Float, default=0.0)
    task_profile: Mapped[str] = mapped_column(String(30), default="general")
    explanation: Mapped[str] = mapped_column(Text, nullable=True, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
