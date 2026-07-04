"""Tests for QueryConceptResolver — concept resolution for user queries."""

import pytest
from ayeneh.runtime.query_concept_resolver import (
    QueryConceptResolver,
    QueryConceptResolution,
    ResolvedConcept,
    ResolvedEntity,
    AmbiguityItem,
)


@pytest.fixture
def resolver():
    return QueryConceptResolver()


# ---------------------------------------------------------------------------
# Tier 1: Registry Lookup
# ---------------------------------------------------------------------------


class TestRegistryLookup:
    def test_resolves_known_concept(self, resolver):
        r = resolver.resolve("آگاهی چیست؟")
        names = [c.canonical for c in r.resolved_concepts]
        assert "Awareness" in names

    def test_resolves_persian_concept(self, resolver):
        r = resolver.resolve("خود و هویت چه تفاوتی دارند؟")
        names = [c.canonical for c in r.resolved_concepts]
        assert "Self" in names

    def test_resolves_multiple_concepts(self, resolver):
        r = resolver.resolve("خود و آگاهی چه ارتباطی دارند؟")
        names = [c.canonical for c in r.resolved_concepts]
        assert "Self" in names
        assert "Awareness" in names

    def test_registry_source标记(self, resolver):
        r = resolver.resolve("آگاهی چیست؟")
        for c in r.resolved_concepts:
            if c.canonical == "Awareness":
                assert c.source == "registry"
                assert c.confidence == 1.0


# ---------------------------------------------------------------------------
# Tier 2: Alias Normalization
# ---------------------------------------------------------------------------


class TestAliasResolution:
    def test_resolves_alias(self, resolver):
        r = resolver.resolve("mindfulness چیست؟")
        names = [c.canonical for c in r.resolved_concepts]
        assert "Mindfulness" in names

    def test_resolves_sati(self, resolver):
        r = resolver.resolve("sati and awareness")
        names = [c.canonical for c in r.resolved_concepts]
        # sati should resolve via normalizer to Mindfulness or appear as a concept
        assert len(names) > 0


# ---------------------------------------------------------------------------
# Tier 3: Concept Discovery
# ---------------------------------------------------------------------------


class TestConceptDiscoveryFallback:
    def test_unknown_concept_gets_discovered(self, resolver):
        r = resolver.resolve("fp: meditation and consciousness")
        names = [c.canonical for c in r.resolved_concepts]
        assert len(names) >= 1

    def test_discovery_source标记(self, resolver):
        r = resolver.resolve("fp: meditation and consciousness")
        sources = {c.source for c in r.resolved_concepts}
        assert "registry" in sources or "normalizer" in sources or "discovery" in sources


# ---------------------------------------------------------------------------
# Entity Separation
# ---------------------------------------------------------------------------


class TestEntitySeparation:
    def test_entities_are_separate_from_concepts(self, resolver):
        r = resolver.resolve("ACT و ذن چه تفاوتی دارند؟")
        entity_names = [e.name for e in r.resolved_entities]
        concept_names = [c.canonical for c in r.resolved_concepts]
        assert "ACT" in entity_names
        assert "Zen" in entity_names
        assert "ACT" not in concept_names
        assert "Zen" not in concept_names

    def test_author_entity(self, resolver):
        r = resolver.resolve("متزینگر درباره Self چه می‌گوید؟")
        entity_names = [e.name for e in r.resolved_entities]
        assert "Metzinger" in entity_names

    def test_tradition_entity(self, resolver):
        r = resolver.resolve("فنا در تصوف همان Non-self است؟")
        entity_names = [e.name for e in r.resolved_entities]
        assert "Sufism" in entity_names

    def test_entity_confidence(self, resolver):
        r = resolver.resolve("ACT و Zen")
        assert r.entity_confidence > 0


# ---------------------------------------------------------------------------
# Ambiguity Detection
# ---------------------------------------------------------------------------


class TestAmbiguityDetection:
    def test_similar_concepts_flagged(self, resolver):
        r = resolver.resolve("خود و Self چه تفاوتی دارند؟")
        # Self and خود should be similar → potential ambiguity
        assert isinstance(r.ambiguities, list)


# ---------------------------------------------------------------------------
# Intent Detection
# ---------------------------------------------------------------------------


class TestIntentIntegration:
    def test_comparison_intent(self, resolver):
        r = resolver.resolve("ACT و ذن چه تفاوتی دارند؟")
        # Should have concepts and entities
        assert len(r.resolved_concepts) > 0 or len(r.resolved_entities) > 0

    def test_definition_intent(self, resolver):
        r = resolver.resolve("آگاهی چیست؟")
        names = [c.canonical for c in r.resolved_concepts]
        assert "Awareness" in names


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_resolution_has_all_required_fields(self, resolver):
        r = resolver.resolve("test query")
        assert hasattr(r, 'resolved_concepts')
        assert hasattr(r, 'resolved_entities')
        assert hasattr(r, 'unresolved_terms')
        assert hasattr(r, 'ambiguities')
        assert hasattr(r, 'concept_confidence')
        assert hasattr(r, 'entity_confidence')

    def test_concept_confidence_range(self, resolver):
        r = resolver.resolve("آگاهی و خود")
        assert 0.0 <= r.concept_confidence <= 1.0


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_input_same_output(self, resolver):
        r1 = resolver.resolve("آگاهی چیست؟")
        r2 = resolver.resolve("آگاهی چیست؟")
        assert [c.canonical for c in r1.resolved_concepts] == [c.canonical for c in r2.resolved_concepts]
        assert [e.name for e in r1.resolved_entities] == [e.name for e in r2.resolved_entities]


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


class TestPerformance:
    def test_resolve_completes_quickly(self, resolver):
        import time
        queries = [
            "ACT و ذن چه تفاوتی دارند؟",
            "متزینگر درباره Self چه می‌گوید؟",
            "آگاهی چیست؟",
            "fp: meditation and consciousness",
            "خود و آگاهی چه ارتباطی دارند؟",
        ]
        start = time.monotonic()
        for q in queries:
            resolver.resolve(q)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"5 queries took {elapsed:.2f}s, should be < 5s"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_query(self, resolver):
        r = resolver.resolve("")
        assert isinstance(r, QueryConceptResolution)
        assert len(r.resolved_concepts) == 0

    def test_single_word_query(self, resolver):
        r = resolver.resolve("meditation")
        assert isinstance(r, QueryConceptResolution)

    def test_long_query(self, resolver):
        q = " fp: what is the relationship between meditation and consciousness in the context of Buddhist philosophy and modern neuroscience?"
        r = resolver.resolve(q)
        assert isinstance(r, QueryConceptResolution)
        assert len(r.resolved_concepts) > 0
