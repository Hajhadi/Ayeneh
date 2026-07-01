"""Tests for Unit of Work pattern."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ayeneh.infrastructure.persistence.base import Base
from ayeneh.infrastructure.persistence.models.user import UserModel
from ayeneh.infrastructure.persistence.unit_of_work import UnitOfWork

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


def _utcnow() -> datetime:
    return datetime.now(UTC)


@pytest_asyncio.fixture
async def async_session_factory() -> AsyncGenerator:
    """Create an async in-memory SQLite session factory."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_uow_enter_exit(async_session_factory: async_sessionmaker) -> None:
    """Verify Unit of Work can be entered and exited."""
    async with UnitOfWork(async_session_factory) as uow:
        assert uow.users is not None
        assert uow.memories is not None
        assert uow.conversations is not None


@pytest.mark.asyncio
async def test_uow_create_and_commit(async_session_factory: async_sessionmaker) -> None:
    """Verify creating an entity and committing."""
    async with UnitOfWork(async_session_factory) as uow:
        user = UserModel(
            id=uuid.uuid4(),
            email="test@example.com",
            status="active",
            preferences={},
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        await uow.users.create(user)
        await uow.commit()

    # Verify by reading in a new session
    async with UnitOfWork(async_session_factory) as uow:
        found = await uow.users.get_by_id(user.id)
        assert found is not None
        assert found.email == "test@example.com"


@pytest.mark.asyncio
async def test_uow_rollback_on_exception(async_session_factory: async_sessionmaker) -> None:
    """Verify rollback on exception."""
    user_id = uuid.uuid4()
    try:
        async with UnitOfWork(async_session_factory) as uow:
            user = UserModel(
                id=user_id,
                email="rollback@example.com",
                status="active",
                preferences={},
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            await uow.users.create(user)
            raise ValueError("simulate error")
    except ValueError:
        pass

    # Verify user was NOT persisted
    async with UnitOfWork(async_session_factory) as uow:
        found = await uow.users.get_by_id(user_id)
        assert found is None


@pytest.mark.asyncio
async def test_uow_soft_delete(async_session_factory: async_sessionmaker) -> None:
    """Verify soft-delete sets deleted_at."""
    user_id = uuid.uuid4()
    async with UnitOfWork(async_session_factory) as uow:
        user = UserModel(
            id=user_id,
            email="delete@example.com",
            status="active",
            preferences={},
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        await uow.users.create(user)
        await uow.commit()

    async with UnitOfWork(async_session_factory) as uow:
        await uow.users.delete(user_id)
        await uow.commit()

    async with UnitOfWork(async_session_factory) as uow:
        found = await uow.users.get_by_id(user_id)
        assert found is None  # filtered by deleted_at


@pytest.mark.asyncio
async def test_uow_list_with_filters(async_session_factory: async_sessionmaker) -> None:
    """Verify listing with filters."""
    async with UnitOfWork(async_session_factory) as uow:
        for i in range(5):
            user = UserModel(
                id=uuid.uuid4(),
                email=f"user{i}@example.com",
                status="active" if i < 3 else "paused",
                preferences={},
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            await uow.users.create(user)
        await uow.commit()

    async with UnitOfWork(async_session_factory) as uow:
        active_users = await uow.users.list(filters={"status": "active"})
        assert len(active_users) == 3
