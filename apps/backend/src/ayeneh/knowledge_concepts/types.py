"""Knowledge Concepts types — core domain objects for concept extraction."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConceptProvenance:
    """Provenance for a concept."""

    book_id: str = ""
    chapter_id: str = ""
    chunk_id: str = ""
    character_start: int = 0
    character_end: int = 0
    language: str = "en"
    parser: str = ""
    text_origin: str = "native"


@dataclass(frozen=True)
class EvidenceReference:
    """Complete reference to an evidence occurrence.

    First-class model that preserves full provenance for every piece of evidence.
    """

    document_id: str = ""
    book_id: str = ""
    chapter_id: str = ""
    chunk_id: str = ""
    page_number: int = 0
    character_start: int = 0
    character_end: int = 0
    language: str = "en"
    framework: str = ""
    epistemic_profile_id: str = ""
    hierarchical_profile_id: str = ""
    text_origin: str = "native"
    ocr_confidence: float = 1.0
    source_confidence: float = 0.5
    extraction_confidence: float = 0.5
    timestamp: str = ""


@dataclass
class CandidateEvidence:
    """Evidence collected during candidate generation.

    References are the primary source of truth.
    Statistics are derived from references.
    """

    references: list[EvidenceReference] = field(default_factory=list)
    occurrence_count: int = 0
    supporting_books: list[str] = field(default_factory=list)
    supporting_languages: list[str] = field(default_factory=list)
    cross_framework_count: int = 0
    cross_tradition_count: int = 0

    def add_reference(self, ref: EvidenceReference) -> None:
        """Add a reference and update derived statistics."""
        self.references.append(ref)
        self._update_derived()

    def _update_derived(self) -> None:
        """Update derived statistics from references."""
        self.occurrence_count = len(self.references)
        self.supporting_books = list({r.book_id for r in self.references if r.book_id})
        self.supporting_languages = list({r.language for r in self.references if r.language})
        self.cross_framework_count = len({r.framework for r in self.references if r.framework})
        self.cross_tradition_count = len({r.epistemic_profile_id for r in self.references if r.epistemic_profile_id})


@dataclass
class CandidateWithEvidence:
    """A candidate concept with its evidence."""

    text: str = ""
    evidence: CandidateEvidence = field(default_factory=CandidateEvidence)


@dataclass
class CanonicalConcept:
    """A normalized concept with aliases."""

    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    confidence: float = 0.5
    domain: str = ""
    definition: str = ""


@dataclass
class NormalizedConcept:
    """A concept after normalization."""

    original: str = ""
    canonical: str = ""
    confidence: float = 0.5
    evidence: CandidateEvidence = field(default_factory=CandidateEvidence)


@dataclass
class ConceptConfidence:
    """Decomposed confidence for a concept."""

    extraction_confidence: float = 0.5
    normalization_confidence: float = 0.5
    graph_support_confidence: float = 0.5
    epistemic_support_confidence: float = 0.5
    support_frequency: float = 0.5
    cross_book_support: float = 0.5
    cross_language_support: float = 0.5
    overall_confidence: float = 0.5


@dataclass
class EpistemicRule:
    """A validation rule for epistemic validation."""

    id: str = ""
    description: str = ""
    severity: str = "warning"  # "warning" | "error"
    enabled: bool = True

    def validate(self, concept: str) -> tuple[bool, str]:
        """Validate a concept. Returns (is_valid, reason)."""
        return True, ""


@dataclass
class RuleValidationResult:
    """Result of validating a concept against rules."""

    rule_id: str = ""
    is_valid: bool = True
    reason: str = ""
    severity: str = "warning"


@dataclass
class ConceptNode:
    """A concept node in the knowledge graph."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    canonical_name: str = ""
    aliases: list[str] = field(default_factory=list)
    domain: str = ""
    definition: str = ""
    language: str = "en"
    extraction_confidence: float = 0.5
    normalization_confidence: float = 0.5
    graph_confidence: float = 0.5
    epistemic_support_confidence: float = 0.5
    confidence: ConceptConfidence | None = None
    provenance: list[ConceptProvenance] = field(default_factory=list)
    evidence: CandidateEvidence = field(default_factory=CandidateEvidence)


@dataclass
class AmbiguityRecord:
    """Record of ambiguity between two concepts that cannot be confidently merged."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    concept_a: str = ""
    concept_b: str = ""
    similarity_score: float = 0.0
    reason: str = ""
    evidence: list[str] = field(default_factory=list)
    provenance: list[ConceptProvenance] = field(default_factory=list)


@dataclass
class DiscoveredConcept:
    """A concept discovered through semantic analysis (not dictionary lookup)."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    normalized: str = ""
    confidence: ConceptConfidence = field(default_factory=ConceptConfidence)
    provenance: list[ConceptProvenance] = field(default_factory=list)
    discovery_method: str = "rule_based"
    evidence: CandidateEvidence = field(default_factory=CandidateEvidence)


@dataclass
class TopicNode:
    """A topic node grouping related concepts."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    concept_ids: list[str] = field(default_factory=list)
    domain: str = ""
    confidence: float = 0.5
    provenance: list[ConceptProvenance] = field(default_factory=list)


@dataclass
class ExtractionResult:
    """Result of concept extraction from a chunk."""

    chunk_id: str = ""
    concepts: list[str] = field(default_factory=list)
    discovered_concepts: list[DiscoveredConcept] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    ambiguities: list[AmbiguityRecord] = field(default_factory=list)
    confidence: float = 0.5
    language_detected: str = "en"
