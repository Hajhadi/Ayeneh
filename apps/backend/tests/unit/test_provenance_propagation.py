"""Comprehensive tests for End-to-End Provenance Propagation."""

from __future__ import annotations

import pytest

from ayeneh.provenance.bundle import ProvenanceBundle, merge_bundles
from ayeneh.provenance.types import (
    ChunkOrigin,
    DocumentOrigin,
    EdgeOrigin,
    InterpretationOrigin,
    NodeOrigin,
    ReasoningOrigin,
    ResponseMetadata,
    SafetyOrigin,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bundle() -> ProvenanceBundle:
    return ProvenanceBundle()


@pytest.fixture
def document_origin() -> DocumentOrigin:
    return DocumentOrigin(
        document_id="doc1",
        book_id="book1",
        title="Test Book",
        author="Test Author",
    )


@pytest.fixture
def chunk_origin() -> ChunkOrigin:
    return ChunkOrigin(
        chunk_id="chunk1",
        chapter_id="ch1",
        page_number=1,
        text_origin="native",
        ocr_confidence=1.0,
    )


# ---------------------------------------------------------------------------
# ProvenanceBundle creation tests
# ---------------------------------------------------------------------------


class TestProvenanceBundleCreation:
    def test_bundle_has_id(self, bundle: ProvenanceBundle) -> None:
        assert bundle.id is not None
        assert len(bundle.id) > 0

    def test_bundle_has_timestamps(self, bundle: ProvenanceBundle) -> None:
        assert bundle.created_at is not None
        assert bundle.updated_at is not None

    def test_bundle_starts_empty(self, bundle: ProvenanceBundle) -> None:
        assert bundle.get_total_references() == 0


# ---------------------------------------------------------------------------
# ProvenanceBundle immutability tests
# ---------------------------------------------------------------------------


class TestProvenanceBundleImmutability:
    def test_with_document_returns_new_bundle(
        self, bundle: ProvenanceBundle, document_origin: DocumentOrigin,
    ) -> None:
        new_bundle = bundle.with_document(document_origin)
        assert new_bundle.id == bundle.id
        assert new_bundle.document == document_origin
        assert bundle.document != document_origin

    def test_with_chunk_returns_new_bundle(
        self, bundle: ProvenanceBundle, chunk_origin: ChunkOrigin,
    ) -> None:
        new_bundle = bundle.with_chunk(chunk_origin)
        assert new_bundle.id == bundle.id
        assert len(new_bundle.chunks) == 1
        assert len(bundle.chunks) == 0

    def test_with_node_returns_new_bundle(
        self, bundle: ProvenanceBundle,
    ) -> None:
        node = NodeOrigin(node_id="n1", node_type="concept", title="Test")
        new_bundle = bundle.with_node(node)
        assert len(new_bundle.nodes) == 1
        assert len(bundle.nodes) == 0

    def test_with_edge_returns_new_bundle(
        self, bundle: ProvenanceBundle,
    ) -> None:
        edge = EdgeOrigin(edge_id="e1", source_node_id="n1", target_node_id="n2")
        new_bundle = bundle.with_edge(edge)
        assert len(new_bundle.edges) == 1
        assert len(bundle.edges) == 0

    def test_with_reasoning_returns_new_bundle(
        self, bundle: ProvenanceBundle,
    ) -> None:
        step = ReasoningOrigin(step_id="s1", step_type="inference")
        new_bundle = bundle.with_reasoning(step)
        assert len(new_bundle.reasoning_steps) == 1
        assert len(bundle.reasoning_steps) == 0

    def test_with_interpretation_returns_new_bundle(
        self, bundle: ProvenanceBundle,
    ) -> None:
        interp = InterpretationOrigin(interpretation_id="i1", confidence=0.8)
        new_bundle = bundle.with_interpretation(interp)
        assert len(new_bundle.interpretations) == 1
        assert len(bundle.interpretations) == 0

    def test_with_safety_returns_new_bundle(
        self, bundle: ProvenanceBundle,
    ) -> None:
        safety = SafetyOrigin(rule_id="r1", reason="hedging")
        new_bundle = bundle.with_safety(safety)
        assert len(new_bundle.safety_interventions) == 1
        assert len(bundle.safety_interventions) == 0

    def test_with_engine_version_returns_new_bundle(
        self, bundle: ProvenanceBundle,
    ) -> None:
        new_bundle = bundle.with_engine_version("interpreter", "1.0.0")
        assert new_bundle.engine_versions["interpreter"] == "1.0.0"
        assert "interpreter" not in bundle.engine_versions


# ---------------------------------------------------------------------------
# Bundle merging tests
# ---------------------------------------------------------------------------


class TestBundleMerging:
    def test_merge_empty_bundles(self) -> None:
        merged = merge_bundles()
        assert merged.get_total_references() == 0

    def test_merge_single_bundle(self) -> None:
        b1 = ProvenanceBundle(
            chunks=[ChunkOrigin(chunk_id="c1")],
        )
        merged = merge_bundles(b1)
        assert len(merged.chunks) == 1

    def test_merge_two_bundles(self) -> None:
        b1 = ProvenanceBundle(chunks=[ChunkOrigin(chunk_id="c1")])
        b2 = ProvenanceBundle(chunks=[ChunkOrigin(chunk_id="c2")])
        merged = merge_bundles(b1, b2)
        assert len(merged.chunks) == 2

    def test_merge_avoids_duplicate_chunks(self) -> None:
        b1 = ProvenanceBundle(chunks=[ChunkOrigin(chunk_id="c1")])
        b2 = ProvenanceBundle(chunks=[ChunkOrigin(chunk_id="c1")])
        merged = merge_bundles(b1, b2)
        assert len(merged.chunks) == 1

    def test_merge_preserves_all_references(self) -> None:
        b1 = ProvenanceBundle(
            chunks=[ChunkOrigin(chunk_id="c1")],
            nodes=[NodeOrigin(node_id="n1")],
        )
        b2 = ProvenanceBundle(
            chunks=[ChunkOrigin(chunk_id="c2")],
            edges=[EdgeOrigin(edge_id="e1")],
        )
        merged = merge_bundles(b1, b2)
        assert len(merged.chunks) == 2
        assert len(merged.nodes) == 1
        assert len(merged.edges) == 1

    def test_merge_multiple_bundles(self) -> None:
        bundles = [
            ProvenanceBundle(chunks=[ChunkOrigin(chunk_id=f"c{i}")])
            for i in range(5)
        ]
        merged = merge_bundles(*bundles)
        assert len(merged.chunks) == 5


# ---------------------------------------------------------------------------
# ResponseMetadata tests
# ---------------------------------------------------------------------------


class TestResponseMetadata:
    def test_to_response_metadata(self, bundle: ProvenanceBundle) -> None:
        bundle = bundle.with_chunk(ChunkOrigin(chunk_id="c1"))
        bundle = bundle.with_interpretation(InterpretationOrigin(interpretation_id="i1"))
        bundle = bundle.with_node(NodeOrigin(node_id="n1"))

        metadata = bundle.to_response_metadata()
        assert metadata.provenance_bundle_id == bundle.id
        assert "c1" in metadata.cited_chunks
        assert "i1" in metadata.interpretation_ids
        assert "n1" in metadata.graph_nodes


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_bundle_has_required_fields(self) -> None:
        bundle = ProvenanceBundle()
        assert hasattr(bundle, "document")
        assert hasattr(bundle, "chunks")
        assert hasattr(bundle, "nodes")
        assert hasattr(bundle, "edges")
        assert hasattr(bundle, "reasoning_steps")
        assert hasattr(bundle, "interpretations")
        assert hasattr(bundle, "safety_interventions")
        assert hasattr(bundle, "engine_versions")

    def test_merge_bundles_function_exists(self) -> None:
        assert callable(merge_bundles)


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    def test_merge_performance(self) -> None:
        import time
        bundles = [
            ProvenanceBundle(chunks=[ChunkOrigin(chunk_id=f"c{i}")])
            for i in range(100)
        ]
        start = time.monotonic()
        merged = merge_bundles(*bundles)
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 100  # 100 merges in under 100ms
        assert len(merged.chunks) == 100
