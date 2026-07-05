"""Forgetting memory model for MEMO subsystem."""



import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class MEMForgettingModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "mem_forgetting"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    affected_memory_ids: Mapped[str] = mapped_column(Text, default="[]")
    compression_strategy: Mapped[str] = mapped_column(String(30), default="redundancy")
    reason: Mapped[str] = mapped_column(Text, nullable=True, default="")
    knowledge_preserved: Mapped[str] = mapped_column(Text, nullable=True, default="")
    information_reduced: Mapped[float] = mapped_column(Float, default=0.0)
    recoverability_status: Mapped[str] = mapped_column(String(20), default="recoverable")
    tier: Mapped[str] = mapped_column(String(30), default="dormant")
    access_count: Mapped[int] = mapped_column(default=0)
    access_frequency_score: Mapped[float] = mapped_column(Float, default=0.0)
