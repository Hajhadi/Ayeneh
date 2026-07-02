"""Comprehensive tests for Cross-Book Semantic Linking."""

from __future__ import annotations

import pytest

from ayeneh.cross_book_linking.engine import CrossBookConceptLinker
from ayeneh.cross_book_linking.types import (
    AmbiguousRelation,
    CrossBookDiff,
    SemanticEdge,
    SemanticRelationType,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def linker() -> CrossBookConceptLinker:
    return CrossBookConceptLinker()


# ---------------------------------------------------------------------------
# Concept linking tests
# ---------------------------------------------------------------------------


class TestConceptLinking:
    def test_links_similar_concepts(self, linker: CrossBookConceptLinker) -> None:
        edge = linker.link_concepts("acceptance", "non-resistance", "book1", "book2")
        assert edge is not None
        assert edge.similarity_score > 0

    def test_rejects_dissimilar_concepts(self, linker: CrossBookConceptLinker) -> None:
        edge = linker.link_concepts("acceptance", "quantum physics", "book1", "book2")
        assert edge is None

    def test_edge_has_provenance(self, linker: CrossBookConceptLinker) -> None:
        edge = linker.link_concepts("mindfulness", "awareness", "book1", "book2")
        assert edge is not None
        assert "book1" in edge.supporting_books
        assert "book2" in edge.supporting_books

    def test_edge_has_confidence(self, linker: CrossBookConceptLinker) -> None:
        edge = linker.link_concepts("self", "ego", "book1", "book2")
        assert edge is not None
        assert 0 <= edge.confidence <= 1


# ---------------------------------------------------------------------------
# Ambiguity tests
# ---------------------------------------------------------------------------


class TestAmbiguity:
    def test_finds_ambiguous_relations(self, linker: CrossBookConceptLinker) -> None:
        ambiguous = linker.find_ambiguous_relations(
            ["mindfulness", "awareness", "attention", "concentration"]
        )
        assert len(ambiguous) > 0

    def test_ambiguous_has_probabilities(self, linker: CrossBookConceptLinker) -> None:
        ambiguous = linker.find_ambiguous_relations(["mindfulness", "awareness"])
        if ambiguous:
            assert ambiguous[0].probabilities
            assert ambiguous[0].similarity_score > 0


# ---------------------------------------------------------------------------
# Diff tests
# ---------------------------------------------------------------------------


class TestDiff:
    def test_detects_new_concepts(self, linker: CrossBookConceptLinker) -> None:
        diff = linker.detect_diff(["a", "b"], ["a", "b", "c"])
        assert "c" in diff.new_concepts

    def test_detects_affected_concepts(self, linker: CrossBookConceptLinker) -> None:
        diff = linker.detect_diff(["a", "b"], ["a", "b", "c"])
        assert "a" in diff.affected_concepts
        assert "b" in diff.affected_concepts


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_linker_works(self, linker: CrossBookConceptLinker) -> None:
        edge = linker.link_concepts("test", "test", "book1", "book2")
        assert edge is not None

    def test_metrics_work(self, linker: CrossBookConceptLinker) -> None:
        linker.link_concepts("a", "b", "book1", "book2")
        metrics = linker.get_metrics()
        assert "edges_created" in metrics
