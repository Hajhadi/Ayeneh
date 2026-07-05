"""Consolidation memory model for MEMO subsystem."""



import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class MEMConsolidationModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "mem_consolidation"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    target_memory_id: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=True, default="")
    supporting_episodes: Mapped[str] = mapped_column(Text, default="[]")
    supporting_conversations: Mapped[str] = mapped_column(Text, default="[]")
    confidence_before: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_after: Mapped[float] = mapped_column(Float, default=0.0)
    reason_for_promotion: Mapped[str] = mapped_column(Text, nullable=True, default="")
    reason_for_rejection: Mapped[str] = mapped_column(Text, nullable=True, default="")
    decision: Mapped[str] = mapped_column(String(20), default="defer")
    consolidation_level: Mapped[str] = mapped_column(String(30), default="observation")
