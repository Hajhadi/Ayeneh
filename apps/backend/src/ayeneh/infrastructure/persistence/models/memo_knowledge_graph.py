"""Knowledge graph memory model for MEMO subsystem."""



import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class MEMKnowledgeGraphNodeModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "mem_kg_nodes"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    layer: Mapped[str] = mapped_column(String(30), default="semantic")
    properties: Mapped[str] = mapped_column(Text, default="{}")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)


class MEMKnowledgeGraphEdgeModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "mem_kg_edges"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mem_kg_nodes.id"), nullable=False,
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mem_kg_nodes.id"), nullable=False,
    )
    relationship: Mapped[str] = mapped_column(String(50), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    properties: Mapped[str] = mapped_column(Text, default="{}")
