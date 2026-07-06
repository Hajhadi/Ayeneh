"""INT Integration Architecture API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

router = APIRouter(prefix="/integration", tags=["integration"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class OrchestrateInput(BaseModel):
    task_description: str = ''
    task_id: str = ''
    required_capabilities: list[str] = []
    context: dict[str, Any] = {}
    session_id: str = ''


class OrchestrateResponse(BaseModel):
    orchestration_id: str
    status: str
    modules: int
    confidence: float
    duration_ms: float


class ContextInput(BaseModel):
    current_goals: list[str] = []
    active_workflows: list[str] = []
    context: dict[str, Any] = {}
    session_id: str = ''


class ContextResponse(BaseModel):
    context_id: str
    goal_count: int
    workflow_count: int
    confidence: float
    duration_ms: float


class CommunicateInput(BaseModel):
    source_module: str = ''
    target_module: str = ''
    message_type: str = 'data'
    payload: dict[str, Any] = {}
    session_id: str = ''


class CommunicateResponse(BaseModel):
    communication_id: str
    source_module: str
    target_module: str
    delivered: bool
    confidence: float
    duration_ms: float


class StateResponse(BaseModel):
    state_id: str
    consistency_status: str
    architecture_health: float
    dimension_count: int
    conflict_count: int
    global_confidence: float
    duration_ms: float


class GovernanceInput(BaseModel):
    domain: str = 'architectural'
    current_stage: str = 'normal_operation'
    policies: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []
    context: dict[str, Any] = {}
    session_id: str = ''


class GovernanceResponse(BaseModel):
    governance_id: str
    approval_status: str
    lifecycle_stage: str
    audit_count: int
    enforcement_count: int
    confidence: float
    duration_ms: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
async def integration_health() -> dict[str, str]:
    """Health check for INT subsystem."""
    return {"status": "ok", "subsystem": "integration"}


@router.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(body: OrchestrateInput) -> OrchestrateResponse:
    """Run INT-01 cognitive orchestration pipeline."""
    try:
        from ayeneh.int.orchestrator.engine import CognitiveOrchestrator

        engine = CognitiveOrchestrator()
        result = engine.orchestrate(
            task_description=body.task_description,
            task_id=body.task_id or str(uuid.uuid4()),
            context=body.context,
            required_capabilities=body.required_capabilities,
            session_id=body.session_id,
        )

        return OrchestrateResponse(
            orchestration_id=result.orchestration_id,
            status=result.orchestration_object.current_status if result.orchestration_object else 'failed',
            modules=result.module_count,
            confidence=result.confidence,
            duration_ms=result.duration_ms,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {exc}")


@router.post("/context", response_model=ContextResponse)
async def create_context(body: ContextInput) -> ContextResponse:
    """Run INT-02 global context management pipeline."""
    try:
        from ayeneh.int.global_context.engine import GlobalContextManager

        engine = GlobalContextManager()
        result = engine.manage_context(
            context_sources={
                'current_goals': body.current_goals,
                'active_workflows': body.active_workflows,
                **body.context,
            },
            goals=body.current_goals,
            session_id=body.session_id,
        )

        return ContextResponse(
            context_id=result.context_id,
            goal_count=len(result.context_object.current_goals) if result.context_object else 0,
            workflow_count=len(result.context_object.active_workflows) if result.context_object else 0,
            confidence=result.confidence,
            duration_ms=result.duration_ms,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Context creation failed: {exc}")


@router.get("/context")
async def get_context() -> dict[str, Any]:
    """Get current global context state."""
    return {"context_id": "", "entries": [], "total": 0}


@router.post("/communicate", response_model=CommunicateResponse)
async def communicate(body: CommunicateInput) -> CommunicateResponse:
    """Run INT-03 inter-module communication."""
    try:
        from ayeneh.int.communication.engine import CommunicationBus

        engine = CommunicationBus()
        result = engine.send(
            sender_module=body.source_module,
            recipient_modules=[body.target_module],
            message_type=body.message_type,
            payload=body.payload,
            session_id=body.session_id,
        )

        return CommunicateResponse(
            communication_id=result.message_id,
            source_module=body.source_module,
            target_module=body.target_module,
            delivered=result.all_delivered,
            confidence=result.confidence,
            duration_ms=result.duration_ms,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Communication failed: {exc}")


@router.get("/state", response_model=StateResponse)
async def get_state() -> StateResponse:
    """Get current unified cognitive state (INT-04)."""
    try:
        from ayeneh.int.cognitive_state.engine import CognitiveStateEngine

        engine = CognitiveStateEngine()
        result = engine.process()

        state_obj = result.state_object
        return StateResponse(
            state_id=result.state_id,
            consistency_status=state_obj.consistency_status if state_obj else 'unknown',
            architecture_health=state_obj.architecture_health if state_obj else 0.0,
            dimension_count=result.dimension_count,
            conflict_count=len(result.conflicts),
            global_confidence=result.global_confidence,
            duration_ms=result.duration_ms,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"State retrieval failed: {exc}")


@router.post("/governance", response_model=GovernanceResponse)
async def create_governance(body: GovernanceInput) -> GovernanceResponse:
    """Run INT-05 system governance pipeline."""
    try:
        from ayeneh.int.governance.engine import GovernanceEngine

        engine = GovernanceEngine()
        result = engine.process(
            context={
                'domain': body.domain,
                'current_stage': body.current_stage,
                'policies': body.policies,
                'constraints': body.constraints,
                **body.context,
            },
            session_id=body.session_id,
        )

        gov_obj = result.governance_object
        return GovernanceResponse(
            governance_id=result.governance_id,
            approval_status=gov_obj.approval_status if gov_obj else 'pending',
            lifecycle_stage=gov_obj.lifecycle_stage if gov_obj else body.current_stage,
            audit_count=result.audit_count,
            enforcement_count=len(result.enforcement_actions),
            confidence=result.confidence,
            duration_ms=result.duration_ms,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Governance failed: {exc}")


@router.get("/governance")
async def get_governance() -> dict[str, Any]:
    """Get current governance state."""
    return {"governance_id": "", "policies": [], "total": 0}
