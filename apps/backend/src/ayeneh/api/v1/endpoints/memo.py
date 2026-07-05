"""MEMO memory API endpoints — wired to database."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from ayeneh.api.deps import get_container

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    module: str
    timestamp: str


# -- Episodes ---------------------------------------------------------------

class CreateEpisodeRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = ""
    episode_type: str = Field(default="learning", max_length=50)
    state: str = Field(default="candidate", max_length=20)
    confidence: float = 0.0
    importance: float = 0.0
    primary_context: str = ""
    primary_project: str = ""
    primary_people: list[str] = Field(default_factory=list)
    primary_places: list[str] = Field(default_factory=list)
    outcome: str = "still_unknown"


class EpisodeResponse(BaseModel):
    id: str
    user_id: str
    title: str
    summary: str
    episode_type: str
    state: str
    confidence: float
    importance: float
    outcome: str | list[str]
    created_at: str | None = None


class EpisodeListResponse(BaseModel):
    data: list[EpisodeResponse]
    total: int


# -- Semantic ---------------------------------------------------------------

class CreateSemanticRequest(BaseModel):
    knowledge_statement: str = Field(min_length=1)
    category: str = Field(default="personal_interests", max_length=50)
    confidence: float = 0.0
    importance: float = 0.0
    temporal_stability: str = "long_term"
    lifecycle_state: str = "candidate"


class SemanticResponse(BaseModel):
    id: str
    user_id: str
    knowledge_statement: str
    category: str
    confidence: float
    importance: float
    temporal_stability: str
    lifecycle_state: str
    created_at: str | None = None


class SemanticListResponse(BaseModel):
    data: list[SemanticResponse]
    total: int


# -- Working Memory ---------------------------------------------------------

class CreateWorkingRequest(BaseModel):
    source_memory_id: str = ""
    activation_reason: str = ""
    activation_score: float = 0.0
    priority_score: float = 0.0
    temporal_relevance: float = 0.0
    estimated_lifetime_s: float = 0.0
    status: str = "active"


class WorkingResponse(BaseModel):
    id: str
    user_id: str
    source_memory_id: str
    activation_reason: str
    activation_score: float
    priority_score: float
    temporal_relevance: float
    estimated_lifetime_s: float
    status: str
    created_at: str | None = None


class WorkingListResponse(BaseModel):
    data: list[WorkingResponse]
    total: int


# -- Knowledge Graph --------------------------------------------------------

class CreateKGNodeRequest(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=50)
    layer: str = "semantic"
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class CreateKGEdgeRequest(BaseModel):
    source_node_id: str
    target_node_id: str
    relationship: str = "associated_with"
    weight: float = 1.0
    confidence: float = 1.0
    properties: dict[str, Any] = Field(default_factory=dict)


class KGNodeResponse(BaseModel):
    id: str
    user_id: str
    label: str
    category: str
    layer: str
    properties: dict[str, Any]
    confidence: float


class KGEdgeResponse(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    relationship: str
    weight: float
    confidence: float


class KnowledgeGraphResponse(BaseModel):
    nodes: list[KGNodeResponse]
    edges: list[KGEdgeResponse]
    node_count: int
    edge_count: int


# -- Consolidation ----------------------------------------------------------

class ConsolidateRequest(BaseModel):
    target_memory_id: str
    evidence_summary: str = ""
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    decision: str = "promote"
    consolidation_level: str = "candidate"


class ConsolidationResponse(BaseModel):
    id: str
    user_id: str
    target_memory_id: str
    decision: str
    confidence_before: float
    confidence_after: float
    created_at: str | None = None


class ConsolidationListResponse(BaseModel):
    data: list[ConsolidationResponse]
    total: int


# -- Retrieval --------------------------------------------------------------

class RetrieveRequest(BaseModel):
    memory_type: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class RetrieveResponseItem(BaseModel):
    id: str
    memory_id: str
    memory_type: str
    final_score: float
    strategy_used: str


class RetrieveResponse(BaseModel):
    data: list[RetrieveResponseItem]
    total: int


# -- Ranking ----------------------------------------------------------------

class RankRequest(BaseModel):
    target_memory_id: str
    task_profile: str = "general"


class RankingResponse(BaseModel):
    id: str
    target_memory_id: str
    overall_score: float
    task_profile: str
    created_at: str | None = None


# -- Forgetting -------------------------------------------------------------

class ForgetRequest(BaseModel):
    affected_memory_ids: list[str] = Field(default_factory=list)
    compression_strategy: str = "redundancy"
    reason: str = ""
    knowledge_preserved: str = ""
    recoverability_status: str = "recoverable"
    tier: str = "dormant"


class ForgettingResponse(BaseModel):
    id: str
    user_id: str
    affected_memory_ids: list[str]
    compression_strategy: str
    recoverability_status: str
    created_at: str | None = None


# -- Versioning -------------------------------------------------------------

class VersionResponse(BaseModel):
    id: str
    target_memory_id: str
    version_number: int
    revision_type: str
    reason: str
    created_at: str | None = None


class VersionListResponse(BaseModel):
    data: list[VersionResponse]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_id() -> str:
    """Generate a user ID. Replace with auth when available."""
    return str(uuid.uuid4())


def _get_session(container: Any):
    return container.database.session_factory()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
async def memo_health() -> dict:
    return {
        "status": "ok",
        "module": "memo",
        "timestamp": datetime.now(UTC).isoformat(),
    }


# -- Episodes ---------------------------------------------------------------

@router.post("/episodes", response_model=EpisodeResponse, status_code=201)
async def create_episode(body: CreateEpisodeRequest) -> dict:
    container = get_container()
    user_id = _get_user_id()

    if container.database:
        from ayeneh.memo.persistence.repository import MEMRepository

        async with _get_session(container) as session:
            repo = MEMRepository(session)
            episode_id = await repo.save_episode(user_id, {
                "title": body.title,
                "summary": body.summary,
                "episode_type": body.episode_type,
                "state": body.state,
                "confidence": body.confidence,
                "importance": body.importance,
                "primary_context": body.primary_context,
                "primary_project": body.primary_project,
                "primary_people": body.primary_people,
                "primary_places": body.primary_places,
                "outcome": body.outcome,
            })
            await session.commit()
            episode = await repo.get_episode(episode_id)
            return episode

    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": body.title,
        "summary": body.summary,
        "episode_type": body.episode_type,
        "state": body.state,
        "confidence": body.confidence,
        "importance": body.importance,
        "outcome": body.outcome,
    }


@router.get("/episodes", response_model=EpisodeListResponse)
async def list_episodes(
    state: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    container = get_container()
    if not container.database:
        return {"data": [], "total": 0}

    from ayeneh.memo.persistence.repository import MEMRepository
    from ayeneh.infrastructure.persistence.models.memo_episodic import MEMEpisodeModel
    from sqlalchemy import select

    async with _get_session(container) as session:
        query = select(MEMEpisodeModel).where(MEMEpisodeModel.deleted_at.is_(None))
        if state:
            query = query.where(MEMEpisodeModel.state == state)
        query = query.order_by(MEMEpisodeModel.created_at.desc()).limit(limit)
        result = await session.execute(query)
        models = result.scalars().all()
        repo = MEMRepository(session)
        return {
            "data": [repo._episode_to_dict(m) for m in models],
            "total": len(models),
        }


# -- Semantic ---------------------------------------------------------------

@router.post("/semantic", response_model=SemanticResponse, status_code=201)
async def create_semantic(body: CreateSemanticRequest) -> dict:
    container = get_container()
    user_id = _get_user_id()

    if container.database:
        from ayeneh.memo.persistence.repository import MEMRepository

        async with _get_session(container) as session:
            repo = MEMRepository(session)
            sem_id = await repo.save_semantic(user_id, {
                "knowledge_statement": body.knowledge_statement,
                "category": body.category,
                "confidence": body.confidence,
                "importance": body.importance,
                "temporal_stability": body.temporal_stability,
                "lifecycle_state": body.lifecycle_state,
            })
            await session.commit()
            semantic = await repo.get_semantic(sem_id)
            return semantic

    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "knowledge_statement": body.knowledge_statement,
        "category": body.category,
        "confidence": body.confidence,
        "importance": body.importance,
        "temporal_stability": body.temporal_stability,
        "lifecycle_state": body.lifecycle_state,
    }


@router.get("/semantic", response_model=SemanticListResponse)
async def list_semantic(
    category: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    container = get_container()
    if not container.database:
        return {"data": [], "total": 0}

    from ayeneh.infrastructure.persistence.models.memo_semantic import MEMSemanticModel
    from sqlalchemy import select

    async with _get_session(container) as session:
        query = select(MEMSemanticModel).where(MEMSemanticModel.deleted_at.is_(None))
        if category:
            query = query.where(MEMSemanticModel.category == category)
        query = query.order_by(MEMSemanticModel.created_at.desc()).limit(limit)
        result = await session.execute(query)
        models = result.scalars().all()
        from ayeneh.memo.persistence.repository import MEMRepository
        repo = MEMRepository(session)
        return {
            "data": [repo._semantic_to_dict(m) for m in models],
            "total": len(models),
        }


# -- Working Memory ---------------------------------------------------------

@router.post("/working", response_model=WorkingResponse, status_code=201)
async def create_working(body: CreateWorkingRequest) -> dict:
    container = get_container()
    user_id = _get_user_id()

    if container.database:
        from ayeneh.memo.persistence.repository import MEMRepository

        async with _get_session(container) as session:
            repo = MEMRepository(session)
            w_id = await repo.save_working(user_id, {
                "source_memory_id": body.source_memory_id,
                "activation_reason": body.activation_reason,
                "activation_score": body.activation_score,
                "priority_score": body.priority_score,
                "temporal_relevance": body.temporal_relevance,
                "estimated_lifetime_s": body.estimated_lifetime_s,
                "status": body.status,
            })
            await session.commit()
            working = await repo.get_working(w_id)
            return working

    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "source_memory_id": body.source_memory_id,
        "activation_reason": body.activation_reason,
        "activation_score": body.activation_score,
        "priority_score": body.priority_score,
        "temporal_relevance": body.temporal_relevance,
        "estimated_lifetime_s": body.estimated_lifetime_s,
        "status": body.status,
    }


@router.get("/working", response_model=WorkingListResponse)
async def list_working(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    container = get_container()
    if not container.database:
        return {"data": [], "total": 0}

    from ayeneh.memo.persistence.repository import MEMRepository
    from ayeneh.infrastructure.persistence.models.memo_working import MEMWorkingModel
    from sqlalchemy import select

    async with _get_session(container) as session:
        query = select(MEMWorkingModel).where(MEMWorkingModel.deleted_at.is_(None))
        if status:
            query = query.where(MEMWorkingModel.status == status)
        query = query.order_by(MEMWorkingModel.created_at.desc()).limit(limit)
        result = await session.execute(query)
        models = result.scalars().all()
        repo = MEMRepository(session)
        return {
            "data": [repo._working_to_dict(m) for m in models],
            "total": len(models),
        }


# -- Knowledge Graph --------------------------------------------------------

@router.post("/graph/nodes", response_model=KGNodeResponse, status_code=201)
async def create_kg_node(body: CreateKGNodeRequest) -> dict:
    container = get_container()
    user_id = _get_user_id()

    if container.database:
        from ayeneh.memo.persistence.repository import MEMRepository

        async with _get_session(container) as session:
            repo = MEMRepository(session)
            node_id = await repo.save_kg_node(user_id, {
                "label": body.label,
                "category": body.category,
                "layer": body.layer,
                "properties": body.properties,
                "confidence": body.confidence,
            })
            await session.commit()
            node = await repo.get_kg_node(node_id)
            return node

    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "label": body.label,
        "category": body.category,
        "layer": body.layer,
        "properties": body.properties,
        "confidence": body.confidence,
    }


@router.post("/graph/edges", response_model=KGEdgeResponse, status_code=201)
async def create_kg_edge(body: CreateKGEdgeRequest) -> dict:
    container = get_container()
    user_id = _get_user_id()

    if container.database:
        from ayeneh.memo.persistence.repository import MEMRepository

        async with _get_session(container) as session:
            repo = MEMRepository(session)
            edge_id = await repo.save_kg_edge(user_id, {
                "source_node_id": body.source_node_id,
                "target_node_id": body.target_node_id,
                "relationship": body.relationship,
                "weight": body.weight,
                "confidence": body.confidence,
                "properties": body.properties,
            })
            await session.commit()
            return {
                "id": edge_id,
                "source_node_id": body.source_node_id,
                "target_node_id": body.target_node_id,
                "relationship": body.relationship,
                "weight": body.weight,
                "confidence": body.confidence,
            }

    return {
        "id": str(uuid.uuid4()),
        "source_node_id": body.source_node_id,
        "target_node_id": body.target_node_id,
        "relationship": body.relationship,
        "weight": body.weight,
        "confidence": body.confidence,
    }


@router.get("/graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    category: str | None = Query(default=None),
) -> dict:
    container = get_container()
    if not container.database:
        return {"nodes": [], "edges": [], "node_count": 0, "edge_count": 0}

    from ayeneh.memo.persistence.repository import MEMRepository

    async with _get_session(container) as session:
        repo = MEMRepository(session)
        user_id = _get_user_id()
        nodes = await repo.load_kg_nodes(user_id, category=category)
        edges = await repo.load_kg_edges(user_id)
        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }


# -- Consolidation ----------------------------------------------------------

@router.post("/consolidate", response_model=ConsolidationResponse, status_code=201)
async def consolidate_memories(body: ConsolidateRequest) -> dict:
    container = get_container()
    user_id = _get_user_id()

    if container.database:
        from ayeneh.memo.persistence.repository import MEMRepository

        async with _get_session(container) as session:
            repo = MEMRepository(session)
            c_id = await repo.save_consolidation(user_id, {
                "target_memory_id": body.target_memory_id,
                "evidence_summary": body.evidence_summary,
                "confidence_before": body.confidence_before,
                "confidence_after": body.confidence_after,
                "decision": body.decision,
                "consolidation_level": body.consolidation_level,
            })
            await session.commit()
            consolidation = await repo.get_consolidation(c_id)
            return consolidation

    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "target_memory_id": body.target_memory_id,
        "decision": body.decision,
        "confidence_before": body.confidence_before,
        "confidence_after": body.confidence_after,
    }


@router.get("/consolidate", response_model=ConsolidationListResponse)
async def list_consolidations(
    decision: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    container = get_container()
    if not container.database:
        return {"data": [], "total": 0}

    from ayeneh.memo.persistence.repository import MEMRepository

    async with _get_session(container) as session:
        repo = MEMRepository(session)
        user_id = _get_user_id()
        data = await repo.load_consolidations(user_id, decision=decision)
        return {"data": data[:limit], "total": len(data)}


# -- Retrieval --------------------------------------------------------------

@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_memories(body: RetrieveRequest) -> dict:
    container = get_container()
    user_id = _get_user_id()

    if not container.database:
        return {"data": [], "total": 0}

    from ayeneh.memo.persistence.repository import MEMRepository

    async with _get_session(container) as session:
        repo = MEMRepository(session)
        data = await repo.load_retrievals(user_id)
        if body.memory_type:
            data = [d for d in data if d.get("memory_type") == body.memory_type]
        return {"data": data[:body.limit], "total": len(data)}


# -- Ranking ----------------------------------------------------------------

@router.post("/rank", response_model=RankingResponse, status_code=201)
async def rank_memories(body: RankRequest) -> dict:
    container = get_container()
    user_id = _get_user_id()

    if container.database:
        from ayeneh.memo.persistence.repository import MEMRepository

        async with _get_session(container) as session:
            repo = MEMRepository(session)
            r_id = await repo.save_ranking(user_id, {
                "target_memory_id": body.target_memory_id,
                "task_profile": body.task_profile,
            })
            await session.commit()
            ranking = await repo.get_ranking(r_id)
            return ranking

    return {
        "id": str(uuid.uuid4()),
        "target_memory_id": body.target_memory_id,
        "overall_score": 0.0,
        "task_profile": body.task_profile,
    }


# -- Forgetting -------------------------------------------------------------

@router.post("/forget", response_model=ForgettingResponse, status_code=201)
async def forget_memories(body: ForgetRequest) -> dict:
    container = get_container()
    user_id = _get_user_id()

    if container.database:
        from ayeneh.memo.persistence.repository import MEMRepository

        async with _get_session(container) as session:
            repo = MEMRepository(session)
            f_id = await repo.save_forgetting(user_id, {
                "affected_memory_ids": body.affected_memory_ids,
                "compression_strategy": body.compression_strategy,
                "reason": body.reason,
                "knowledge_preserved": body.knowledge_preserved,
                "recoverability_status": body.recoverability_status,
                "tier": body.tier,
            })
            await session.commit()
            forgetting = await repo.get_forgetting(f_id)
            return forgetting

    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "affected_memory_ids": body.affected_memory_ids,
        "compression_strategy": body.compression_strategy,
        "recoverability_status": body.recoverability_status,
    }


# -- Versioning -------------------------------------------------------------

@router.get("/versions", response_model=VersionListResponse)
async def list_versions(
    memory_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    container = get_container()
    if not container.database:
        return {"data": [], "total": 0}

    from ayeneh.memo.persistence.repository import MEMRepository

    async with _get_session(container) as session:
        repo = MEMRepository(session)
        user_id = _get_user_id()
        data = await repo.load_versions(user_id, memory_id=memory_id)
        return {"data": data[:limit], "total": len(data)}
