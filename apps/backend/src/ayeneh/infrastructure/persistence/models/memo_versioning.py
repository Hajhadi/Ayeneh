"""Versioning memory model for MEMO subsystem."""



import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class MEMVersionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "mem_versions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    target_memory_id: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_version_id: Mapped[str] = mapped_column(String(100), nullable=True, default="")
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    revision_type: Mapped[str] = mapped_column(String(30), default="expansion")
    reason: Mapped[str] = mapped_column(Text, nullable=True, default="")
    confidence_before: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_after: Mapped[float] = mapped_column(Float, default=0.0)
    affected_relationships: Mapped[str] = mapped_column(Text, default="[]")
    supporting_evidence: Mapped[str] = mapped_column(Text, default="[]")
    snapshot_id: Mapped[str] = mapped_column(String(100), nullable=True, default="")
