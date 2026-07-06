"""DEC Decision Architecture API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from ayeneh.dec.action_evaluation.engine import ActionEvaluationEngine
from ayeneh.dec.strategy_optimization.engine import StrategyOptimizationEngine

router = APIRouter(prefix="/dec", tags=["decision"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class DecisionInput(BaseModel):
    user_id: str = ""
    decision_type: str = "general"
    description: str = ""
    context: dict[str, Any] = {}
    options_considered: list[dict[str, Any]] = []
    chosen_option: str = ""
    reasoning: str = ""
    confidence: float = 0.0


class DecisionResponse(BaseModel):
    decision_id: str
    decision_type: str
    description: str
    confidence: float
    status: str


class GoalInput(BaseModel):
    user_id: str = ""
    goal_type: str = "outcome"
    title: str = ""
    description: str = ""
    priority: str = "medium"
    importance: float = 0.5
    success_criteria: list[dict[str, Any]] = []


class GoalResponse(BaseModel):
    goal_id: str
    goal_type: str
    title: str
    status: str
    priority: str
    importance: float
    confidence: float


class PlanInput(BaseModel):
    user_id: str = ""
    plan_type: str = "action"
    title: str = ""
    description: str = ""
    steps: list[dict[str, Any]] = []
    associated_goal_id: str = ""
    associated_decision_id: str = ""
    confidence: float = 0.0


class PlanResponse(BaseModel):
    plan_id: str
    plan_type: str
    title: str
    status: str
    confidence: float
    total_steps: int


class EvaluateInput(BaseModel):
    user_id: str = ""
    action_description: str = ""
    expected_outcome: str = ""
    observed_outcome: str = ""
    context: dict[str, Any] = {}
    evidence: list[dict[str, Any]] = []
    associated_plan: str = ""
    associated_goal: str = ""


class EvaluateResponse(BaseModel):
    evaluation_id: str
    outcome_category: str
    confidence: float
    lessons_count: int
    has_suggestions: bool


class StrategyInput(BaseModel):
    user_id: str = ""
    strategy_description: str = ""
    strategy_id: str = ""
    context: dict[str, Any] = {}
    historical_decisions: list[dict[str, Any]] = []
    historical_plans: list[dict[str, Any]] = []
    action_evaluations: list[dict[str, Any]] = []


class StrategyResponse(BaseModel):
    strategy_id: str
    description: str
    historical_performance: float
    confidence: float
    suggestions_count: int
    patterns_count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
async def dec_health() -> dict[str, str]:
    """Health check for DEC subsystem."""
    return {"status": "ok", "subsystem": "dec"}


@router.post("/decisions", response_model=DecisionResponse)
async def create_decision(body: DecisionInput) -> DecisionResponse:
    """Create a new DEC-01 decision."""
    import uuid
    decision_id = str(uuid.uuid4())
    return DecisionResponse(
        decision_id=decision_id,
        decision_type=body.decision_type,
        description=body.description,
        confidence=body.confidence,
        status="pending",
    )


@router.get("/decisions")
async def list_decisions() -> dict[str, Any]:
    """List DEC-01 decisions."""
    return {"decisions": [], "total": 0}


@router.post("/goals", response_model=GoalResponse)
async def create_goal(body: GoalInput) -> GoalResponse:
    """Create a new DEC-02 goal."""
    import uuid
    goal_id = str(uuid.uuid4())
    return GoalResponse(
        goal_id=goal_id,
        goal_type=body.goal_type,
        title=body.title,
        status="active",
        priority=body.priority,
        importance=body.importance,
        confidence=0.5,
    )


@router.get("/goals")
async def list_goals() -> dict[str, Any]:
    """List DEC-02 goals."""
    return {"goals": [], "total": 0}


@router.post("/plans", response_model=PlanResponse)
async def create_plan(body: PlanInput) -> PlanResponse:
    """Create a new DEC-03 plan."""
    import uuid
    plan_id = str(uuid.uuid4())
    return PlanResponse(
        plan_id=plan_id,
        plan_type=body.plan_type,
        title=body.title,
        status="draft",
        confidence=body.confidence,
        total_steps=len(body.steps),
    )


@router.get("/plans")
async def list_plans() -> dict[str, Any]:
    """List DEC-03 plans."""
    return {"plans": [], "total": 0}


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_action(body: EvaluateInput) -> EvaluateResponse:
    """Run DEC-04 action evaluation pipeline."""
    try:
        engine = ActionEvaluationEngine()
        result = engine.evaluate(
            action_description=body.action_description,
            expected_outcome=body.expected_outcome,
            observed_outcome=body.observed_outcome,
            context=body.context,
            evidence=body.evidence,
            associated_plan=body.associated_plan,
            associated_goal=body.associated_goal,
        )
        category = 'inconclusive'
        if result.comparison and result.comparison.category:
            category = result.comparison.category.category
        return EvaluateResponse(
            evaluation_id=result.evaluation_id,
            outcome_category=category,
            confidence=result.confidence,
            lessons_count=len(result.lessons),
            has_suggestions=len(result.lessons) > 0,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Action evaluation failed: {exc}")


@router.post("/strategies", response_model=StrategyResponse)
async def create_strategy(body: StrategyInput) -> StrategyResponse:
    """Run DEC-05 strategy optimization pipeline."""
    try:
        engine = StrategyOptimizationEngine()
        result = engine.optimize(
            strategy_description=body.strategy_description,
            context=body.context,
            historical_decisions=body.historical_decisions,
            historical_plans=body.historical_plans,
            action_evaluations=body.action_evaluations,
            strategy_id=body.strategy_id,
        )
        return StrategyResponse(
            strategy_id=result.strategy_id,
            description=result.strategy.description if result.strategy else "",
            historical_performance=result.performance.overall_score,
            confidence=result.confidence,
            suggestions_count=len(result.suggestions),
            patterns_count=len(result.patterns),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Strategy optimization failed: {exc}")


@router.get("/strategies")
async def list_strategies() -> dict[str, Any]:
    """List DEC-05 strategies."""
    return {"strategies": [], "total": 0}
