"""Interpretation types — core domain objects for knowledge interpretations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InterpretationType(StrEnum):
    """Types of interpretations (framework-specific)."""

    PRACTICAL_INSIGHT = "practical_insight"
    CONCEPTUAL_MEANING = "conceptual_meaning"
    MODERN_TRANSLATION = "modern_translation"
    PSYCHOLOGICAL = "psychological"
    NEUROSCIENCE = "neuroscience"
    ACT = "act"
    ANALYTICAL_PHILOSOPHICAL = "analytical_philosophy"
    ZEN = "zen"
    KHORASAN_MYSTICISM = "khorasan_mysticism"
    PHENOMENOLOGICAL = "phenomenological"
    HERMENEUTIC = "hermeneutic"


class InterpretationKind(StrEnum):
    """High-level interpretation kind (how the interpretation approaches the source)."""

    CONSERVATIVE = "conservative"
    COMPARATIVE = "comparative"
    PRACTICAL = "practical"
    CROSS_TRADITION = "cross_tradition"
    EXPLORATORY = "exploratory"


class ConfidenceLevel(StrEnum):
    """Confidence levels for interpretations."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SPECULATIVE = "speculative"


# ---------------------------------------------------------------------------
# Source Reference
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceReference:
    """Reference to the original source passage."""

    document_id: str = ""
    book_id: str = ""
    chapter_id: str = ""
    chapter_title: str = ""
    chunk_id: str = ""
    topic_id: str | None = None
    character_start: int = 0
    character_end: int = 0
    page_start: int | None = None
    page_end: int | None = None
    original_text: str = ""


# ---------------------------------------------------------------------------
# Modern Mapping
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModernMapping:
    """Mapping to a modern framework or tradition."""

    framework: str = ""
    tradition: str = ""
    mapping: str = ""
    confidence: float = 0.5
    language: str = "may resemble"
    limitations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Cross-Tradition Mapping
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CrossTraditionMapping:
    """Mapping between different traditions or frameworks."""

    source_tradition: str = ""
    target_tradition: str = ""
    concept: str = ""
    source_description: str = ""
    target_description: str = ""
    mapping_description: str = ""
    confidence: float = 0.5
    language: str = "shares similarities with"
    limitations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Graph Context
# ---------------------------------------------------------------------------


@dataclass
class GraphContext:
    """Context from the knowledge graph for interpretation generation."""

    related_concepts: list[str] = field(default_factory=list)
    supporting_books: list[str] = field(default_factory=list)
    alternative_traditions: list[str] = field(default_factory=list)
    known_disagreements: list[str] = field(default_factory=list)
    complementary_viewpoints: list[str] = field(default_factory=list)
    shared_concepts: list[str] = field(default_factory=list)
    historical_influences: list[str] = field(default_factory=list)
    authority_comparisons: list[str] = field(default_factory=list)
    scope_comparisons: list[str] = field(default_factory=list)
    graph_confidence: float = 0.5


# ---------------------------------------------------------------------------
# Context-Aware Cache Key
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InterpretationCacheKey:
    """Structured cache key for interpretations.

    Same chunk may produce different interpretations depending on:
    - Product Profile
    - Interpretation Kind
    - Generator Version
    """

    chunk_id: str = ""
    product_profile: str = "default"
    interpretation_kind: str = InterpretationKind.CONSERVATIVE
    generator_version: str = "1.0.0"

    def to_string(self) -> str:
        """Convert to deterministic string key."""
        return f"{self.chunk_id}:{self.product_profile}:{self.interpretation_kind}:{self.generator_version}"

    def __hash__(self) -> int:
        return hash(self.to_string())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, InterpretationCacheKey):
            return False
        return self.to_string() == other.to_string()


# ---------------------------------------------------------------------------
# Graph Reasoning Result
# ---------------------------------------------------------------------------


@dataclass
class GraphReasoningResult:
    """Result of deep knowledge graph reasoning."""

    # Supporting perspectives
    supporting_perspectives: list[str] = field(default_factory=list)

    # Alternative perspectives
    alternative_perspectives: list[str] = field(default_factory=list)

    # Conflicting perspectives
    conflicting_perspectives: list[str] = field(default_factory=list)

    # Complementary perspectives
    complementary_perspectives: list[str] = field(default_factory=list)

    # Scope limitations
    scope_limitations: list[str] = field(default_factory=list)

    # Authority differences
    authority_differences: list[str] = field(default_factory=list)

    # Reasoning confidence
    reasoning_confidence: float = 0.5

    # Evidence used
    evidence_used: list[str] = field(default_factory=list)

    # Provenance for reasoning elements
    supporting_provenance: list[Provenance] = field(default_factory=list)
    alternative_provenance: list[Provenance] = field(default_factory=list)
    conflicting_provenance: list[Provenance] = field(default_factory=list)
    complementary_provenance: list[Provenance] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


@dataclass
class Provenance:
    """Traceable origin for an interpretation element.

    Every generated insight must remain inspectable.
    Nothing should become an anonymous interpretation.
    """

    # Source references
    book_id: str = ""
    chapter_id: str = ""
    chunk_id: str = ""
    character_start: int = 0
    character_end: int = 0

    # Knowledge graph references
    concept_id: str = ""
    graph_edge_id: str = ""

    # Engine metadata
    engine_version: str = "1.0.0"
    generator: str = "rule_based"

    # Reasoning trace
    reasoning_step: str = ""
    evidence_summary: str = ""

    # Confidence attribution
    confidence_contribution: float = 0.0
    confidence_reason: str = ""


