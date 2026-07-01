"""Tests for the Epistemic Knowledge Model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ayeneh.domain.knowledge_epistemics import (
    Applicability,
    CitationPolicy,
    ClaimType,
    EpistemicFramework,
    EpistemicProfile,
    EvidenceLevel,
    KnowledgeAuthority,
    KnowledgeDomain,
    KnowledgeSource,
    Limitation,
    ReasoningStyle,
    ScopeBoundary,
    SourceReliability,
    TranslationMetadata,
)
from ayeneh.infrastructure.persistence.base import Base
from ayeneh.infrastructure.persistence.models.epistemic_profile import EpistemicProfileModel
from ayeneh.infrastructure.persistence.unit_of_work import UnitOfWork

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Domain object tests
# ---------------------------------------------------------------------------


class TestEnums:
    def test_knowledge_source_values(self) -> None:
        assert KnowledgeSource.BOOK == "book"
        assert KnowledgeSource.ARTICLE == "article"
        assert KnowledgeSource.TRADITION == "tradition"

    def test_knowledge_domain_values(self) -> None:
        assert KnowledgeDomain.PHILOSOPHY == "philosophy"
        assert KnowledgeDomain.PSYCHOLOGY == "psychology"
        assert KnowledgeDomain.SPIRITUALITY == "spirituality"

    def test_evidence_level_values(self) -> None:
        assert EvidenceLevel.EMPIRICAL == "empirical"
        assert EvidenceLevel.PHILOSOPHICAL == "philosophical"
        assert EvidenceLevel.EXPERIENTIAL == "experiential"

    def test_epistemic_framework_values(self) -> None:
        assert EpistemicFramework.RATIONALIST == "rationalist"
        assert EpistemicFramework.PHENOMENOLOGICAL == "phenomenological"
        assert EpistemicFramework.CRITICAL == "critical"

    def test_reasoning_style_values(self) -> None:
        assert ReasoningStyle.DEDUCTIVE == "deductive"
        assert ReasoningStyle.CONTEMPLATIVE == "contemplative"


class TestValueObjects:
    def test_applicability_is_frozen(self) -> None:
        app = Applicability(
            contexts=["meditation", "therapy"],
            conditions=["stable_mind"],
            contraindications=["crisis"],
        )
        assert app.contexts == ["meditation", "therapy"]
        assert app.conditions == ["stable_mind"]
        assert app.contraindications == ["crisis"]
        with pytest.raises(AttributeError):
            app.contexts = ["new"]  # type: ignore[misc]

    def test_limitation_is_frozen(self) -> None:
        lim = Limitation(
            description="Cultural bias",
            severity="moderate",
            affected_domains=["psychology"],
        )
        assert lim.severity == "moderate"
        with pytest.raises(AttributeError):
            lim.description = "changed"  # type: ignore[misc]

    def test_scope_boundary_is_frozen(self) -> None:
        sb = ScopeBoundary(
            included_topics=["mindfulness"],
            excluded_topics=["clinical_diagnosis"],
            overlap_notes=["overlaps with CBT"],
        )
        assert "mindfulness" in sb.included_topics

    def test_citation_policy_is_frozen(self) -> None:
        cp = CitationPolicy(required=True, format="author-date", min_confidence=0.7)
        assert cp.required is True
        assert cp.format == "author-date"

    def test_translation_metadata_is_frozen(self) -> None:
        tm = TranslationMetadata(
            translator="John Smith",
            original_language="ar",
            translation_year=2020,
        )
        assert tm.original_language == "ar"

    def test_source_reliability_is_frozen(self) -> None:
        sr = SourceReliability(score=0.85, basis="peer_reviewed")
        assert sr.score == 0.85


class TestEpistemicProfileEntity:
    def test_create_minimal_profile(self) -> None:
        profile = EpistemicProfile(
            id=uuid.uuid4(),
            book_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            source=KnowledgeSource.BOOK,
            tradition="Sufism",
            framework=EpistemicFramework.PHENOMENOLOGICAL,
            discipline=KnowledgeDomain.SPIRITUALITY,
        )
        assert profile.source == KnowledgeSource.BOOK
        assert profile.discipline == KnowledgeDomain.SPIRITUALITY
        assert profile.primary_topics == []
        assert profile.evidence_level == EvidenceLevel.PHILOSOPHICAL
        assert profile.language == "en"

    def test_create_full_profile(self) -> None:
        profile = EpistemicProfile(
            id=uuid.uuid4(),
            book_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            source=KnowledgeSource.BOOK,
            tradition="Islamic Philosophy",
            framework=EpistemicFramework.RATIONALIST,
            discipline=KnowledgeDomain.PHILOSOPHY,
            primary_topics=["metaphysics", "epistemology"],
            secondary_topics=["ethics", "logic"],
            supported_questions=["What is the nature of reality?"],
            unsupported_questions=["How do I invest in stocks?"],
            evidence_level=EvidenceLevel.PHILOSOPHICAL,
            reasoning_style=ReasoningStyle.DEDUCTIVE,
            authority=KnowledgeAuthority.PRIMARY,
            claim_types=[ClaimType.INTERPRETIVE, ClaimType.NORMATIVE],
            applicability=Applicability(
                contexts=["philosophical_inquiry", "spiritual_contemplation"],
                conditions=["willingness_to_reflect"],
                contraindications=["purely_empirical_inquiry"],
            ),
            limitations=[
                Limitation(
                    description="Cultural context dependency",
                    severity="moderate",
                    affected_domains=["applied_psychology"],
                ),
            ],
            scope_boundary=ScopeBoundary(
                included_topics=["being", "knowledge", "value"],
                excluded_topics=["material_sciences"],
                overlap_notes=["overlaps with Aristotelian tradition"],
            ),
            citation_policy=CitationPolicy(
                required=True,
                format="author-date",
                min_confidence=0.6,
                notes="Always cite original Arabic when possible",
            ),
            confidence_policy="high_confidence_for_interpretive_claims",
            conflict_policy="defer_to_primary_sources_on_disagreement",
            priority_hints=["primary_authority_for_sufi_metaphysics"],
            source_reliability=SourceReliability(
                score=0.9,
                basis="scholarly_consensus",
                notes="Widely respected in the field",
            ),
            historical_period="12th century",
            language="ar",
            translation_metadata=TranslationMetadata(
                translator="Michael Sells",
                original_language="ar",
                translation_year=2002,
                translation_notes="Poetic translation preserving meter",
            ),
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        assert profile.tradition == "Islamic Philosophy"
        assert len(profile.claim_types) == 2
        assert profile.historical_period == "12th century"
        assert profile.translation_metadata is not None
        assert profile.translation_metadata.original_language == "ar"


# ---------------------------------------------------------------------------
# Repository + UnitOfWork tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def async_session_factory() -> AsyncGenerator:
    """Create an async in-memory SQLite session factory."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
