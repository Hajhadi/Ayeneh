"""Custom SQLAlchemy types for cross-dialect compatibility."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import String, TypeDecorator


class JSONBCompat(TypeDecorator):
    """JSONB that falls back to JSON text on SQLite."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value: str | None, dialect: Any) -> Any:
        if value is None:
            return None
        return json.loads(value)

    def load_dialect_impl(self, dialect: Any) -> Any:
        from sqlalchemy.dialects.postgresql import JSONB

        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(String())


class ArrayCompat(TypeDecorator):
    """ARRAY that falls back to JSON text on SQLite."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        return json.dumps([str(v) for v in value])

    def process_result_value(self, value: str | None, dialect: Any) -> list[Any]:
        if value is None:
            return []
        return json.loads(value)

    def load_dialect_impl(self, dialect: Any) -> Any:
        from sqlalchemy import Uuid
        from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY

        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_ARRAY(Uuid()))
        return dialect.type_descriptor(String())


class VectorCompat(TypeDecorator):
    """VECTOR that falls back to TEXT on SQLite."""

    impl = String
    cache_ok = True

    def __init__(self, dimensions: int = 1536) -> None:
        self.dimensions = dimensions
        super().__init__()

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value: str | None, dialect: Any) -> list[float]:
        if value is None:
            return []
        return json.loads(value)

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(self.dimensions))
        return dialect.type_descriptor(String())
