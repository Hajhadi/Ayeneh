"""Unified persistence repository for all MEMO memory types."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


def _json_list(obj: Any) -> str:
    if isinstance(obj, str):
        return obj
    return json.dumps(obj) if obj else "[]"


def _parse_json_list(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []


class MEMRepository:
    """Unified persistence for all memory types."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- Episodes (MEM-02) ---------------------------------------------------

    async def save_episode(self, user_id: str, episode: dict[str, Any]) -> str:
        model = MEMEpisodeModel(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            title=episode.get("title", ""),
            summary=episode.get("summary", ""),
            episode_type=episode.get("episode_type", episode.get("category", "learning")),
            state=episode.get("state", "candidate"),
            start_time=episode.get("start_time"),
            end_time=episode.get("end_time"),
            estimated_duration_s=episode.get("estimated_duration_s", 0.0),
            confidence=episode.get("confidence", 0.0),
            importance=episode.get("importance", 0.0),
            primary_context=episode.get("primary_context", ""),
            primary_project=episode.get("primary_project", ""),
            primary_people=_json_list(episode.get("primary_people", [])),
            primary_places=_json_list(episode.get("primary_places", [])),
            supporting_conversations=_json_list(episode.get("supporting_conversations", [])),
            supporting_evidence=_json_list(episode.get("supporting_evidence", [])),
            major_decisions=_json_list(episode.get("major_decisions", [])),
            major_behaviors=_json_list(episode.get("major_behaviors", [])),
            major_reflections=_json_list(episode.get("major_reflections", [])),
            associated_narratives=_json_list(episode.get("associated_narratives", [])),
            associated_beliefs=_json_list(episode.get("associated_beliefs", [])),
            associated_goals=_json_list(episode.get("associated_goals", [])),
            associated_identity=_json_list(episode.get("associated_identity", [])),
            outcome=_json_list(episode.get("outcome", [])),
            open_questions=_json_list(episode.get("open_questions", [])),
            version=episode.get("version", 1),
            superseded_by=episode.get("superseded_by"),
        )
        self._session.add(model)
        await self._session.flush()
        return str(model.id)

    async def load_episodes(
        self, user_id: str, state: str | None = None,
    ) -> list[dict[str, Any]]:
        query = select(MEMEpisodeModel).where(
            MEMEpisodeModel.user_id == uuid.UUID(user_id),
            MEMEpisodeModel.deleted_at.is_(None),
        )
        if state:
            query = query.where(MEMEpisodeModel.state == state)
        query = query.order_by(MEMEpisodeModel.created_at.desc())

        result = await self._session.execute(query)
        return [self._episode_to_dict(m) for m in result.scalars().all()]

    async def get_episode(self, episode_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            select(MEMEpisodeModel).where(MEMEpisodeModel.id == uuid.UUID(episode_id)),
        )
        model = result.scalar_one_or_none()
        return self._episode_to_dict(model) if model else None

    async def update_episode(self, episode_id: str, updates: dict[str, Any]) -> bool:
        result = await self._session.execute(
            select(MEMEpisodeModel).where(MEMEpisodeModel.id == uuid.UUID(episode_id)),
        )
        model = result.scalar_one_or_none()
        if not model:
            return False
        for key in ("title", "summary", "state", "confidence", "importance", "outcome"):
            if key in updates:
                setattr(model, key, updates[key])
        for key in ("primary_people", "primary_places", "open_questions"):
            if key in updates:
                setattr(model, key, _json_list(updates[key]))
        model.version = model.version + 1
        await self._session.flush()
        return True

    # -- Semantic (MEM-03) ---------------------------------------------------

    async def save_semantic(self, user_id: str, semantic: dict[str, Any]) -> str:
        model = MEMSemanticModel(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            knowledge_statement=semantic.get("knowledge_statement", ""),
            category=semantic.get("category", semantic.get("knowledge_category", "")),
            confidence=semantic.get("confidence", 0.0),
            importance=semantic.get("importance", 0.0),
            temporal_stability=semantic.get("temporal_stability", "stable"),
            supporting_evidence=_json_list(semantic.get("supporting_evidence", [])),
            supporting_episodes=_json_list(semantic.get("supporting_episodes", [])),
            contradictory_evidence=_json_list(semantic.get("contradictory_evidence", [])),
            lifecycle_state=semantic.get("lifecycle_state", "candidate"),
            version=semantic.get("version", 1),
            superseded_by=semantic.get("superseded_by"),
        )
        self._session.add(model)
        await self._session.flush()
        return str(model.id)

    async def load_semantics(
        self, user_id: str, category: str | None = None,
    ) -> list[dict[str, Any]]:
        query = select(MEMSemanticModel).where(
            MEMSemanticModel.user_id == uuid.UUID(user_id),
            MEMSemanticModel.deleted_at.is_(None),
        )
        if category:
            query = query.where(MEMSemanticModel.category == category)
        query = query.order_by(MEMSemanticModel.created_at.desc())

        result = await self._session.execute(query)
        return [self._semantic_to_dict(m) for m in result.scalars().all()]

    async def get_semantic(self, semantic_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            select(MEMSemanticModel).where(MEMSemanticModel.id == uuid.UUID(semantic_id)),
        )
        model = result.scalar_one_or_none()
        return self._semantic_to_dict(model) if model else None

    async def update_semantic(self, semantic_id: str, updates: dict[str, Any]) -> bool:
        result = await self._session.execute(
            select(MEMSemanticModel).where(MEMSemanticModel.id == uuid.UUID(semantic_id)),
        )
        model = result.scalar_one_or_none()
        if not model:
            return False
        for key in ("knowledge_statement", "category", "confidence", "importance",
                     "temporal_stability", "lifecycle_state"):
            if key in updates:
                setattr(model, key, updates[key])
        model.version = model.version + 1
        await self._session.flush()
        return True

    # -- Working (MEM-04) ----------------------------------------------------

    async def save_working(self, user_id: str, working: dict[str, Any]) -> str:
        model = MEMWorkingModel(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            source_memory_id=working.get("source_memory_id", working.get("source_memory", "")),
            activation_reason=working.get("activation_reason", ""),
            activation_score=working.get("activation_score", 0.0),
            priority_score=working.get("priority_score", 0.0),
            temporal_relevance=working.get("temporal_relevance", 0.0),
            estimated_lifetime_s=working.get("estimated_lifetime_s",
                                             working.get("estimated_lifetime", 0.0)),
            status=working.get("status", "active"),
        )
        self._session.add(model)
        await self._session.flush()
        return str(model.id)

    async def load_working(
        self, user_id: str, status: str | None = None,
    ) -> list[dict[str, Any]]:
        query = select(MEMWorkingModel).where(
            MEMWorkingModel.user_id == uuid.UUID(user_id),
            MEMWorkingModel.deleted_at.is_(None),
        )
        if status:
            query = query.where(MEMWorkingModel.status == status)
        query = query.order_by(MEMWorkingModel.created_at.desc())

        result = await self._session.execute(query)
        return [self._working_to_dict(m) for m in result.scalars().all()]

    async def get_working(self, working_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            select(MEMWorkingModel).where(MEMWorkingModel.id == uuid.UUID(working_id)),
        )
        model = result.scalar_one_or_none()
        return self._working_to_dict(model) if model else None

    async def update_working(self, working_id: str, updates: dict[str, Any]) -> bool:
        result = await self._session.execute(
            select(MEMWorkingModel).where(MEMWorkingModel.id == uuid.UUID(working_id)),
        )
        model = result.scalar_one_or_none()
        if not model:
            return False
        for key in ("activation_reason", "activation_score", "priority_score",
                     "temporal_relevance", "estimated_lifetime_s", "status"):
            if key in updates:
                setattr(model, key, updates[key])
        await self._session.flush()
        return True

    # -- Consolidation (MEM-05) ----------------------------------------------

    async def save_consolidation(
        self, user_id: str, consolidation: dict[str, Any],
    ) -> str:
        model = MEMConsolidationModel(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            target_memory_id=consolidation.get("target_memory_id",
                                               consolidation.get("target_memory", "")),
            evidence_summary=consolidation.get("evidence_summary", ""),
            supporting_episodes=_json_list(consolidation.get("supporting_episodes", [])),
            supporting_conversations=_json_list(
                consolidation.get("supporting_conversations", []),
            ),
            confidence_before=consolidation.get("confidence_before", 0.0),
            confidence_after=consolidation.get("confidence_after", 0.0),
            reason_for_promotion=consolidation.get("reason_for_promotion", ""),
            reason_for_rejection=consolidation.get("reason_for_rejection", ""),
            decision=consolidation.get("decision", "defer"),
            consolidation_level=consolidation.get("consolidation_level", "observation"),
        )
        self._session.add(model)
        await self._session.flush()
        return str(model.id)

    async def load_consolidations(
        self, user_id: str, decision: str | None = None,
    ) -> list[dict[str, Any]]:
        query = select(MEMConsolidationModel).where(
            MEMConsolidationModel.user_id == uuid.UUID(user_id),
            MEMConsolidationModel.deleted_at.is_(None),
        )
        if decision:
            query = query.where(MEMConsolidationModel.decision == decision)
        query = query.order_by(MEMConsolidationModel.created_at.desc())

        result = await self._session.execute(query)
        return [self._consolidation_to_dict(m) for m in result.scalars().all()]

    async def get_consolidation(self, consolidation_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            select(MEMConsolidationModel).where(
                MEMConsolidationModel.id == uuid.UUID(consolidation_id),
            ),
        )
        model = result.scalar_one_or_none()
        return self._consolidation_to_dict(model) if model else None

    # -- Retrieval (MEM-06) --------------------------------------------------

    async def save_retrieval(self, user_id: str, retrieval: dict[str, Any]) -> str:
        model = MEMRetrievalModel(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            request_id=retrieval.get("request_id", ""),
            memory_id=retrieval.get("memory_id", ""),
            memory_type=retrieval.get("memory_type", ""),
            relevance_score=retrieval.get("relevance_score", 0.0),
            recency_score=retrieval.get("recency_score", 0.0),
            importance_score=retrieval.get("importance_score", 0.0),
            confidence_score=retrieval.get("confidence_score", 0.0),
            final_score=retrieval.get("final_score", 0.0),
            strategy_used=retrieval.get("strategy_used", "composite"),
            retrieval_path=_json_list(retrieval.get("retrieval_path", [])),
        )
        self._session.add(model)
        await self._session.flush()
        return str(model.id)

    async def load_retrievals(
        self, user_id: str, request_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = select(MEMRetrievalModel).where(
            MEMRetrievalModel.user_id == uuid.UUID(user_id),
            MEMRetrievalModel.deleted_at.is_(None),
        )
        if request_id:
            query = query.where(MEMRetrievalModel.request_id == request_id)
        query = query.order_by(MEMRetrievalModel.final_score.desc())

        result = await self._session.execute(query)
        return [self._retrieval_to_dict(m) for m in result.scalars().all()]

    # -- Ranking (MEM-07) ----------------------------------------------------

    async def save_ranking(self, user_id: str, ranking: dict[str, Any]) -> str:
        model = MEMRankingModel(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            target_memory_id=ranking.get("target_memory_id",
                                         ranking.get("target_memory", "")),
            overall_score=ranking.get("overall_score", 0.0),
            relevance_score=ranking.get("relevance_score", 0.0),
            importance_score=ranking.get("importance_score", 0.0),
            confidence_score=ranking.get("confidence_score", 0.0),
            centrality_score=ranking.get("centrality_score", 0.0),
            recency_score=ranking.get("recency_score", 0.0),
            behavioral_impact=ranking.get("behavioral_impact",
                                          ranking.get("behavioral_impact_score", 0.0)),
            identity_impact=ranking.get("identity_impact",
                                        ranking.get("identity_impact_score", 0.0)),
            evidence_quality=ranking.get("evidence_quality",
                                         ranking.get("evidence_quality_score", 0.0)),
            task_profile=ranking.get("task_profile", "general"),
            explanation=ranking.get("explanation",
                                    ranking.get("ranking_explanation", "")),
            version=ranking.get("version", 1),
        )
        self._session.add(model)
        await self._session.flush()
        return str(model.id)

    async def load_rankings(
        self, user_id: str, memory_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = select(MEMRankingModel).where(
            MEMRankingModel.user_id == uuid.UUID(user_id),
            MEMRankingModel.deleted_at.is_(None),
        )
        if memory_id:
            query = query.where(MEMRankingModel.target_memory_id == memory_id)
        query = query.order_by(MEMRankingModel.overall_score.desc())

        result = await self._session.execute(query)
        return [self._ranking_to_dict(m) for m in result.scalars().all()]

    async def get_ranking(self, ranking_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            select(MEMRankingModel).where(MEMRankingModel.id == uuid.UUID(ranking_id)),
        )
        model = result.scalar_one_or_none()
        return self._ranking_to_dict(model) if model else None

    # -- Forgetting (MEM-08) -------------------------------------------------

    async def save_forgetting(self, user_id: str, forgetting: dict[str, Any]) -> str:
        model = MEMForgettingModel(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            affected_memory_ids=_json_list(forgetting.get("affected_memory_ids", [])),
            compression_strategy=forgetting.get("compression_strategy", "redundancy"),
            reason=forgetting.get("reason", ""),
            knowledge_preserved=forgetting.get("knowledge_preserved", ""),
            information_reduced=forgetting.get("information_reduced", 0.0),
            recoverability_status=forgetting.get("recoverability_status", "recoverable"),
            tier=forgetting.get("tier", "dormant"),
            access_count=forgetting.get("access_count", 0),
            access_frequency_score=forgetting.get("access_frequency_score", 0.0),
        )
        self._session.add(model)
        await self._session.flush()
        return str(model.id)

    async def load_forgettings(
        self, user_id: str, tier: str | None = None,
    ) -> list[dict[str, Any]]:
        query = select(MEMForgettingModel).where(
            MEMForgettingModel.user_id == uuid.UUID(user_id),
            MEMForgettingModel.deleted_at.is_(None),
        )
        if tier:
            query = query.where(MEMForgettingModel.tier == tier)
        query = query.order_by(MEMForgettingModel.created_at.desc())

        result = await self._session.execute(query)
        return [self._forgetting_to_dict(m) for m in result.scalars().all()]

    async def get_forgetting(self, forgetting_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            select(MEMForgettingModel).where(
                MEMForgettingModel.id == uuid.UUID(forgetting_id),
            ),
        )
        model = result.scalar_one_or_none()
        return self._forgetting_to_dict(model) if model else None

    # -- Knowledge Graph (MEM-09) --------------------------------------------

    async def save_kg_node(self, user_id: str, node: dict[str, Any]) -> str:
        model = MEMKnowledgeGraphNodeModel(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            label=node.get("label", ""),
            category=node.get("category", ""),
            layer=node.get("layer", "semantic"),
            properties=json.dumps(node.get("properties", {})),
            confidence=node.get("confidence", 1.0),
        )
        self._session.add(model)
        await self._session.flush()
        return str(model.id)

    async def save_kg_edge(self, user_id: str, edge: dict[str, Any]) -> str:
        model = MEMKnowledgeGraphEdgeModel(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            source_node_id=uuid.UUID(edge["source_node_id"]),
            target_node_id=uuid.UUID(edge["target_node_id"]),
            relationship=edge.get("relationship", "associated_with"),
            weight=edge.get("weight", 1.0),
            confidence=edge.get("confidence", 1.0),
            properties=json.dumps(edge.get("properties", {})),
        )
        self._session.add(model)
        await self._session.flush()
        return str(model.id)

    async def load_kg_nodes(
        self, user_id: str, category: str | None = None,
    ) -> list[dict[str, Any]]:
        query = select(MEMKnowledgeGraphNodeModel).where(
            MEMKnowledgeGraphNodeModel.user_id == uuid.UUID(user_id),
            MEMKnowledgeGraphNodeModel.deleted_at.is_(None),
        )
        if category:
            query = query.where(MEMKnowledgeGraphNodeModel.category == category)

        result = await self._session.execute(query)
        return [self._kg_node_to_dict(m) for m in result.scalars().all()]

    async def load_kg_edges(self, user_id: str) -> list[dict[str, Any]]:
        query = select(MEMKnowledgeGraphEdgeModel).where(
            MEMKnowledgeGraphEdgeModel.user_id == uuid.UUID(user_id),
            MEMKnowledgeGraphEdgeModel.deleted_at.is_(None),
        )
        result = await self._session.execute(query)
        return [self._kg_edge_to_dict(m) for m in result.scalars().all()]

    async def get_kg_node(self, node_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            select(MEMKnowledgeGraphNodeModel).where(
                MEMKnowledgeGraphNodeModel.id == uuid.UUID(node_id),
            ),
        )
        model = result.scalar_one_or_none()
        return self._kg_node_to_dict(model) if model else None

    # -- Versioning (MEM-10) -------------------------------------------------

    async def save_version(self, user_id: str, version: dict[str, Any]) -> str:
        model = MEMVersionModel(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            target_memory_id=version.get("target_memory_id",
                                         version.get("target_memory", "")),
            parent_version_id=version.get("parent_version_id",
                                          version.get("parent_version", "")),
            version_number=version.get("version_number", 1),
            revision_type=version.get("revision_type", "expansion"),
            reason=version.get("reason", version.get("reason_for_revision", "")),
            confidence_before=version.get("confidence_before", 0.0),
            confidence_after=version.get("confidence_after", 0.0),
            affected_relationships=_json_list(version.get("affected_relationships", [])),
            supporting_evidence=_json_list(version.get("supporting_evidence", [])),
            snapshot_id=version.get("snapshot_id", ""),
        )
        self._session.add(model)
        await self._session.flush()
        return str(model.id)

    async def load_versions(
        self, user_id: str, memory_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = select(MEMVersionModel).where(
            MEMVersionModel.user_id == uuid.UUID(user_id),
            MEMVersionModel.deleted_at.is_(None),
        )
        if memory_id:
            query = query.where(MEMVersionModel.target_memory_id == memory_id)
        query = query.order_by(MEMVersionModel.version_number.asc())

        result = await self._session.execute(query)
        return [self._version_to_dict(m) for m in result.scalars().all()]

    async def get_version(self, version_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            select(MEMVersionModel).where(MEMVersionModel.id == uuid.UUID(version_id)),
        )
        model = result.scalar_one_or_none()
        return self._version_to_dict(model) if model else None

    # -- Conversion helpers ---------------------------------------------------

    @staticmethod
    def _episode_to_dict(m: MEMEpisodeModel) -> dict[str, Any]:
        return {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "title": m.title,
            "summary": m.summary,
            "episode_type": m.episode_type,
            "state": m.state,
            "start_time": m.start_time.isoformat() if m.start_time else None,
            "end_time": m.end_time.isoformat() if m.end_time else None,
            "estimated_duration_s": m.estimated_duration_s,
            "confidence": m.confidence,
            "importance": m.importance,
            "primary_context": m.primary_context,
            "primary_project": m.primary_project,
            "primary_people": _parse_json_list(m.primary_people),
            "primary_places": _parse_json_list(m.primary_places),
            "supporting_conversations": _parse_json_list(m.supporting_conversations),
            "supporting_evidence": _parse_json_list(m.supporting_evidence),
            "major_decisions": _parse_json_list(m.major_decisions),
            "major_behaviors": _parse_json_list(m.major_behaviors),
            "major_reflections": _parse_json_list(m.major_reflections),
            "associated_narratives": _parse_json_list(m.associated_narratives),
            "associated_beliefs": _parse_json_list(m.associated_beliefs),
            "associated_goals": _parse_json_list(m.associated_goals),
            "associated_identity": _parse_json_list(m.associated_identity),
            "outcome": _parse_json_list(m.outcome),
            "open_questions": _parse_json_list(m.open_questions),
            "version": m.version,
            "superseded_by": str(m.superseded_by) if m.superseded_by else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }

    @staticmethod
    def _semantic_to_dict(m: MEMSemanticModel) -> dict[str, Any]:
        return {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "knowledge_statement": m.knowledge_statement,
            "category": m.category,
            "confidence": m.confidence,
            "importance": m.importance,
            "temporal_stability": m.temporal_stability,
            "supporting_evidence": _parse_json_list(m.supporting_evidence),
            "supporting_episodes": _parse_json_list(m.supporting_episodes),
            "contradictory_evidence": _parse_json_list(m.contradictory_evidence),
            "lifecycle_state": m.lifecycle_state,
            "version": m.version,
            "superseded_by": str(m.superseded_by) if m.superseded_by else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }

    @staticmethod
    def _working_to_dict(m: MEMWorkingModel) -> dict[str, Any]:
        return {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "source_memory_id": m.source_memory_id,
            "activation_reason": m.activation_reason,
            "activation_score": m.activation_score,
            "priority_score": m.priority_score,
            "temporal_relevance": m.temporal_relevance,
            "estimated_lifetime_s": m.estimated_lifetime_s,
            "status": m.status,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }

    @staticmethod
    def _consolidation_to_dict(m: MEMConsolidationModel) -> dict[str, Any]:
        return {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "target_memory_id": m.target_memory_id,
            "evidence_summary": m.evidence_summary,
            "supporting_episodes": _parse_json_list(m.supporting_episodes),
            "supporting_conversations": _parse_json_list(m.supporting_conversations),
            "confidence_before": m.confidence_before,
            "confidence_after": m.confidence_after,
            "reason_for_promotion": m.reason_for_promotion,
            "reason_for_rejection": m.reason_for_rejection,
            "decision": m.decision,
            "consolidation_level": m.consolidation_level,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }

    @staticmethod
    def _retrieval_to_dict(m: MEMRetrievalModel) -> dict[str, Any]:
        return {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "request_id": m.request_id,
            "memory_id": m.memory_id,
            "memory_type": m.memory_type,
            "relevance_score": m.relevance_score,
            "recency_score": m.recency_score,
            "importance_score": m.importance_score,
            "confidence_score": m.confidence_score,
            "final_score": m.final_score,
            "strategy_used": m.strategy_used,
            "retrieval_path": _parse_json_list(m.retrieval_path),
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }

    @staticmethod
    def _ranking_to_dict(m: MEMRankingModel) -> dict[str, Any]:
        return {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "target_memory_id": m.target_memory_id,
            "overall_score": m.overall_score,
            "relevance_score": m.relevance_score,
            "importance_score": m.importance_score,
            "confidence_score": m.confidence_score,
            "centrality_score": m.centrality_score,
            "recency_score": m.recency_score,
            "behavioral_impact": m.behavioral_impact,
            "identity_impact": m.identity_impact,
            "evidence_quality": m.evidence_quality,
            "task_profile": m.task_profile,
            "explanation": m.explanation,
            "version": m.version,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }

    @staticmethod
    def _forgetting_to_dict(m: MEMForgettingModel) -> dict[str, Any]:
        return {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "affected_memory_ids": _parse_json_list(m.affected_memory_ids),
            "compression_strategy": m.compression_strategy,
            "reason": m.reason,
            "knowledge_preserved": m.knowledge_preserved,
            "information_reduced": m.information_reduced,
            "recoverability_status": m.recoverability_status,
            "tier": m.tier,
            "access_count": m.access_count,
            "access_frequency_score": m.access_frequency_score,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }

    @staticmethod
    def _kg_node_to_dict(m: MEMKnowledgeGraphNodeModel) -> dict[str, Any]:
        try:
            props = json.loads(m.properties) if m.properties else {}
        except (json.JSONDecodeError, TypeError):
            props = {}
        return {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "label": m.label,
            "category": m.category,
            "layer": m.layer,
            "properties": props,
            "confidence": m.confidence,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }

    @staticmethod
    def _kg_edge_to_dict(m: MEMKnowledgeGraphEdgeModel) -> dict[str, Any]:
        try:
            props = json.loads(m.properties) if m.properties else {}
        except (json.JSONDecodeError, TypeError):
            props = {}
        return {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "source_node_id": str(m.source_node_id),
            "target_node_id": str(m.target_node_id),
            "relationship": m.relationship,
            "weight": m.weight,
            "confidence": m.confidence,
            "properties": props,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }

    @staticmethod
    def _version_to_dict(m: MEMVersionModel) -> dict[str, Any]:
        return {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "target_memory_id": m.target_memory_id,
            "parent_version_id": m.parent_version_id,
            "version_number": m.version_number,
            "revision_type": m.revision_type,
            "reason": m.reason,
            "confidence_before": m.confidence_before,
            "confidence_after": m.confidence_after,
            "affected_relationships": _parse_json_list(m.affected_relationships),
            "supporting_evidence": _parse_json_list(m.supporting_evidence),
            "snapshot_id": m.snapshot_id,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }
