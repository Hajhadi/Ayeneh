"""Concept Extraction Engine — single owner of concept extraction and normalization.

Refactored to use a pipeline architecture with independent stages.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
import structlog
from typing import Any, Protocol, runtime_checkable

from ayeneh.knowledge_concepts.types import (
    AmbiguityRecord,
    CandidateEvidence,
    CandidateWithEvidence,
    CanonicalConcept,
    ConceptConfidence,
    ConceptNode,
    ConceptProvenance,
    DiscoveredConcept,
    EvidenceReference,
    ExtractionResult,
    NormalizedConcept,
    TopicNode,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Protocol for concept discovery engines
# ---------------------------------------------------------------------------


@runtime_checkable
class ConceptDiscoveryEngine(Protocol):
    """Protocol for concept discovery engines.

    Implementations must discover concepts that are NOT present
    in predefined dictionaries.
    """

    def discover(
        self,
        text: str,
        provenance: ConceptProvenance,
    ) -> list[DiscoveredConcept]:
        """Discover concepts from text."""
        ...

    def find_ambiguities(
        self,
        concepts: list[DiscoveredConcept],
    ) -> list[AmbiguityRecord]:
        """Find ambiguous concept pairs that cannot be confidently merged."""
        ...


# ---------------------------------------------------------------------------
# Pipeline Stages
# ---------------------------------------------------------------------------


class CandidateGenerator:
    """Stage 1: Generate concept candidates from multiple signals.

    Every generated candidate carries its evidence from the beginning.
    """

    # Multilingual concept dictionaries
    DICTIONARY_CONCEPTS: dict[str, list[str]] = {
        "fa": ["خود", "هویت", "آگاهی", "حضور", "شهود", "فنا", "توبه", "صبر", "توکل", "معرفت", "ذکر", "تمرین", "مراقبه"],
        "ar": ["النفس", "الذات", "الوعي", "الحضور", "الشهود", "الفنا", "التوبة", "الصبر", "التوكل", "المعرفة", "الذكر", "التأمل"],
        "es": ["self", "ego", "identidad", "conciencia", "atención", "mindfulness", "aceptación", "compasión", "sufrimiento", "presencia", "meditación"],
    }

    # English concept patterns
    EN_PATTERNS = [
        r"\b(self|ego|identity|consciousness|awareness|attention|mindfulness)\b",
        r"\b(acceptance|non-attachment|compassion|suffering|presence)\b",
        r"\b(prediction|volition|cognition|perception|emotion)\b",
        r"\b(cognitive fusion|defusion|experiential avoidance)\b",
        r"\b(meditation|contemplation|contemplative practice)\b",
        r"\b(freewill|determinism|causation|emergence)\b",
    ]

    # Philosophical construct patterns
    PHILOSOPHICAL_PATTERNS = [
        r"\b(the\s+\w+\s+of\s+\w+)\b",
        r"\b(\w+\s+and\s+\w+\s+are\s+related)\b",
        r"(relationship\s+between\s+\w+\s+and\s+\w+)",
    ]

    def generate(
        self,
        text: str,
        language: str = "en",
        chunk_id: str = "",
        book_id: str = "",
    ) -> list[CandidateWithEvidence]:
        """Generate candidate concepts with evidence."""
        candidates: list[CandidateWithEvidence] = []
        text_lower = text.lower()

        # Track occurrences
        occurrence_counts: dict[str, int] = {}

        # Add dictionary concepts
        dict_concepts = self.DICTIONARY_CONCEPTS.get(language, [])
        for concept in dict_concepts:
            if concept not in occurrence_counts:
                occurrence_counts[concept] = 0
            occurrence_counts[concept] += 1

        # Add English patterns
        for pattern in self.EN_PATTERNS:
            for match in re.findall(pattern, text_lower):
                if match not in occurrence_counts:
                    occurrence_counts[match] = 0
                occurrence_counts[match] += 1

        # Add philosophical patterns
        for pattern in self.PHILOSOPHICAL_PATTERNS:
            for match in re.findall(pattern, text_lower):
                if match not in occurrence_counts:
                    occurrence_counts[match] = 0
                occurrence_counts[match] += 1

        # Add language-specific patterns
        if language == "fa":
            fa_patterns = [r"(خود| هویت | آگاهی | حضور | شهود)", r"(فنا| توبه | صبر | توکل | معرفت)", r"(ذکر| تمرین | مراقبه | عبادت)"]
            for p in fa_patterns:
                for match in re.findall(p, text):
                    if match not in occurrence_counts:
                        occurrence_counts[match] = 0
                    occurrence_counts[match] += 1
        elif language == "ar":
            ar_patterns = [r"(النفس| الذات | الوعي | الحضور | الشهود)", r"(الفنا | التوبة | الصبر | التوكل | المعرفة)", r"(الذكر | التأمل | العبادة)"]
            for p in ar_patterns:
                for match in re.findall(p, text):
                    if match not in occurrence_counts:
                        occurrence_counts[match] = 0
                    occurrence_counts[match] += 1
        elif language == "es":
            es_patterns = [r"\b(self|ego|identidad|conciencia|atención|mindfulness)\b", r"\b(aceptación|compasión|sufrimiento|presencia)\b", r"\b(meditación|contemplación|oración)\b"]
            for p in es_patterns:
                for match in re.findall(p, text_lower):
                    if match not in occurrence_counts:
                        occurrence_counts[match] = 0
                    occurrence_counts[match] += 1

        # Create candidates with evidence
        for concept, count in occurrence_counts.items():
            # Create EvidenceReference for each occurrence
            references = []
            for _ in range(count):
                ref = EvidenceReference(
                    document_id=book_id,
                    book_id=book_id,
                    chunk_id=chunk_id,
                    language=language,
                    timestamp=str(datetime.now()),
                )
                references.append(ref)

            evidence = CandidateEvidence(
                references=references,
                occurrence_count=count,
                supporting_books=[book_id] if book_id else [],
                supporting_languages=[language],
            )
            candidates.append(CandidateWithEvidence(text=concept, evidence=evidence))

        return candidates


class CandidateFilter:
    """Stage 2: Filter weak candidates."""

    MIN_LENGTH = 3
    MAX_LENGTH = 100

    def filter(self, candidates: list[CandidateWithEvidence]) -> list[CandidateWithEvidence]:
        """Filter out weak candidates while preserving evidence."""
        filtered: list[CandidateWithEvidence] = []
        for candidate in candidates:
            if self._is_valid(candidate.text):
                filtered.append(candidate)
        return filtered

    def _is_valid(self, candidate: str) -> bool:
        """Check if a candidate is valid."""
        if not candidate:
            return False
        stripped = candidate.strip()
        if len(stripped) < self.MIN_LENGTH:
            return False
        if len(stripped) > self.MAX_LENGTH:
            return False
        # Filter punctuation-only
        if all(c in ".,;:!?-—()[]{}" for c in stripped):
            return False
        # Filter numbers only
        if stripped.isdigit():
            return False
        return True


class CandidateNormalizer:
    """Stage 3: Normalize concepts while preserving aliases and evidence."""

    NORMALIZATIONS: dict[str, str] = {
        "self": "Self",
        "sense of self": "Self",
        "identity": "Self",
        "selfhood": "Self",
        "mindfulness": "Mindfulness",
        "sati": "Mindfulness",
        "present awareness": "Mindfulness",
        "acceptance": "Acceptance",
        "non-attachment": "Non-attachment",
        "non-resistance": "Non-attachment",
        "attention": "Attention",
        "awareness": "Awareness",
        "consciousness": "Consciousness",
        "cognition": "Cognition",
        "perception": "Perception",
        "compassion": "Compassion",
        "suffering": "Suffering",
        "presence": "Presence",
        "meditation": "Meditation",
        "contemplation": "Meditation",
    }

    def normalize(self, candidates: list[CandidateWithEvidence]) -> list[NormalizedConcept]:
        """Normalize candidates while preserving evidence."""
        normalized: list[NormalizedConcept] = []
        seen: set[str] = set()

        for candidate in candidates:
            canonical = self._normalize_one(candidate.text)
            canonical_lower = canonical.lower()
            if canonical_lower not in seen:
                seen.add(canonical_lower)
                confidence = self._compute_confidence(candidate.text, canonical)
                normalized.append(NormalizedConcept(
                    original=candidate.text,
                    canonical=canonical,
                    confidence=confidence,
                    evidence=candidate.evidence,
                ))

        return normalized

    def _normalize_one(self, concept: str) -> str:
        """Normalize a single concept."""
        concept_lower = concept.lower().strip()
        if concept_lower in self.NORMALIZATIONS:
            return self.NORMALIZATIONS[concept_lower]
        return concept.title()

    def _compute_confidence(self, original: str, canonical: str) -> float:
        """Compute normalization confidence."""
        if original.lower() == canonical.lower():
            return 1.0
        if canonical.lower() in original.lower():
            return 0.9
        if original.lower() in canonical.lower():
            return 0.8
        return 0.6


class EpistemicRule:
    """A validation rule for epistemic validation."""

    def __init__(
        self,
        rule_id: str,
        description: str,
        severity: str = "warning",
        enabled: bool = True,
    ) -> None:
        self.rule_id = rule_id
        self.description = description
        self.severity = severity
        self.enabled = enabled

    def validate(self, concept: str) -> tuple[bool, str]:
        """Validate a concept. Returns (is_valid, reason)."""
        return True, ""


class PageNumberRule(EpistemicRule):
    """Reject page numbers."""

    def __init__(self) -> None:
        super().__init__("page_number", "Rejects page numbers", "error")

    def validate(self, concept: str) -> tuple[bool, str]:
        if re.match(r"^\d+$", concept.strip()):
            return False, "Page number"
        return True, ""


class HeaderRule(EpistemicRule):
    """Reject document headers."""

    def __init__(self) -> None:
        super().__init__("header", "Rejects document headers", "warning")

    def validate(self, concept: str) -> tuple[bool, str]:
        if re.match(r"^(page|chapter|section|part)\s+\d+$", concept.strip()):
            return False, "Document header"
        return True, ""


class ReferenceRule(EpistemicRule):
    """Reject reference markers."""

    def __init__(self) -> None:
        super().__init__("reference", "Rejects reference markers", "warning")

    def validate(self, concept: str) -> tuple[bool, str]:
        if re.match(r"^(fig|table|appendix)\s+\d+$", concept.strip()):
            return False, "Reference marker"
        return True, ""


class MetadataRule(EpistemicRule):
    """Reject publisher metadata."""

    def __init__(self) -> None:
        super().__init__("metadata", "Rejects publisher metadata", "warning")

    def validate(self, concept: str) -> tuple[bool, str]:
        if re.match(r"^(copyright|publisher|isbn|doi)", concept.strip()):
            return False, "Publisher metadata"
        return True, ""


class PunctuationRule(EpistemicRule):
    """Reject punctuation-only content."""

    def __init__(self) -> None:
        super().__init__("punctuation", "Rejects punctuation-only content", "error")

    def validate(self, concept: str) -> tuple[bool, str]:
        if re.match(r"^\W+$", concept.strip()):
            return False, "Punctuation only"
        return True, ""


class EpistemicValidator:
    """Stage 4: Reject concepts that are not epistemically meaningful.

    Uses a registry of rules for validation.
    """

    def __init__(self) -> None:
        self._rules: list[EpistemicRule] = [
            PageNumberRule(),
            HeaderRule(),
            ReferenceRule(),
            MetadataRule(),
            PunctuationRule(),
        ]

    def add_rule(self, rule: EpistemicRule) -> None:
        """Add a validation rule."""
        self._rules.append(rule)

    def validate(self, concepts: list[NormalizedConcept]) -> list[NormalizedConcept]:
        """Validate and filter concepts using registered rules."""
        validated: list[NormalizedConcept] = []
        for concept in concepts:
            if self._passes_all_rules(concept.canonical):
                validated.append(concept)
        return validated

    def _passes_all_rules(self, concept: str) -> bool:
        """Check if a concept passes all enabled rules."""
        for rule in self._rules:
            if not rule.enabled:
                continue
            is_valid, _ = rule.validate(concept)
            if not is_valid:
                return False
        return True


class ConfidenceAggregator:
    """Stage 5: Compute final confidence from multiple independent evidence sources."""

    def aggregate(
        self,
        concepts: list[NormalizedConcept],
        text: str,
        supporting_chunks: int = 1,
    ) -> list[tuple[NormalizedConcept, ConceptConfidence]]:
        """Aggregate confidence for each concept."""
        results: list[tuple[NormalizedConcept, ConceptConfidence]] = []

        for concept in concepts:
            confidence = self._compute_confidence(concept, text)
            results.append((concept, confidence))

        return results

    def _compute_confidence(
        self,
        concept: NormalizedConcept,
        text: str,
    ) -> ConceptConfidence:
        """Compute confidence from multiple independent evidence sources."""
        evidence = concept.evidence

        # Extraction confidence (from normalization)
        extraction = concept.confidence

        # Normalization confidence
        normalization = concept.confidence

        # Graph support (based on references)
        graph_support = min(1.0, len(evidence.references) / 3)

        # Epistemic support (based on text quality)
        text_words = len(text.split())
        epistemic = min(1.0, text_words / 100)

        # Support frequency
        frequency = min(1.0, evidence.occurrence_count / 5)

        # Cross-book support
        cross_book = min(1.0, len(evidence.supporting_books) / 2)

        # Cross-language support
        cross_language = min(1.0, len(evidence.supporting_languages) / 2)

        # Overall confidence from all components
        overall = (
            extraction * 0.20
            + normalization * 0.15
            + graph_support * 0.15
            + epistemic * 0.15
            + frequency * 0.15
            + cross_book * 0.10
            + cross_language * 0.10
        )

        return ConceptConfidence(
            extraction_confidence=extraction,
            normalization_confidence=normalization,
            graph_support_confidence=graph_support,
            epistemic_support_confidence=epistemic,
            support_frequency=frequency,
            cross_book_support=cross_book,
            cross_language_support=cross_language,
            overall_confidence=overall,
        )


class ConceptDeduplicator:
    """Stage 6: Deduplicate concepts and produce final set."""

    def deduplicate(
        self,
        concepts: list[tuple[NormalizedConcept, ConceptConfidence]],
    ) -> list[DiscoveredConcept]:
        """Deduplicate and produce final concept set."""
        seen: dict[str, DiscoveredConcept] = {}

        for normalized, confidence in concepts:
            canonical = normalized.canonical.lower()
            if canonical in seen:
                # Merge evidence and update with better confidence
                existing = seen[canonical]
                merged_evidence = self._merge_evidence(existing.evidence, normalized.evidence)
                if confidence.overall_confidence > existing.confidence.overall_confidence:
                    seen[canonical] = DiscoveredConcept(
                        text=normalized.original,
                        normalized=normalized.canonical,
                        confidence=confidence,
                        discovery_method="deduplicated",
                        evidence=merged_evidence,
                    )
                else:
                    seen[canonical] = DiscoveredConcept(
                        text=existing.text,
                        normalized=existing.normalized,
                        confidence=existing.confidence,
                        discovery_method=existing.discovery_method,
                        evidence=merged_evidence,
                    )
            else:
                seen[canonical] = DiscoveredConcept(
                    text=normalized.original,
                    normalized=normalized.canonical,
                    confidence=confidence,
                    discovery_method="extracted",
                    evidence=normalized.evidence,
                )

        return list(seen.values())

    def _merge_evidence(
        self,
        existing: CandidateEvidence,
        new: CandidateEvidence,
    ) -> CandidateEvidence:
        """Merge evidence from two candidates, preserving all references."""
        # Merge references without duplicates
        existing_ids = {id(r) for r in existing.references}
        merged_references = list(existing.references)
        for ref in new.references:
            if id(ref) not in existing_ids:
                merged_references.append(ref)

        # Create new evidence with merged references
        merged = CandidateEvidence(references=merged_references)
        return merged


# ---------------------------------------------------------------------------
# Rule-Based Concept Discovery (Pipeline Composition)
# ---------------------------------------------------------------------------


class RuleBasedConceptDiscovery:
    """Rule-based concept discovery using a pipeline of independent stages.

    Composes:
    1. CandidateGeneration (with evidence)
    2. CandidateFiltering
    3. CandidateNormalization (preserves evidence)
    4. EpistemicValidation (registry-based)
    5. ConfidenceAggregation (multi-source)
    6. ConceptDeduplication
    """

    def __init__(self) -> None:
        self._candidate_generator = CandidateGenerator()
        self._candidate_filter = CandidateFilter()
        self._normalizer = CandidateNormalizer()
        self._validator = EpistemicValidator()
        self._confidence_aggregator = ConfidenceAggregator()
        self._deduplicator = ConceptDeduplicator()

    def discover(
        self,
        text: str,
        provenance: ConceptProvenance,
    ) -> list[DiscoveredConcept]:
        """Discover concepts from text using pipeline stages."""
        # Stage 1: Generate candidates with evidence
        language = provenance.language if provenance.language else "en"
        candidates = self._candidate_generator.generate(
            text, language,
            chunk_id=provenance.chunk_id,
            book_id=provenance.book_id,
        )

        # Stage 2: Filter weak candidates (preserves evidence)
        filtered = self._candidate_filter.filter(candidates)

        # Stage 3: Normalize (preserves evidence)
        normalized = self._normalizer.normalize(filtered)

        # Stage 4: Epistemic validation
        validated = self._validator.validate(normalized)

        # Stage 5: Confidence aggregation (uses evidence)
        with_confidence = self._confidence_aggregator.aggregate(
            validated, text,
        )

        # Stage 6: Deduplicate (preserves evidence)
        concepts = self._deduplicator.deduplicate(with_confidence)

        # Add provenance to all concepts
        for concept in concepts:
            concept.provenance = [provenance]

        return concepts

    def find_ambiguities(
        self,
        concepts: list[DiscoveredConcept],
    ) -> list[AmbiguityRecord]:
        """Find ambiguous concept pairs that cannot be confidently merged."""
        ambiguities: list[AmbiguityRecord] = []

        for i, c1 in enumerate(concepts):
            for c2 in concepts[i + 1:]:
                similarity = self._compute_similarity(c1.normalized, c2.normalized)
                if 0.3 <= similarity < 0.8:
                    ambiguities.append(AmbiguityRecord(
                        concept_a=c1.normalized,
                        concept_b=c2.normalized,
                        similarity_score=similarity,
                        reason=f"Similarity {similarity:.2f} is in ambiguous range",
                        provenance=c1.provenance + c2.provenance,
                    ))

        return ambiguities

    def _compute_similarity(self, a: str, b: str) -> float:
        """Compute simple word overlap similarity."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        return intersection / union if union > 0 else 0.0