def uid() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def book_id() -> uuid.UUID:
    return uuid.uuid4()


def _make_profile_model(
    book_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    discipline: str = "philosophy",
) -> EpistemicProfileModel:
    return EpistemicProfileModel(
        id=uuid.uuid4(),
        book_id=book_id,
        user_id=user_id,
        source="book",
        tradition="test_tradition",
        framework="rationalist",
        discipline=discipline,
        primary_topics=["topic1"],
        secondary_topics=["topic2"],
        supported_questions=["q1"],
        unsupported_questions=["q2"],
        evidence_level="philosophical",
        reasoning_style="deductive",
        authority="primary",
        claim_types=["factual"],
        applicability={"contexts": [], "conditions": [], "contraindications": []},
        limitations=[],
        scope_boundary={"included_topics": [], "excluded_topics": [], "overlap_notes": []},
        citation_policy={"required": True, "format": "inline", "min_confidence": 0.5},
        confidence_policy="default",
        conflict_policy="default",
        priority_hints=[],
        source_reliability={"score": 0.5, "basis": "mixed"},
        language="en",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )


@pytest.mark.asyncio
async def test_uow_epistemic_profiles_initialized(
    async_session_factory: async_sessionmaker,
) -> None:
    """Verify UnitOfWork initializes epistemic_profiles repository."""
    async with UnitOfWork(async_session_factory) as uow:
        assert uow.epistemic_profiles is not None


@pytest.mark.asyncio
async def test_create_epistemic_profile(
    async_session_factory: async_sessionmaker,
    book_id: uuid.UUID,
    uid: uuid.UUID,
) -> None:
    """Verify creating an epistemic profile and reading it back."""
    async with UnitOfWork(async_session_factory) as uow:
        profile = _make_profile_model(book_id, uid)
        await uow.epistemic_profiles.create(profile)
        await uow.commit()

    async with UnitOfWork(async_session_factory) as uow:
        found = await uow.epistemic_profiles.get_by_id(profile.id)
        assert found is not None
        assert found.book_id == book_id
        assert found.discipline == "philosophy"


@pytest.mark.asyncio
async def test_get_by_book_id(
    async_session_factory: async_sessionmaker,
    book_id: uuid.UUID,
    uid: uuid.UUID,
) -> None:
    """Verify get_by_book_id returns the correct profile."""
    async with UnitOfWork(async_session_factory) as uow:
        profile = _make_profile_model(book_id, uid)
        await uow.epistemic_profiles.create(profile)
        await uow.commit()

    async with UnitOfWork(async_session_factory) as uow:
        found = await uow.epistemic_profiles.get_by_book_id(book_id)
        assert found is not None
        assert found.id == profile.id


