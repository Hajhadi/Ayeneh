"""Embedding model — vector storage."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import Base, UUIDPrimaryKeyMixin
from ayeneh.infrastructure.persistence.types import VectorCompat


class EmbeddingModel(Base, UUIDPrimaryKeyMixin):
    """Embeddings table — vector representations for semantic search."""

    __tablename__ = "embeddings"

    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(VectorCompat(1536), nullable=False)
    model_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
