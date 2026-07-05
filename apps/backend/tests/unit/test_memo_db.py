"""Tests for all 9 MEMO DB models."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from ayeneh.infrastructure.persistence.base import Base
from ayeneh.infrastructure.persistence.models.user import UserModel
from ayeneh.infrastructure.persistence.models.memo_consolidation import MEMConsolidationModel
from ayeneh.infrastructure.persistence.models.memo_episodic import MEMEpisodeModel
from ayeneh.infrastructure.persistence.models.memo_forgetting import MEMForgettingModel
from ayeneh.infrastructure.persistence.models.memo_knowledge_graph import (
    MEMKnowledgeGraphEdgeModel,
    MEMKnowledgeGraphNodeModel,
)
from ayeneh.infrastructure.persistence.models.memo_ranking import MEMRankingModel
from ayeneh.infrastructure.persistence.models.memo_retrieval import MEMRetrievalModel
from ayeneh.infrastructure.persistence.models.memo_semantic import MEMSemanticModel
from ayeneh.infrastructure.persistence.models.memo_versioning import MEMVersionModel
from ayeneh.infrastructure.persistence.models.memo_working import MEMWorkingModel


@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:")

    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture()
def session(engine):
    SessionLocal = sessionmaker(bind=engine)
    s = SessionLocal()
    yield s
    s.rollback()
    s.close()


@pytest.fixture()
def user(session):
    u = UserModel(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Test User",
        status="active",
        preferences={},
    )
    session.add(u)
    session.commit()
    return u


class TestMEMEpisodeModel:
    def test_create(self, session: Session, user):
        model = MEMEpisodeModel(
            id=uuid.uuid4(),
            user_id=user.id,
            title="Test Episode",
            summary="A test episode",
            episode_type="learning",
            state="candidate",
            confidence=0.7,
            importance=0.5,
        )
        session.add(model)
        session.commit()

        loaded = session.get(MEMEpisodeModel, model.id)
        assert loaded is not None
        assert loaded.title == "Test Episode"
        assert loaded.episode_type == "learning"
        assert loaded.state == "candidate"
        assert loaded.confidence == 0.7
        assert loaded.primary_people == "[]"

    def test_defaults(self, session: Session, user):
        model = MEMEpisodeModel(
            id=uuid.uuid4(),
            user_id=user.id,
            title="Defaults",
            episode_type="research",
        )
        session.add(model)
        session.commit()

        assert model.state == "candidate"
        assert model.version == 1
        assert model.estimated_duration_s == 0.0
        assert model.confidence == 0.0
        assert model.importance == 0.0

    def test_timestamps(self, session: Session, user):
        model = MEMEpisodeModel(
            id=uuid.uuid4(),
            user_id=user.id,
            title="Timestamps",
            episode_type="career",
        )
        session.add(model)
        session.commit()
        assert model.created_at is not None
        assert model.updated_at is not None

    def test_soft_delete(self, session: Session, user):
        model = MEMEpisodeModel(
            id=uuid.uuid4(),
            user_id=user.id,
            title="To Delete",
            episode_type="health",
        )
        session.add(model)
        session.commit()
        assert model.deleted_at is None

    def test_json_list_fields(self, session: Session, user):
        model = MEMEpisodeModel(
            id=uuid.uuid4(),
            user_id=user.id,
            title="JSON Fields",
            episode_type="creative",
            primary_people=json.dumps(["Alice", "Bob"]),
            primary_places=json.dumps(["Office"]),
            major_decisions=json.dumps(["Decision 1"]),
        )
        session.add(model)
        session.commit()

        loaded = session.get(MEMEpisodeModel, model.id)
        assert json.loads(loaded.primary_people) == ["Alice", "Bob"]
        assert json.loads(loaded.primary_places) == ["Office"]
        assert json.loads(loaded.major_decisions) == ["Decision 1"]


class TestMEMSemanticModel:
    def test_create(self, session: Session, user):
        model = MEMSemanticModel(
            id=uuid.uuid4(),
            user_id=user.id,
            knowledge_statement="User prefers Python",
            category="skills",
            confidence=0.9,
            importance=0.8,
            temporal_stability="long_term",
        )
        session.add(model)
        session.commit()

        loaded = session.get(MEMSemanticModel, model.id)
        assert loaded is not None
        assert loaded.knowledge_statement == "User prefers Python"
        assert loaded.category == "skills"
        assert loaded.lifecycle_state == "candidate"

    def test_defaults(self, session: Session, user):
        model = MEMSemanticModel(
            id=uuid.uuid4(),
            user_id=user.id,
            knowledge_statement="Test statement",
            category="core_values",
        )
        session.add(model)
        session.commit()
        assert model.confidence == 0.0
        assert model.version == 1
        assert model.temporal_stability == "stable"


class TestMEMWorkingModel:
    def test_create(self, session: Session, user):
        model = MEMWorkingModel(
            id=uuid.uuid4(),
            user_id=user.id,
            source_memory_id="mem-123",
            activation_reason="relevant to conversation",
            activation_score=0.8,
            priority_score=0.7,
            temporal_relevance=0.9,
            estimated_lifetime_s=300.0,
            status="active",
        )
        session.add(model)
        session.commit()

        loaded = session.get(MEMWorkingModel, model.id)
        assert loaded is not None
        assert loaded.source_memory_id == "mem-123"
        assert loaded.activation_score == 0.8
        assert loaded.status == "active"

    def test_defaults(self, session: Session, user):
        model = MEMWorkingModel(
            id=uuid.uuid4(),
            user_id=user.id,
        )
        session.add(model)
        session.commit()
        assert model.status == "active"
        assert model.activation_score == 0.0


class TestMEMConsolidationModel:
    def test_create(self, session: Session, user):
        model = MEMConsolidationModel(
            id=uuid.uuid4(),
            user_id=user.id,
            target_memory_id="mem-456",
            evidence_summary="Strong evidence",
            confidence_before=0.3,
            confidence_after=0.8,
            decision="promote",
            consolidation_level="validated_pattern",
        )
        session.add(model)
        session.commit()

        loaded = session.get(MEMConsolidationModel, model.id)
        assert loaded is not None
        assert loaded.target_memory_id == "mem-456"
        assert loaded.decision == "promote"
        assert loaded.confidence_before == 0.3
        assert loaded.confidence_after == 0.8

    def test_defaults(self, session: Session, user):
        model = MEMConsolidationModel(
            id=uuid.uuid4(),
            user_id=user.id,
            target_memory_id="mem-default",
        )
        session.add(model)
        session.commit()
        assert model.decision == "defer"
        assert model.consolidation_level == "observation"


class TestMEMRetrievalModel:
    def test_create(self, session: Session, user):
        model = MEMRetrievalModel(
            id=uuid.uuid4(),
            user_id=user.id,
            request_id="req-001",
            memory_id="mem-789",
            memory_type="episodic",
            relevance_score=0.9,
            final_score=0.85,
            strategy_used="composite",
        )
        session.add(model)
        session.commit()

        loaded = session.get(MEMRetrievalModel, model.id)
        assert loaded is not None
        assert loaded.request_id == "req-001"
        assert loaded.memory_type == "episodic"
        assert loaded.final_score == 0.85


class TestMEMRankingModel:
    def test_create(self, session: Session, user):
        model = MEMRankingModel(
            id=uuid.uuid4(),
            user_id=user.id,
            target_memory_id="mem-rank",
            overall_score=0.75,
            relevance_score=0.8,
            task_profile="Debugging",
            version=1,
        )
        session.add(model)
        session.commit()

        loaded = session.get(MEMRankingModel, model.id)
        assert loaded is not None
        assert loaded.overall_score == 0.75
        assert loaded.task_profile == "Debugging"
        assert loaded.version == 1


class TestMEMForgettingModel:
    def test_create(self, session: Session, user):
        model = MEMForgettingModel(
            id=uuid.uuid4(),
            user_id=user.id,
            affected_memory_ids='["mem-1", "mem-2"]',
            compression_strategy="redundancy",
            information_reduced=0.5,
            recoverability_status="recoverable",
            tier="dormant",
        )
        session.add(model)
        session.commit()

        loaded = session.get(MEMForgettingModel, model.id)
        assert loaded is not None
        assert loaded.compression_strategy == "redundancy"
        assert loaded.tier == "dormant"
        assert loaded.information_reduced == 0.5


class TestMEMKnowledgeGraphModels:
    def test_create_node(self, session: Session, user):
        node = MEMKnowledgeGraphNodeModel(
            id=uuid.uuid4(),
            user_id=user.id,
            label="Python Skills",
            category="skills",
            layer="semantic",
            confidence=0.95,
        )
        session.add(node)
        session.commit()

        loaded = session.get(MEMKnowledgeGraphNodeModel, node.id)
        assert loaded is not None
        assert loaded.label == "Python Skills"
        assert loaded.category == "skills"
        assert loaded.layer == "semantic"

    def test_create_edge(self, session: Session, user):
        node_a = MEMKnowledgeGraphNodeModel(
            id=uuid.uuid4(),
            user_id=user.id,
            label="Node A",
            category="concepts",
        )
        node_b = MEMKnowledgeGraphNodeModel(
            id=uuid.uuid4(),
            user_id=user.id,
            label="Node B",
            category="concepts",
        )
        session.add_all([node_a, node_b])
        session.flush()

        edge = MEMKnowledgeGraphEdgeModel(
            id=uuid.uuid4(),
            user_id=user.id,
            source_node_id=node_a.id,
            target_node_id=node_b.id,
            relationship="supports",
            weight=0.8,
        )
        session.add(edge)
        session.commit()

        loaded = session.get(MEMKnowledgeGraphEdgeModel, edge.id)
        assert loaded is not None
        assert loaded.source_node_id == node_a.id
        assert loaded.target_node_id == node_b.id
        assert loaded.relationship == "supports"
        assert loaded.weight == 0.8


class TestMEMVersionModel:
    def test_create(self, session: Session, user):
        model = MEMVersionModel(
            id=uuid.uuid4(),
            user_id=user.id,
            target_memory_id="mem-version",
            version_number=2,
            revision_type="expansion",
            reason="Added more context",
            confidence_before=0.5,
            confidence_after=0.7,
        )
        session.add(model)
        session.commit()

        loaded = session.get(MEMVersionModel, model.id)
        assert loaded is not None
        assert loaded.target_memory_id == "mem-version"
        assert loaded.version_number == 2
        assert loaded.revision_type == "expansion"
        assert loaded.confidence_after == 0.7

    def test_defaults(self, session: Session, user):
        model = MEMVersionModel(
            id=uuid.uuid4(),
            user_id=user.id,
            target_memory_id="mem-default",
        )
        session.add(model)
        session.commit()
        assert model.version_number == 1
        assert model.revision_type == "expansion"
