"""Comprehensive tests for Knowledge Concepts extensions."""

from __future__ import annotations

import pytest

from ayeneh.knowledge_concepts.engine import (
    ConceptDiscoveryEngine,
    ConceptExtractionEngine,
    RuleBasedConceptDiscovery,
)
from ayeneh.knowledge_concepts.types import (
    AmbiguityRecord,
    ConceptConfidence,
    ConceptProvenance,
    DiscoveredConcept,
    ExtractionResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def extraction_engine() -> ConceptExtractionEngine:
    return ConceptExtractionEngine()


@pytest.fixture
def discovery_engine() -> RuleBasedConceptDiscovery:
    return RuleBasedConceptDiscovery()


@pytest.fixture
def provenance() -> ConceptProvenance:
    return ConceptProvenance(
        book_id="book1",
        chapter_id="ch1",
        chunk_id="chunk1",
        language="en",
    )


# ---------------------------------------------------------------------------
# Concept Discovery tests
# ---------------------------------------------------------------------------


class TestConceptDiscovery:
    def test_discovers_abstractions(self, discovery_engine: RuleBasedConceptDiscovery) -> None:
        concepts = discovery_engine.discover(
            "Mindfulness and awarenessness are important for practice",
            ConceptProvenance(),
        )
        assert len(concepts) > 0
        assert any("ness" in c.normalized.lower() for c in concepts)

    def test_discovers_philosophical_constructs(
        self, discovery_engine: RuleBasedConceptDiscovery,
    ) -> None:
        concepts = discovery_engine.discover(
            "The relationship between mind and body is complex",
            ConceptProvenance(),
        )
        assert len(concepts) > 0

    def test_discovers_contemplative_practices(
        self, discovery_engine: RuleBasedConceptDiscovery,
    ) -> None:
        concepts = discovery_engine.discover(
            "The practice of meditation leads to awareness",
            ConceptProvenance(),
        )
        assert len(concepts) > 0

    def test_discovers_causal_mechanisms(
        self, discovery_engine: RuleBasedConceptDiscovery,
    ) -> None:
        concepts = discovery_engine.discover(
            "Regular practice causes increased awareness",
            ConceptProvenance(),
        )
        assert len(concepts) > 0

    def test_deduplicates_concepts(
        self, discovery_engine: RuleBasedConceptDiscovery,
    ) -> None:
        concepts = discovery_engine.discover(
            "awareness and awarenessness are related",
            ConceptProvenance(),
        )
        # Should deduplicate similar concepts
        normalized = [c.normalized.lower() for c in concepts]
        assert len(normalized) == len(set(normalized))

    def test_discovered_concept_has_provenance(
        self, discovery_engine: RuleBasedConceptDiscovery,
        provenance: ConceptProvenance,
    ) -> None:
        concepts = discovery_engine.discover("meditation practice", provenance)
        for concept in concepts:
            assert len(concept.provenance) > 0
            assert concept.provenance[0].book_id == "book1"

    def test_discovered_concept_has_confidence(
        self, discovery_engine: RuleBasedConceptDiscovery,
    ) -> None:
        concepts = discovery_engine.discover("meditation practice", ConceptProvenance())
        for concept in concepts:
            assert concept.confidence.extraction_confidence > 0
            assert concept.confidence.overall_confidence > 0


# ---------------------------------------------------------------------------
# Ambiguity Detection tests
# ---------------------------------------------------------------------------


class TestAmbiguityDetection:
    def test_finds_ambiguous_pairs(
        self, discovery_engine: RuleBasedConceptDiscovery,
    ) -> None:
        concepts = [
            DiscoveredConcept(normalized="Meditation Practice", confidence=ConceptConfidence()),
            DiscoveredConcept(normalized="Meditation Exercise", confidence=ConceptConfidence()),
            DiscoveredConcept(normalized="Completely Different", confidence=ConceptConfidence()),
        ]
        ambiguities = discovery_engine.find_ambiguities(concepts)
        assert len(ambiguities) > 0
        assert any(
            a.concept_a == "Meditation Practice" and a.concept_b == "Meditation Exercise"
            for a in ambiguities
        )

    def test_no_ambiguity_for_distinct_concepts(
        self, discovery_engine: RuleBasedConceptDiscovery,
    ) -> None:
        concepts = [
            DiscoveredConcept(normalized="Meditation", confidence=ConceptConfidence()),
            DiscoveredConcept(normalized="Completely Different Topic", confidence=ConceptConfidence()),
        ]
        ambiguities = discovery_engine.find_ambiguities(concepts)
        assert len(ambiguities) == 0

    def test_ambiguity_has_provenance(
        self, discovery_engine: RuleBasedConceptDiscovery,
        provenance: ConceptProvenance,
    ) -> None:
        concepts = [
            DiscoveredConcept(normalized="Meditation Practice", provenance=[provenance]),
            DiscoveredConcept(normalized="Meditation Exercise", provenance=[provenance]),
        ]
        ambiguities = discovery_engine.find_ambiguities(concepts)
        assert len(ambiguities) > 0
        assert len(ambiguities[0].provenance) > 0


# ---------------------------------------------------------------------------
# Concept Confidence tests
# ---------------------------------------------------------------------------


class TestConceptConfidence:
    def test_confidence_has_all_fields(self) -> None:
        conf = ConceptConfidence(
            extraction_confidence=0.8,
            normalization_confidence=0.9,
            graph_support_confidence=0.7,
            epistemic_support_confidence=0.6,
        )
        assert conf.extraction_confidence == 0.8
        assert conf.normalization_confidence == 0.9
        assert conf.graph_support_confidence == 0.7
        assert conf.epistemic_support_confidence == 0.6

    def test_confidence_defaults(self) -> None:
        conf = ConceptConfidence()
        assert conf.extraction_confidence == 0.5
        assert conf.overall_confidence == 0.5


# ---------------------------------------------------------------------------
# Discovered Concept tests
# ---------------------------------------------------------------------------


class TestDiscoveredConcept:
    def test_discovered_concept_fields(self) -> None:
        concept = DiscoveredConcept(
            text="meditation practice",
            normalized="Meditation Practice",
            confidence=ConceptConfidence(extraction_confidence=0.8),
            discovery_method="contemplative",
        )
        assert concept.text == "meditation practice"
        assert concept.normalized == "Meditation Practice"
        assert concept.confidence.extraction_confidence == 0.8
        assert concept.discovery_method == "contemplative"


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_existing_engine_still_works(self, extraction_engine: ConceptExtractionEngine) -> None:
        result = extraction_engine.extract_from_text("Test text")
        assert isinstance(result, ExtractionResult)

    def test_discovery_engine_independent(
        self, discovery_engine: RuleBasedConceptDiscovery,
    ) -> None:
        concepts = discovery_engine.discover("Test text", ConceptProvenance())
        assert isinstance(concepts, list)


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    def test_discovery_completes_quickly(
        self, discovery_engine: RuleBasedConceptDiscovery,
    ) -> None:
        import time
        start = time.monotonic()
        for _ in range(100):
            discovery_engine.discover(
                "Meditation and awareness practice leads to increased consciousness",
                ConceptProvenance(),
            )
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 1000
