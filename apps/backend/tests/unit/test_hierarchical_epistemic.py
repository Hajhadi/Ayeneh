"""Comprehensive tests for the Hierarchical Epistemic Profile System."""

from __future__ import annotations

import uuid

import pytest

from ayeneh.domain.knowledge_epistemics.entities import EpistemicProfile
from ayeneh.domain.knowledge_epistemics.enums import (
    EvidenceLevel,
    EpistemicFramework,
    KnowledgeAuthority,
    KnowledgeDomain,
    ReasoningStyle,
)
from ayeneh.domain.knowledge_epistemics.hierarchical import (
    ChapterContext,
    ChapterProfile,
    HierarchicalEpistemicProfile,
    HierarchicalGenerationEngine,
    ProfileLevel,
    TopicContext,
    TopicProfile,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> HierarchicalGenerationEngine:
    return HierarchicalGenerationEngine()


@pytest.fixture
def book_profile() -> EpistemicProfile:
    return EpistemicProfile(
        id=uuid.uuid4(),
        book_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        source="book",
        tradition="test",
        framework=EpistemicFramework.RATIONALIST,
        discipline=KnowledgeDomain.PHILOSOPHY,
        primary_topics=["truth", "reality"],
    )


@pytest.fixture
def philosophy_chapter() -> ChapterContext:
    return ChapterContext(
        chapter_id="ch1",
        title="Chapter 1: What is Truth?",
        content="Truth is a fundamental concept in philosophy. Philosophers have debated the nature of truth for centuries. The correspondence theory suggests truth matches reality. The coherence theory suggests truth is consistency within a system of beliefs.",
        sequence_number=0,
        token_count=500,
    )


@pytest.fixture
def psychology_chapter() -> ChapterContext:
    return ChapterContext(
        chapter_id="ch2",
        title="Chapter 2: Cognitive Behavioral Therapy",
        content="Cognitive behavioral therapy is an empirical approach to treating mental health disorders. Research studies have shown its effectiveness. The therapy focuses on changing negative thought patterns and behaviors through structured interventions.",
        sequence_number=1,
        token_count=600,
    )


@pytest.fixture
def spirituality_chapter() -> ChapterContext:
    return ChapterContext(
        chapter_id="ch3",
        title="Chapter 3: Meditation Practice",
        content="Meditation is a contemplative practice for inner peace. Through meditation, practitioners develop mindfulness and awareness. The spiritual tradition emphasizes direct experience over intellectual understanding.",
        sequence_number=2,
        token_count=400,
    )


# ---------------------------------------------------------------------------
# Hierarchical profile structure tests
# ---------------------------------------------------------------------------


class TestHierarchicalStructure:
    def test_hierarchical_profile_has_book_profile(
        self, book_profile: EpistemicProfile,
    ) -> None:
        h = HierarchicalEpistemicProfile(book_profile=book_profile)
        assert h.book_profile.discipline == KnowledgeDomain.PHILOSOPHY

    def test_hierarchical_profile_has_chapter_profiles(
        self, book_profile: EpistemicProfile,
    ) -> None:
        h = HierarchicalEpistemicProfile(book_profile=book_profile)
        h.chapter_profiles = [
            ChapterProfile(chapter_id="ch1", chapter_title="Introduction"),
            ChapterProfile(chapter_id="ch2", chapter_title="Methods"),
        ]
        assert len(h.chapter_profiles) == 2

    def test_hierarchical_profile_has_topic_profiles(
        self, book_profile: EpistemicProfile,
    ) -> None:
        h = HierarchicalEpistemicProfile(book_profile=book_profile)
        h.topic_profiles = {
            "ch1": [
                TopicProfile(concept="Truth", definition="Correspondence with reality"),
                TopicProfile(concept="Knowledge", definition="Justified true belief"),
            ],
        }
        assert len(h.get_topic_profiles("ch1")) == 2

    def test_get_chapter_profile(
        self, book_profile: EpistemicProfile,
    ) -> None:
        h = HierarchicalEpistemicProfile(book_profile=book_profile)
        h.chapter_profiles = [
            ChapterProfile(chapter_id="ch1", chapter_title="Intro"),
        ]
        cp = h.get_chapter_profile("ch1")
        assert cp is not None
        assert cp.chapter_title == "Intro"

    def test_get_chapter_profile_not_found(
        self, book_profile: EpistemicProfile,
    ) -> None:
        h = HierarchicalEpistemicProfile(book_profile=book_profile)
        cp = h.get_chapter_profile("nonexistent")
        assert cp is None

    def test_get_all_topic_profiles(
        self, book_profile: EpistemicProfile,
    ) -> None:
        h = HierarchicalEpistemicProfile(book_profile=book_profile)
        h.topic_profiles = {
            "ch1": [TopicProfile(concept="A")],
            "ch2": [TopicProfile(concept="B"), TopicProfile(concept="C")],
        }
        all_topics = h.get_all_topic_profiles()
        assert len(all_topics) == 3

    def test_get_coverage(
        self, book_profile: EpistemicProfile,
    ) -> None:
        h = HierarchicalEpistemicProfile(
            book_profile=book_profile,
            total_chapters=10,
            chapters_with_profiles=5,
            total_topics=20,
            topics_with_profiles=8,
        )
        coverage = h.get_coverage()
        assert coverage["chapter_coverage"] == 0.5
        assert coverage["topic_coverage"] == 0.4


# ---------------------------------------------------------------------------
# Chapter profile generation tests
# ---------------------------------------------------------------------------


class TestChapterGeneration:
    def test_generates_chapter_profile(
        self, engine: HierarchicalGenerationEngine,
        philosophy_chapter: ChapterContext,
        book_profile: EpistemicProfile,
    ) -> None:
        cp = engine.generate_chapter_profile(philosophy_chapter, book_profile)
        assert isinstance(cp, ChapterProfile)
        assert cp.chapter_id == "ch1"

    def test_chapter_detects_philosophy_domain(
        self, engine: HierarchicalGenerationEngine,
        philosophy_chapter: ChapterContext,
        book_profile: EpistemicProfile,
    ) -> None:
        cp = engine.generate_chapter_profile(philosophy_chapter, book_profile)
        assert "philosophy" in cp.domains

    def test_chapter_detects_psychology_domain(
        self, engine: HierarchicalGenerationEngine,
        psychology_chapter: ChapterContext,
        book_profile: EpistemicProfile,
    ) -> None:
        cp = engine.generate_chapter_profile(psychology_chapter, book_profile)
        assert "psychology" in cp.domains

    def test_chapter_detects_spirituality_domain(
        self, engine: HierarchicalGenerationEngine,
        spirituality_chapter: ChapterContext,
        book_profile: EpistemicProfile,
    ) -> None:
        cp = engine.generate_chapter_profile(spirituality_chapter, book_profile)
        assert "spirituality" in cp.domains

    def test_chapter_has_independent_authority(
        self, engine: HierarchicalGenerationEngine,
        philosophy_chapter: ChapterContext,
        book_profile: EpistemicProfile,
    ) -> None:
        cp = engine.generate_chapter_profile(philosophy_chapter, book_profile)
        assert cp.authority in ["primary", "secondary", "commentary", "reference"]

    def test_chapter_has_confidence(
        self, engine: HierarchicalGenerationEngine,
        philosophy_chapter: ChapterContext,
        book_profile: EpistemicProfile,
    ) -> None:
        cp = engine.generate_chapter_profile(philosophy_chapter, book_profile)
        assert 0.0 <= cp.confidence <= 1.0

    def test_chapter_has_summary(
        self, engine: HierarchicalGenerationEngine,
        philosophy_chapter: ChapterContext,
        book_profile: EpistemicProfile,
    ) -> None:
        cp = engine.generate_chapter_profile(philosophy_chapter, book_profile)
        assert len(cp.summary) > 0

    def test_chapter_has_supported_topics(
        self, engine: HierarchicalGenerationEngine,
        philosophy_chapter: ChapterContext,
        book_profile: EpistemicProfile,
    ) -> None:
        cp = engine.generate_chapter_profile(philosophy_chapter, book_profile)
        assert len(cp.supported_topics) > 0

    def test_chapter_has_limitations(
        self, engine: HierarchicalGenerationEngine,
        philosophy_chapter: ChapterContext,
        book_profile: EpistemicProfile,
    ) -> None:
        cp = engine.generate_chapter_profile(philosophy_chapter, book_profile)
        assert len(cp.limitations) > 0


# ---------------------------------------------------------------------------
# Topic profile generation tests
# ---------------------------------------------------------------------------


class TestTopicGeneration:
    def test_generates_topic_profile(
        self, engine: HierarchicalGenerationEngine,
    ) -> None:
        chapter = ChapterProfile(
            chapter_id="ch1",
            chapter_title="Truth",
            domains=["philosophy"],
        )
        topic = TopicContext(
            topic_id="t1",
            concept="Correspondence Theory",
            definition="Truth as correspondence with reality",
            scope="Metaphysics",
            chapter_id="ch1",
            content_snippet="The correspondence theory of truth states that a proposition is true if it corresponds to a fact. This is a fundamental concept in metaphysics and epistemology. The theory has been defended by many philosophers throughout history.",
        )
        tp = engine.generate_topic_profile(topic, chapter)
        assert tp is not None
        assert tp.concept == "Correspondence Theory"

    def test_topic_incoherent_returns_none(
        self, engine: HierarchicalGenerationEngine,
    ) -> None:
        chapter = ChapterProfile(chapter_id="ch1")
        topic = TopicContext(
            concept="Short",
            content_snippet="Too short",
        )
        tp = engine.generate_topic_profile(topic, chapter)
        assert tp is None

    def test_topic_has_independent_authority(
        self, engine: HierarchicalGenerationEngine,
    ) -> None:
        chapter = ChapterProfile(chapter_id="ch1", authority="secondary")
        topic = TopicContext(
            concept="Concept",
            content_snippet="This is a well-established concept with empirical evidence supporting its validity in multiple contexts. " * 5,
        )
        tp = engine.generate_topic_profile(topic, chapter)
        assert tp is not None
        assert tp.authority in ["primary", "secondary"]

    def test_topic_has_confidence(
        self, engine: HierarchicalGenerationEngine,
    ) -> None:
        chapter = ChapterProfile(chapter_id="ch1")
        topic = TopicContext(
            concept="Concept",
            content_snippet="This concept is well-defined and has been studied extensively in the literature. " * 5,
        )
        tp = engine.generate_topic_profile(topic, chapter)
        assert tp is not None
        assert 0.0 <= tp.confidence <= 1.0


# ---------------------------------------------------------------------------
# Mixed domain tests
# ---------------------------------------------------------------------------


class TestMixedDomains:
    def test_mixed_chapter_detects_multiple_domains(
        self, engine: HierarchicalGenerationEngine,
        book_profile: EpistemicProfile,
    ) -> None:
        mixed = ChapterContext(
            chapter_id="ch_mix",
            title="Mind and Spirit",
            content="The relationship between mind and spirit involves both psychological research and spiritual contemplation. Meditation affects brain function. Spiritual practice influences mental health.",
        )
        cp = engine.generate_chapter_profile(mixed, book_profile)
        assert len(cp.domains) >= 2
        assert "psychology" in cp.domains or "spirituality" in cp.domains


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_existing_profile_still_works(
        self, book_profile: EpistemicProfile,
    ) -> None:
        h = HierarchicalEpistemicProfile(book_profile=book_profile)
        assert h.book_profile.discipline == KnowledgeDomain.PHILOSOPHY
        assert h.book_profile.framework == EpistemicFramework.RATIONALIST

    def test_chapter_profile_independent_from_book(
        self, engine: HierarchicalGenerationEngine,
        book_profile: EpistemicProfile,
    ) -> None:
        book_profile.discipline = KnowledgeDomain.PHILOSOPHY
        psych_chapter = ChapterContext(
            chapter_id="ch_psych",
            title="Behavioral Psychology",
            content="Psychology studies the mind and behavior. Cognitive processes and emotion are central. Therapy techniques address mental health through behavioral interventions.",
        )
        cp = engine.generate_chapter_profile(psych_chapter, book_profile)
        # Chapter should detect psychology independently
        assert "psychology" in cp.domains


# ---------------------------------------------------------------------------
# ProfileLevel enum tests
# ---------------------------------------------------------------------------


class TestProfileLevel:
    def test_all_levels_exist(self) -> None:
        assert ProfileLevel.BOOK == "book"
        assert ProfileLevel.CHAPTER == "chapter"
        assert ProfileLevel.TOPIC == "topic"
