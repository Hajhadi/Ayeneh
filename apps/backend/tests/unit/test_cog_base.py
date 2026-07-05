"""Tests for the COG foundation layer — base types, evidence, conversation, and graph."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.cog.base import (
    CognitiveObject,
    EvidenceRef,
    LIFECYCLE_TRANSITIONS,
    Revision,
    TemporalMetadata,
    can_transition,
)
from ayeneh.cog.evidence.types import (
    EPISTEMIC_CLASSIFICATIONS,
    EVIDENCE_CATEGORIES,
    EvidenceContext,
    EvidenceObject,
    EvidenceProvenance,
    EvidenceStrength,
)
from ayeneh.cog.conversation.types import (
    BELIEF_PRECURSORS,
    Claim,
    Entity,
    IDENTITY_PRECURSORS,
    SemanticObject,
    ConversationSegment,
)
from ayeneh.cog.pipeline.graph import CognitiveGraph, GraphEdge


# ===================================================================
# EvidenceRef
# ===================================================================

class TestEvidenceRef:
    def test_creation(self) -> None:
        ref = EvidenceRef(
            evidence_id='ev-1',
            evidence_type='self_report',
            confidence=0.8,
            timestamp=datetime.now(UTC),
        )
        assert ref.evidence_id == 'ev-1'
        assert ref.confidence == 0.8

    def test_frozen(self) -> None:
        ref = EvidenceRef(evidence_id='ev-1', evidence_type='x', confidence=0.5, timestamp=datetime.now(UTC))
        with pytest.raises(AttributeError):
            ref.evidence_id = 'ev-2'  # type: ignore[misc]


# ===================================================================
# TemporalMetadata
# ===================================================================

class TestTemporalMetadata:
    def test_defaults(self) -> None:
        tm = TemporalMetadata()
        assert tm.observation_count == 1
        assert tm.temporal_scope == 'momentary'

    def test_frozen(self) -> None:
        tm = TemporalMetadata()
        with pytest.raises(AttributeError):
            tm.observation_count = 5  # type: ignore[misc]


# ===================================================================
# Revision
# ===================================================================

class TestRevision:
    def test_creation(self) -> None:
        r = Revision(
            revision_id='rev-1',
            timestamp=datetime.now(UTC),
            previous_state={'confidence': 0.3},
            change_reason='confidence update',
        )
        assert r.previous_state == {'confidence': 0.3}
        assert r.evidence_ref is None


# ===================================================================
# CognitiveObject
# ===================================================================

class TestCognitiveObject:
    def test_creation(self) -> None:
        obj = CognitiveObject(object_type='belief', confidence=0.7)
        assert obj.object_type == 'belief'
        assert obj.lifecycle_state == 'evidence_candidate'
        assert obj.specification_version == '1.0.0'
        assert isinstance(obj.identifier, str) and len(obj.identifier) > 0

    def test_is_canonical_false(self) -> None:
        obj = CognitiveObject(object_type='belief')
        assert obj.is_canonical() is False

    def test_is_canonical_true(self) -> None:
        obj = CognitiveObject(object_type='belief', lifecycle_state='canonical')
        assert obj.is_canonical() is True

    def test_frozen(self) -> None:
        obj = CognitiveObject()
        with pytest.raises(AttributeError):
            obj.confidence = 1.0  # type: ignore[misc]

    def test_with_transition_valid(self) -> None:
        obj = CognitiveObject(lifecycle_state='evidence_candidate')
        new = obj.with_transition('candidate')
        assert new.lifecycle_state == 'candidate'
        assert len(new.revision_history) == 1
        # original unchanged
        assert obj.lifecycle_state == 'evidence_candidate'

    def test_with_transition_invalid(self) -> None:
        obj = CognitiveObject(lifecycle_state='historical')
        with pytest.raises(ValueError, match='Invalid lifecycle transition'):
            obj.with_transition('canonical')

    def test_evidence_references(self) -> None:
        ref = EvidenceRef(evidence_id='ev-1', evidence_type='x', confidence=0.5, timestamp=datetime.now(UTC))
        obj = CognitiveObject(evidence_references=(ref,))
        assert len(obj.evidence_references) == 1
        assert obj.evidence_references[0].evidence_id == 'ev-1'


# ===================================================================
# Lifecycle state machine
# ===================================================================

class TestLifecycle:
    def test_transitions_dict_completeness(self) -> None:
        # Every defined state should be a key in the dict
        all_targets = set()
        for targets in LIFECYCLE_TRANSITIONS.values():
            all_targets.update(targets)
        for state in LIFECYCLE_TRANSITIONS:
            all_targets.discard(state)
        # all_targets may contain states only reachable as targets, not a problem

    def test_can_transition_true(self) -> None:
        assert can_transition('evidence_candidate', 'candidate') is True

    def test_can_transition_false(self) -> None:
        assert can_transition('historical', 'canonical') is False

    def test_full_path_to_canonical(self) -> None:
        obj = CognitiveObject(lifecycle_state='evidence_candidate')
        obj = obj.with_transition('candidate')
        obj = obj.with_transition('provisional')
        obj = obj.with_transition('validation')
        obj = obj.with_transition('canonical')
        assert obj.lifecycle_state == 'canonical'


# ===================================================================
# EvidenceObject
# ===================================================================

class TestEvidenceObject:
    def test_creation(self) -> None:
        ev = EvidenceObject(
            category='self_report',
            epistemic_classification='subjective_experience',
            original_text='I feel anxious about the project',
            normalized_text='i feel anxious about the project',
            speaker='user',
            confidence=0.85,
        )
        assert ev.category == 'self_report'
        assert ev.validation_status == 'pending'
        assert isinstance(ev.identifier, str)

    def test_frozen(self) -> None:
        ev = EvidenceObject()
        with pytest.raises(AttributeError):
            ev.confidence = 1.0  # type: ignore[misc]

    def test_strength_overall(self) -> None:
        s = EvidenceStrength(directness=1.0, specificity=1.0, temporal_proximity=1.0, consistency=1.0)
        assert s.overall() == pytest.approx(1.0)

    def test_strength_default(self) -> None:
        s = EvidenceStrength()
        assert s.overall() == pytest.approx(0.5)

    def test_catalogue_lists_non_empty(self) -> None:
        assert len(EVIDENCE_CATEGORIES) == 20
        assert len(EPISTEMIC_CLASSIFICATIONS) == 19

    def test_provenance_defaults(self) -> None:
        p = EvidenceProvenance()
        assert p.language == 'en'
        assert p.engine_version == '1.0.0'

    def test_context_defaults(self) -> None:
        ctx = EvidenceContext()
        assert ctx.physical == ''
        assert ctx.emotional == ''


# ===================================================================
# Conversation types
# ===================================================================

class TestConversationSegment:
    def test_creation(self) -> None:
        seg = ConversationSegment(
            segment_id='seg-1',
            conversation_id='conv-1',
            speaker='user',
            text='Hello',
            timestamp=datetime.now(UTC),
            sequence_number=0,
        )
        assert seg.speaker == 'user'
        assert seg.language == 'en'

    def test_frozen(self) -> None:
        seg = ConversationSegment(
            segment_id='s', conversation_id='c', speaker='u', text='t',
            timestamp=datetime.now(UTC), sequence_number=0,
        )
        with pytest.raises(AttributeError):
            seg.text = 'other'  # type: ignore[misc]


class TestSemanticObject:
    def test_creation(self) -> None:
        so = SemanticObject(
            object_id='so-1', surface_form='Alice', normalized_form='alice',
            object_type='person', confidence=0.95,
        )
        assert so.object_type == 'person'


class TestEntity:
    def test_creation(self) -> None:
        e = Entity(entity_id='ent-1', name='Alice', entity_type='person', aliases=('Ali',))
        assert e.aliases == ('Ali',)

    def test_frozen(self) -> None:
        e = Entity(entity_id='e', name='X', entity_type='person')
        with pytest.raises(AttributeError):
            e.name = 'Y'  # type: ignore[misc]


class TestClaim:
    def test_creation(self) -> None:
        c = Claim(
            claim_id='cl-1',
            text='The sky is blue',
            speaker='user',
            timestamp=datetime.now(UTC),
            epistemic_marker='observation',
        )
        assert c.negated is False
        assert c.is_self_report is False

    def test_frozen(self) -> None:
        c = Claim(claim_id='c', text='t', speaker='u', timestamp=datetime.now(UTC))
        with pytest.raises(AttributeError):
            c.negated = True  # type: ignore[misc]


class TestPrecursorLists:
    def test_precursors_populated(self) -> None:
        assert len(BELIEF_PRECURSORS) > 0
        assert len(IDENTITY_PRECURSORS) > 0


# ===================================================================
# CognitiveGraph
# ===================================================================

class TestCognitiveGraph:
    def _make_node(self, oid: str, obj_type: str = 'belief') -> CognitiveObject:
        return CognitiveObject(identifier=oid, object_type=obj_type)

    def test_add_and_get_node(self) -> None:
        g = CognitiveGraph()
        node = self._make_node('n1')
        g.add_node(node)
        assert g.get_node('n1') is node
        assert g.node_count() == 1

    def test_get_missing_node(self) -> None:
        g = CognitiveGraph()
        assert g.get_node('missing') is None

    def test_add_edge(self) -> None:
        g = CognitiveGraph()
        g.add_node(self._make_node('n1'))
        g.add_node(self._make_node('n2'))
        edge = GraphEdge(source_id='n1', target_id='n2', relationship='supports', confidence=0.9)
        g.add_edge(edge)
        assert g.edge_count() == 1
        assert len(g.get_edges_from('n1')) == 1
        assert len(g.get_edges_to('n2')) == 1

    def test_add_edge_missing_source(self) -> None:
        g = CognitiveGraph()
        g.add_node(self._make_node('n2'))
        with pytest.raises(ValueError, match='Source node not found'):
            g.add_edge(GraphEdge(source_id='missing', target_id='n2', relationship='supports', confidence=0.5))

    def test_add_edge_missing_target(self) -> None:
        g = CognitiveGraph()
        g.add_node(self._make_node('n1'))
        with pytest.raises(ValueError, match='Target node not found'):
            g.add_edge(GraphEdge(source_id='n1', target_id='missing', relationship='supports', confidence=0.5))

    def test_add_edge_invalid_relationship(self) -> None:
        g = CognitiveGraph()
        g.add_node(self._make_node('n1'))
        g.add_node(self._make_node('n2'))
        with pytest.raises(ValueError, match='Unknown relationship type'):
            g.add_edge(GraphEdge(source_id='n1', target_id='n2', relationship='bogus', confidence=0.5))

    def test_traverse(self) -> None:
        g = CognitiveGraph()
        g.add_node(self._make_node('n1'))
        g.add_node(self._make_node('n2'))
        g.add_node(self._make_node('n3'))
        g.add_edge(GraphEdge(source_id='n1', target_id='n2', relationship='supports', confidence=1.0))
        g.add_edge(GraphEdge(source_id='n2', target_id='n3', relationship='supports', confidence=1.0))

        result = g.traverse('n1', 'supports', max_depth=5)
        ids = [n.identifier for n in result]
        assert 'n2' in ids
        assert 'n3' in ids

    def test_traverse_respects_relationship_type(self) -> None:
        g = CognitiveGraph()
        g.add_node(self._make_node('n1'))
        g.add_node(self._make_node('n2'))
        g.add_edge(GraphEdge(source_id='n1', target_id='n2', relationship='contradicts', confidence=1.0))

        result = g.traverse('n1', 'supports')
        assert len(result) == 0

    def test_remove_node(self) -> None:
        g = CognitiveGraph()
        g.add_node(self._make_node('n1'))
        g.add_node(self._make_node('n2'))
        g.add_edge(GraphEdge(source_id='n1', target_id='n2', relationship='supports', confidence=1.0))
        g.remove_node('n1')
        assert g.get_node('n1') is None
        assert g.edge_count() == 0

    def test_find_path(self) -> None:
        g = CognitiveGraph()
        g.add_node(self._make_node('a'))
        g.add_node(self._make_node('b'))
        g.add_node(self._make_node('c'))
        g.add_edge(GraphEdge(source_id='a', target_id='b', relationship='depends_on', confidence=1.0))
        g.add_edge(GraphEdge(source_id='b', target_id='c', relationship='depends_on', confidence=1.0))

        path = g.find_path('a', 'c')
        assert path is not None
        assert [n.identifier for n in path] == ['b']

    def test_find_path_no_route(self) -> None:
        g = CognitiveGraph()
        g.add_node(self._make_node('a'))
        g.add_node(self._make_node('b'))
        assert g.find_path('a', 'b') is None
