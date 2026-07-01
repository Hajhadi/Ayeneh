"""Tests for SQLAlchemy models — verify schema correctness without database."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ayeneh.infrastructure.persistence.base import Base
from ayeneh.infrastructure.persistence.models import (
    BookModel,
    ConversationModel,
    MemoryModel,
    MessageModel,
    PatternModel,
    PromptTemplateModel,
    ReflectionModel,
    SessionModel,
    UserModel,
)


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine for testing."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    """Provide a transactional session for testing."""
    with Session(engine) as sess:
        yield sess


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TestUserModel:
    def test_create_user(self, session: Session) -> None:
        user = UserModel(
            id=uuid.uuid4(),
            email="test@example.com",
            display_name="Test User",
            status="active",
            preferences={"llm_provider": "openai"},
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        session.add(user)
        session.commit()
        assert user.id is not None
        assert user.email == "test@example.com"


class TestSessionModel:
    def test_create_session(self, session: Session) -> None:
        user = UserModel(
            id=uuid.uuid4(), email="u@s.com", status="active",
            preferences={}, created_at=_utcnow(), updated_at=_utcnow(),
        )
        session.add(user)
        session.flush()

        sess = SessionModel(
            id=uuid.uuid4(),
            user_id=user.id,
            started_at=_utcnow(),
            created_at=_utcnow(),
        )
        session.add(sess)
        session.commit()
        assert sess.user_id == user.id


class TestConversationModel:
    def test_create_conversation(self, session: Session) -> None:
        user = UserModel(
            id=uuid.uuid4(), email="u@s.com", status="active",
            preferences={}, created_at=_utcnow(), updated_at=_utcnow(),
        )
        session.add(user)
        session.flush()

        sess = SessionModel(
            id=uuid.uuid4(), user_id=user.id,
            started_at=_utcnow(), created_at=_utcnow(),
        )
        session.add(sess)
        session.flush()

        conv = ConversationModel(
            id=uuid.uuid4(),
            user_id=user.id,
            session_id=sess.id,
            status="active",
            message_count=0,
            started_at=_utcnow(),
            created_at=_utcnow(),
        )
        session.add(conv)
        session.commit()
        assert conv.status == "active"


class TestMessageModel:
    def test_create_message(self, session: Session) -> None:
        user = UserModel(
            id=uuid.uuid4(), email="u@s.com", status="active",
            preferences={}, created_at=_utcnow(), updated_at=_utcnow(),
        )
        session.add(user)
        session.flush()

        sess = SessionModel(
            id=uuid.uuid4(), user_id=user.id,
            started_at=_utcnow(), created_at=_utcnow(),
        )
        session.add(sess)
        session.flush()

        conv = ConversationModel(
            id=uuid.uuid4(), user_id=user.id, session_id=sess.id,
            status="active", message_count=0, started_at=_utcnow(), created_at=_utcnow(),
        )
        session.add(conv)
        session.flush()

        msg = MessageModel(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            user_id=user.id,
            role="user",
            content="Hello world",
            sequence_number=1,
            created_at=_utcnow(),
        )
        session.add(msg)
        session.commit()
        assert msg.role == "user"


class TestMemoryModel:
    def test_create_memory(self, session: Session) -> None:
        user = UserModel(
            id=uuid.uuid4(), email="u@s.com", status="active",
            preferences={}, created_at=_utcnow(), updated_at=_utcnow(),
        )
        session.add(user)
        session.flush()

        mem = MemoryModel(
            id=uuid.uuid4(),
            user_id=user.id,
            type="episodic",
            content="User mentioned they enjoy reading",
            confidence=0.8,
            source_message_ids=[],
            status="active",
            embedding_version=0,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        session.add(mem)
        session.commit()
        assert mem.type == "episodic"
        assert mem.confidence == 0.8


class TestPatternModel:
    def test_create_pattern(self, session: Session) -> None:
        user = UserModel(
            id=uuid.uuid4(), email="u@s.com", status="active",
            preferences={}, created_at=_utcnow(), updated_at=_utcnow(),
        )
        session.add(user)
        session.flush()

        pat = PatternModel(
            id=uuid.uuid4(),
            user_id=user.id,
            description="User tends to read before bed",
            strength=0.7,
            evidence_count=3,
            status="active",
            first_detected_at=_utcnow(),
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        session.add(pat)
        session.commit()
        assert pat.strength == 0.7


class TestBookModel:
    def test_create_book(self, session: Session) -> None:
        user = UserModel(
            id=uuid.uuid4(), email="u@s.com", status="active",
            preferences={}, created_at=_utcnow(), updated_at=_utcnow(),
        )
        session.add(user)
        session.flush()

        book = BookModel(
            id=uuid.uuid4(),
            user_id=user.id,
            title="Thinking, Fast and Slow",
            author="Daniel Kahneman",
            source_format="pdf",
            status="processing",
            chunk_count=0,
            metadata_json={},
            imported_at=_utcnow(),
            created_at=_utcnow(),
        )
        session.add(book)
        session.commit()
        assert book.title == "Thinking, Fast and Slow"
        assert book.status == "processing"


class TestReflectionModel:
    def test_create_reflection(self, session: Session) -> None:
        user = UserModel(
            id=uuid.uuid4(), email="u@s.com", status="active",
            preferences={}, created_at=_utcnow(), updated_at=_utcnow(),
        )
        session.add(user)
        session.flush()

        now = _utcnow()
        refl = ReflectionModel(
            id=uuid.uuid4(),
            user_id=user.id,
            title="Weekly Reflection",
            narrative="This week the user focused on reading habits.",
            period_start=now,
            period_end=now,
            status="draft",
            evidence_snapshot=[],
            created_at=now,
        )
        session.add(refl)
        session.commit()
        assert refl.status == "draft"


class TestPromptTemplateModel:
    def test_create_template(self, session: Session) -> None:
        tpl = PromptTemplateModel(
            id=uuid.uuid4(),
            task_type="conversation",
            version=1,
            content="You are a helpful assistant.",
            is_active=True,
            created_at=_utcnow(),
        )
        session.add(tpl)
        session.commit()
        assert tpl.is_active is True
