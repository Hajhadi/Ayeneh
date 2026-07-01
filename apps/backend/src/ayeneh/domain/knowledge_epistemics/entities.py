"""Epistemic entities — core domain objects for knowledge source reasoning."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from ayeneh.domain.knowledge_epistemics.enums import (
    ClaimType,
    EvidenceLevel,
    EpistemicFramework,
    KnowledgeAuthority,
    KnowledgeDomain,
    KnowledgeSource,
    ReasoningStyle,
)
from ayeneh.domain.knowledge_epistemics.value_objects import (
    Applicability,
    CitationPolicy,
    Limitation,
    ScopeBoundary,
    SourceReliability,
    TranslationMetadata,
)


@dataclass
class EpistemicProfile:
    """Core epistemic identity of a knowledge source. One per book.

    This is NOT metadata or tagging. Each imported book owns exactly one
    EpistemicProfile that captures how the source can be used for reasoning,
    what its limitations are, and how it relates to other knowledge sources.
    """

    id: uuid.UUID
    book_id: uuid.UUID
    user_id: uuid.UUID

    # Identity
    source: KnowledgeSource
    tradition: str
    framework: EpistemicFramework
    discipline: KnowledgeDomain

    # Topics
    primary_topics: list[str] = field(default_factory=list)
    secondary_topics: list[str] = field(default_factory=list)

    # Question support
    supported_questions: list[str] = field(default_factory=list)
    unsupported_questions: list[str] = field(default_factory=list)

    # Epistemic properties
    evidence_level: EvidenceLevel = EvidenceLevel.PHILOSOPHICAL
    reasoning_style: ReasoningStyle = ReasoningStyle.DEDUCTIVE
    authority: KnowledgeAuthority = KnowledgeAuthority.PRIMARY
    claim_types: list[ClaimType] = field(default_factory=list)

    # Scope
    applicability: Applicability = field(
        default_factory=lambda: Applicability(contexts=[], conditions=[], contraindications=[]),
    )
    limitations: list[Limitation] = field(default_factory=list)
    scope_boundary: ScopeBoundary = field(
        default_factory=lambda: ScopeBoundary(
            included_topics=[], excluded_topics=[], overlap_notes=[],
        ),
    )

    # Policy
    citation_policy: CitationPolicy = field(
        default_factory=lambda: CitationPolicy(required=True, format="inline", min_confidence=0.5),
    )
    confidence_policy: str = ""
    conflict_policy: str = ""
    priority_hints: list[str] = field(default_factory=list)

    # Source metadata
    source_reliability: SourceReliability = field(
        default_factory=lambda: SourceReliability(score=0.5, basis="mixed"),
    )
    historical_period: str | None = None
    language: str = "en"
    translation_metadata: TranslationMetadata | None = None

    # Reference to source document
    document_id: str | None = None

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None