# ---------------------------------------------------------------------------
# Legacy ConceptExtractionEngine (backward compatible)
# ---------------------------------------------------------------------------


class ConceptExtractionEngine:
    """Legacy extraction engine (backward compatible)."""

    def extract_from_text(
        self,
        text: str,
        chunk_id: str = "",
        book_id: str = "",
        chapter_id: str = "",
        language: str = "en",
    ) -> ExtractionResult:
        """Extract concepts from text."""
        discovery = RuleBasedConceptDiscovery()
        provenance = ConceptProvenance(
            book_id=book_id,
            chapter_id=chapter_id,
            chunk_id=chunk_id,
            language=language,
        )
        discovered = discovery.discover(text, provenance)
        concepts = [d.normalized for d in discovered]
        topics = self._extract_topics(concepts)
        return ExtractionResult(
            chunk_id=chunk_id,
            concepts=concepts,
            discovered_concepts=discovered,
            topics=topics,
            confidence=self._compute_confidence(concepts, text),
            language_detected=language,
        )

    def _extract_topics(self, concepts: list[str]) -> list[str]:
        """Group concepts into topics."""
        topics: list[str] = []
        if not concepts:
            return topics
        # Single concepts with multiple words become topics
        for concept in concepts:
            if len(concept.split()) >= 2:
                topics.append(concept)
        # If we have multiple concepts, they form a topic group
        if len(concepts) >= 2:
            topics.append("Related Concepts")
        return topics

    def _compute_confidence(self, concepts: list[str], text: str) -> float:
        """Compute extraction confidence."""
        if not concepts:
            return 0.0
        concept_score = min(1.0, len(concepts) / 10)
        text_score = min(1.0, len(text.split()) / 200)
        return (concept_score + text_score) / 2

    def normalize_concepts(self, concepts: list[str]) -> list[NormalizedConcept]:
        """Normalize concepts (legacy)."""
        normalizer = CandidateNormalizer()
        # Convert strings to CandidateWithEvidence for backward compatibility
        candidates = [CandidateWithEvidence(text=c) for c in concepts]
        return normalizer.normalize(candidates)

    def create_concept_node(
        self,
        canonical: str,
        provenance: ConceptProvenance,
        aliases: list[str] | None = None,
        domain: str = "",
    ) -> ConceptNode:
        """Create a concept node (legacy)."""
        return ConceptNode(
            canonical_name=canonical,
            aliases=aliases or [],
            domain=domain,
            provenance=[provenance],
            extraction_confidence=0.7,
            normalization_confidence=0.8,
            graph_confidence=0.6,
        )

    def create_topic_node(
        self,
        name: str,
        concept_ids: list[str],
        provenance: ConceptProvenance,
        domain: str = "",
    ) -> TopicNode:
        """Create a topic node (legacy)."""
        return TopicNode(
            name=name,
            concept_ids=concept_ids,
            domain=domain,
            provenance=[provenance],
            confidence=0.6,
        )
