"""Comprehensive tests for the Knowledge Concepts module."""

from __future__ import annotations

import pytest

from ayeneh.knowledge_concepts.engine import ConceptExtractionEngine
from ayeneh.knowledge_concepts.types import (
    CanonicalConcept,
    ConceptNode,
    ConceptProvenance,
    ExtractionResult,
    NormalizedConcept,
    TopicNode,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> ConceptExtractionEngine:
    return ConceptExtractionEngine()


# ---------------------------------------------------------------------------
# Concept Extraction tests
# ---------------------------------------------------------------------------


class TestConceptExtraction:
    def test_extracts_concepts_from_english(self, engine: ConceptExtractionEngine) -> None:
        result = engine.extract_from_text(
            "Mindfulness and awareness are key to meditation practice.",
            language="en",
        )
        assert len(result.concepts) > 0
        assert any("mindfulness" in c.lower() or "awareness" in c.lower() for c in result.concepts)

    def test_extracts_concepts_from_persian(self, engine: ConceptExtractionEngine) -> None:
        result = engine.extract_from_text(
            "ذکر و مراقبه در عرفان اهمیت دارد",
            language="fa",
        )
        assert len(result.concepts) > 0

    def test_extracts_concepts_from_arabic(self, engine: ConceptExtractionEngine) -> None:
        result = engine.extract_from_text(
            "الذكر والتأمل مهمان في الصوفية",
            language="ar",
        )
        assert len(result.concepts) > 0

    def test_extracts_concepts_from_spanish(self, engine: ConceptExtractionEngine) -> None:
        result = engine.extract_from_text(
            "La meditación y la atención plena son importantes",
            language="es",
        )
        assert len(result.concepts) > 0

    def test_ignores_stop_words(self, engine: ConceptExtractionEngine) -> None:
        result = engine.extract_from_text(
            "The is a the test of the system",
            language="en",
        )
        # Stop words should be filtered
        assert "the" not in [c.lower() for c in result.concepts]
        assert "is" not in [c.lower() for c in result.concepts]

    def test_extracts_self_concept(self, engine: ConceptExtractionEngine) -> None:
        result = engine.extract_from_text(
            "The concept of self and identity is fundamental",
            language="en",
        )
        assert any("self" in c.lower() for c in result.concepts)

    def test_extracts_acceptance_concept(self, engine: ConceptExtractionEngine) -> None:
        result = engine.extract_from_text(
            "Acceptance and non-attachment are key practices",
            language="en",
        )
        assert any("acceptance" in c.lower() for c in result.concepts)


# ---------------------------------------------------------------------------
# Concept Normalization tests
# ---------------------------------------------------------------------------


class TestConceptNormalization:
    def test_normalize_self_variants(self, engine: ConceptExtractionEngine) -> None:
        normalized = engine.normalize_concepts(["Self", "Sense of Self", "Identity", "Selfhood"])
        assert all(n.canonical == "Self" for n in normalized)

    def test_normalize_mindfulness_variants(self, engine: ConceptExtractionEngine) -> None:
        normalized = engine.normalize_concepts(["Mindfulness", "Sati", "Present Awareness"])
        assert all(n.canonical == "Mindfulness" for n in normalized)

    def test_normalize_unknown_concept(self, engine: ConceptExtractionEngine) -> None:
        normalized = engine.normalize_concepts(["UnknownConcept"])
        assert normalized[0].canonical == "Unknownconcept"

    def test_normalization_confidence(self, engine: ConceptExtractionEngine) -> None:
        normalized = engine.normalize_concepts(["Self", "Unknown"])
        assert normalized[0].confidence >= normalized[1].confidence


# ---------------------------------------------------------------------------
# Topic Extraction tests
# ---------------------------------------------------------------------------


class TestTopicExtraction:
    def test_groups_concepts_into_topics(self, engine: ConceptExtractionEngine) -> None:
        result = engine.extract_from_text(
            "Attention, mindfulness, and awareness are related practices",
            language="en",
        )
        assert len(result.topics) > 0

    def test_single_concept_no_topic(self, engine: ConceptExtractionEngine) -> None:
        result = engine.extract_from_text(
            "Just one concept here",
            language="en",
        )
        # Single concepts may or may not form topics
        assert isinstance(result.topics, list)


# ---------------------------------------------------------------------------
# Concept Node tests
# ---------------------------------------------------------------------------


class TestConceptNode:
    def test_create_concept_node(self, engine: ConceptExtractionEngine) -> None:
        provenance = ConceptProvenance(
            book_id="book1",
            chapter_id="ch1",
            chunk_id="chunk1",
        )
        node = engine.create_concept_node("mindfulness", provenance, ["sati", "awareness"])
        assert node.canonical_name == "mindfulness"
        assert "sati" in node.aliases
        assert len(node.provenance) == 1

    def test_concept_node_has_confidence(self, engine: ConceptExtractionEngine) -> None:
        provenance = ConceptProvenance()
        node = engine.create_concept_node("test", provenance)
        assert 0.0 <= node.extraction_confidence <= 1.0
        assert 0.0 <= node.normalization_confidence <= 1.0
        assert 0.0 <= node.graph_confidence <= 1.0


# ---------------------------------------------------------------------------
# Topic Node tests
# ---------------------------------------------------------------------------


class TestTopicNode:
    def test_create_topic_node(self, engine: ConceptExtractionEngine) -> None:
        provenance = ConceptProvenance(book_id="book1")
        node = engine.create_topic_node(
            "Attention Practice",
            ["concept1", "concept2"],
            provenance,
        )
        assert node.name == "Attention Practice"
        assert len(node.concept_ids) == 2


# ---------------------------------------------------------------------------
# Extraction Result tests
# ---------------------------------------------------------------------------


class TestExtractionResult:
    def test_result_has_required_fields(self) -> None:
        result = ExtractionResult(
            chunk_id="chunk1",
            concepts=["mindfulness", "awareness"],
            topics=["meditation"],
            confidence=0.7,
            language_detected="en",
        )
        assert result.chunk_id == "chunk1"
        assert len(result.concepts) == 2
        assert result.confidence == 0.7


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_engine_works_without_llm(self) -> None:
        engine = ConceptExtractionEngine()
        result = engine.extract_from_text("Test text with concepts", language="en")
        assert isinstance(result, ExtractionResult)

    def test_provenance_has_required_fields(self) -> None:
        prov = ConceptProvenance(
            book_id="book1",
            chapter_id="ch1",
            chunk_id="chunk1",
            language="en",
        )
        assert prov.book_id == "book1"
        assert prov.language == "en"


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    def test_extraction_completes_quickly(self, engine: ConceptExtractionEngine) -> None:
        import time
        start = time.monotonic()
        for _ in range(100):
            engine.extract_from_text(
                "Mindfulness and awareness are key concepts in meditation practice",
                language="en",
            )
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 1000  # 100 extractions in under 1 second
