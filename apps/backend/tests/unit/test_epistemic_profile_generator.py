"""Comprehensive tests for the Epistemic Profile Generator."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock

import pytest

from ayeneh.domain.knowledge_epistemics.entities import EpistemicProfile
from ayeneh.domain.knowledge_epistemics.enums import (
    ClaimType,
    EvidenceLevel,
    EpistemicFramework,
    KnowledgeAuthority,
    KnowledgeDomain,
    ReasoningStyle,
)
from ayeneh.domain.knowledge_epistemics.generator.engine import RuleBasedProfileGenerator
from ayeneh.domain.knowledge_epistemics.generator.service import (
    DocumentReader,
    EpistemicProfileGenerator,
    EventPublisher,
    ProfileStore,
    ProfileVersionStore,
)
from ayeneh.domain.knowledge_epistemics.generator.types import (
    DocumentContext,
    GenerationResult,
    GenerationStatus,
    ProfileVersion,
    ValidationResult,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class InMemoryProfileStore(ProfileStore):
    def __init__(self) -> None:
        self._profiles: dict[str, EpistemicProfile] = {}
        self._by_book: dict[str, str] = {}  # book_id -> profile_id

    async def save_profile(self, profile: EpistemicProfile) -> EpistemicProfile:
        self._profiles[str(profile.id)] = profile
        self._by_book[str(profile.book_id)] = str(profile.id)
        return profile

    async def get_profile_by_book(self, book_id: str) -> EpistemicProfile | None:
        profile_id = self._by_book.get(book_id)
        if profile_id:
            return self._profiles.get(profile_id)
        # Fallback: check if any profile's book_id matches
        for p in self._profiles.values():
            if str(p.book_id) == book_id:
                return p
        return None

    async def update_profile(self, profile: EpistemicProfile) -> None:
        self._profiles[str(profile.id)] = profile

    async def delete_profile(self, profile_id: str) -> None:
        profile = self._profiles.pop(profile_id, None)
        if profile:
            self._by_book.pop(str(profile.book_id), None)


class InMemoryVersionStore(ProfileVersionStore):
    def __init__(self) -> None:
        self._versions: dict[str, list[ProfileVersion]] = {}

    async def save_version(self, version: ProfileVersion) -> ProfileVersion:
        self._versions.setdefault(version.profile_id, []).append(version)
        return version

    async def get_versions(self, profile_id: str) -> list[ProfileVersion]:
        return self._versions.get(profile_id, [])

    async def get_current_version(self, profile_id: str) -> ProfileVersion | None:
        versions = self._versions.get(profile_id, [])
        for v in versions:
            if v.is_current:
                return v
        return versions[-1] if versions else None


class FakeDocumentReader(DocumentReader):
    def __init__(self) -> None:
        self._docs: dict[str, dict] = {}
        self._chapters: dict[str, list[dict]] = {}

    def add_document(self, doc_id: str, doc: dict, chapters: list[dict]) -> None:
        self._docs[doc_id] = doc
        self._chapters[doc_id] = chapters

    async def get_document(self, document_id: str) -> dict[str, Any] | None:
        return self._docs.get(document_id)

    async def get_chapters(self, document_id: str) -> list[dict[str, Any]]:
        return self._chapters.get(document_id, [])


class FakeEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, payload))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def profile_store() -> InMemoryProfileStore:
    return InMemoryProfileStore()


@pytest.fixture
def version_store() -> InMemoryVersionStore:
    return InMemoryVersionStore()


@pytest.fixture
def doc_reader() -> FakeDocumentReader:
    reader = FakeDocumentReader()
    reader.add_document(
        "doc1",
        {"title": "Introduction to Philosophy", "author": "John Smith", "language": "en", "page_count": 200},
        [
            {"title": "Chapter 1: What is Philosophy?", "content": "Philosophy explores truth and reality through reason and argument.", "token_count": 1000},
            {"title": "Chapter 2: Ethics", "content": "Ethics examines moral questions about right and wrong.", "token_count": 800},
        ],
    )
    reader.add_document(
        "doc2",
        {"title": "Meditation and Mindfulness", "author": "Jane Doe", "language": "en", "page_count": 150},
        [
            {"title": "Chapter 1: Introduction to Meditation", "content": "Meditation is a contemplative practice for inner peace.", "token_count": 900},
            {"title": "Chapter 2: Mindfulness Techniques", "content": "Mindfulness involves present-moment awareness.", "token_count": 700},
        ],
    )
    reader.add_document(
        "doc3",
        {"title": "Neuroscience and Brain Research", "author": "Dr. Brown", "language": "en", "page_count": 300},
        [
            {"title": "Chapter 1: Research Methods", "content": "Scientific experiment study data empirical research hypothesis testing.", "token_count": 1200},
            {"title": "Chapter 2: Brain Systems", "content": "Neural brain neuroscience research data empirical evidence.", "token_count": 1000},
        ],
    )
    return reader


@pytest.fixture
def event_publisher() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def engine() -> RuleBasedProfileGenerator:
    return RuleBasedProfileGenerator()


@pytest.fixture
def generator(
    profile_store: InMemoryProfileStore,
    version_store: InMemoryVersionStore,
    doc_reader: FakeDocumentReader,
    event_publisher: FakeEventPublisher,
) -> EpistemicProfileGenerator:
    return EpistemicProfileGenerator(
        profile_store=profile_store,
        version_store=version_store,
        document_reader=doc_reader,
        event_publisher=event_publisher,
    )


# ---------------------------------------------------------------------------
# Rule-based generation tests
# ---------------------------------------------------------------------------


class TestRuleBasedGeneration:
    def test_generates_profile(self, engine: RuleBasedProfileGenerator) -> None:
        context = DocumentContext(
            document_id="doc1",
            title="Introduction to Philosophy",
            author="John Smith",
            chapters=[
                {"title": "Chapter 1", "content": "Philosophy explores truth and reality.", "token_count": 500},
            ],
        )
        profile, metadata = engine.generate(context, "book1", "user1")
        assert isinstance(profile, EpistemicProfile)
        assert metadata.engine_type == "rule_based"

    def test_detects_philosophy_domain(self, engine: RuleBasedProfileGenerator) -> None:
        context = DocumentContext(
            title="Introduction to Philosophy",
            chapters=[{"content": "truth reality existence meaning reason logic", "token_count": 500}],
        )
        profile, _ = engine.generate(context, "book1", "user1")
        assert profile.discipline == KnowledgeDomain.PHILOSOPHY

    def test_detects_psychology_domain(self, engine: RuleBasedProfileGenerator) -> None:
        context = DocumentContext(
            title="Cognitive Psychology",
            chapters=[{"content": "mind brain behavior cognition therapy clinical", "token_count": 500}],
        )
        profile, _ = engine.generate(context, "book1", "user1")
        assert profile.discipline == KnowledgeDomain.PSYCHOLOGY

    def test_detects_spirituality_domain(self, engine: RuleBasedProfileGenerator) -> None:
        context = DocumentContext(
            title="Meditation and Spirituality",
            chapters=[{"content": "meditation contemplation spiritual enlightenment awakening", "token_count": 500}],
        )
        profile, _ = engine.generate(context, "book1", "user1")
        assert profile.discipline == KnowledgeDomain.SPIRITUALITY

    def test_detects_science_domain(self, engine: RuleBasedProfileGenerator) -> None:
        context = DocumentContext(
            title="Neuroscience Research",
            chapters=[{"content": "experiment hypothesis data empirical study research", "token_count": 500}],
        )
        profile, _ = engine.generate(context, "book1", "user1")
        assert profile.discipline == KnowledgeDomain.SCIENCE


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestValidation:
    def test_valid_profile_passes(self, engine: RuleBasedProfileGenerator) -> None:
        context = DocumentContext(
            title="Test Book",
            chapters=[{"content": "philosophy truth reality", "token_count": 500}],
        )
        profile, _ = engine.generate(context, "book1", "user1")
        result = engine.validate(profile)
        assert result.is_valid

    def test_missing_tradition_fails(self, engine: RuleBasedProfileGenerator) -> None:
        from ayeneh.domain.knowledge_epistemics.enums import KnowledgeSource
        import uuid
        profile = EpistemicProfile(
            id=uuid.uuid4(),
            book_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            source=KnowledgeSource.BOOK,
            tradition="",
            framework=EpistemicFramework.RATIONALIST,
            discipline=KnowledgeDomain.PHILOSOPHY,
        )
        result = engine.validate(profile)
        assert not result.is_valid
        assert any("tradition" in e for e in result.errors)

    def test_overlap_detected(self, engine: RuleBasedProfileGenerator) -> None:
        from ayeneh.domain.knowledge_epistemics.enums import KnowledgeSource
        import uuid
        profile = EpistemicProfile(
            id=uuid.uuid4(),
            book_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            source=KnowledgeSource.BOOK,
            tradition="test",
            framework=EpistemicFramework.RATIONALIST,
            discipline=KnowledgeDomain.PHILOSOPHY,
            supported_questions=["What is truth?"],
            unsupported_questions=["What is truth?"],
        )
        result = engine.validate(profile)
        assert not result.is_valid
        assert any("overlap" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Generator service tests
# ---------------------------------------------------------------------------


class TestGeneratorService:
    @pytest.mark.asyncio
    async def test_generate_profile(
        self, generator: EpistemicProfileGenerator,
    ) -> None:
        result = await generator.generate_profile("doc1", "book1", "user1")
        assert result.status == GenerationStatus.COMPLETED
        assert result.profile_id is not None

    @pytest.mark.asyncio
    async def test_generate_creates_profile(
        self, generator: EpistemicProfileGenerator, profile_store: InMemoryProfileStore,
    ) -> None:
        import uuid
        book_id = str(uuid.uuid4())
        result = await generator.generate_profile("doc1", book_id, "user1")
        profile = await generator.get_profile(book_id)
        assert profile is not None

    @pytest.mark.asyncio
    async def test_generate_publishes_event(
        self, generator: EpistemicProfileGenerator, event_publisher: FakeEventPublisher,
    ) -> None:
        await generator.generate_profile("doc1", "book1", "user1")
        assert len(event_publisher.events) > 0
        assert event_publisher.events[0][0] == "EpistemicProfileGenerated"

    @pytest.mark.asyncio
    async def test_generate_creates_version(
        self, generator: EpistemicProfileGenerator, version_store: InMemoryVersionStore,
    ) -> None:
        result = await generator.generate_profile("doc1", "book1", "user1")
        versions = await generator.get_profile_history(result.profile_id)
        assert len(versions) == 1
        assert versions[0].version == 1

    @pytest.mark.asyncio
    async def test_generate_not_found(
        self, generator: EpistemicProfileGenerator,
    ) -> None:
        result = await generator.generate_profile("nonexistent", "book1", "user1")
        assert result.status == GenerationStatus.FAILED


# ---------------------------------------------------------------------------
# Regeneration tests
# ---------------------------------------------------------------------------


class TestRegeneration:
    @pytest.mark.asyncio
    async def test_regenerate_no_existing(
        self, generator: EpistemicProfileGenerator,
    ) -> None:
        result = await generator.regenerate_profile("nonexistent", "user1")
        assert result.status == GenerationStatus.FAILED

    @pytest.mark.asyncio
    async def test_regenerate_profile(
        self, generator: EpistemicProfileGenerator,
    ) -> None:
        import uuid
        book_id = str(uuid.uuid4())
        r1 = await generator.generate_profile("doc1", book_id, "user1")
        r2 = await generator.regenerate_profile(book_id, "user1")
        assert r2.status == GenerationStatus.COMPLETED
        assert r2.version == 2


# ---------------------------------------------------------------------------
# Different discipline tests
# ---------------------------------------------------------------------------


class TestDifferentDisciplines:
    @pytest.mark.asyncio
    async def test_philosophy_book(
        self, generator: EpistemicProfileGenerator,
    ) -> None:
        import uuid
        book_id = str(uuid.uuid4())
        result = await generator.generate_profile("doc1", book_id, "user1")
        profile = await generator.get_profile(book_id)
        assert profile is not None
        assert profile.discipline == KnowledgeDomain.PHILOSOPHY

    @pytest.mark.asyncio
    async def test_spirituality_book(
        self, generator: EpistemicProfileGenerator,
    ) -> None:
        import uuid
        book_id = str(uuid.uuid4())
        result = await generator.generate_profile("doc2", book_id, "user1")
        profile = await generator.get_profile(book_id)
        assert profile is not None
        assert profile.discipline == KnowledgeDomain.SPIRITUALITY

    @pytest.mark.asyncio
    async def test_science_book(
        self, generator: EpistemicProfileGenerator,
    ) -> None:
        import uuid
        book_id = str(uuid.uuid4())
        result = await generator.generate_profile("doc3", book_id, "user1")
        profile = await generator.get_profile(book_id)
        assert profile is not None
        assert profile.discipline == KnowledgeDomain.SCIENCE


# ---------------------------------------------------------------------------
# Observability tests
# ---------------------------------------------------------------------------


class TestObservability:
    def test_metrics_recorded(self) -> None:
        from ayeneh.infrastructure.observability import PrometheusMetrics

        metrics = PrometheusMetrics()
        metrics.record_epistemic_analysis(
            duration_ms=10.0,
            confidence=0.8,
            frameworks=["rationalist"],
            intent="profile_generation",
            requires_uncertainty=False,
            cross_framework=False,
        )
        assert metrics.epistemic_analysis_count == 1


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_chapters(
        self, generator: EpistemicProfileGenerator, doc_reader: FakeDocumentReader,
    ) -> None:
        doc_reader.add_document(
            "empty_doc",
            {"title": "Empty Book", "author": "Nobody", "language": "en"},
            [],
        )
        result = await generator.generate_profile("empty_doc", "book_empty", "user1")
        assert result.status == GenerationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_special_characters_in_title(
        self, generator: EpistemicProfileGenerator, doc_reader: FakeDocumentReader,
    ) -> None:
        doc_reader.add_document(
            "special_doc",
            {"title": "Book: A Story (2024)", "author": "Author", "language": "en"},
            [{"title": "Ch1", "content": "content", "token_count": 100}],
        )
        result = await generator.generate_profile("special_doc", "book_special", "user1")
        assert result.status == GenerationStatus.COMPLETED


# ---------------------------------------------------------------------------
# Concurrency tests
# ---------------------------------------------------------------------------


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_generation(
        self, generator: EpistemicProfileGenerator,
    ) -> None:
        tasks = [
            generator.generate_profile("doc1", f"book{i}", "user1")
            for i in range(5)
        ]
        import asyncio
        results = await asyncio.gather(*tasks)
        assert len(results) == 5
        assert all(r.status == GenerationStatus.COMPLETED for r in results)


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    @pytest.mark.asyncio
    async def test_generation_completes_quickly(
        self, generator: EpistemicProfileGenerator,
    ) -> None:
        start = time.monotonic()
        for i in range(20):
            await generator.generate_profile("doc1", f"book{i}", "user1")
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 5000  # 20 generations in under 5 seconds


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_same_document_different_books(
        self, generator: EpistemicProfileGenerator,
    ) -> None:
        r1 = await generator.generate_profile("doc1", "book1", "user1")
        r2 = await generator.generate_profile("doc1", "book2", "user1")
        assert r1.profile_id != r2.profile_id


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    @pytest.mark.asyncio
    async def test_generator_works_with_defaults(
        self,
    ) -> None:
        generator = EpistemicProfileGenerator(
            profile_store=InMemoryProfileStore(),
            version_store=InMemoryVersionStore(),
            document_reader=FakeDocumentReader(),
            event_publisher=FakeEventPublisher(),
        )
        assert generator._engine is not None
