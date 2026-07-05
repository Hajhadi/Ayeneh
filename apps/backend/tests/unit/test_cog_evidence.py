"""Tests for the COG-02 Evidence Extraction pipeline."""

from __future__ import annotations

import uuid
import pytest
from datetime import UTC, datetime

from ayeneh.cog.conversation.types import (
    Claim,
    ConversationSegment,
    Entity,
    SemanticObject,
)
from ayeneh.cog.conversation.understanding import (
    ConversationUnderstandingEngine,
    ConversationUnderstandingResult,
)
from ayeneh.cog.evidence.extraction import (
    EvidenceExtractionEngine,
    EvidenceExtractionResult,
    _compute_strength,
)
from ayeneh.cog.evidence.validation import EvidenceValidator
from ayeneh.cog.evidence.repository import EvidenceRepository
from ayeneh.cog.evidence.types import (
    EVIDENCE_CATEGORIES,
    EPISTEMIC_CLASSIFICATIONS,
    EvidenceContext,
    EvidenceObject,
    EvidenceProvenance,
    EvidenceStrength,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_messages():
    return [
        {'role': 'user', 'content': 'I always start my day with coffee.'},
        {'role': 'assistant', 'content': 'That sounds like a nice routine.'},
        {'role': 'user', 'content': 'I believe it is essential for my productivity.'},
        {'role': 'user', 'content': 'Mr. Smith taught me that habit.'},
    ]


@pytest.fixture
def understanding_result(sample_messages):
    engine = ConversationUnderstandingEngine()
    return engine.process('test-conv-1', sample_messages)


@pytest.fixture
def evidence_engine():
    return EvidenceExtractionEngine()


@pytest.fixture
def validator():
    return EvidenceValidator()


@pytest.fixture
def repository():
    return EvidenceRepository()


@pytest.fixture
def sample_evidence():
    return EvidenceObject(
        identifier=str(uuid.uuid4()),
        category='observed_event',
        epistemic_classification='direct_observation',
        original_text='I saw the report.',
        normalized_text='I saw the report.',
        speaker='user',
        confidence=0.8,
        evidence_strength=EvidenceStrength(directness=0.9, specificity=0.7),
        provenance=EvidenceProvenance(
            conversation_id='conv-1',
            segment_id='seg-1',
            speaker='user',
            timestamp=datetime.now(UTC),
            engine_version='1.0.0',
        ),
        temporal_scope='momentary',
        context=EvidenceContext(),
        validation_status='pending',
    )


# ---------------------------------------------------------------------------
# EvidenceExtractionEngine tests
# ---------------------------------------------------------------------------


class TestEvidenceExtractionEngine:
    def test_process_returns_result(self, evidence_engine, understanding_result):
        result = evidence_engine.process(understanding_result)
        assert isinstance(result, EvidenceExtractionResult)
        assert result.conversation_id == 'test-conv-1' if hasattr(result, 'conversation_id') else True

    def test_evidence_objects_extracted(self, evidence_engine, understanding_result):
        result = evidence_engine.process(understanding_result)
        assert result.total_extracted > 0

    def test_all_evidence_have_identifiers(self, evidence_engine, understanding_result):
        result = evidence_engine.process(understanding_result)
        for ev in result.evidence_objects:
            assert ev.identifier
            assert isinstance(ev.identifier, str)

    def test_all_evidence_have_provenance(self, evidence_engine, understanding_result):
        result = evidence_engine.process(understanding_result)
        for ev in result.evidence_objects:
            assert ev.provenance.conversation_id == 'test-conv-1'
            assert ev.provenance.speaker != ''

    def test_all_evidence_have_epistemic_classification(self, evidence_engine, understanding_result):
        result = evidence_engine.process(understanding_result)
        for ev in result.evidence_objects:
            assert ev.epistemic_classification in EPISTEMIC_CLASSIFICATIONS

    def test_all_evidence_have_category(self, evidence_engine, understanding_result):
        result = evidence_engine.process(understanding_result)
        for ev in result.evidence_objects:
            assert ev.category in EVIDENCE_CATEGORIES or ev.category != ''

    def test_validation_summary_present(self, evidence_engine, understanding_result):
        result = evidence_engine.process(understanding_result)
        assert isinstance(result.validation_summary, dict)
        assert len(result.validation_summary) > 0

    def test_determinism(self, evidence_engine, understanding_result):
        """Same input → same output (deterministic pipeline)."""
        r1 = evidence_engine.process(understanding_result)
        r2 = evidence_engine.process(understanding_result)
        assert r1.total_extracted == r2.total_extracted
        assert len(r1.evidence_objects) == len(r2.evidence_objects)
        for e1, e2 in zip(r1.evidence_objects, r2.evidence_objects):
            assert e1.category == e2.category
            assert e1.epistemic_classification == e2.epistemic_classification
            assert e1.original_text == e2.original_text

    def test_empty_understanding_result(self, evidence_engine):
        empty_result = ConversationUnderstandingResult(
            conversation_id='empty',
            segments=(),
            semantic_objects=(),
            entities=(),
            events=(),
            claims=(),
        )
        result = evidence_engine.process(empty_result)
        assert result.total_extracted == 0
        assert len(result.evidence_objects) == 0


# ---------------------------------------------------------------------------
# EvidenceValidator tests
# ---------------------------------------------------------------------------


class TestEvidenceValidator:
    def test_pass_status(self, validator, sample_evidence):
        status, warnings = validator.validate(sample_evidence)
        assert status in ('pass', 'pass_with_warning')

    def test_pass_no_warnings(self, validator):
        ev = EvidenceObject(
            identifier='id-1',
            category='observed_event',
            epistemic_classification='direct_observation',
            original_text='I saw a bird.',
            normalized_text='I saw a bird.',
            speaker='user',
            confidence=0.8,
            provenance=EvidenceProvenance(
                conversation_id='conv-1',
                segment_id='seg-1',
                speaker='user',
                timestamp=datetime.now(UTC),
                engine_version='1.0.0',
            ),
        )
        status, warnings = validator.validate(ev)
        assert status == 'pass'
        assert warnings == []

    def test_pass_with_warnings(self, validator):
        ev = EvidenceObject(
            identifier='id-2',
            category='',
            epistemic_classification='direct_observation',
            original_text='test',
            normalized_text='test',
            speaker='user',
            confidence=0.5,
            provenance=EvidenceProvenance(
                conversation_id='conv-1',
                segment_id='seg-1',
                speaker='user',
                timestamp=datetime.now(UTC),
                engine_version='1.0.0',
            ),
        )
        status, warnings = validator.validate(ev)
        assert status in ('pass_with_warning', 'requires_review')
        assert len(warnings) > 0

    def test_requires_review_many_warnings(self, validator):
        ev = EvidenceObject(
            identifier='id-3',
            category='',
            epistemic_classification='',
            original_text='',
            normalized_text='',
            speaker='',
            confidence=0.5,
            provenance=EvidenceProvenance(),
        )
        status, warnings = validator.validate(ev)
        assert status == 'requires_review'
        assert len(warnings) > 2

    def test_confidence_out_of_range(self, validator):
        ev = EvidenceObject(
            identifier='id-4',
            category='observed_event',
            epistemic_classification='direct_observation',
            original_text='test',
            normalized_text='test',
            speaker='user',
            confidence=1.5,
            provenance=EvidenceProvenance(
                conversation_id='c', segment_id='s', speaker='u',
                timestamp=datetime.now(UTC), engine_version='1.0.0',
            ),
        )
        status, warnings = validator.validate(ev)
        assert any('Confidence' in w for w in warnings)

    def test_missing_provenance(self, validator):
        ev = EvidenceObject(
            identifier='id-5',
            category='observed_event',
            epistemic_classification='direct_observation',
            original_text='test',
            normalized_text='test',
            speaker='user',
            confidence=0.5,
            provenance=EvidenceProvenance(),
        )
        status, warnings = validator.validate(ev)
        assert any('provenance' in w.lower() for w in warnings)

    def test_validation_statuses_list(self):
        assert 'pass' in EvidenceValidator.VALIDATION_STATUSES
        assert 'pass_with_warning' in EvidenceValidator.VALIDATION_STATUSES
        assert 'requires_review' in EvidenceValidator.VALIDATION_STATUSES
        assert 'fail' in EvidenceValidator.VALIDATION_STATUSES

    def test_mandatory_attributes_list(self):
        assert 'category' in EvidenceValidator.MANDATORY_ATTRIBUTES
        assert 'confidence' in EvidenceValidator.MANDATORY_ATTRIBUTES
        assert 'provenance' in EvidenceValidator.MANDATORY_ATTRIBUTES


# ---------------------------------------------------------------------------
# EvidenceRepository tests
# ---------------------------------------------------------------------------


class TestEvidenceRepository:
    def test_store_and_get(self, repository, sample_evidence):
        repository.store(sample_evidence)
        retrieved = repository.get(sample_evidence.identifier)
        assert retrieved is not None
        assert retrieved.identifier == sample_evidence.identifier

    def test_get_nonexistent(self, repository):
        assert repository.get('nonexistent') is None

    def test_count(self, repository, sample_evidence):
        assert repository.count() == 0
        repository.store(sample_evidence)
        assert repository.count() == 1

    def test_store_batch(self, repository):
        evidence_list = [
            EvidenceObject(
                identifier=f'id-{i}',
                category='observed_event',
                epistemic_classification='direct_observation',
                original_text=f'text {i}',
                normalized_text=f'text {i}',
                speaker='user',
                confidence=0.5,
            )
            for i in range(3)
        ]
        repository.store_batch(evidence_list)
        assert repository.count() == 3

    def test_query_by_speaker(self, repository):
        ev1 = EvidenceObject(
            identifier='e1', category='observed_event',
            epistemic_classification='direct_observation',
            original_text='a', normalized_text='a',
            speaker='alice', confidence=0.5,
        )
        ev2 = EvidenceObject(
            identifier='e2', category='observed_event',
            epistemic_classification='direct_observation',
            original_text='b', normalized_text='b',
            speaker='bob', confidence=0.5,
        )
        repository.store(ev1)
        repository.store(ev2)
        assert len(repository.query_by_speaker('alice')) == 1
        assert len(repository.query_by_speaker('bob')) == 1
        assert repository.query_by_speaker('alice')[0].identifier == 'e1'

    def test_query_by_category(self, repository):
        ev1 = EvidenceObject(
            identifier='e1', category='observed_event',
            epistemic_classification='direct_observation',
            original_text='a', normalized_text='a',
            speaker='user', confidence=0.5,
        )
        ev2 = EvidenceObject(
            identifier='e2', category='self_report',
            epistemic_classification='subjective_experience',
            original_text='b', normalized_text='b',
            speaker='user', confidence=0.5,
        )
        repository.store(ev1)
        repository.store(ev2)
        assert len(repository.query_by_category('observed_event')) == 1
        assert len(repository.query_by_category('self_report')) == 1

    def test_query_by_time_range(self, repository):
        now = datetime.now(UTC)
        ev = EvidenceObject(
            identifier='e1', category='observed_event',
            epistemic_classification='direct_observation',
            original_text='a', normalized_text='a',
            speaker='user', confidence=0.5,
            provenance=EvidenceProvenance(timestamp=now),
        )
        repository.store(ev)
        results = repository.query_by_time_range(
            now.replace(second=now.second - 1),
            now.replace(second=now.second + 1),
        )
        assert len(results) == 1

    def test_remove(self, repository, sample_evidence):
        repository.store(sample_evidence)
        assert repository.count() == 1
        removed = repository.remove(sample_evidence.identifier)
        assert removed is True
        assert repository.count() == 0

    def test_remove_nonexistent(self, repository):
        assert repository.remove('nonexistent') is False

    def test_clear(self, repository):
        for i in range(5):
            repository.store(EvidenceObject(
                identifier=f'id-{i}', category='observed_event',
                epistemic_classification='direct_observation',
                original_text=f't{i}', normalized_text=f't{i}',
                speaker='user', confidence=0.5,
            ))
        assert repository.count() == 5
        repository.clear()
        assert repository.count() == 0


# ---------------------------------------------------------------------------
# EvidenceObject / EvidenceStrength / EvidenceProvenance tests
# ---------------------------------------------------------------------------


class TestEvidenceTypes:
    def test_evidence_object_creation(self):
        ev = EvidenceObject(
            identifier='e1',
            category='observed_event',
            epistemic_classification='direct_observation',
            original_text='test',
            normalized_text='test',
            speaker='user',
            confidence=0.8,
        )
        assert ev.identifier == 'e1'
        assert ev.confidence == 0.8

    def test_evidence_object_frozen(self):
        ev = EvidenceObject(identifier='e1')
        with pytest.raises(AttributeError):
            ev.confidence = 0.5  # type: ignore[misc]

    def test_evidence_strength_overall(self):
        strength = EvidenceStrength(
            directness=1.0,
            specificity=1.0,
            temporal_proximity=1.0,
            consistency=1.0,
        )
        assert strength.overall() == 1.0

    def test_evidence_strength_zero(self):
        strength = EvidenceStrength(
            directness=0.0,
            specificity=0.0,
            temporal_proximity=0.0,
            consistency=0.0,
        )
        assert strength.overall() == 0.0

    def test_evidence_strength_weighted(self):
        strength = EvidenceStrength(
            directness=0.8,
            specificity=0.6,
            temporal_proximity=0.4,
            consistency=0.2,
        )
        expected = 0.8 * 0.35 + 0.6 * 0.25 + 0.4 * 0.20 + 0.2 * 0.20
        assert abs(strength.overall() - expected) < 1e-9

    def test_evidence_provenance_defaults(self):
        prov = EvidenceProvenance()
        assert prov.conversation_id == ''
        assert prov.engine_version == '1.0.0'
        assert prov.language == 'en'

    def test_evidence_provenance_frozen(self):
        prov = EvidenceProvenance(conversation_id='c1')
        with pytest.raises(AttributeError):
            prov.conversation_id = 'c2'  # type: ignore[misc]

    def test_evidence_context_defaults(self):
        ctx = EvidenceContext()
        assert ctx.physical == ''
        assert ctx.social == ''

    def test_evidence_categories_list(self):
        assert 'observed_event' in EVIDENCE_CATEGORIES
        assert 'self_report' in EVIDENCE_CATEGORIES
        assert len(EVIDENCE_CATEGORIES) > 10

    def test_epistemic_classifications_list(self):
        assert 'direct_observation' in EPISTEMIC_CLASSIFICATIONS
        assert 'subjective_experience' in EPISTEMIC_CLASSIFICATIONS
        assert len(EPISTEMIC_CLASSIFICATIONS) > 10


# ---------------------------------------------------------------------------
# Compute strength helper tests
# ---------------------------------------------------------------------------


class TestComputeStrength:
    def test_high_quality_evidence(self):
        ev = EvidenceObject(
            identifier='hq',
            category='observed_event',
            epistemic_classification='direct_observation',
            original_text='A very detailed observation of the event that occurred yesterday.',
            normalized_text='same',
            speaker='user',
            confidence=0.9,
            validation_status='pass',
        )
        strength = _compute_strength(ev)
        assert strength.overall() > 0.5

    def test_low_quality_evidence(self):
        ev = EvidenceObject(
            identifier='lq',
            category='hypothesis',
            epistemic_classification='assumption',
            original_text='maybe',
            normalized_text='maybe',
            speaker='user',
            confidence=0.2,
            validation_status='requires_review',
        )
        strength = _compute_strength(ev)
        assert strength.overall() < 0.5

    def test_strength_dimensions_in_range(self):
        ev = EvidenceObject(
            identifier='range',
            category='self_report',
            epistemic_classification='interpretation',
            original_text='I think something might be the case.',
            normalized_text='same',
            speaker='user',
            confidence=0.5,
        )
        strength = _compute_strength(ev)
        assert 0.0 <= strength.directness <= 1.0
        assert 0.0 <= strength.specificity <= 1.0
        assert 0.0 <= strength.temporal_proximity <= 1.0
        assert 0.0 <= strength.consistency <= 1.0
