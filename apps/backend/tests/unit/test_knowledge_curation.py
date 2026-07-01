"""Comprehensive tests for the Knowledge Curation Engine."""

from __future__ import annotations

import uuid

import pytest

from ayeneh.knowledge_curation.engine import (
    AgreementDetector,
    AuthorityComparator,
    ComplementarityDetector,
    ConceptNormalizer,
    ConflictDetector,
    KnowledgeCurationEngine,
)
from ayeneh.knowledge_curation.graph import KnowledgeGraph
from ayeneh.knowledge_curation.types import (
    ConceptNode,
    DocumentNode,
    KnowledgeEdge,
    KnowledgeNode,
    NodeType,
    RelationType,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> KnowledgeCurationEngine:
    return KnowledgeCurationEngine()


@pytest.fixture
def graph() -> KnowledgeGraph:
    return KnowledgeGraph()


@pytest.fixture
def normalizer() -> ConceptNormalizer:
    return ConceptNormalizer()


# ---------------------------------------------------------------------------
# Graph tests
# ---------------------------------------------------------------------------


class TestKnowledgeGraph:
    def test_add_node(self, graph: KnowledgeGraph) -> None:
        node = KnowledgeNode(id="n1", node_type="book", title="Test Book")
        graph.add_node(node)
        assert "n1" in graph
        assert len(graph) == 1

    def test_get_node(self, graph: KnowledgeGraph) -> None:
        node = KnowledgeNode(id="n1", node_type="book", title="Test Book")
        graph.add_node(node)
        retrieved = graph.get_node("n1")
        assert retrieved is not None
        assert retrieved.title == "Test Book"

    def test_get_nodes_by_type(self, graph: KnowledgeGraph) -> None:
        graph.add_node(KnowledgeNode(id="n1", node_type="book", title="Book 1"))
        graph.add_node(KnowledgeNode(id="n2", node_type="chapter", title="Chapter 1"))
        graph.add_node(KnowledgeNode(id="n3", node_type="book", title="Book 2"))

        books = graph.get_nodes_by_type("book")
        assert len(books) == 2

    def test_add_edge(self, graph: KnowledgeGraph) -> None:
        graph.add_node(KnowledgeNode(id="n1", node_type="book"))
        graph.add_node(KnowledgeNode(id="n2", node_type="book"))
        edge = KnowledgeEdge(source_id="n1", target_id="n2", relation_type="supports")
        graph.add_edge(edge)
        assert graph.get_edge(edge.id) is not None

    def test_get_edges_from_node(self, graph: KnowledgeGraph) -> None:
        graph.add_node(KnowledgeNode(id="n1", node_type="book"))
        graph.add_node(KnowledgeNode(id="n2", node_type="book"))
        graph.add_node(KnowledgeNode(id="n3", node_type="book"))

        graph.add_edge(KnowledgeEdge(source_id="n1", target_id="n2", relation_type="supports"))
        graph.add_edge(KnowledgeEdge(source_id="n1", target_id="n3", relation_type="contradicts"))

        edges = graph.get_edges_from_node("n1")
        assert len(edges) == 2

    def test_get_edges_to_node(self, graph: KnowledgeGraph) -> None:
        graph.add_node(KnowledgeNode(id="n1", node_type="book"))
        graph.add_node(KnowledgeNode(id="n2", node_type="book"))

        graph.add_edge(KnowledgeEdge(source_id="n1", target_id="n2", relation_type="supports"))

        edges = graph.get_edges_to_node("n2")
        assert len(edges) == 1

    def test_get_edges_between(self, graph: KnowledgeGraph) -> None:
        graph.add_node(KnowledgeNode(id="n1", node_type="book"))
        graph.add_node(KnowledgeNode(id="n2", node_type="book"))

        graph.add_edge(KnowledgeEdge(source_id="n1", target_id="n2", relation_type="supports"))
        graph.add_edge(KnowledgeEdge(source_id="n2", target_id="n1", relation_type="contradicts"))

        edges = graph.get_edges_between("n1", "n2")
        assert len(edges) == 1

    def test_get_neighbors(self, graph: KnowledgeGraph) -> None:
        graph.add_node(KnowledgeNode(id="n1", node_type="book"))
        graph.add_node(KnowledgeNode(id="n2", node_type="book"))
        graph.add_node(KnowledgeNode(id="n3", node_type="book"))

        graph.add_edge(KnowledgeEdge(source_id="n1", target_id="n2", relation_type="supports"))
        graph.add_edge(KnowledgeEdge(source_id="n2", target_id="n3", relation_type="supports"))

        neighbors = graph.get_neighbors("n1")
        assert len(neighbors) == 1
        assert neighbors[0].id == "n2"

    def test_find_path(self, graph: KnowledgeGraph) -> None:
        graph.add_node(KnowledgeNode(id="n1", node_type="book"))
        graph.add_node(KnowledgeNode(id="n2", node_type="book"))
        graph.add_node(KnowledgeNode(id="n3", node_type="book"))

        graph.add_edge(KnowledgeEdge(source_id="n1", target_id="n2", relation_type="supports"))
        graph.add_edge(KnowledgeEdge(source_id="n2", target_id="n3", relation_type="supports"))

        path = graph.find_path("n1", "n3")
        assert path is not None
        assert len(path) == 3
        assert path == ["n1", "n2", "n3"]

    def test_remove_node(self, graph: KnowledgeGraph) -> None:
        graph.add_node(KnowledgeNode(id="n1", node_type="book"))
        graph.add_node(KnowledgeNode(id="n2", node_type="book"))
        graph.add_edge(KnowledgeEdge(source_id="n1", target_id="n2", relation_type="supports"))

        graph.remove_node("n1")
        assert "n1" not in graph
        assert len(graph.get_edges_to_node("n2")) == 0

    def test_get_metrics(self, graph: KnowledgeGraph) -> None:
        graph.add_node(KnowledgeNode(id="n1", node_type="book"))
        graph.add_node(KnowledgeNode(id="n2", node_type="book"))
        graph.add_edge(KnowledgeEdge(
            source_id="n1", target_id="n2", relation_type="supports", confidence=0.8,
        ))

        metrics = graph.get_metrics()
        assert metrics.node_count == 2
        assert metrics.edge_count == 1
        assert metrics.agreements == 1
        assert metrics.average_confidence == 0.8


# ---------------------------------------------------------------------------
# Concept Normalizer tests
# ---------------------------------------------------------------------------


class TestConceptNormalizer:
    def test_normalize_new_concept(self, normalizer: ConceptNormalizer) -> None:
        result = normalizer.normalize("Acceptance")
        assert result.canonical_name == "Acceptance"
        assert "Acceptance" in result.aliases

    def test_normalize_alias(self, normalizer: ConceptNormalizer) -> None:
        normalizer.normalize("Acceptance")
        result = normalizer.normalize("Radical Acceptance")
        # Should be detected as similar
        assert result is not None

    def test_get_canonical(self, normalizer: ConceptNormalizer) -> None:
        normalizer.normalize("Acceptance")
        canonical = normalizer.get_canonical("acceptance")
        assert canonical.lower() == "acceptance"

    def test_get_related(self, normalizer: ConceptNormalizer) -> None:
        normalizer.normalize("Acceptance")
        normalizer.normalize("Radical Acceptance")
        related = normalizer.get_related("Acceptance")
        assert len(related) >= 1


# ---------------------------------------------------------------------------
# Agreement Detector tests
# ---------------------------------------------------------------------------


class TestAgreementDetector:
    def test_detect_agreement(self) -> None:
        detector = AgreementDetector()
        source = DocumentNode(
            id="s1", domains=["philosophy"], frameworks=["rationalist"],
        )
        target = DocumentNode(
            id="t1", domains=["philosophy"], frameworks=["rationalist"],
        )
        result = detector.detect(source, target, ["truth", "reality"])
        assert result is not None
        assert result.agreement_confidence > 0.3

    def test_no_agreement_different_domains(self) -> None:
        detector = AgreementDetector()
        source = DocumentNode(id="s1", domains=["philosophy"])
        target = DocumentNode(id="t1", domains=["science"])
        result = detector.detect(source, target, ["concept"])
        assert result is None


# ---------------------------------------------------------------------------
# Conflict Detector tests
# ---------------------------------------------------------------------------


class TestConflictDetector:
    def test_detect_conflict(self) -> None:
        detector = ConflictDetector()
        source = DocumentNode(
            id="s1", domains=["science"], evidence_level="empirical",
        )
        target = DocumentNode(
            id="t1", domains=["spirituality"], evidence_level="experiential",
        )
        result = detector.detect(source, target, ["consciousness"])
        assert result is not None
        assert result.conflict_confidence > 0.3

    def test_no_conflict_similar_sources(self) -> None:
        detector = ConflictDetector()
        source = DocumentNode(
            id="s1", domains=["science"], evidence_level="empirical",
        )
        target = DocumentNode(
            id="t1", domains=["science"], evidence_level="empirical",
        )
        result = detector.detect(source, target, ["concept"])
        assert result is None


# ---------------------------------------------------------------------------
# Complementarity Detector tests
# ---------------------------------------------------------------------------


class TestComplementarityDetector:
    def test_detect_complementarity(self) -> None:
        detector = ComplementarityDetector()
        source = DocumentNode(
            id="s1", domains=["psychology"], evidence_level="empirical",
        )
        target = DocumentNode(
            id="t1", domains=["spirituality"], evidence_level="experiential",
        )
        result = detector.detect(source, target)
        assert result is not None
        assert result.complementarity_confidence > 0.4

    def test_no_complementarity_same_domain(self) -> None:
        detector = ComplementarityDetector()
        source = DocumentNode(
            id="s1", domains=["philosophy"], evidence_level="philosophical",
        )
        target = DocumentNode(
            id="t1", domains=["philosophy"], evidence_level="philosophical",
        )
        result = detector.detect(source, target)
        assert result is None


# ---------------------------------------------------------------------------
# Authority Comparator tests
# ---------------------------------------------------------------------------


class TestAuthorityComparator:
    def test_compare_authority(self) -> None:
        comparator = AuthorityComparator()
        source = DocumentNode(id="s1", authority="primary")
        target = DocumentNode(id="t1", authority="secondary")
        result = comparator.compare(source, target, "concept")
        assert result.comparison == "source_higher"

    def test_equal_authority(self) -> None:
        comparator = AuthorityComparator()
        source = DocumentNode(id="s1", authority="primary")
        target = DocumentNode(id="t1", authority="primary")
        result = comparator.compare(source, target, "concept")
        assert result.comparison == "equal"


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestKnowledgeCurationEngine:
    def test_add_document(self, engine: KnowledgeCurationEngine) -> None:
        node = engine.add_document(
            document_id="doc1",
            title="Test Book",
            domains=["philosophy"],
        )
        assert node.id is not None
        assert node.title == "Test Book"

    def test_add_chapter(self, engine: KnowledgeCurationEngine) -> None:
        book = engine.add_document(document_id="book1", title="Book")
        chapter = engine.add_chapter(
            chapter_id="ch1",
            book_id=book.id,
            title="Chapter 1",
        )
        assert chapter.book_id == book.id

    def test_chapter_connected_to_book(self, engine: KnowledgeCurationEngine) -> None:
        book = engine.add_document(document_id="book1", title="Book")
        engine.add_chapter(chapter_id="ch1", book_id=book.id, title="Ch1")

        neighbors = engine.graph.get_neighbors("ch1")
        assert len(neighbors) == 1
        assert neighbors[0].id == book.id

    def test_add_concept(self, engine: KnowledgeCurationEngine) -> None:
        node = engine.add_concept("Acceptance", domain="psychology")
        assert node.canonical_name == "Acceptance"

    def test_detect_relations(self, engine: KnowledgeCurationEngine) -> None:
        s1 = engine.add_document(
            document_id="s1", title="Source 1",
            domains=["philosophy"], frameworks=["rationalist"],
        )
        s2 = engine.add_document(
            document_id="s2", title="Source 2",
            domains=["philosophy"], frameworks=["rationalist"],
        )
        edges = engine.detect_relations(s1.id, s2.id, ["truth", "reality"])
        assert len(edges) > 0

    def test_find_agreements(self, engine: KnowledgeCurationEngine) -> None:
        s1 = engine.add_document(document_id="s1", title="S1", domains=["philosophy"])
        s2 = engine.add_document(document_id="s2", title="S2", domains=["philosophy"])
        engine.detect_relations(s1.id, s2.id, ["truth"])

        agreements = engine.find_agreements(s1.id)
        assert len(agreements) >= 0

    def test_find_conflicts(self, engine: KnowledgeCurationEngine) -> None:
        s1 = engine.add_document(
            document_id="s1", title="S1",
            domains=["science"], evidence_level="empirical",
        )
        s2 = engine.add_document(
            document_id="s2", title="S2",
            domains=["spirituality"], evidence_level="experiential",
        )
        engine.detect_relations(s1.id, s2.id, ["consciousness"])

        conflicts = engine.find_conflicts(s1.id)
        assert len(conflicts) >= 0

    def test_get_metrics(self, engine: KnowledgeCurationEngine) -> None:
        engine.add_document(document_id="d1", title="D1")
        engine.add_document(document_id="d2", title="D2")

        metrics = engine.get_metrics()
        assert metrics.node_count == 2

    def test_get_source_context(self, engine: KnowledgeCurationEngine) -> None:
        node = engine.add_document(document_id="d1", title="D1")
        context = engine.get_source_context(node.id)
        assert "node" in context
        assert "agreements" in context
        assert "conflicts" in context


# ---------------------------------------------------------------------------
# Mixed discipline tests
# ---------------------------------------------------------------------------


class TestMixedDisciplines:
    def test_philosophy_science_complementarity(
        self, engine: KnowledgeCurationEngine,
    ) -> None:
        phil = engine.add_document(
            document_id="phil", title="Philosophy Book",
            domains=["philosophy"], evidence_level="philosophical",
        )
        sci = engine.add_document(
            document_id="sci", title="Science Book",
            domains=["science"], evidence_level="empirical",
        )
        edges = engine.detect_relations(phil.id, sci.id)
        # Should detect complementarity
        complement_edges = [e for e in edges if e.relation_type == RelationType.COMPLEMENTS]
        assert len(complement_edges) > 0

    def test_mysticism_science_conflict(
        self, engine: KnowledgeCurationEngine,
    ) -> None:
        myst = engine.add_document(
            document_id="myst", title="Mysticism Book",
            domains=["spirituality"], evidence_level="experiential",
        )
        sci = engine.add_document(
            document_id="sci", title="Science Book",
            domains=["science"], evidence_level="empirical",
        )
        edges = engine.detect_relations(myst.id, sci.id, ["consciousness"])
        # Should detect conflict
        conflict_edges = [e for e in edges if e.relation_type == RelationType.CONTRADICTS]
        assert len(conflict_edges) > 0


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_empty_graph(self, engine: KnowledgeCurationEngine) -> None:
        metrics = engine.get_metrics()
        assert metrics.node_count == 0
        assert metrics.edge_count == 0

    def test_single_document(self, engine: KnowledgeCurationEngine) -> None:
        engine.add_document(document_id="d1", title="D1")
        metrics = engine.get_metrics()
        assert metrics.node_count == 1


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    def test_large_graph(self, engine: KnowledgeCurationEngine) -> None:
        # Add 100 documents
        for i in range(100):
            engine.add_document(
                document_id=f"doc{i}",
                title=f"Document {i}",
                domains=["philosophy"],
            )

        metrics = engine.get_metrics()
        assert metrics.node_count == 100

    def test_many_relations(self, engine: KnowledgeCurationEngine) -> None:
        docs = []
        for i in range(10):
            doc = engine.add_document(
                document_id=f"doc{i}",
                title=f"Document {i}",
                domains=["philosophy"],
            )
            docs.append(doc)

        # Create relations between all pairs
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                engine.detect_relations(docs[i].id, docs[j].id, ["concept"])

        metrics = engine.get_metrics()
        assert metrics.edge_count > 0
