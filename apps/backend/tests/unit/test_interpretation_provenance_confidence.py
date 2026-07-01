"""Tests for Interpretation Layer: provenance and decomposed confidence."""

from __future__ import annotations

import pytest

from ayeneh.knowledge_interpretation.engine import InterpretationGenerator
from ayeneh.knowledge_interpretation.types import (
    ConfidenceBreakdown,
    Interpretation,
    InterpretationContext,
    Provenance,
    SourceReference,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def generator() -> InterpretationGenerator:
    return InterpretationGenerator()


@pytest.fixture
def meditation_context() -> InterpretationContext:
    return InterpretationContext(
        document_id="doc1",
        book_id="book1",
        chapter_id="ch1",
        chapter_title="Meditation Practice",
        chunk_id="chunk1",
        chunk_content="Meditation is a contemplative practice for inner peace. Through meditation, practitioners develop mindfulness and awareness.",
    )


@pytest.fixture
def graph_context() -> InterpretationContext:
    return InterpretationContext(
        document_id="doc2",
        book_id="book2",
        chapter_id="ch2",
        chapter_title="Cross-Tradition",
        chunk_id="chunk2",
        chunk_content="This practice shares similarities with Zen and Sufi traditions.",
        knowledge_graph_context={
            "shared_concepts": ["mindfulness", "presence"],
            "alternative_traditions": ["Zen", "Sufism"],
            "supporting_books": ["Book A", "Book B"],
            "graph_confidence": 0.8,
        },
    )


# ---------------------------------------------------------------------------
# Provenance tests
# ---------------------------------------------------------------------------


class TestProvenance:
    def test_interpretation_has_provenance(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        assert len(interp.provenance) > 0

    def test_provenance_has_source_references(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        for p in interp.provenance:
            assert p.book_id == "book1"
            assert p.chapter_id == "ch1"
            assert p.chunk_id == "chunk1"

    def test_provenance_has_engine_metadata(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        for p in interp.provenance:
            assert p.engine_version == "1.0.0"
            assert p.generator == "rule_based"

    def test_provenance_has_reasoning_steps(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        steps = [p.reasoning_step for p in interp.provenance]
        assert "practical_insight_generation" in steps
        assert "conceptual_meaning_generation" in steps

    def test_provenance_has_confidence_contributions(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        for p in interp.provenance:
            assert 0.0 <= p.confidence_contribution <= 1.0
            assert len(p.confidence_reason) > 0

    def test_graph_provenance_when_available(
        self, generator: InterpretationGenerator,
        graph_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(graph_context)
        graph_provenance = [p for p in interp.provenance if p.generator == "graph_enhanced"]
        assert len(graph_provenance) > 0

    def test_no_graph_provenance_when_unavailable(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        graph_provenance = [p for p in interp.provenance if p.generator == "graph_enhanced"]
        assert len(graph_provenance) == 0


# ---------------------------------------------------------------------------
# Confidence Breakdown tests
# ---------------------------------------------------------------------------


class TestConfidenceBreakdown:
    def test_interpretation_has_confidence_breakdown(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        assert interp.confidence_breakdown is not None

    def test_breakdown_has_all_components(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        bd = interp.confidence_breakdown
        assert 0.0 <= bd.source_confidence <= 1.0
        assert 0.0 <= bd.interpretation_confidence <= 1.0
        assert 0.0 <= bd.graph_confidence <= 1.0
        assert 0.0 <= bd.cross_tradition_confidence <= 1.0
        assert 0.0 <= bd.mapping_confidence <= 1.0
        assert 0.0 <= bd.evidence_confidence <= 1.0
        assert 0.0 <= bd.overall_confidence <= 1.0

    def test_overall_matches_confidence(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        assert interp.confidence == interp.confidence_breakdown.overall_confidence

    def test_low_source_caps_overall(self) -> None:
        bd = ConfidenceBreakdown(
            source_confidence=0.2,
            interpretation_confidence=0.9,
            graph_confidence=0.9,
            cross_tradition_confidence=0.9,
            mapping_confidence=0.9,
            evidence_confidence=0.9,
        )
        overall = bd.compute_overall()
        # Low source should cap overall
        assert overall < 0.5

    def test_graph_cannot_compensate_weak_source(self) -> None:
        bd_weak = ConfidenceBreakdown(
            source_confidence=0.3,
            graph_confidence=0.9,
        )
        bd_strong = ConfidenceBreakdown(
            source_confidence=0.7,
            graph_confidence=0.9,
        )
        weak_overall = bd_weak.compute_overall()
        strong_overall = bd_strong.compute_overall()
        # Weak source should produce lower overall even with strong graph
        assert weak_overall < strong_overall

    def test_cross_tradition_stays_conservative(self) -> None:
        bd = ConfidenceBreakdown(
            cross_tradition_confidence=0.95,
        )
        overall = bd.compute_overall()
        # Cross-tradition contribution should be capped in calculation
        # The overall should reflect this cap
        assert overall <= 0.7  # Cross-tradition capped at 0.7 with weight 0.1

    def test_weighted_aggregation(self) -> None:
        bd = ConfidenceBreakdown(
            source_confidence=0.8,
            interpretation_confidence=0.7,
            graph_confidence=0.6,
            cross_tradition_confidence=0.5,
            mapping_confidence=0.7,
            evidence_confidence=0.6,
        )
        overall = bd.compute_overall()
        assert 0.0 <= overall <= 1.0

    def test_breakdown_weights_stored(self) -> None:
        bd = ConfidenceBreakdown()
        bd.compute_overall()
        assert "source" in bd.weight_used
        assert "interpretation" in bd.weight_used


# ---------------------------------------------------------------------------
# Reasoning Rules tests
# ---------------------------------------------------------------------------


class TestReasoningRules:
    def test_low_source_never_high_overall(self) -> None:
        """Low source confidence must never produce high overall confidence."""
        bd = ConfidenceBreakdown(
            source_confidence=0.1,
            interpretation_confidence=0.9,
            graph_confidence=0.9,
            evidence_confidence=0.9,
        )
        overall = bd.compute_overall()
        assert overall < 0.5

    def test_strong_graph_cannot_compensate_weak_source(self) -> None:
        """Strong graph support cannot compensate for weak source grounding."""
        bd = ConfidenceBreakdown(
            source_confidence=0.2,
            graph_confidence=1.0,
        )
        overall = bd.compute_overall()
        # Even with perfect graph, weak source limits overall
        assert overall < 0.4

    def test_cross_tradition_remains_conservative(self) -> None:
        """Cross-tradition mappings must remain conservative."""
        bd = ConfidenceBreakdown(
            cross_tradition_confidence=0.95,
        )
        overall = bd.compute_overall()
        # Cross-tradition contribution is capped at 0.7 in calculation
        # Overall should reflect this cap
        assert overall <= 0.7


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_provenance_and_breakdown_together(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        assert len(interp.provenance) > 0
        assert interp.confidence_breakdown is not None
        assert interp.confidence == interp.confidence_breakdown.overall_confidence

    def test_graph_enhances_both(
        self, generator: InterpretationGenerator,
        graph_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(graph_context)
        # Graph should add provenance
        assert len(interp.provenance) > 3
        # Graph should affect confidence breakdown
        assert interp.confidence_breakdown.graph_confidence > 0.3


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_existing_interpretation_still_works(self) -> None:
        interp = Interpretation(
            source=SourceReference(document_id="doc1", original_text="text"),
            practical_insight="test",
        )
        assert interp.practical_insight == "test"
        assert interp.confidence == 0.5
        # New fields have defaults
        assert interp.provenance == []
        assert interp.confidence_breakdown is None

    def test_provenance_is_optional(self) -> None:
        interp = Interpretation()
        assert interp.provenance == []

    def test_breakdown_is_optional(self) -> None:
        interp = Interpretation()
        assert interp.confidence_breakdown is None
