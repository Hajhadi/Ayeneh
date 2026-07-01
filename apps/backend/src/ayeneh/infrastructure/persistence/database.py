"""Database connection manager."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

logger = structlog.get_logger(__name__)


class Database:
    """Async database engine and session factory."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker | None = None

    async def connect(self) -> None:
        """Create the engine and session factory."""
        self._engine = create_async_engine(
            self._url,
            echo=False,
            pool_size=20,
            max_overflow=10,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
        )
        logger.info("database_connected")

    async def disconnect(self) -> None:
        """Dispose of the engine."""
        if self._engine:
            await self._engine.dispose()
            logger.info("database_disconnected")

    @property
    def session_factory(self) -> async_sessionmaker:
        assert self._session_factory is not None, "Database not connected"
        return self._session_factory
