"""Hierarchical Epistemic Profile System.

Extends the flat EpistemicProfile into a three-layer hierarchy:
Book Profile → Chapter Profile → Topic Profile (optional).

Each layer owns its own epistemic properties.
Inheritance is explicit, never blind.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from ayeneh.domain.knowledge_epistemics.entities import EpistemicProfile
from ayeneh.domain.knowledge_epistemics.enums import (
    ClaimType,
    EvidenceLevel,
    EpistemicFramework,
    KnowledgeAuthority,
    KnowledgeDomain,
    ReasoningStyle,
)
from ayeneh.domain.knowledge_epistemics.value_objects import (
    Applicability,
    CitationPolicy,
    Limitation,
    ScopeBoundary,
    SourceReliability,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ProfileLevel(StrEnum):
    """Level in the hierarchical profile system."""

    BOOK = "book"
    CHAPTER = "chapter"
    TOPIC = "topic"


class GenerationPhase(StrEnum):
    """Phase of hierarchical generation."""

    BOOK_PROFILE = "book_profile"
    CHAPTER_PROFILES = "chapter_profiles"
    TOPIC_PROFILES = "topic_profiles"
    COMPLETE = "complete"


# ---------------------------------------------------------------------------
# Chapter Profile
# ---------------------------------------------------------------------------


@dataclass
class ChapterProfile:
    """Epistemic profile for a single chapter.

    Every chapter owns its own epistemic properties.
    Never infer chapter authority directly from book authority.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    book_profile_id: str = ""
    chapter_id: str = ""
    chapter_title: str = ""
    sequence_number: int = 0

    # Summary
    summary: str = ""

    # Epistemic properties (independent from book)
    domains: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    authority: str = KnowledgeAuthority.SECONDARY
    evidence_level: str = EvidenceLevel.PHILOSOPHICAL
    reasoning_style: str = ReasoningStyle.DEDUCTIVE
    claim_types: list[str] = field(default_factory=list)

    # Scope
    supported_topics: list[str] = field(default_factory=list)
    unsupported_topics: list[str] = field(default_factory=list)
    limitations: list[dict] = field(default_factory=list)
    scope_boundary: dict = field(default_factory=dict)

    # Confidence
    confidence: float = 0.5
    confidence_factors: list[str] = field(default_factory=list)

    # References
    embedding_ids: list[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Topic Profile
# ---------------------------------------------------------------------------


@dataclass
class TopicProfile:
    """Optional epistemic profile for a specific topic within a chapter.

    Generated only when the chapter contains sufficiently coherent themes.
    Each topic is evaluated independently.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chapter_profile_id: str = ""
    book_profile_id: str = ""

    # Identity
    concept: str = ""
    definition: str = ""
    scope: str = ""

    # Epistemic properties (independent from chapter)
    authority: str = KnowledgeAuthority.SECONDARY
    evidence_level: str = EvidenceLevel.PHILOSOPHICAL
    reasoning_style: str = ReasoningStyle.DEDUCTIVE
    limitations: list[dict] = field(default_factory=list)

    # Relations
    related_chapters: list[str] = field(default_factory=list)
    related_books: list[str] = field(default_factory=list)

    # Confidence
    confidence: float = 0.5
    confidence_factors: list[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Hierarchical Epistemic Profile
# ---------------------------------------------------------------------------


@dataclass
class HierarchicalEpistemicProfile:
    """Three-layer hierarchical epistemic profile.

    Book Profile → Chapter Profile → Topic Profile (optional).

    Each layer represents an independent epistemic interpretation.
    Never infer chapter authority directly from book authority.
    Never infer topic authority directly from chapter authority.
    """

    # Book-level profile (wraps existing EpistemicProfile)
    book_profile: EpistemicProfile = field(default_factory=lambda: EpistemicProfile(
        id=uuid.uuid4(),
        book_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        source="book",
        tradition="",
        framework="rationalist",
        discipline="philosophy",
    ))

    # Chapter-level profiles
    chapter_profiles: list[ChapterProfile] = field(default_factory=list)

    # Topic-level profiles (optional, nested within chapters)
    topic_profiles: dict[str, list[TopicProfile]] = field(default_factory=dict)

    # Generation metadata
    generation_phase: str = GenerationPhase.BOOK_PROFILE
    total_chapters: int = 0
    chapters_with_profiles: int = 0
    total_topics: int = 0
    topics_with_profiles: int = 0

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def get_chapter_profile(self, chapter_id: str) -> ChapterProfile | None:
        """Get a chapter profile by ID."""
        for cp in self.chapter_profiles:
            if cp.chapter_id == chapter_id:
                return cp
        return None

    def get_topic_profiles(self, chapter_id: str) -> list[TopicProfile]:
        """Get topic profiles for a chapter."""
        return self.topic_profiles.get(chapter_id, [])

    def get_all_topic_profiles(self) -> list[TopicProfile]:
        """Get all topic profiles across all chapters."""
        topics: list[TopicProfile] = []
        for chapter_topics in self.topic_profiles.values():
            topics.extend(chapter_topics)
        return topics

    def get_coverage(self) -> dict[str, float]:
        """Get coverage statistics."""
        chapter_coverage = (
            self.chapters_with_profiles / self.total_chapters
            if self.total_chapters > 0
            else 0.0
        )
        topic_coverage = (
            self.topics_with_profiles / self.total_topics
            if self.total_topics > 0
            else 0.0
        )
        return {
            "chapter_coverage": chapter_coverage,
            "topic_coverage": topic_coverage,
            "total_chapters": self.total_chapters,
            "chapters_with_profiles": self.chapters_with_profiles,
            "total_topics": self.total_topics,
            "topics_with_profiles": self.topics_with_profiles,
        }


# ---------------------------------------------------------------------------
# Hierarchical Generation Types
# ---------------------------------------------------------------------------


@dataclass
class ChapterContext:
    """Context for generating a chapter profile."""

    chapter_id: str = ""
    title: str = ""
    content: str = ""
    sequence_number: int = 0
    page_start: int | None = None
    page_end: int | None = None
    token_count: int = 0
    book_context: dict = field(default_factory=dict)


@dataclass
class TopicContext:
    """Context for generating a topic profile."""

    topic_id: str = ""
    concept: str = ""
    definition: str = ""
    scope: str = ""
    chapter_id: str = ""
    chapter_title: str = ""
    content_snippet: str = ""
    related_chapters: list[str] = field(default_factory=list)


@dataclass
class HierarchicalGenerationResult:
    """Result of hierarchical profile generation."""

    status: str = "completed"
    book_profile_id: str = ""
    chapter_profiles_generated: int = 0
    topic_profiles_generated: int = 0
    total_duration_ms: float = 0.0
    book_generation_ms: float = 0.0
    chapter_generation_ms: float = 0.0
    topic_generation_ms: float = 0.0
    error: str | None = None


# ---------------------------------------------------------------------------
# Hierarchical Generation Engine
# ---------------------------------------------------------------------------


class HierarchicalGenerationEngine:
    """Generates hierarchical epistemic profiles.

    This engine extends the flat profile generation into a three-layer hierarchy.
    Each layer is evaluated independently.
    """

    def __init__(self, flat_engine: Any | None = None) -> None:
        from ayeneh.domain.knowledge_epistemics.generator.engine import RuleBasedProfileGenerator
        self._flat_engine = flat_engine or RuleBasedProfileGenerator()

    def generate_book_profile(
        self,
        document_id: str,
        book_id: str,
        user_id: str,
        title: str = "",
        author: str = "",
        language: str = "en",
        chapters: list[dict] | None = None,
    ) -> EpistemicProfile:
        """Generate the book-level profile."""
        from ayeneh.domain.knowledge_epistemics.generator.types import DocumentContext

        context = DocumentContext(
            document_id=document_id,
            title=title,
            author=author,
            language=language,
            chapters=chapters or [],
        )

        profile, _ = self._flat_engine.generate(context, book_id, user_id)
        return profile

    def generate_chapter_profile(
        self,
        chapter_context: ChapterContext,
        book_profile: EpistemicProfile,
    ) -> ChapterProfile:
        """Generate a chapter-level profile.

        Each chapter is evaluated independently.
        Never infer chapter authority directly from book authority.
        """
        text = chapter_context.content.lower()
        title = chapter_context.title.lower()

        # Detect domains (independent from book)
        domains = self._detect_chapter_domains(text, title)

        # Detect framework (independent from book)
        frameworks = self._detect_chapter_frameworks(text, domains)

        # Detect authority (independent from book)
        authority = self._detect_chapter_authority(text, title)

        # Detect evidence level (independent from book)
        evidence_level = self._detect_chapter_evidence(text, domains)

        # Detect reasoning style (independent from book)
        reasoning_style = self._detect_chapter_reasoning(text, domains)

        # Detect claim types
        claim_types = self._detect_chapter_claim_types(text)

        # Detect topics
        supported, unsupported = self._detect_chapter_topics(text, domains)

        # Detect limitations
        limitations = self._detect_chapter_limitations(text, domains)

        # Detect scope boundary
        scope_boundary = self._detect_chapter_scope(text, domains)

        # Compute confidence
        confidence = self._compute_chapter_confidence(
            text, domains, authority, evidence_level,
        )

        # Build summary
        summary = self._build_chapter_summary(
            chapter_context.title, domains, authority, evidence_level,
        )

        return ChapterProfile(
            book_profile_id=str(book_profile.id),
            chapter_id=chapter_context.chapter_id,
            chapter_title=chapter_context.title,
            sequence_number=chapter_context.sequence_number,
            summary=summary,
            domains=domains,
            frameworks=frameworks,
            authority=authority,
            evidence_level=evidence_level,
            reasoning_style=reasoning_style,
            claim_types=claim_types,
            supported_topics=supported,
            unsupported_topics=unsupported,
            limitations=limitations,
            scope_boundary=scope_boundary,
            confidence=confidence,
            confidence_factors=[
                f"domains:{','.join(domains)}",
                f"authority:{authority}",
                f"evidence:{evidence_level}",
            ],
        )

    def generate_topic_profile(
        self,
        topic_context: TopicContext,
        chapter_profile: ChapterProfile,
    ) -> TopicProfile | None:
        """Generate a topic-level profile.

        Only generated when the chapter contains sufficiently coherent themes.
        Each topic is evaluated independently.
        """
        text = topic_context.content_snippet.lower()

        # Check if topic is coherent enough to warrant a profile
        if not self._is_topic_coherent(text, topic_context.concept):
            return None

        # Detect authority (independent from chapter)
        authority = self._detect_topic_authority(text, topic_context.concept)

        # Detect evidence level (independent from chapter)
        evidence_level = self._detect_topic_evidence(text)

        # Detect reasoning style (independent from chapter)
        reasoning_style = self._detect_topic_reasoning(text)

        # Detect limitations
        limitations = self._detect_topic_limitations(text, topic_context.concept)

        # Compute confidence
        confidence = self._compute_topic_confidence(
            text, authority, evidence_level,
        )

        return TopicProfile(
            chapter_profile_id=chapter_profile.id,
            book_profile_id=chapter_profile.book_profile_id,
            concept=topic_context.concept,
            definition=topic_context.definition,
            scope=topic_context.scope,
            authority=authority,
            evidence_level=evidence_level,
            reasoning_style=reasoning_style,
            limitations=limitations,
            related_chapters=topic_context.related_chapters,
            confidence=confidence,
            confidence_factors=[
                f"authority:{authority}",
                f"evidence:{evidence_level}",
            ],
        )

    # ------------------------------------------------------------------
    # Chapter-level detection methods
    # ------------------------------------------------------------------

    def _detect_chapter_domains(self, text: str, title: str) -> list[str]:
        """Detect domains for a chapter."""
        domains: list[str] = []

        domain_keywords: dict[str, list[str]] = {
            "philosophy": ["truth", "reality", "existence", "meaning", "reason", "logic", "argument"],
            "psychology": ["mind", "brain", "behavior", "cognition", "emotion", "therapy"],
            "spirituality": ["meditation", "contemplation", "spiritual", "mystical", "prayer"],
            "science": ["experiment", "hypothesis", "data", "empirical", "research", "study"],
            "history": ["century", "era", "period", "ancient", "historical"],
            "literature": ["story", "narrative", "character", "theme", "symbol"],
            "social_science": ["society", "culture", "community", "social", "power"],
        }

        for domain, keywords in domain_keywords.items():
            matches = sum(1 for kw in keywords if kw in text or kw in title)
            if matches >= 2:
                domains.append(domain)

        if not domains:
            domains = ["philosophy"]  # Default

        return domains[:3]

    def _detect_chapter_frameworks(self, text: str, domains: list[str]) -> list[str]:
        """Detect frameworks for a chapter."""
        frameworks: list[str] = []

        framework_keywords: dict[str, list[str]] = {
            "rationalist": ["reason", "logic", "argument", "proof"],
            "empiricist": ["evidence", "data", "observation", "experiment"],
            "phenomenological": ["experience", "lived", "phenomenon", "consciousness"],
            "hermeneutic": ["interpret", "meaning", "text", "understanding"],
            "dialectical": ["contradiction", "tension", "thesis", "synthesis"],
            "intuitionist": ["intuition", "direct", "inner", "contemplative"],
        }

        for framework, keywords in framework_keywords.items():
            matches = sum(1 for kw in keywords if kw in text)
            if matches >= 2:
                frameworks.append(framework)

        if not frameworks:
            frameworks = ["rationalist"]

        return frameworks[:2]

    def _detect_chapter_authority(self, text: str, title: str) -> str:
        """Detect authority level for a chapter."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["professor", "university", "research", "peer-reviewed"]):
            return "primary"
        if any(w in text_lower for w in ["commentary", "analysis", "interpretation"]):
            return "commentary"
        if any(w in text_lower for w in ["reference", "handbook", "manual"]):
            return "reference"

        return "secondary"

    def _detect_chapter_evidence(self, text: str, domains: list[str]) -> str:
        """Detect evidence level for a chapter."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["study", "research", "data", "experiment", "empirical"]):
            return "empirical"
        if any(w in text_lower for w in ["experience", "felt", "lived", "personal"]):
            return "experiential"
        if any(w in text_lower for w in ["tradition", "traditional", "ancient"]):
            return "traditional"

        if "science" in domains or "psychology" in domains:
            return "empirical"
        if "spirituality" in domains:
            return "experiential"

        return "philosophical"

    def _detect_chapter_reasoning(self, text: str, domains: list[str]) -> str:
        """Detect reasoning style for a chapter."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["therefore", "thus", "consequently", "logically"]):
            return "deductive"
        if any(w in text_lower for w in ["pattern", "trend", "observe", "inductively"]):
            return "inductive"
        if any(w in text_lower for w in ["contemplat", "meditat", "inner", "silence"]):
            return "contemplative"
        if any(w in text_lower for w in ["story", "narrative", "journey"]):
            return "narrative"

        if "science" in domains:
            return "inductive"
        if "spirituality" in domains:
            return "contemplative"

        return "deductive"

    def _detect_chapter_claim_types(self, text: str) -> list[str]:
        """Detect claim types for a chapter."""
        text_lower = text.lower()
        claims: list[str] = []

        if any(w in text_lower for w in ["is", "are", "fact", "reality"]):
            claims.append("factual")
        if any(w in text_lower for w in ["interpret", "meaning", "understand"]):
            claims.append("interpretive")
        if any(w in text_lower for w in ["should", "ought", "moral"]):
            claims.append("normative")
        if any(w in text_lower for w in ["describe", "observed"]):
            claims.append("descriptive")

        return claims if claims else ["interpretive"]

    def _detect_chapter_topics(
        self, text: str, domains: list[str],
    ) -> tuple[list[str], list[str]]:
        """Detect supported and unsupported topics."""
        text_lower = text.lower()
        supported: list[str] = []
        unsupported: list[str] = []

        if "philosophy" in domains:
            supported = ["metaphysics", "epistemology", "ethics", "logic"]
            unsupported = ["clinical diagnosis", "medical treatment"]
        elif "psychology" in domains:
            supported = ["cognition", "behavior", "emotion", "therapy"]
            unsupported = ["spiritual practice", "metaphysical claims"]
        elif "spirituality" in domains:
            supported = ["contemplation", "meditation", "inner experience"]
            unsupported = ["clinical diagnosis", "scientific proof"]
        elif "science" in domains:
            supported = ["empirical research", "data analysis"]
            unsupported = ["spiritual claims", "moral prescriptions"]

        return supported, unsupported

    def _detect_chapter_limitations(self, text: str, domains: list[str]) -> list[dict]:
        """Detect limitations for a chapter."""
        limitations: list[dict] = []

        if "philosophy" in domains:
            limitations.append({
                "description": "Philosophical arguments may not be empirically verifiable",
                "severity": "moderate",
                "affected_domains": ["science", "clinical"],
            })
        elif "spirituality" in domains:
            limitations.append({
                "description": "Spiritual experiences are subjective",
                "severity": "significant",
                "affected_domains": ["science", "clinical"],
            })
        elif "science" in domains:
            limitations.append({
                "description": "Findings may not generalize across all populations",
                "severity": "moderate",
                "affected_domains": ["spirituality", "philosophy"],
            })

        return limitations

    def _detect_chapter_scope(self, text: str, domains: list[str]) -> dict:
        """Detect scope boundary for a chapter."""
        included: list[str] = []
        excluded: list[str] = []

        if "philosophy" in domains:
            included = ["metaphysics", "epistemology", "ethics"]
            excluded = ["clinical diagnosis", "medical treatment"]
        elif "psychology" in domains:
            included = ["cognition", "behavior", "emotion"]
            excluded = ["spiritual practice", "metaphysical claims"]
        elif "spirituality" in domains:
            included = ["contemplation", "meditation", "inner experience"]
            excluded = ["clinical diagnosis", "scientific proof"]
        elif "science" in domains:
            included = ["empirical research", "data analysis"]
            excluded = ["spiritual claims", "moral prescriptions"]

        return {
            "included_topics": included,
            "excluded_topics": excluded,
            "overlap_notes": [],
        }

    def _compute_chapter_confidence(
        self, text: str, domains: list[str], authority: str, evidence: str,
    ) -> float:
        """Compute confidence for a chapter profile."""
        confidence = 0.5

        # Text length factor
        word_count = len(text.split())
        if word_count > 500:
            confidence += 0.1
        elif word_count > 100:
            confidence += 0.05

        # Domain clarity
        if len(domains) == 1:
            confidence += 0.1
        elif len(domains) <= 2:
            confidence += 0.05

        # Authority factor
        if authority == "primary":
            confidence += 0.1
        elif authority == "secondary":
            confidence += 0.05

        # Evidence factor
        if evidence == "empirical":
            confidence += 0.1
        elif evidence == "philosophical":
            confidence += 0.05

        return min(1.0, confidence)

    def _build_chapter_summary(
        self, title: str, domains: list[str], authority: str, evidence: str,
    ) -> str:
        """Build a summary for the chapter."""
        domain_str = ", ".join(domains) if domains else "general"
        return f"Chapter on {title}. Domains: {domain_str}. Authority: {authority}. Evidence: {evidence}."

    # ------------------------------------------------------------------
    # Topic-level detection methods
    # ------------------------------------------------------------------

    def _is_topic_coherent(self, text: str, concept: str) -> bool:
        """Check if a topic is coherent enough for a profile."""
        if len(text.split()) < 20:
            return False
        if concept.lower() in text:
            return True
        return len(text.split()) > 50

    def _detect_topic_authority(self, text: str, concept: str) -> str:
        """Detect authority for a topic."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["definition", "established", "consensus"]):
            return "primary"
        return "secondary"

    def _detect_topic_evidence(self, text: str) -> str:
        """Detect evidence level for a topic."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["empirical", "data", "research"]):
            return "empirical"
        if any(w in text_lower for w in ["experience", "felt"]):
            return "experiential"
        return "philosophical"

    def _detect_topic_reasoning(self, text: str) -> str:
        """Detect reasoning style for a topic."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["therefore", "logically"]):
            return "deductive"
        if any(w in text_lower for w in ["contemplat", "meditat"]):
            return "contemplative"
        return "deductive"

    def _detect_topic_limitations(self, text: str, concept: str) -> list[dict]:
        """Detect limitations for a topic."""
        return [{
            "description": f"Limited to context of {concept}",
            "severity": "minor",
            "affected_domains": ["cross-domain"],
        }]

    def _compute_topic_confidence(
        self, text: str, authority: str, evidence: str,
    ) -> float:
        """Compute confidence for a topic profile."""
        confidence = 0.4

        if len(text.split()) > 100:
            confidence += 0.1
        if authority == "primary":
            confidence += 0.1
        if evidence == "empirical":
            confidence += 0.1

        return min(1.0, confidence)