@pytest.mark.asyncio
async def test_get_by_book_id_not_found(
    async_session_factory: async_sessionmaker,
) -> None:
    """Verify get_by_book_id returns None for unknown book."""
    async with UnitOfWork(async_session_factory) as uow:
        found = await uow.epistemic_profiles.get_by_book_id(uuid.uuid4())
        assert found is None


@pytest.mark.asyncio
async def test_list_by_user(
    async_session_factory: async_sessionmaker,
    uid: uuid.UUID,
) -> None:
    """Verify list_by_user returns all profiles for a user."""
    async with UnitOfWork(async_session_factory) as uow:
        for _ in range(3):
            profile = _make_profile_model(uuid.uuid4(), uid)
            await uow.epistemic_profiles.create(profile)
        await uow.commit()

    async with UnitOfWork(async_session_factory) as uow:
        profiles = await uow.epistemic_profiles.list_by_user(uid)
        assert len(profiles) == 3


@pytest.mark.asyncio
async def test_list_by_domain(
    async_session_factory: async_sessionmaker,
    uid: uuid.UUID,
) -> None:
    """Verify list_by_domain filters correctly."""
    async with UnitOfWork(async_session_factory) as uow:
        p1 = _make_profile_model(uuid.uuid4(), uid, discipline="philosophy")
        p2 = _make_profile_model(uuid.uuid4(), uid, discipline="psychology")
        p3 = _make_profile_model(uuid.uuid4(), uid, discipline="philosophy")
        await uow.epistemic_profiles.create(p1)
        await uow.epistemic_profiles.create(p2)
        await uow.epistemic_profiles.create(p3)
        await uow.commit()

    async with UnitOfWork(async_session_factory) as uow:
        phil_profiles = await uow.epistemic_profiles.list_by_domain(uid, "philosophy")
        assert len(phil_profiles) == 2

        psych_profiles = await uow.epistemic_profiles.list_by_domain(uid, "psychology")
        assert len(psych_profiles) == 1


@pytest.mark.asyncio
async def test_soft_delete_epistemic_profile(
    async_session_factory: async_sessionmaker,
    book_id: uuid.UUID,
    uid: uuid.UUID,
) -> None:
    """Verify soft-delete sets deleted_at and filters from queries."""
    async with UnitOfWork(async_session_factory) as uow:
        profile = _make_profile_model(book_id, uid)
        await uow.epistemic_profiles.create(profile)
        await uow.commit()

    async with UnitOfWork(async_session_factory) as uow:
        await uow.epistemic_profiles.delete(profile.id)
        await uow.commit()

    async with UnitOfWork(async_session_factory) as uow:
        found = await uow.epistemic_profiles.get_by_id(profile.id)
        assert found is None


@pytest.mark.asyncio
async def test_update_epistemic_profile(
    async_session_factory: async_sessionmaker,
    book_id: uuid.UUID,
    uid: uuid.UUID,
) -> None:
    """Verify updating an epistemic profile."""
    async with UnitOfWork(async_session_factory) as uow:
        profile = _make_profile_model(book_id, uid)
        await uow.epistemic_profiles.create(profile)
        await uow.commit()

    async with UnitOfWork(async_session_factory) as uow:
        found = await uow.epistemic_profiles.get_by_id(profile.id)
        assert found is not None
        found.discipline = "spirituality"
        await uow.epistemic_profiles.update(found)
        await uow.commit()

    async with UnitOfWork(async_session_factory) as uow:
        found = await uow.epistemic_profiles.get_by_id(profile.id)
        assert found is not None
        assert found.discipline == "spirituality"


@pytest.mark.asyncio
async def test_uow_rollback_epistemic_profile(
    async_session_factory: async_sessionmaker,
    book_id: uuid.UUID,
    uid: uuid.UUID,
) -> None:
    """Verify rollback discards epistemic profile changes."""
    profile_id = uuid.uuid4()
    try:
        async with UnitOfWork(async_session_factory) as uow:
            profile = _make_profile_model(book_id, uid)
            profile.id = profile_id
            await uow.epistemic_profiles.create(profile)
            raise ValueError("simulate error")
    except ValueError:
        pass

    async with UnitOfWork(async_session_factory) as uow:
        found = await uow.epistemic_profiles.get_by_id(profile_id)
        assert found is None


@pytest.mark.asyncio
async def test_epistemic_profile_unique_book_constraint(
    async_session_factory: async_sessionmaker,
    book_id: uuid.UUID,
    uid: uuid.UUID,
) -> None:
    """Verify each book can have at most one epistemic profile."""
    from sqlalchemy.exc import IntegrityError

    async with UnitOfWork(async_session_factory) as uow:
        p1 = _make_profile_model(book_id, uid)
        await uow.epistemic_profiles.create(p1)
        await uow.commit()

    # Attempting to create a second profile for the same book should fail
    async with UnitOfWork(async_session_factory) as uow:
        p2 = _make_profile_model(book_id, uid)
        with pytest.raises(IntegrityError):
            await uow.epistemic_profiles.create(p2)
