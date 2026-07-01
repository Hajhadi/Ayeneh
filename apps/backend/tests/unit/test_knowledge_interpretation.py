"""Comprehensive tests for the Knowledge Interpretation Layer."""

from __future__ import annotations

import uuid

import pytest

from ayeneh.knowledge_interpretation.engine import (
    InterpretationEngine,
    InterpretationGenerator,
    InterpretationValidator,
)
from ayeneh.knowledge_interpretation.types import (
    ConfidenceLevel,
    CrossTraditionMapping,
    Interpretation,
    InterpretationContext,
    InterpretationMetadata,
    InterpretationVersion,
    ModernMapping,
    SourceReference,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> InterpretationEngine:
    return InterpretationEngine()


@pytest.fixture
def generator() -> InterpretationGenerator:
    return InterpretationGenerator()


@pytest.fixture
def validator() -> InterpretationValidator:
    return InterpretationValidator()


@pytest.fixture
def meditation_context() -> InterpretationContext:
    return InterpretationContext(
        document_id="doc1",
        book_id="book1",
        chapter_id="ch1",
        chapter_title="Meditation Practice",
        chunk_id="chunk1",
        chunk_content="Meditation is a contemplative practice for inner peace. Through meditation, practitioners develop mindfulness and awareness. The practice involves repeated attentional focus.",
        epistemic_profile={"tradition": "Zen Buddhism", "domain": "spirituality"},
    )


@pytest.fixture
def philosophy_context() -> InterpretationContext:
    return InterpretationContext(
        document_id="doc2",
        book_id="book2",
        chapter_id="ch2",
        chapter_title="Truth and Reality",
        chunk_id="chunk2",
        chunk_content="Truth is a fundamental concept in philosophy. Philosophers have debated the nature of truth for centuries. The correspondence theory suggests truth matches reality.",
        epistemic_profile={"tradition": "Analytical Philosophy", "domain": "philosophy"},
    )


@pytest.fixture
def act_context() -> InterpretationContext:
    return InterpretationContext(
        document_id="doc3",
        book_id="book3",
        chapter_id="ch3",
        chapter_title="Acceptance",
        chunk_id="chunk3",
        chunk_content="Acceptance means allowing difficult experiences to be present without trying to change them. This acceptance creates space for new possibilities.",
        epistemic_profile={"tradition": "ACT", "domain": "psychology"},
    )


# ---------------------------------------------------------------------------
# Generator tests
# ---------------------------------------------------------------------------


class TestInterpretationGenerator:
    def test_generates_interpretation(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        assert isinstance(interp, Interpretation)
        assert interp.source.chunk_id == "chunk1"

    def test_has_practical_insight(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        assert len(interp.practical_insight) > 0

    def test_has_conceptual_meaning(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        assert len(interp.conceptual_meaning) > 0

    def test_has_modern_translation(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        assert len(interp.modern_translation) > 0

    def test_has_framework_interpretations(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        # At least one framework should have an interpretation
        has_interpretation = any([
            interp.psychological_interpretation,
            interp.neuroscience_interpretation,
            interp.act_interpretation,
            interp.analytical_philosophy_interpretation,
            interp.zen_interpretation,
            interp.khorasan_mysticism_interpretation,
        ])
        assert has_interpretation

    def test_has_alternatives(
        self, generator: InterpretationGenerator,
        philosophy_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(philosophy_context)
        assert len(interp.alternative_interpretations) > 0

    def test_has_limitations(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        assert len(interp.limitations) > 0

    def test_has_uncertainties(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        assert len(interp.uncertainties) > 0

    def test_confidence_in_range(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        assert 0.0 <= interp.confidence <= 1.0

    def test_source_reference_populated(
        self, generator: InterpretationGenerator,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = generator.generate(meditation_context)
        assert interp.source.document_id == "doc1"
        assert interp.source.chunk_id == "chunk1"
        assert len(interp.source.original_text) > 0


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------


class TestInterpretationValidator:
    def test_valid_interpretation_passes(
        self, validator: InterpretationValidator,
        philosophy_context: InterpretationContext,
    ) -> None:
        generator = InterpretationGenerator()
        interp = generator.generate(philosophy_context)
        errors = validator.validate(interp)
        assert len(errors) == 0

    def test_missing_source_reference_fails(
        self, validator: InterpretationValidator,
    ) -> None:
        interp = Interpretation(
            source=SourceReference(),
            limitations=["test"],
            uncertainties=["test"],
            alternative_interpretations=["test"],
        )
        errors = validator.validate(interp)
        assert any("document_id" in e for e in errors)

    def test_missing_limitations_fails(
        self, validator: InterpretationValidator,
    ) -> None:
        interp = Interpretation(
            source=SourceReference(document_id="doc1", original_text="text"),
            limitations=[],
            uncertainties=["test"],
            alternative_interpretations=["test"],
        )
        errors = validator.validate(interp)
        assert any("Limitations" in e for e in errors)

    def test_certainty_language_fails(
        self, validator: InterpretationValidator,
    ) -> None:
        interp = Interpretation(
            source=SourceReference(document_id="doc1", original_text="text"),
            limitations=["test"],
            uncertainties=["test"],
            alternative_interpretations=["test"],
            modern_mappings=[ModernMapping(language="is")],
        )
        errors = validator.validate(interp)
        assert any("certainty" in e for e in errors)


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestInterpretationEngine:
    @pytest.mark.asyncio
    async def test_generate_interpretation(
        self, engine: InterpretationEngine,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = await engine.generate_interpretation(meditation_context)
        assert isinstance(interp, Interpretation)
        assert interp.id is not None

    @pytest.mark.asyncio
    async def test_generate_with_confidence(
        self, engine: InterpretationEngine,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = await engine.generate_interpretation(meditation_context)
        assert 0.0 <= interp.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_generate_with_metadata(
        self, engine: InterpretationEngine,
        meditation_context: InterpretationContext,
    ) -> None:
        interp = await engine.generate_interpretation(meditation_context)
        assert interp.generator == "rule_based"
        assert interp.generation_version == "1.0.0"


# ---------------------------------------------------------------------------
# Framework-specific tests
# ---------------------------------------------------------------------------


class TestFrameworkInterpretations:
    def test_meditation_generates_zen_interpretation(
        self, generator: InterpretationGenerator,
    ) -> None:
        context = InterpretationContext(
            chunk_content="Meditation and contemplation practice for inner peace.",
        )
        interp = generator.generate(context)
        assert len(interp.zen_interpretation) > 0

    def test_acceptance_generates_act_interpretation(
        self, generator: InterpretationGenerator,
    ) -> None:
        context = InterpretationContext(
            chunk_content="Acceptance of difficult experiences without trying to change them.",
        )
        interp = generator.generate(context)
        assert len(interp.act_interpretation) > 0

    def test_truth_generates_analytical_interpretation(
        self, generator: InterpretationGenerator,
    ) -> None:
        context = InterpretationContext(
            chunk_content="Truth and reality are fundamental philosophical concepts.",
        )
        interp = generator.generate(context)
        assert len(interp.analytical_philosophy_interpretation) > 0


# ---------------------------------------------------------------------------
# Modern mapping tests
# ---------------------------------------------------------------------------


class TestModernMappings:
    def test_attention_generates_neuroscience_mapping(
        self, generator: InterpretationGenerator,
    ) -> None:
        context = InterpretationContext(
            chunk_content="Attention and focus are key cognitive processes.",
        )
        interp = generator.generate(context)
        neuro_mappings = [m for m in interp.modern_mappings if m.framework == "Cognitive Science"]
        assert len(neuro_mappings) > 0

    def test_acceptance_generates_act_mapping(
        self, generator: InterpretationGenerator,
    ) -> None:
        context = InterpretationContext(
            chunk_content="Acceptance and allowing difficult experiences.",
        )
        interp = generator.generate(context)
        act_mappings = [m for m in interp.modern_mappings if m.framework == "ACT"]
        assert len(act_mappings) > 0

    def test_mappings_use_hedging_language(
        self, generator: InterpretationGenerator,
    ) -> None:
        context = InterpretationContext(
            chunk_content="Meditation and contemplation practice.",
        )
        interp = generator.generate(context)
        for mapping in interp.modern_mappings:
            assert mapping.language in ("may resemble", "can be interpreted as", "shares similarities with")


# ---------------------------------------------------------------------------
# Cross-tradition mapping tests
# ---------------------------------------------------------------------------


class TestCrossTraditionMappings:
    def test_meditation_generates_cross_tradition_mapping(
        self, generator: InterpretationGenerator,
    ) -> None:
        context = InterpretationContext(
            chunk_content="Meditation practice for awareness.",
            epistemic_profile={"tradition": "Sufism"},
        )
        interp = generator.generate(context)
        assert len(interp.cross_tradition_mappings) > 0

    def test_mappings_use_hedging_language(
        self, generator: InterpretationGenerator,
    ) -> None:
        context = InterpretationContext(
            chunk_content="Contemplative practice.",
            epistemic_profile={"tradition": "Zen"},
        )
        interp = generator.generate(context)
        for mapping in interp.cross_tradition_mappings:
            assert mapping.language in ("shares similarities with", "may partially overlap")


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_content(
        self, generator: InterpretationGenerator,
    ) -> None:
        context = InterpretationContext(chunk_content="")
        interp = generator.generate(context)
        assert isinstance(interp, Interpretation)

    def test_short_content(
        self, generator: InterpretationGenerator,
    ) -> None:
        context = InterpretationContext(chunk_content="Short text.")
        interp = generator.generate(context)
        assert isinstance(interp, Interpretation)

    def test_long_content(
        self, generator: InterpretationGenerator,
    ) -> None:
        context = InterpretationContext(
            chunk_content="This is a very long text about meditation and contemplation. " * 100,
        )
        interp = generator.generate(context)
        assert isinstance(interp, Interpretation)


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_interpretation_has_required_fields(
        self, engine: InterpretationEngine,
        meditation_context: InterpretationContext,
    ) -> None:
        import asyncio
        interp = asyncio.run(engine.generate_interpretation(meditation_context))
        assert hasattr(interp, "id")
        assert hasattr(interp, "source")
        assert hasattr(interp, "confidence")
        assert hasattr(interp, "version")


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    def test_generation_completes_quickly(
        self, generator: InterpretationGenerator,
    ) -> None:
        import time
        context = InterpretationContext(
            chunk_content="Test content about meditation and philosophy.",
        )
        start = time.monotonic()
        for _ in range(100):
            generator.generate(context)
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 1000  # 100 generations in under 1 second
