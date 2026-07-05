"""Tests for COG cognitive object SQLAlchemy models."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ayeneh.infrastructure.persistence.base import Base
from ayeneh.infrastructure.persistence.models.cog_belief import CognitiveBeliefModel
from ayeneh.infrastructure.persistence.models.cog_decision import CognitiveDecisionModel
from ayeneh.infrastructure.persistence.models.cog_evidence import CognitiveEvidenceModel
from ayeneh.infrastructure.persistence.models.cog_identity import CognitiveIdentityModel
from ayeneh.infrastructure.persistence.models.cog_meta import CognitiveMetaObjectModel
from ayeneh.infrastructure.persistence.models.cog_narrative import CognitiveNarrativeModel
from ayeneh.infrastructure.persistence.models.cog_reflection import CognitiveReflectionModel
from ayeneh.infrastructure.persistence.models.cog_trajectory import CognitiveTrajectoryModel
from ayeneh.infrastructure.persistence.models.cog_value import CognitiveValueModel

USER_ID = uuid.uuid4()


@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        yield s


# ── Evidence ────────────────────────────────────────────────────────


class TestCognitiveEvidenceModel:
    def test_table_name(self):
        assert CognitiveEvidenceModel.__tablename__ == "cognitive_evidence"

    def test_instantiation(self, session):
        obj = CognitiveEvidenceModel(
            user_id=USER_ID,
            category="testimony",
            epistemic_classification="testimonial",
            original_text="I believe X",
            speaker="user",
            confidence=0.8,
        )
        session.add(obj)
        session.commit()
        assert obj.id is not None
        assert obj.created_at is not None

    def test_foreign_key(self):
        cols = CognitiveEvidenceModel.__table__.c
        fk = cols.user_id.foreign_keys
        assert any("users.id" in str(k) for k in fk)

    def test_defaults(self, session):
        obj = CognitiveEvidenceModel(
            user_id=USER_ID,
            category="observation",
            epistemic_classification="empirical",
            original_text="observed",
            speaker="system",
        )
        session.add(obj)
        session.commit()
        assert obj.confidence == 0.0
        assert obj.evidence_strength_directness == 0.5
        assert obj.language == "en"
        assert obj.temporal_scope == "momentary"
        assert obj.validation_status == "pending"

    def test_nullable_fields(self, session):
        obj = CognitiveEvidenceModel(
            user_id=USER_ID,
            category="inference",
            epistemic_classification="inferential",
            original_text="inferred",
            speaker="analyst",
        )
        session.add(obj)
        session.commit()
        assert obj.normalized_text is None
        assert obj.conversation_id is None
        assert obj.segment_id is None


# ── Belief ──────────────────────────────────────────────────────────


class TestCognitiveBeliefModel:
    def test_table_name(self):
        assert CognitiveBeliefModel.__tablename__ == "cognitive_beliefs"

    def test_instantiation(self, session):
        obj = CognitiveBeliefModel(
            user_id=USER_ID,
            belief_statement="The world is flat",
            category="worldview",
        )
        session.add(obj)
        session.commit()
        assert obj.id is not None
        assert obj.created_at is not None

    def test_foreign_key(self):
        cols = CognitiveBeliefModel.__table__.c
        fk = cols.user_id.foreign_keys
        assert any("users.id" in str(k) for k in fk)

    def test_defaults(self, session):
        obj = CognitiveBeliefModel(
            user_id=USER_ID,
            belief_statement="gravity exists",
            category="science",
        )
        session.add(obj)
        session.commit()
        assert obj.confidence == 0.0
        assert obj.strength == 0.0
        assert obj.stability == 0.0
        assert obj.influence == 0.0
        assert obj.identity_coupling_score == 0.0
        assert obj.lifecycle_state == "candidate"
        assert obj.version == 1

    def test_superseded_by_nullable(self, session):
        obj = CognitiveBeliefModel(
            user_id=USER_ID,
            belief_statement="old belief",
            category="test",
        )
        session.add(obj)
        session.commit()
        assert obj.superseded_by is None


# ── Narrative ───────────────────────────────────────────────────────


class TestCognitiveNarrativeModel:
    def test_table_name(self):
        assert CognitiveNarrativeModel.__tablename__ == "cognitive_narratives"

    def test_instantiation(self, session):
        obj = CognitiveNarrativeModel(
            user_id=USER_ID,
            narrative_type="redemption",
            title="My journey",
        )
        session.add(obj)
        session.commit()
        assert obj.id is not None

    def test_foreign_key(self):
        cols = CognitiveNarrativeModel.__table__.c
        fk = cols.user_id.foreign_keys
        assert any("users.id" in str(k) for k in fk)

    def test_json_defaults(self, session):
        obj = CognitiveNarrativeModel(
            user_id=USER_ID,
            narrative_type="contamination",
            title="Dark story",
        )
        session.add(obj)
        session.commit()
        assert obj.core_assumptions == "[]"
        assert obj.implicit_rules == "[]"
        assert obj.behavioral_consequences == "[]"

    def test_defaults(self, session):
        obj = CognitiveNarrativeModel(
            user_id=USER_ID,
            narrative_type="agency",
            title="Agency narrative",
        )
        session.add(obj)
        session.commit()
        assert obj.confidence == 0.0
        assert obj.influence_score == 0.0
        assert obj.lifecycle_state == "candidate"
        assert obj.version == 1
        assert obj.superseded_by is None


# ── Value ───────────────────────────────────────────────────────────


class TestCognitiveValueModel:
    def test_table_name(self):
        assert CognitiveValueModel.__tablename__ == "cognitive_values"

    def test_instantiation(self, session):
        obj = CognitiveValueModel(
            user_id=USER_ID,
            value_statement="honesty is key",
            category="moral",
        )
        session.add(obj)
        session.commit()
        assert obj.id is not None

    def test_foreign_key(self):
        cols = CognitiveValueModel.__table__.c
        fk = cols.user_id.foreign_keys
        assert any("users.id" in str(k) for k in fk)

    def test_defaults(self, session):
        obj = CognitiveValueModel(
            user_id=USER_ID,
            value_statement="be kind",
            category="social",
        )
        session.add(obj)
        session.commit()
        assert obj.confidence == 0.0
        assert obj.stability == 0.0
        assert obj.priority == 0.0
        assert obj.influence == 0.0
        assert obj.declared_vs_observed == "unknown"
        assert obj.lifecycle_state == "candidate"
        assert obj.version == 1
        assert obj.superseded_by is None


# ── Identity ────────────────────────────────────────────────────────


class TestCognitiveIdentityModel:
    def test_table_name(self):
        assert CognitiveIdentityModel.__tablename__ == "cognitive_identity"

    def test_instantiation(self, session):
        obj = CognitiveIdentityModel(
            user_id=USER_ID,
            identity_statement="I am a developer",
        )
        session.add(obj)
        session.commit()
        assert obj.id is not None

    def test_foreign_key(self):
        cols = CognitiveIdentityModel.__table__.c
        fk = cols.user_id.foreign_keys
        assert any("users.id" in str(k) for k in fk)

    def test_defaults(self, session):
        obj = CognitiveIdentityModel(
            user_id=USER_ID,
            identity_statement="I am creative",
        )
        session.add(obj)
        session.commit()
        assert obj.confidence == 0.0
        assert obj.stability == 0.0
        assert obj.centrality == 0.0
        assert obj.influence == 0.0
        assert obj.observer_strength == 0.0
        assert obj.narrative_identification_score == 0.0
        assert obj.lifecycle_state == "candidate"
        assert obj.version == 1
        assert obj.superseded_by is None


# ── Decision ────────────────────────────────────────────────────────


class TestCognitiveDecisionModel:
    def test_table_name(self):
        assert CognitiveDecisionModel.__tablename__ == "cognitive_decisions"

    def test_instantiation(self, session):
        obj = CognitiveDecisionModel(
            user_id=USER_ID,
            decision_statement="chose Python over Rust",
        )
        session.add(obj)
        session.commit()
        assert obj.id is not None

    def test_foreign_key(self):
        cols = CognitiveDecisionModel.__table__.c
        fk = cols.user_id.foreign_keys
        assert any("users.id" in str(k) for k in fk)

    def test_json_defaults(self, session):
        obj = CognitiveDecisionModel(
            user_id=USER_ID,
            decision_statement="buy a house",
        )
        session.add(obj)
        session.commit()
        assert obj.rejected_alternatives == "[]"

    def test_defaults(self, session):
        obj = CognitiveDecisionModel(
            user_id=USER_ID,
            decision_statement="start a project",
        )
        session.add(obj)
        session.commit()
        assert obj.confidence == 0.0
        assert obj.uncertainty == 0.0
        assert obj.decision_inertia == 0.0
        assert obj.lifecycle_state == "candidate"
        assert obj.version == 1
        assert obj.superseded_by is None


# ── Reflection ──────────────────────────────────────────────────────


class TestCognitiveReflectionModel:
    def test_table_name(self):
        assert CognitiveReflectionModel.__tablename__ == "cognitive_reflections"

    def test_instantiation(self, session):
        obj = CognitiveReflectionModel(
            user_id=USER_ID,
            reflection_statement="I learn best by doing",
        )
        session.add(obj)
        session.commit()
        assert obj.id is not None

    def test_foreign_key(self):
        cols = CognitiveReflectionModel.__table__.c
        fk = cols.user_id.foreign_keys
        assert any("users.id" in str(k) for k in fk)

    def test_defaults(self, session):
        obj = CognitiveReflectionModel(
            user_id=USER_ID,
            reflection_statement="patience helps",
        )
        session.add(obj)
        session.commit()
        assert obj.granularity == "session"
        assert obj.confidence == 0.0
        assert obj.lifecycle_state == "candidate"
        assert obj.version == 1
        assert obj.superseded_by is None

    def test_nullable_fields(self, session):
        obj = CognitiveReflectionModel(
            user_id=USER_ID,
            reflection_statement="nullable scope",
        )
        session.add(obj)
        session.commit()
        assert obj.scope is None


# ── Trajectory ──────────────────────────────────────────────────────


class TestCognitiveTrajectoryModel:
    def test_table_name(self):
        assert CognitiveTrajectoryModel.__tablename__ == "cognitive_trajectories"

    def test_instantiation(self, session):
        obj = CognitiveTrajectoryModel(
            user_id=USER_ID,
            target_cognitive_object="belief-123",
            target_type="belief",
        )
        session.add(obj)
        session.commit()
        assert obj.id is not None

    def test_foreign_key(self):
        cols = CognitiveTrajectoryModel.__table__.c
        fk = cols.user_id.foreign_keys
        assert any("users.id" in str(k) for k in fk)

    def test_defaults(self, session):
        obj = CognitiveTrajectoryModel(
            user_id=USER_ID,
            target_cognitive_object="identity-abc",
            target_type="identity",
        )
        session.add(obj)
        session.commit()
        assert obj.rate_of_change == 0.0
        assert obj.confidence == 0.0
        assert obj.historical_continuity == 0.0
        assert obj.lifecycle_state == "candidate"

    def test_nullable_fields(self, session):
        obj = CognitiveTrajectoryModel(
            user_id=USER_ID,
            target_cognitive_object="value-xyz",
            target_type="value",
        )
        session.add(obj)
        session.commit()
        assert obj.direction is None


# ── Meta-Object ─────────────────────────────────────────────────────


class TestCognitiveMetaObjectModel:
    def test_table_name(self):
        assert CognitiveMetaObjectModel.__tablename__ == "cognitive_meta_objects"

    def test_instantiation(self, session):
        obj = CognitiveMetaObjectModel(
            user_id=USER_ID,
            observed_process="pattern recognition",
        )
        session.add(obj)
        session.commit()
        assert obj.id is not None

    def test_foreign_key(self):
        cols = CognitiveMetaObjectModel.__table__.c
        fk = cols.user_id.foreign_keys
        assert any("users.id" in str(k) for k in fk)

    def test_defaults(self, session):
        obj = CognitiveMetaObjectModel(
            user_id=USER_ID,
            observed_process="decision making",
        )
        session.add(obj)
        session.commit()
        assert obj.awareness_level == 0
        assert obj.confidence == 0.0
        assert obj.stability == 0.0
        assert obj.lifecycle_state == "candidate"

    def test_nullable_fields(self, session):
        obj = CognitiveMetaObjectModel(
            user_id=USER_ID,
            observed_process="metacognition",
        )
        session.add(obj)
        session.commit()
        assert obj.awareness_description is None
