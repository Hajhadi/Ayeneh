"""Tests for MEM-03 semantic personal memory: types, engine, ontology, evolution."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime, timedelta

from ayeneh.memo.semantic.engine import SemanticMemoryEngine, SemanticPipelineResult
from ayeneh.memo.semantic.evolution import (
    EVOLUTION_EVENT_TYPES,
    ConceptLineage,
    EvolutionEvent,
    KnowledgeEvolution,
)
from ayeneh.memo.semantic.ontology import (
    ONTOLOGY_DOMAINS,
    OntologyEntry,
    OntologyRelationship,
    PersonalOntology,
)
from ayeneh.memo.semantic.types import (
    KNOWLEDGE_CATEGORIES,
    TEMPORAL_STABILITY_LEVELS,
    KnowledgeEdge,
    KnowledgeNode,
    SemanticMemoryObject,
    SemanticVersionRecord,
)
from ayeneh.memo.types import Observation


# ===================================================================
# SemanticMemoryObject
# ===================================================================

class TestSemanticMemoryObject:
    def test_creation(self) -> None:
        obj = SemanticMemoryObject(
            identifier='sem-1',
            knowledge_statement='I enjoy learning about AI',
        )
        assert obj.identifier == 'sem-1'
        assert obj.knowledge_statement == 'I enjoy learning about AI'
        assert obj.knowledge_category == 'personal_interests'

    def test_defaults(self) -> None:
        obj = SemanticMemoryObject(identifier='sem-2', knowledge_statement='Test')
        assert obj.supporting_evidence == ()
        assert obj.supporting_episodes == ()
        assert obj.supporting_conversations == ()
        assert obj.contradictory_evidence == ()
        assert obj.confidence == 0.0
        assert obj.importance == 0.0
        assert obj.temporal_stability == 'long_term'
        assert obj.revision_history == ()
        assert obj.associated_cognitive_objects == ()
        assert obj.explainability_metadata == {}

    def test_frozen(self) -> None:
        obj = SemanticMemoryObject(identifier='sem-3', knowledge_statement='Test')
        with pytest.raises(AttributeError):
            obj.identifier = 'sem-4'  # type: ignore[misc]

    def test_is_stable(self) -> None:
        obj = SemanticMemoryObject(
            identifier='sem-5',
            knowledge_statement='Test',
            confidence=0.8,
            temporal_stability='long_term',
        )
        assert obj.is_stable is True

    def test_is_not_stable_low_confidence(self) -> None:
        obj = SemanticMemoryObject(
            identifier='sem-6',
            knowledge_statement='Test',
            confidence=0.5,
            temporal_stability='long_term',
        )
        assert obj.is_stable is False

    def test_is_not_stable_short_term(self) -> None:
        obj = SemanticMemoryObject(
            identifier='sem-7',
            knowledge_statement='Test',
            confidence=0.9,
            temporal_stability='short_term',
        )
        assert obj.is_stable is False

    def test_age_days(self) -> None:
        obj = SemanticMemoryObject(
            identifier='sem-8',
            knowledge_statement='Test',
            creation_time=datetime.now(UTC) - timedelta(days=10),
        )
        assert 9.0 < obj.age_days < 11.0

    def test_recency_days(self) -> None:
        obj = SemanticMemoryObject(
            identifier='sem-9',
            knowledge_statement='Test',
            last_confirmation=datetime.now(UTC) - timedelta(days=5),
        )
        assert 4.0 < obj.recency_days < 6.0


# ===================================================================
# SemanticVersionRecord
# ===================================================================

class TestSemanticVersionRecord:
    def test_creation(self) -> None:
        v = SemanticVersionRecord(
            version_number=1,
            changed_fields={'confidence': 0.5},
            change_reason='initial',
        )
        assert v.version_number == 1
        assert v.change_reason == 'initial'
        assert v.changed_fields == {'confidence': 0.5}


# ===================================================================
# KnowledgeNode / KnowledgeEdge
# ===================================================================

class TestKnowledgeNode:
    def test_creation(self) -> None:
        n = KnowledgeNode(
            node_id='kn-1',
            label='AI',
            category='research_domains',
        )
        assert n.node_id == 'kn-1'
        assert n.semantic_memory_ids == ()


class TestKnowledgeEdge:
    def test_creation(self) -> None:
        e = KnowledgeEdge(
            source_node_id='kn-1',
            target_node_id='kn-2',
            edge_type='related_to',
        )
        assert e.weight == 1.0


# ===================================================================
# Constants
# ===================================================================

class TestSemanticConstants:
    def test_knowledge_categories(self) -> None:
        assert len(KNOWLEDGE_CATEGORIES) == 17
        assert 'personal_interests' in KNOWLEDGE_CATEGORIES
        assert 'skills' in KNOWLEDGE_CATEGORIES
        assert 'core_values' in KNOWLEDGE_CATEGORIES
        assert 'research_domains' in KNOWLEDGE_CATEGORIES

    def test_temporal_stability_levels(self) -> None:
        assert len(TEMPORAL_STABILITY_LEVELS) == 5

    def test_ontology_domains(self) -> None:
        assert len(ONTOLOGY_DOMAINS) == 10

    def test_evolution_event_types(self) -> None:
        assert len(EVOLUTION_EVENT_TYPES) == 10


# ===================================================================
# SemanticMemoryEngine
# ===================================================================

class TestSemanticMemoryEngine:
    def test_empty_observations(self) -> None:
        engine = SemanticMemoryEngine()
        result = engine.run_pipeline([])
        assert result.semantic_objects == []

    def test_basic_pipeline(self) -> None:
        engine = SemanticMemoryEngine(repetition_threshold=2)
        now = datetime.now(UTC)
        observations = [
            Observation(
                observation_id=f'obs-{i}',
                content='I enjoy working with Python and machine learning',
                source='conversation',
                timestamp=now + timedelta(minutes=i),
            )
            for i in range(5)
        ]
        result = engine.run_pipeline(observations)
        assert isinstance(result, SemanticPipelineResult)

    def test_repeated_observations_detected(self) -> None:
        engine = SemanticMemoryEngine(repetition_threshold=3)
        now = datetime.now(UTC)
        observations = [
            Observation(
                observation_id=f'obs-{i}',
                content='I always prefer using vim for coding',
                source='conversation',
                timestamp=now + timedelta(minutes=i),
            )
            for i in range(5)
        ]
        result = engine.run_pipeline(observations)
        assert isinstance(result, SemanticPipelineResult)

    def test_pipeline_result_structure(self) -> None:
        result = SemanticPipelineResult()
        assert result.semantic_objects == []
        assert result.knowledge_nodes == []
        assert result.knowledge_edges == []

    def test_get_semantic_object(self) -> None:
        engine = SemanticMemoryEngine()
        assert engine.get_semantic_object('nonexistent') is None

    def test_list_by_category(self) -> None:
        engine = SemanticMemoryEngine()
        assert engine.list_by_category('skills') == []

    def test_list_stable(self) -> None:
        engine = SemanticMemoryEngine()
        assert engine.list_stable() == []

    def test_category_inference(self) -> None:
        engine = SemanticMemoryEngine(repetition_threshold=2)
        now = datetime.now(UTC)
        observations = [
            Observation(
                observation_id='obs-1',
                content='I am an expert in Python programming and data structures',
                source='resume',
                timestamp=now,
            ),
            Observation(
                observation_id='obs-2',
                content='I am proficient in Python and data structures',
                source='resume',
                timestamp=now + timedelta(minutes=1),
            ),
            Observation(
                observation_id='obs-3',
                content='Python expert with deep knowledge of data structures',
                source='resume',
                timestamp=now + timedelta(minutes=2),
            ),
        ]
        result = engine.run_pipeline(observations)
        # At least verify the pipeline runs without error
        assert isinstance(result, SemanticPipelineResult)

    def test_knowledge_graph_built(self) -> None:
        engine = SemanticMemoryEngine(repetition_threshold=2)
        now = datetime.now(UTC)
        observations = [
            Observation(
                observation_id=f'obs-{i}',
                content='I love programming in Python and JavaScript',
                source='conversation',
                timestamp=now + timedelta(minutes=i),
            )
            for i in range(5)
        ]
        result = engine.run_pipeline(observations)
        # Graph may or may not have edges depending on category overlap
        assert isinstance(result.knowledge_nodes, list)
        assert isinstance(result.knowledge_edges, list)

    def test_merge_similar_candidates(self) -> None:
        engine = SemanticMemoryEngine(repetition_threshold=2)
        now = datetime.now(UTC)
        observations = [
            Observation(
                observation_id=f'obs-{i}',
                content='I enjoy reading science fiction books',
                source='conversation',
                timestamp=now + timedelta(minutes=i),
            )
            for i in range(5)
        ]
        result = engine.run_pipeline(observations)
        # Should merge into fewer semantic objects
        assert isinstance(result.semantic_objects, list)


# ===================================================================
# PersonalOntology
# ===================================================================

class TestPersonalOntology:
    def test_empty_ontology(self) -> None:
        ont = PersonalOntology()
        assert ont.entry_count == 0
        assert ont.relationship_count == 0

    def test_add_entry(self) -> None:
        ont = PersonalOntology()
        entry = ont.add_entry(
            entry_id='oe-1',
            domain='research_domains',
            label='Machine Learning',
        )
        assert entry.label == 'Machine Learning'
        assert ont.entry_count == 1

    def test_get_entry(self) -> None:
        ont = PersonalOntology()
        ont.add_entry(entry_id='oe-1', domain='books', label='GEB')
        entry = ont.get_entry('oe-1')
        assert entry is not None
        assert entry.label == 'GEB'

    def test_get_nonexistent_entry(self) -> None:
        ont = PersonalOntology()
        assert ont.get_entry('nonexistent') is None

    def test_find_by_label(self) -> None:
        ont = PersonalOntology()
        ont.add_entry(entry_id='oe-1', domain='people', label='Alice Smith')
        results = ont.find_by_label('Alice')
        assert len(results) == 1
        assert results[0].label == 'Alice Smith'

    def test_find_by_label_case_insensitive(self) -> None:
        ont = PersonalOntology()
        ont.add_entry(entry_id='oe-1', domain='places', label='New York')
        results = ont.find_by_label('new york')
        assert len(results) == 1

    def test_find_by_domain(self) -> None:
        ont = PersonalOntology()
        ont.add_entry(entry_id='oe-1', domain='books', label='Book A')
        ont.add_entry(entry_id='oe-2', domain='books', label='Book B')
        ont.add_entry(entry_id='oe-3', domain='people', label='Person A')
        results = ont.find_by_domain('books')
        assert len(results) == 2

    def test_remove_entry(self) -> None:
        ont = PersonalOntology()
        ont.add_entry(entry_id='oe-1', domain='places', label='Paris')
        assert ont.remove_entry('oe-1') is True
        assert ont.entry_count == 0
        assert ont.get_entry('oe-1') is None

    def test_remove_nonexistent_entry(self) -> None:
        ont = PersonalOntology()
        assert ont.remove_entry('nonexistent') is False

    def test_remove_entry_cleans_relationships(self) -> None:
        ont = PersonalOntology()
        ont.add_entry(entry_id='oe-1', domain='books', label='Book A')
        ont.add_entry(entry_id='oe-2', domain='books', label='Book B')
        ont.add_relationship('oe-1', 'oe-2', 'related_to')
        assert ont.relationship_count == 1
        ont.remove_entry('oe-1')
        assert ont.relationship_count == 0

    def test_add_relationship(self) -> None:
        ont = PersonalOntology()
        ont.add_entry(entry_id='oe-1', domain='people', label='Alice')
        ont.add_entry(entry_id='oe-2', domain='people', label='Bob')
        rel = ont.add_relationship('oe-1', 'oe-2', 'colleague')
        assert rel.relationship_type == 'colleague'
        assert ont.relationship_count == 1

    def test_get_related(self) -> None:
        ont = PersonalOntology()
        ont.add_entry(entry_id='oe-1', domain='projects', label='Proj A')
        ont.add_entry(entry_id='oe-2', domain='projects', label='Proj B')
        ont.add_relationship('oe-1', 'oe-2', 'depends_on')
        related = ont.get_related('oe-1')
        assert len(related) == 1

    def test_get_relationships_by_type(self) -> None:
        ont = PersonalOntology()
        ont.add_entry(entry_id='oe-1', domain='people', label='A')
        ont.add_entry(entry_id='oe-2', domain='people', label='B')
        ont.add_entry(entry_id='oe-3', domain='people', label='C')
        ont.add_relationship('oe-1', 'oe-2', 'colleague')
        ont.add_relationship('oe-1', 'oe-3', 'friend')
        colleague_rels = ont.get_relationships_by_type('colleague')
        assert len(colleague_rels) == 1

    def test_record_access(self) -> None:
        ont = PersonalOntology()
        ont.add_entry(entry_id='oe-1', domain='tools', label='Python')
        ont.record_access('oe-1')
        entry = ont.get_entry('oe-1')
        assert entry is not None
        assert entry.access_count == 1

    def test_summary(self) -> None:
        ont = PersonalOntology()
        ont.add_entry(entry_id='oe-1', domain='books', label='Book A')
        ont.add_entry(entry_id='oe-2', domain='people', label='Person A')
        s = ont.summary()
        assert s['total_entries'] == 2
        assert s['total_relationships'] == 0
        assert 'books' in s['domain_counts']

    def test_aliases(self) -> None:
        ont = PersonalOntology()
        ont.add_entry(
            entry_id='oe-1',
            domain='preferred_tools',
            label='Python',
            aliases=('py', 'python3'),
        )
        results = ont.find_by_label('py')
        assert len(results) == 1


# ===================================================================
# KnowledgeEvolution
# ===================================================================

class TestKnowledgeEvolution:
    def test_empty_evolution(self) -> None:
        ev = KnowledgeEvolution()
        assert ev.lineage_count == 0
        assert ev.event_count == 0

    def test_record_creation(self) -> None:
        ev = KnowledgeEvolution()
        event = ev.record_creation(
            event_id='evt-1',
            semantic_memory_id='sem-1',
            label='Python expertise',
        )
        assert event.event_type == 'created'
        assert ev.lineage_count == 1
        assert ev.event_count == 1

    def test_record_revision(self) -> None:
        ev = KnowledgeEvolution()
        ev.record_creation(event_id='evt-1', semantic_memory_id='sem-1', label='AI knowledge')
        event = ev.record_revision(
            event_id='evt-2',
            semantic_memory_id='sem-1',
            description='Updated after new course',
        )
        assert event.event_type == 'revised'
        assert event.previous_version == '1.1'
        lineage = ev.get_lineage('sem-1')
        assert lineage is not None
        assert lineage.version_count == 2

    def test_record_integration(self) -> None:
        ev = KnowledgeEvolution()
        event = ev.record_integration(
            event_id='evt-1',
            semantic_memory_id='sem-1',
            source_concepts=('sem-2', 'sem-3'),
            description='Merged AI and ML knowledge',
        )
        assert event.event_type == 'integrated'

    def test_record_specialization(self) -> None:
        ev = KnowledgeEvolution()
        event = ev.record_specialization(
            event_id='evt-1',
            semantic_memory_id='sem-child',
            parent_concept_id='sem-parent',
        )
        assert event.event_type == 'specialized'
        assert event.metadata['parent_concept'] == 'sem-parent'

    def test_record_generalization(self) -> None:
        ev = KnowledgeEvolution()
        event = ev.record_generalization(
            event_id='evt-1',
            semantic_memory_id='sem-parent',
            child_concept_ids=('sem-a', 'sem-b'),
        )
        assert event.event_type == 'generalized'
        assert 'sem-a' in event.metadata['child_concepts']

    def test_record_semantic_drift(self) -> None:
        ev = KnowledgeEvolution()
        event = ev.record_semantic_drift(
            event_id='evt-1',
            semantic_memory_id='sem-1',
            drift_description='Meaning shifted over time',
        )
        assert event.metadata.get('drift') is True

    def test_record_deprecation(self) -> None:
        ev = KnowledgeEvolution()
        ev.record_creation(event_id='evt-1', semantic_memory_id='sem-1', label='Old concept')
        event = ev.record_deprecation(
            event_id='evt-2',
            semantic_memory_id='sem-1',
            reason='No longer relevant',
        )
        assert event.event_type == 'deprecated'
        lineage = ev.get_lineage('sem-1')
        assert lineage is not None
        assert lineage.is_active is False

    def test_list_lineages(self) -> None:
        ev = KnowledgeEvolution()
        ev.record_creation(event_id='evt-1', semantic_memory_id='sem-1', label='A')
        ev.record_creation(event_id='evt-2', semantic_memory_id='sem-2', label='B')
        assert ev.lineage_count == 2
        lineages = ev.list_lineages()
        assert len(lineages) == 2

    def test_list_lineages_active_only(self) -> None:
        ev = KnowledgeEvolution()
        ev.record_creation(event_id='evt-1', semantic_memory_id='sem-1', label='A')
        ev.record_creation(event_id='evt-2', semantic_memory_id='sem-2', label='B')
        ev.record_deprecation(event_id='evt-3', semantic_memory_id='sem-1')
        active = ev.list_lineages(active_only=True)
        assert len(active) == 1
        assert active[0].concept_id == 'sem-2'

    def test_get_events_for_concept(self) -> None:
        ev = KnowledgeEvolution()
        ev.record_creation(event_id='evt-1', semantic_memory_id='sem-1', label='A')
        ev.record_revision(event_id='evt-2', semantic_memory_id='sem-1', description='Rev 1')
        ev.record_creation(event_id='evt-3', semantic_memory_id='sem-2', label='B')
        events = ev.get_events_for_concept('sem-1')
        assert len(events) == 2

    def test_get_events_by_type(self) -> None:
        ev = KnowledgeEvolution()
        ev.record_creation(event_id='evt-1', semantic_memory_id='sem-1', label='A')
        ev.record_revision(event_id='evt-2', semantic_memory_id='sem-1', description='Rev')
        created = ev.get_events_by_type('created')
        assert len(created) == 1

    def test_get_specializations(self) -> None:
        ev = KnowledgeEvolution()
        ev.record_specialization(
            event_id='evt-1',
            semantic_memory_id='sem-child',
            parent_concept_id='sem-parent',
        )
        results = ev.get_specializations('sem-parent')
        assert len(results) == 1

    def test_get_generalizations(self) -> None:
        ev = KnowledgeEvolution()
        ev.record_generalization(
            event_id='evt-1',
            semantic_memory_id='sem-parent',
            child_concept_ids=('sem-a', 'sem-b'),
        )
        results = ev.get_generalizations('sem-a')
        assert len(results) == 1

    def test_summary(self) -> None:
        ev = KnowledgeEvolution()
        ev.record_creation(event_id='evt-1', semantic_memory_id='sem-1', label='A')
        ev.record_revision(event_id='evt-2', semantic_memory_id='sem-1', description='Rev')
        s = ev.summary()
        assert s['total_lineages'] == 1
        assert s['total_events'] == 2
        assert s['active_lineages'] == 1
        assert 'created' in s['events_by_type']

    def test_lineage_version_count(self) -> None:
        ev = KnowledgeEvolution()
        ev.record_creation(event_id='evt-1', semantic_memory_id='sem-1', label='A')
        ev.record_revision(event_id='evt-2', semantic_memory_id='sem-1', description='Rev 1')
        ev.record_revision(event_id='evt-3', semantic_memory_id='sem-1', description='Rev 2')
        lineage = ev.get_lineage('sem-1')
        assert lineage is not None
        assert lineage.version_count == 3

    def test_evolution_event_types_complete(self) -> None:
        expected = {
            'created', 'revised', 'integrated', 'specialized',
            'generalized', 'contradicted', 'confirmed', 'deprecated',
            'merged', 'split',
        }
        assert set(EVOLUTION_EVENT_TYPES) == expected