# ---------------------------------------------------------------------------
# Confidence Breakdown
# ---------------------------------------------------------------------------


@dataclass
class ConfidenceBreakdown:
    """Decomposed confidence with independent components.

    Overall confidence is derived from components using weighted aggregation.
    Never simply average them.
    """

    # Individual components
    source_confidence: float = 0.5
    interpretation_confidence: float = 0.5
    graph_confidence: float = 0.5
    cross_tradition_confidence: float = 0.5
    mapping_confidence: float = 0.5
    evidence_confidence: float = 0.5

    # Derived overall confidence
    overall_confidence: float = 0.5

    # Weight explanations
    weight_used: dict[str, float] = field(default_factory=dict)

    def compute_overall(
        self,
        weights: dict[str, float] | None = None,
    ) -> float:
        """Compute overall confidence from components using weighted aggregation.

        Reasoning rules:
        - Low source confidence must never produce high overall confidence
        - Strong graph support cannot compensate for weak source grounding
        - Cross-tradition mappings must remain conservative
        """
        w = weights or {
            "source": 0.25,
            "interpretation": 0.20,
            "graph": 0.15,
            "cross_tradition": 0.10,
            "mapping": 0.15,
            "evidence": 0.15,
        }

        # Apply reasoning rules
        # Rule 1: Low source confidence caps overall
        source_cap = min(1.0, self.source_confidence * 1.5)

        # Rule 2: Graph cannot compensate for weak source
        effective_graph = self.graph_confidence if self.source_confidence >= 0.4 else self.graph_confidence * 0.5

        # Rule 3: Cross-tradition stays conservative
        effective_cross_tradition = min(0.7, self.cross_tradition_confidence)

        # Weighted aggregation
        raw = (
            self.source_confidence * w.get("source", 0.25)
            + self.interpretation_confidence * w.get("interpretation", 0.20)
            + effective_graph * w.get("graph", 0.15)
            + effective_cross_tradition * w.get("cross_tradition", 0.10)
            + self.mapping_confidence * w.get("mapping", 0.15)
            + self.evidence_confidence * w.get("evidence", 0.15)
        )

        # Apply source cap
        self.overall_confidence = min(source_cap, raw)
        self.weight_used = w

        return self.overall_confidence


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------


@dataclass
class Interpretation:
    """A single interpretation of a knowledge passage.

    This is a secondary artifact. The original document always remains
    the primary source of truth.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Source reference (mandatory)
    source: SourceReference = field(default_factory=SourceReference)

    # Interpretation kind (how the interpretation approaches the source)
    interpretation_kind: str = InterpretationKind.CONSERVATIVE

    # Interpretation content
    practical_insight: str = ""
    conceptual_meaning: str = ""
    modern_translation: str = ""

    # Framework-specific interpretations
    psychological_interpretation: str = ""
    neuroscience_interpretation: str = ""
    act_interpretation: str = ""
    analytical_philosophy_interpretation: str = ""
    zen_interpretation: str = ""
    khorasan_mysticism_interpretation: str = ""

    # Alternative interpretations
    alternative_interpretations: list[str] = field(default_factory=list)

    # Modern mappings
    modern_mappings: list[ModernMapping] = field(default_factory=list)

    # Cross-tradition mappings
    cross_tradition_mappings: list[CrossTraditionMapping] = field(default_factory=list)

    # Graph context (optional, populated when available)
    graph_context: GraphContext | None = None

    # Deep graph reasoning result (optional, populated when graph available)
    graph_reasoning: GraphReasoningResult | None = None

    # Fine-grained provenance for all interpretation elements
    provenance: list[Provenance] = field(default_factory=list)

    # Decomposed confidence
    confidence_breakdown: ConfidenceBreakdown | None = None

    # Metadata
    confidence: float = 0.5
    confidence_level: str = ConfidenceLevel.MEDIUM
    generator: str = "rule_based"
    generation_version: str = "1.0.0"

    # Limitations and uncertainties
    limitations: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)

    # Versioning
    version: int = 1
    is_current: bool = True

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Interpretation Version
# ---------------------------------------------------------------------------


@dataclass
class InterpretationVersion:
    """Versioned interpretation with history tracking."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    interpretation_id: str = ""
    version: int = 1
    interpretation_data: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    is_current: bool = True


# ---------------------------------------------------------------------------
# Interpretation Context
# ---------------------------------------------------------------------------


@dataclass
class InterpretationContext:
    """Context for generating interpretations."""

    document_id: str = ""
    book_id: str = ""
    chapter_id: str = ""
    chapter_title: str = ""
    chunk_id: str = ""
    chunk_content: str = ""
    topic_id: str | None = None
    epistemic_profile: dict = field(default_factory=dict)
    knowledge_graph_context: dict = field(default_factory=dict)
    related_interpretations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Interpretation Metadata
# ---------------------------------------------------------------------------


@dataclass
class InterpretationMetadata:
    """Metadata about interpretation generation."""

    generator_version: str = "1.0.0"
    engine_type: str = "rule_based"
    generation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    generation_duration_ms: float = 0.0
    chunks_analyzed: int = 0
    frameworks_applied: list[str] = field(default_factory=list)
    confidence_factors: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
