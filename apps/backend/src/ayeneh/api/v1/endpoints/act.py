"""ACT Action Architecture API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

router = APIRouter(prefix="/act", tags=["action_architecture"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ExecutionInput(BaseModel):
    user_id: str = ""
    execution_id: str = ""
    associated_plan: str = ""
    associated_goal: str = ""
    current_state: str = "prepared"
    progress_ratio: float = 0.0
    context: dict[str, Any] = {}


class ExecutionResponse(BaseModel):
    execution_id: str
    state: str
    progress: float
    confidence: float
    deviations: int


class HabitInput(BaseModel):
    user_id: str = ""
    habit_name: str = ""
    habit_type: str = "behavioral"
    trigger: str = ""
    routine: str = ""
    reward: str = ""
    context: dict[str, Any] = {}


class HabitResponse(BaseModel):
    habit_id: str
    habit_name: str
    habit_type: str
    status: str
    streak: int
    confidence: float


class InterventionInput(BaseModel):
    user_id: str = ""
    intervention_type: str = "adaptive"
    trigger_condition: str = ""
    target_module: str = ""
    action_description: str = ""
    context: dict[str, Any] = {}


class InterventionResponse(BaseModel):
    intervention_id: str
    intervention_type: str
    target_module: str
    status: str
    confidence: float


class FeedbackInput(BaseModel):
    user_id: str = ""
    source_event: str = ""
    feedback_type: str = "behavioral"
    context: dict[str, Any] = {}


class FeedbackResponse(BaseModel):
    feedback_id: str
    source_event: str
    confidence: float
    outcomes: int
    adaptations: int


class WorkflowInput(BaseModel):
    user_id: str = ""
    goals: list[dict[str, Any]] = []
    context: dict[str, Any] = {}


class WorkflowResponse(BaseModel):
    workflow_id: str
    phase: str
    status: str
    progress: float
    confidence: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
async def act_health() -> dict[str, str]:
    """Health check for ACT subsystem."""
    return {"status": "ok", "subsystem": "act"}


@router.post("/executions", response_model=ExecutionResponse)
async def create_execution(body: ExecutionInput) -> ExecutionResponse:
    """Create a new ACT-01 execution."""
    try:
        from ayeneh.act.execution_monitoring.engine import ExecutionMonitoringEngine

        engine = ExecutionMonitoringEngine()
        request = {
            'execution_id': body.execution_id or str(uuid.uuid4()),
            'associated_plan': body.associated_plan,
            'associated_goal': body.associated_goal,
            'current_state': body.current_state,
        }
        result = engine.process(request, body.context)

        return ExecutionResponse(
            execution_id=result.execution.execution_id,
            state=result.execution.current_state,
            progress=result.execution.observed_progress,
            confidence=result.execution.execution_confidence,
            deviations=len(result.deviations_detected),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Execution creation failed: {exc}")


@router.get("/executions")
async def list_executions() -> dict[str, Any]:
    """List ACT-01 executions."""
    return {"executions": [], "total": 0}


@router.post("/habits", response_model=HabitResponse)
async def create_habit(body: HabitInput) -> HabitResponse:
    """Create a new ACT-02 habit."""
    habit_id = str(uuid.uuid4())
    return HabitResponse(
        habit_id=habit_id,
        habit_name=body.habit_name,
        habit_type=body.habit_type,
        status="forming",
        streak=0,
        confidence=0.5,
    )


@router.get("/habits")
async def list_habits() -> dict[str, Any]:
    """List ACT-02 habits."""
    return {"habits": [], "total": 0}


@router.post("/interventions", response_model=InterventionResponse)
async def create_intervention(body: InterventionInput) -> InterventionResponse:
    """Create a new ACT-03 intervention."""
    intervention_id = str(uuid.uuid4())
    return InterventionResponse(
        intervention_id=intervention_id,
        intervention_type=body.intervention_type,
        target_module=body.target_module,
        status="pending",
        confidence=0.5,
    )


@router.get("/interventions")
async def list_interventions() -> dict[str, Any]:
    """List ACT-03 interventions."""
    return {"interventions": [], "total": 0}


@router.post("/feedback", response_model=FeedbackResponse)
async def process_feedback(body: FeedbackInput) -> FeedbackResponse:
    """Run ACT-04 feedback loop pipeline."""
    try:
        from ayeneh.act.feedback_loop.engine import FeedbackLoopCoordinator

        engine = FeedbackLoopCoordinator()
        request = {
            'source_event': body.source_event,
        }
        result = engine.process(request, body.context)

        return FeedbackResponse(
            feedback_id=result.feedback.feedback_id,
            source_event=result.feedback.source_event,
            confidence=result.feedback.confidence,
            outcomes=len(result.observed_outcomes),
            adaptations=len(result.behavioral_adaptations),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Feedback processing failed: {exc}")


@router.get("/feedback")
async def list_feedback() -> dict[str, Any]:
    """List ACT-04 feedback items."""
    return {"feedback": [], "total": 0}


@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(body: WorkflowInput) -> WorkflowResponse:
    """Run ACT-05 autonomous workflow pipeline."""
    try:
        from ayeneh.act.autonomous_workflow.engine import AutonomousWorkflowEngine

        engine = AutonomousWorkflowEngine()
        result = engine.process(body.goals, body.context)

        return WorkflowResponse(
            workflow_id=result.workflow.workflow_id,
            phase=result.workflow.current_phase,
            status=result.workflow.current_status,
            progress=result.workflow.progress,
            confidence=result.workflow.confidence,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Workflow creation failed: {exc}")


@router.get("/workflows")
async def list_workflows() -> dict[str, Any]:
    """List ACT-05 workflows."""
    return {"workflows": [], "total": 0}
