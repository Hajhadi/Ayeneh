"""KnowledgeCurationEngine — single owner of knowledge relationships."""

from __future__ import annotations

import time
from typing import Any

import structlog

from ayeneh.knowledge_curation.graph import KnowledgeGraph
from ayeneh.knowledge_curation.types import (
    AgreementAnalysis,
    AuthorityComparison,
    ComplementarityAnalysis,
    ConceptNode,
    ConflictAnalysis,
    DocumentNode,
    KnowledgeEdge,
    KnowledgeGraphMetrics,
    NormalizedConcept,
    RelationType,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Concept Normalizer
# ---------------------------------------------------------------------------


class ConceptNormalizer:
    """Normalizes concepts across different sources.

    Different books often use different words for similar concepts.
    """

    def __init__(self) -> None:
        self._concepts: dict[str, NormalizedConcept] = {}
        self._alias_map: dict[str, str] = {}  # alias -> canonical

    def normalize(self, concept: str, domain: str = "") -> NormalizedConcept:
        """Normalize a concept to its canonical form."""
        concept_lower = concept.lower().strip()

        # Check if already normalized
        if concept_lower in self._alias_map:
            canonical = self._alias_map[concept_lower]
            return self._concepts[canonical]

        # Check for existing similar concept
        for existing in self._concepts.values():
            if self._are_similar(concept_lower, existing.canonical_name.lower()):
                existing.aliases.append(concept)
                self._alias_map[concept_lower] = existing.canonical_name
                return existing

        # Create new normalized concept
        normalized = NormalizedConcept(
            canonical_name=concept,
            aliases=[concept],
            domain=domain,
        )
        self._concepts[concept_lower] = normalized
        self._alias_map[concept_lower] = concept_lower
        return normalized

    def get_canonical(self, concept: str) -> str:
        """Get the canonical name for a concept."""
        concept_lower = concept.lower().strip()
        return self._alias_map.get(concept_lower, concept)

    def get_related(self, concept: str) -> list[str]:
        """Get all aliases for a concept."""
        canonical = self.get_canonical(concept)
        for normalized in self._concepts.values():
            if normalized.canonical_name.lower() == canonical.lower():
                return normalized.aliases
        return [concept]

    def _are_similar(self, c1: str, c2: str) -> bool:
        """Check if two concepts are similar."""
        # Exact match
        if c1 == c2:
            return True

        # One contains the other
        if c1 in c2 or c2 in c1:
            return True

        # Word overlap
        words1 = set(c1.split())
        words2 = set(c2.split())
        if words1 and words2:
            overlap = len(words1 & words2) / max(len(words1), len(words2))
            if overlap > 0.5:
                return True

        return False


# ---------------------------------------------------------------------------
# Agreement Detector
# ---------------------------------------------------------------------------


class AgreementDetector:
    """Detects when two sources independently support the same claim."""

    def detect(
        self,
        source: DocumentNode,
        target: DocumentNode,
        shared_concepts: list[str],
    ) -> AgreementAnalysis | None:
        """Detect agreement between two sources."""
        if not shared_concepts:
            return None

        # Check domain overlap
        domain_overlap = set(source.domains) & set(target.domains)
        if not domain_overlap:
            return None

        # Check framework overlap
        framework_overlap = set(source.frameworks) & set(target.frameworks)

        # Compute agreement confidence
        confidence = 0.0
        if domain_overlap:
            confidence += 0.3
        if framework_overlap:
            confidence += 0.3
        if shared_concepts:
            confidence += min(0.4, len(shared_concepts) * 0.1)

        if confidence < 0.3:
            return None

        return AgreementAnalysis(
            source_id=source.id,
            target_id=target.id,
            agreement_confidence=min(1.0, confidence),
            supporting_evidence=[f"Shared concepts: {', '.join(shared_concepts[:3])}"],
            scope=f"Domains: {', '.join(domain_overlap)}",
            limitations=["Agreement detected through concept overlap, not explicit endorsement"],
        )


# ---------------------------------------------------------------------------
# Conflict Detector
# ---------------------------------------------------------------------------


class ConflictDetector:
    """Detects conflicts between knowledge sources.

    Never delete conflicts. Represent them.
    """

    def detect(
        self,
        source: DocumentNode,
        target: DocumentNode,
        shared_concepts: list[str],
    ) -> ConflictAnalysis | None:
        """Detect conflict between two sources."""
        if not shared_concepts:
            return None

        # Check for opposing evidence levels
        evidence_conflict = (
            source.evidence_level == "empirical"
            and target.evidence_level == "experiential"
        ) or (
            source.evidence_level == "experiential"
            and target.evidence_level == "empirical"
        )

        # Check for opposing frameworks
        framework_conflict = bool(
            set(source.frameworks) & {"rationalist", "empiricist"}
            and set(target.frameworks) & {"intuitionist", "contemplative"}
        )

        # Check for authority differences
        authority_conflict = (
            source.authority == "primary" and target.authority == "contrarian"
        ) or (
            source.authority == "contrarian" and target.authority == "primary"
        )

        if not (evidence_conflict or framework_conflict or authority_conflict):
            return None

        # Compute conflict confidence
        confidence = 0.0
        what_conflicts: list[str] = []
        why_conflicts: list[str] = []

        if evidence_conflict:
            confidence += 0.4
            what_conflicts.append("evidence type")
            why_conflicts.append(f"Source uses {source.evidence_level}, target uses {target.evidence_level}")

        if framework_conflict:
            confidence += 0.3
            what_conflicts.append("epistemological framework")
            why_conflicts.append("Different approaches to knowledge validation")

        if authority_conflict:
            confidence += 0.3
            what_conflicts.append("authority stance")
            why_conflicts.append("Opposing authority positions")

        return ConflictAnalysis(
            source_id=source.id,
            target_id=target.id,
            conflict_description=f"Sources differ on {', '.join(what_conflicts)}",
            conflict_confidence=min(1.0, confidence),
            what_conflicts=what_conflicts,
            why_conflicts=why_conflicts,
            scope=f"Shared concepts: {', '.join(shared_concepts[:3])}",
            possible_reconciliation="",
            is_resolved=False,
        )


# ---------------------------------------------------------------------------
# Complementarity Detector
# ---------------------------------------------------------------------------


class ComplementarityDetector:
    """Detects complementary perspectives between sources.

    Different perspectives answering different questions.
    """

    def detect(
        self,
        source: DocumentNode,
        target: DocumentNode,
    ) -> ComplementarityAnalysis | None:
        """Detect complementarity between two sources."""
        # Sources must be in different domains to be complementary
        if set(source.domains) & set(target.domains):
            return None

        # Check for different evidence types
        if source.evidence_level == target.evidence_level:
            return None

        # Compute complementarity
        confidence = 0.0
        different_questions: list[str] = []
        different_perspectives: list[str] = []

        if source.evidence_level != target.evidence_level:
            confidence += 0.4
            different_perspectives.append(
                f"{source.evidence_level} vs {target.evidence_level}"
            )

        if set(source.frameworks) != set(target.frameworks):
            confidence += 0.3
            different_perspectives.append("Different frameworks")

        if source.domains != target.domains:
            confidence += 0.3
            different_questions.append(
                f"{source.domains[0] if source.domains else 'unknown'} vs "
                f"{target.domains[0] if target.domains else 'unknown'}"
            )

        if confidence < 0.4:
            return None

        return ComplementarityAnalysis(
            source_id=source.id,
            target_id=target.id,
            complementarity_confidence=min(1.0, confidence),
            different_questions=different_questions,
            different_perspectives=different_perspectives,
            scope=f"Cross-domain: {', '.join(source.domains)} ↔ {', '.join(target.domains)}",
        )


# ---------------------------------------------------------------------------
# Authority Comparator
# ---------------------------------------------------------------------------


class AuthorityComparator:
    """Compares authority levels between sources for specific concepts."""

    def compare(
        self,
        source: DocumentNode,
        target: DocumentNode,
        concept: str,
    ) -> AuthorityComparison:
        """Compare authority of two sources for a concept."""
        authority_rank = {
            "primary": 4,
            "secondary": 3,
            "reference": 2,
            "commentary": 1,
            "contrarian": 0,
            "corroborating": 2,
        }

        source_rank = authority_rank.get(source.authority, 1)
        target_rank = authority_rank.get(target.authority, 1)

        if source_rank > target_rank:
            comparison = "source_higher"
        elif target_rank > source_rank:
            comparison = "target_higher"
        else:
            comparison = "equal"

        return AuthorityComparison(
            concept=concept,
            source_id=source.id,
            target_id=target.id,
            source_authority=source.authority,
            target_authority=target.authority,
            domain=source.domains[0] if source.domains else "unknown",
            comparison=comparison,
        )


# ---------------------------------------------------------------------------
# Knowledge Curation Engine
# ---------------------------------------------------------------------------


class KnowledgeCurationEngine:
    """Single owner of knowledge relationships.

    Continuously builds, validates and maintains a knowledge network
    across all imported books.
    """

    def __init__(self) -> None:
        self._graph = KnowledgeGraph()
        self._normalizer = ConceptNormalizer()
        self._agreement_detector = AgreementDetector()
        self._conflict_detector = ConflictDetector()
        self._complementarity_detector = ComplementarityDetector()
        self._authority_comparator = AuthorityComparator()

    @property
    def graph(self) -> KnowledgeGraph:
        """Access the knowledge graph."""
        return self._graph

    @property
    def normalizer(self) -> ConceptNormalizer:
        """Access the concept normalizer."""
        return self._normalizer

    def add_document(
        self,
        document_id: str,
        title: str,
        author: str = "",
        domains: list[str] | None = None,
        frameworks: list[str] | None = None,
        authority: str = "secondary",
        evidence_level: str = "philosophical",
        traditions: list[str] | None = None,
        metadata: dict | None = None,
    ) -> DocumentNode:
        """Add a document to the knowledge graph."""
        node = DocumentNode(
            node_type="book",
            title=title,
            document_id=document_id,
            author=author,
            domains=domains or [],
            frameworks=frameworks or [],
            authority=authority,
            evidence_level=evidence_level,
            traditions=traditions or [],
            metadata=metadata or {},
        )
        self._graph.add_node(node)
        logger.info("document_added", document_id=document_id, title=title)
        return node

    def add_chapter(
        self,
        chapter_id: str,
        book_id: str,
        title: str,
        domains: list[str] | None = None,
        frameworks: list[str] | None = None,
        authority: str = "secondary",
        evidence_level: str = "philosophical",
    ) -> DocumentNode:
        """Add a chapter to the knowledge graph."""
        node = DocumentNode(
            node_type="chapter",
            title=title,
            document_id=chapter_id,
            book_id=book_id,
            domains=domains or [],
            frameworks=frameworks or [],
            authority=authority,
            evidence_level=evidence_level,
        )
        self._graph.add_node(node)

        # Connect chapter to book
        book_node = self._graph.get_node(book_id)
        if book_node:
            edge = KnowledgeEdge(
                source_id=chapter_id,
                target_id=book_id,
                relation_type=RelationType.SPECIALIZES,
                confidence=0.9,
                reason="Chapter is part of book",
            )
            self._graph.add_edge(edge)

        return node

    def add_concept(
        self,
        concept: str,
        domain: str = "",
        definition: str = "",
    ) -> ConceptNode:
        """Add a normalized concept to the graph."""
        normalized = self._normalizer.normalize(concept, domain)

        node = ConceptNode(
            node_type="concept",
            title=normalized.canonical_name,
            canonical_name=normalized.canonical_name,
            aliases=normalized.aliases,
            definition=definition or normalized.definition,
            domain=domain or normalized.domain,
        )
        self._graph.add_node(node)
        return node

    def detect_relations(
        self,
        source_id: str,
        target_id: str,
        shared_concepts: list[str] | None = None,
    ) -> list[KnowledgeEdge]:
        """Detect and create relations between two documents."""
        source = self._graph.get_node(source_id)
        target = self._graph.get_node(target_id)

        if not source or not target:
            return []

        if not isinstance(source, DocumentNode) or not isinstance(target, DocumentNode):
            return []

        edges: list[KnowledgeEdge] = []

        # Detect agreement
        agreement = self._agreement_detector.detect(
            source, target, shared_concepts or [],
        )
        if agreement:
            edge = KnowledgeEdge(
                source_id=source_id,
                target_id=target_id,
                relation_type=RelationType.SUPPORTS,
                confidence=agreement.agreement_confidence,
                evidence=agreement.supporting_evidence,
                reason="Concept overlap detected",
                scope=agreement.scope,
                limitations=agreement.limitations,
            )
            self._graph.add_edge(edge)
            edges.append(edge)

        # Detect conflict
        conflict = self._conflict_detector.detect(
            source, target, shared_concepts or [],
        )
        if conflict:
            edge = KnowledgeEdge(
                source_id=source_id,
                target_id=target_id,
                relation_type=RelationType.CONTRADICTS,
                confidence=conflict.conflict_confidence,
                evidence=conflict.what_conflicts,
                reason=conflict.conflict_description,
                scope=conflict.scope,
                limitations=["Conflict detected through structural analysis"],
            )
            self._graph.add_edge(edge)
            edges.append(edge)

        # Detect complementarity
        complement = self._complementarity_detector.detect(source, target)
        if complement:
            edge = KnowledgeEdge(
                source_id=source_id,
                target_id=target_id,
                relation_type=RelationType.COMPLEMENTS,
                confidence=complement.complementarity_confidence,
                evidence=complement.different_perspectives,
                reason="Cross-domain complementary perspectives",
                scope=complement.scope,
            )
            self._graph.add_edge(edge)
            edges.append(edge)

        # Compare authority
        if shared_concepts:
            authority = self._authority_comparator.compare(
                source, target, shared_concepts[0],
            )
            if authority.comparison != "equal":
                edge = KnowledgeEdge(
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=RelationType.DIFFERENT_SCOPE,
                    confidence=0.7,
                    evidence=[f"Authority: {authority.comparison}"],
                    reason=f"Authority comparison for {shared_concepts[0]}",
                    source_authority=authority.source_authority,
                    target_authority=authority.target_authority,
                    authority_domain=authority.domain,
                )
                self._graph.add_edge(edge)
                edges.append(edge)

        logger.info(
            "relations_detected",
            source_id=source_id,
            target_id=target_id,
            edges_created=len(edges),
        )

        return edges

    def find_agreements(
        self, node_id: str, min_confidence: float = 0.5,
    ) -> list[KnowledgeEdge]:
        """Find all agreements for a node."""
        edges = self._graph.get_edges_from_node(node_id)
        return [
            e
            for e in edges
            if e.relation_type == RelationType.SUPPORTS
            and e.confidence >= min_confidence
        ]

    def find_conflicts(
        self, node_id: str, min_confidence: float = 0.5,
    ) -> list[KnowledgeEdge]:
        """Find all conflicts for a node."""
        edges = self._graph.get_edges_from_node(node_id)
        return [
            e
            for e in edges
            if e.relation_type == RelationType.CONTRADICTS
            and e.confidence >= min_confidence
        ]

    def find_complements(
        self, node_id: str, min_confidence: float = 0.5,
    ) -> list[KnowledgeEdge]:
        """Find all complementary sources for a node."""
        edges = self._graph.get_edges_from_node(node_id)
        return [
            e
            for e in edges
            if e.relation_type == RelationType.COMPLEMENTS
            and e.confidence >= min_confidence
        ]

    def find_authority_for_concept(
        self, concept: str, min_confidence: float = 0.5,
    ) -> list[KnowledgeEdge]:
        """Find authoritative sources for a concept."""
        concept_node = None
        for node in self._graph.get_nodes_by_type("concept"):
            if hasattr(node, "canonical_name") and node.canonical_name.lower() == concept.lower():
                concept_node = node
                break

        if not concept_node:
            return []

        edges = self._graph.get_edges_to_node(concept_node.id)
        return [
            e
            for e in edges
            if e.relation_type == RelationType.SUPPORTS
            and e.confidence >= min_confidence
        ]

    def get_metrics(self) -> KnowledgeGraphMetrics:
        """Get knowledge graph metrics."""
        return self._graph.get_metrics()

    def get_source_context(self, node_id: str) -> dict[str, Any]:
        """Get complete context about a source including relations."""
        node = self._graph.get_node(node_id)
        if not node:
            return {}

        agreements = self.find_agreements(node_id)
        conflicts = self.find_conflicts(node_id)
        complements = self.find_complements(node_id)

        return {
            "node": {
                "id": node.id,
                "type": node.node_type,
                "title": node.title,
            },
            "agreements": [
                {
                    "target_id": e.target_id,
                    "confidence": e.confidence,
                    "reason": e.reason,
                }
                for e in agreements
            ],
            "conflicts": [
                {
                    "target_id": e.target_id,
                    "confidence": e.confidence,
                    "reason": e.reason,
                }
                for e in conflicts
            ],
            "complements": [
                {
                    "target_id": e.target_id,
                    "confidence": e.confidence,
                    "reason": e.reason,
                }
                for e in complements
            ],
        }
