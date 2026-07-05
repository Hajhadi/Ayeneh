"""Tests for the COG-01 Conversation Understanding pipeline."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.cog.conversation.segmentation import SegmentationProcessor
from ayeneh.cog.conversation.reference_resolution import ReferenceResolver
from ayeneh.cog.conversation.understanding import (
    ConversationUnderstandingEngine,
    ConversationUnderstandingResult,
)
from ayeneh.cog.conversation.types import (
    Claim,
    ConversationSegment,
    Entity,
    SemanticObject,
    BELIEF_PRECURSORS,
    IDENTITY_PRECURSORS,
    NARRATIVE_PRECURSORS,
    VALUE_PRECURSORS,
    GOAL_PRECURSORS,
    META_COGNITIVE_SIGNALS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_messages():
    """A realistic multi-turn conversation."""
    return [
        {'role': 'user', 'content': 'I always start my day with coffee.'},
        {'role': 'assistant', 'content': 'That sounds like a nice routine. Do you enjoy it?'},
        {'role': 'user', 'content': 'Yes, I believe it is essential. Mr. Smith taught me that.'},
        {'role': 'assistant', 'content': 'Mr. Smith sounds wise. He helped many people.'},
        {'role': 'user', 'content': 'I want to share this with my team. We need to improve.'},
    ]


@pytest.fixture
def engine():
    return ConversationUnderstandingEngine()


@pytest.fixture
def segmenter():
    return SegmentationProcessor()


@pytest.fixture
def resolver():
    return ReferenceResolver()


# ---------------------------------------------------------------------------
# SegmentationProcessor tests
# ---------------------------------------------------------------------------


class TestSegmentationProcessor:
    def test_basic_segmentation(self, segmenter):
        messages = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there'},
        ]
        segments = segmenter.process(messages, 'conv-1')
        assert len(segments) == 2
        assert segments[0].speaker == 'user'
        assert segments[0].text == 'Hello'
        assert segments[0].conversation_id == 'conv-1'
        assert segments[0].sequence_number == 0

    def test_empty_messages_dropped(self, segmenter):
        messages = [
            {'role': 'user', 'content': ''},
            {'role': 'user', 'content': '  '},
            {'role': 'assistant', 'content': 'Hello'},
        ]
        segments = segmenter.process(messages, 'conv-2')
        assert len(segments) == 1
        assert segments[0].text == 'Hello'

    def test_segment_ids_unique(self, segmenter):
        messages = [{'role': 'user', 'content': f'Message {i}'} for i in range(5)]
        segments = segmenter.process(messages, 'conv-3')
        ids = [s.segment_id for s in segments]
        assert len(ids) == len(set(ids))

    def test_sequence_numbers_sequential(self, segmenter):
        messages = [{'role': 'user', 'content': f'Item {i}'} for i in range(3)]
        segments = segmenter.process(messages, 'conv-4')
        assert [s.sequence_number for s in segments] == [0, 1, 2]

    def test_language_from_message(self, segmenter):
        messages = [{'role': 'user', 'content': 'Bonjour', 'language': 'fr'}]
        segments = segmenter.process(messages, 'conv-5')
        assert segments[0].language == 'fr'

    def test_language_default_en(self, segmenter):
        messages = [{'role': 'user', 'content': 'Hello'}]
        segments = segmenter.process(messages, 'conv-6')
        assert segments[0].language == 'en'

    def test_merge_short_segments(self, segmenter):
        segments = [
            ConversationSegment(
                segment_id='s1', conversation_id='c', speaker='user',
                text='Hi', timestamp=datetime.now(UTC), sequence_number=0,
            ),
            ConversationSegment(
                segment_id='s2', conversation_id='c', speaker='user',
                text='there', timestamp=datetime.now(UTC), sequence_number=1,
            ),
        ]
        merged = SegmentationProcessor.merge_short_segments(segments, threshold=10)
        assert len(merged) == 1
        assert merged[0].text == 'Hi there'

    def test_merge_preserves_different_speakers(self, segmenter):
        segments = [
            ConversationSegment(
                segment_id='s1', conversation_id='c', speaker='user',
                text='Hi', timestamp=datetime.now(UTC), sequence_number=0,
            ),
            ConversationSegment(
                segment_id='s2', conversation_id='c', speaker='assistant',
                text='there', timestamp=datetime.now(UTC), sequence_number=1,
            ),
        ]
        merged = SegmentationProcessor.merge_short_segments(segments, threshold=10)
        assert len(merged) == 2


# ---------------------------------------------------------------------------
# ReferenceResolver tests
# ---------------------------------------------------------------------------


class TestReferenceResolver:
    def test_resolve_pronoun_to_entity(self, resolver):
        segments = [
            ConversationSegment(
                segment_id='s1', conversation_id='c', speaker='user',
                text='Alice is great.', timestamp=datetime.now(UTC), sequence_number=0,
            ),
            ConversationSegment(
                segment_id='s2', conversation_id='c', speaker='user',
                text='She is very kind.', timestamp=datetime.now(UTC), sequence_number=1,
            ),
        ]
        objects = [
            SemanticObject(
                object_id='o1', surface_form='Alice', normalized_form='Alice',
                object_type='entity', confidence=0.8,
            ),
            SemanticObject(
                object_id='o2', surface_form='She', normalized_form='She',
                object_type='entity', confidence=0.6,
            ),
        ]
        resolved = resolver.resolve(objects, segments)
        assert resolved[1].normalized_form == 'Alice'

    def test_self_reference(self, resolver):
        segments = [
            ConversationSegment(
                segment_id='s1', conversation_id='c', speaker='user',
                text='I am a developer.', timestamp=datetime.now(UTC), sequence_number=0,
            ),
        ]
        objects = [
            SemanticObject(
                object_id='o1', surface_form='I', normalized_form='I',
                object_type='entity', confidence=0.5,
            ),
        ]
        resolved = resolver.resolve(objects, segments)
        # Self-reference: should remain as 'I' or resolve to itself
        assert resolved[0].object_type == 'entity'

    def test_no_resolution_without_prior_entity(self, resolver):
        segments = [
            ConversationSegment(
                segment_id='s1', conversation_id='c', speaker='user',
                text='He is great.', timestamp=datetime.now(UTC), sequence_number=0,
            ),
        ]
        objects = [
            SemanticObject(
                object_id='o1', surface_form='He', normalized_form='He',
                object_type='entity', confidence=0.5,
            ),
        ]
        resolved = resolver.resolve(objects, segments)
        # No prior entity — pronoun stays as-is
        assert resolved[0].normalized_form == 'He'


# ---------------------------------------------------------------------------
# SemanticObject / Entity / Claim creation tests
# ---------------------------------------------------------------------------


class TestTypes:
    def test_semantic_object_creation(self):
        obj = SemanticObject(
            object_id='o1',
            surface_form='test',
            normalized_form='test',
            object_type='entity',
            confidence=0.9,
        )
        assert obj.object_id == 'o1'
        assert obj.confidence == 0.9
        assert obj.object_type == 'entity'

    def test_semantic_object_frozen(self):
        obj = SemanticObject(
            object_id='o1', surface_form='x', normalized_form='x',
            object_type='entity',
        )
        with pytest.raises(AttributeError):
            obj.confidence = 0.5  # type: ignore[misc]

    def test_entity_creation(self):
        entity = Entity(
            entity_id='e1',
            name='Alice',
            entity_type='person',
            aliases=('Ms. Alice',),
            confidence=0.95,
        )
        assert entity.name == 'Alice'
        assert entity.aliases == ('Ms. Alice',)

    def test_entity_frozen(self):
        entity = Entity(entity_id='e1', name='Bob', entity_type='person')
        with pytest.raises(AttributeError):
            entity.name = 'Charlie'  # type: ignore[misc]

    def test_claim_creation(self):
        claim = Claim(
            claim_id='c1',
            text='I believe in hard work.',
            speaker='user',
            timestamp=datetime.now(UTC),
            epistemic_marker='belief',
            confidence=0.8,
            is_self_report=True,
        )
        assert claim.epistemic_marker == 'belief'
        assert claim.is_self_report is True

    def test_claim_with_uncertainty_markers(self):
        claim = Claim(
            claim_id='c2',
            text='Maybe it will rain.',
            speaker='user',
            timestamp=datetime.now(UTC),
            uncertainty_markers=('maybe',),
        )
        assert 'maybe' in claim.uncertainty_markers


# ---------------------------------------------------------------------------
# Semantic tag detection tests
# ---------------------------------------------------------------------------


class TestSemanticTags:
    def test_narrative_precursors_present(self):
        assert any('always' in p for p in NARRATIVE_PRECURSORS)

    def test_belief_precursors_present(self):
        assert any('i believe' in p for p in BELIEF_PRECURSORS)

    def test_identity_precursors_present(self):
        assert any('i am' in p for p in IDENTITY_PRECURSORS)

    def test_value_precursors_present(self):
        assert any('i value' in p for p in VALUE_PRECURSORS)

    def test_goal_precursors_present(self):
        assert any('i want to' in p for p in GOAL_PRECURSORS)

    def test_metacognitive_signals_present(self):
        assert any('i notice that' in s for s in META_COGNITIVE_SIGNALS)


# ---------------------------------------------------------------------------
# ConversationUnderstandingEngine tests
# ---------------------------------------------------------------------------


class TestConversationUnderstandingEngine:
    def test_process_returns_result(self, engine, sample_messages):
        result = engine.process('conv-test-1', sample_messages)
        assert isinstance(result, ConversationUnderstandingResult)
        assert result.conversation_id == 'conv-test-1'

    def test_segments_created(self, engine, sample_messages):
        result = engine.process('conv-test-2', sample_messages)
        assert len(result.segments) == 5  # all non-empty messages

    def test_semantic_objects_extracted(self, engine, sample_messages):
        result = engine.process('conv-test-3', sample_messages)
        assert len(result.semantic_objects) > 0

    def test_entities_extracted(self, engine, sample_messages):
        result = engine.process('conv-test-4', sample_messages)
        # 'Mr. Smith' should be extracted as an entity
        assert any('Smith' in e.name for e in result.entities)

    def test_events_extracted(self, engine, sample_messages):
        result = engine.process('conv-test-5', sample_messages)
        # 'start' from 'I always start my day with coffee'
        assert any('start' in e.surface_form for e in result.events)

    def test_claims_extracted(self, engine, sample_messages):
        result = engine.process('conv-test-6', sample_messages)
        # 'I believe it is essential' should produce a claim
        assert len(result.claims) >= 1

    def test_determinism(self, engine, sample_messages):
        """Same input → same output (deterministic engine)."""
        r1 = engine.process('det-1', sample_messages)
        r2 = engine.process('det-1', sample_messages)
        assert len(r1.segments) == len(r2.segments)
        assert len(r1.semantic_objects) == len(r2.semantic_objects)
        assert len(r1.entities) == len(r2.entities)
        assert len(r1.claims) == len(r2.claims)

    def test_empty_messages(self, engine):
        result = engine.process('empty-conv', [])
        assert len(result.segments) == 0
        assert len(result.semantic_objects) == 0

    def test_result_frozen(self, engine, sample_messages):
        result = engine.process('frozen-1', sample_messages)
        with pytest.raises(AttributeError):
            result.segments = ()  # type: ignore[misc]

    def test_result_has_timestamp(self, engine, sample_messages):
        result = engine.process('ts-1', sample_messages)
        assert isinstance(result.processing_timestamp, datetime)
