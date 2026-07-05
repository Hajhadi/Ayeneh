"""Tests for Query Understanding Pipeline per SPEC-21."""

import pytest
from ayeneh.runtime.query_understanding import (
    QueryUnderstandingPipeline,
    LanguageAnalysis,
    IntentAnalysis,
    ConceptDiscovery,
    EntityDiscovery,
    ComplexityEstimate,
    CapabilityAnalysis,
)
from ayeneh.runtime.pipeline import QueryAnalysis


@pytest.fixture
def pipeline():
    return QueryUnderstandingPipeline()


# ---------------------------------------------------------------------------
# Phase 2: Language Detection
# ---------------------------------------------------------------------------


class TestLanguageDetection:
    def test_persian_detected(self, pipeline):
        lang = pipeline._phase_language_detection("آگاهی چیست؟")
        assert lang.primary_language == "fa"

    def test_english_detected(self, pipeline):
        lang = pipeline._phase_language_detection("What is awareness?")
        assert lang.primary_language == "en"

    def test_mixed_language(self, pipeline):
        lang = pipeline._phase_language_detection("fp: meditation and consciousness")
        assert lang.primary_language == "en"

    def test_scripts_detected(self, pipeline):
        lang = pipeline._phase_language_detection("آگاهی")
        assert "Persian" in lang.detected_scripts


# ---------------------------------------------------------------------------
# Phase 3: Intent Analysis
# ---------------------------------------------------------------------------


class TestIntentAnalysis:
    def test_comparison_intent(self, pipeline):
        intent = pipeline._phase_intent_analysis("ACT و ذن چه تفاوتی دارند؟", [])
        assert intent.primary_intent == "comparison"
        assert intent.question_type == "comparative"

    def test_definition_intent(self, pipeline):
        intent = pipeline._phase_intent_analysis("آگاهی چیست؟", [])
        assert intent.primary_intent == "definition"
        assert intent.question_type == "explanatory"

    def test_methodology_intent(self, pipeline):
        intent = pipeline._phase_intent_analysis("چگونه مدیتیشن کنم؟", [])
        assert intent.primary_intent == "methodology"

    def test_question_type_independent(self, pipeline):
        intent = pipeline._phase_intent_analysis("آیا فنا همان Non-self است؟", [])
        # "همان" triggers comparison intent
        assert intent.primary_intent == "comparison"


# ---------------------------------------------------------------------------
# Phase 4: Concept Discovery
# ---------------------------------------------------------------------------


class TestConceptDiscovery:
    def test_discovers_concepts(self, pipeline):
        pipeline._init()
        lang = LanguageAnalysis(primary_language="fa")
        concepts = pipeline._phase_concept_discovery("خود و آگاهی چه ارتباطی دارند؟", lang)
        names = [c["canonical"] for c in concepts.resolved_concepts]
        assert "Self" in names
        assert "Awareness" in names

    def test_empty_query(self, pipeline):
        pipeline._init()
        lang = LanguageAnalysis(primary_language="en")
        concepts = pipeline._phase_concept_discovery("", lang)
        assert len(concepts.resolved_concepts) == 0


# ---------------------------------------------------------------------------
# Phase 6: Entity Recognition
# ---------------------------------------------------------------------------


class TestEntityRecognition:
    def test_recognizes_entities(self, pipeline):
        pipeline._init()
        lang = LanguageAnalysis(primary_language="fa")
        entities = pipeline._phase_entity_recognition("متزینگر درباره Self چه می‌گوید؟", lang)
        names = [e["name"] for e in entities.entities]
        assert "Metzinger" in names

    def test_entities_separate_from_concepts(self, pipeline):
        pipeline._init()
        lang = LanguageAnalysis(primary_language="fa")
        entities = pipeline._phase_entity_recognition("ACT و Zen", lang)
        names = [e["name"] for e in entities.entities]
        assert "ACT" in names
        assert "Zen" in names


# ---------------------------------------------------------------------------
# Phase 7: Complexity Estimation
# ---------------------------------------------------------------------------


class TestComplexityEstimation:
    def test_simple_query_low_complexity(self, pipeline):
        intent = IntentAnalysis(primary_intent="definition")
        concepts = ConceptDiscovery(resolved_concepts=[{"canonical": "Self"}])
        entities = EntityDiscovery(entities=[])
        complexity = pipeline._phase_complexity_estimation(intent, concepts, entities, [])
        assert complexity.level in ("very_low", "low", "medium")

    def test_complex_query_high_complexity(self, pipeline):
        intent = IntentAnalysis(primary_intent="comparison")
        concepts = ConceptDiscovery(resolved_concepts=[{"canonical": "A"}, {"canonical": "B"}, {"canonical": "C"}, {"canonical": "D"}])
        entities = EntityDiscovery(entities=[{"name": "ACT"}, {"name": "Zen"}, {"name": "Sufism"}])
        complexity = pipeline._phase_complexity_estimation(intent, concepts, entities, [])
        assert complexity.level in ("medium", "high", "very_high")
        assert complexity.cross_book is True


# ---------------------------------------------------------------------------
# Phase 8: Capability Analysis
# ---------------------------------------------------------------------------


class TestCapabilityAnalysis:
    def test_comparison_needs_cross_book(self, pipeline):
        intent = IntentAnalysis(primary_intent="comparison")
        concepts = ConceptDiscovery()
        entities = EntityDiscovery(entities=[{"name": "ACT"}, {"name": "Zen"}])
        complexity = ComplexityEstimate(cross_book=True)
        caps = pipeline._phase_capability_analysis(intent, concepts, entities, complexity)
        assert "cross_book_reasoning" in caps.required_capabilities
        assert caps.reasoning_depth == "cross_book"

    def test_definition_needs_summarization(self, pipeline):
        intent = IntentAnalysis(primary_intent="definition")
        caps = pipeline._phase_capability_analysis(intent, ConceptDiscovery(), EntityDiscovery(), ComplexityEstimate())
        assert "summarization" in caps.required_capabilities


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_executes_all_phases(self, pipeline):
        qa = pipeline.execute("ACT و ذن چه تفاوتی دارند؟")
        assert isinstance(qa, QueryAnalysis)
        assert qa.intent == "comparison"
        assert qa.scope == "cross_book"
        assert qa.complexity in ("medium", "high", "very_high")

    def test_persian_query(self, pipeline):
        qa = pipeline.execute("آگاهی چیست؟")
        assert "fa" in qa.languages
        assert qa.intent == "definition"

    def test_deterministic(self, pipeline):
        qa1 = pipeline.execute("آگاهی چیست؟")
        qa2 = pipeline.execute("آگاهی چیست؟")
        assert qa1.intent == qa2.intent
        assert qa1.concepts == qa2.concepts
        assert qa1.entities == qa2.entities


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_output_is_query_analysis(self, pipeline):
        qa = pipeline.execute("test query")
        assert isinstance(qa, QueryAnalysis)
        assert hasattr(qa, 'intent')
        assert hasattr(qa, 'concepts')
        assert hasattr(qa, 'entities')
        assert hasattr(qa, 'complexity')
        assert hasattr(qa, 'scope')
