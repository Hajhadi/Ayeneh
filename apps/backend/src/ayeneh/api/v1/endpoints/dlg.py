"""DLG Dialogue Architecture API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from ayeneh.dlg.manager.engine import DialogueManager
from ayeneh.dlg.state.engine import ConversationStateMachine
from ayeneh.dlg.context.engine import ContextBuilder
from ayeneh.dlg.reflection.engine import ReflectionTimingEngine
from ayeneh.dlg.questioning.engine import QuestionGenerationEngine

router = APIRouter(prefix="/dlg", tags=["dialogue"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class DialogueInput(BaseModel):
    user_id: str = ""
    conversation_id: str = ""
    user_message: str
    conversation_history: list[dict[str, Any]] = []


class DialogueResponse(BaseModel):
    intent: str
    mode: str
    objective: str
    strategy: str
    confidence: float
    uncertainty: float


class StateInput(BaseModel):
    user_message: str
    session_id: str = ""
    user_id: str = ""


class StateResponse(BaseModel):
    state_type: str
    state_name: str
    confidence: float
    turn_number: int
    should_transition: bool


class ContextInput(BaseModel):
    user_message: str
    conversation_id: str = ""
    session_id: str = ""
    user_id: str = ""
    turn_number: int = 0


class ContextResponse(BaseModel):
    intent_type: str
    intent_confidence: float
    dialogue_phase: str
    engagement_level: float
    completeness: float


class ReflectionInput(BaseModel):
    engagement_level: float = 0.5
    depth: int = 0
    conversation_history: list[Any] = []
    behavioral_patterns: list[Any] = []


class ReflectionResponse(BaseModel):
    has_opportunity: bool
    pattern_type: str
    reflection_category: str
    urgency: float
    confidence: float


class QuestionInput(BaseModel):
    engagement_level: float = 0.5
    intent_confidence: float = 0.5
    conversation_history: list[Any] = []
    existing_knowledge: dict[str, Any] | None = None


class QuestionResponse(BaseModel):
    has_question: bool
    question_text: str
    question_type: str
    objective: str
    confidence: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
async def dlg_health() -> dict[str, str]:
    """Health check for DLG subsystem."""
    return {"status": "ok", "subsystem": "dlg"}


@router.post("/analyze", response_model=DialogueResponse)
async def analyze_dialogue(body: DialogueInput) -> DialogueResponse:
    """Run the full DLG-01 dialogue management pipeline."""
    try:
        engine = DialogueManager()
        result = engine.process(body.user_message, {
            'conversation_id': body.conversation_id,
        })
        return DialogueResponse(
            intent=result.detected_intent.intent_type,
            mode=result.response_strategy.mode,
            objective=result.primary_objective.objective_type,
            strategy=result.response_strategy.strategy_type,
            confidence=result.confidence.overall,
            uncertainty=result.uncertainty.overall_confidence
            if hasattr(result.uncertainty, 'overall_confidence')
            else 0.0,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Dialogue analysis failed: {exc}")


@router.post("/state", response_model=StateResponse)
async def get_state(body: StateInput) -> StateResponse:
    """Run the DLG-02 conversation state machine."""
    try:
        engine = ConversationStateMachine()
        result = engine.process(body.user_message, {
            'session_id': body.session_id,
            'user_id': body.user_id,
        })
        return StateResponse(
            state_type=result.current_state_type.state_type,
            state_name=result.current_state_type.state_name,
            confidence=result.confidence.overall,
            turn_number=result.conversation_identifier.turn_number,
            should_transition=result.current_state_type.state_type != "greeting",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"State analysis failed: {exc}")


@router.post("/context", response_model=ContextResponse)
async def build_context(body: ContextInput) -> ContextResponse:
    """Run the DLG-03 context builder pipeline."""
    try:
        engine = ContextBuilder()
        result = engine.build(
            user_input=body.user_message,
            conversation_id=body.conversation_id,
            session_id=body.session_id,
            user_id=body.user_id,
            turn_number=body.turn_number,
        )
        completeness = 0.0
        if result.context_confidence is not None:
            completeness = result.context_confidence.completeness
        return ContextResponse(
            intent_type=result.current_intent.intent_type,
            intent_confidence=result.current_intent.confidence,
            dialogue_phase=result.current_dialogue_state.phase,
            engagement_level=result.current_dialogue_state.engagement_level,
            completeness=completeness,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Context building failed: {exc}")


@router.post("/reflection", response_model=ReflectionResponse)
async def detect_reflections(body: ReflectionInput) -> ReflectionResponse:
    """Run the DLG-04 reflection timing pipeline."""
    try:
        engine = ReflectionTimingEngine()
        result = engine.process(
            {'engagement_level': body.engagement_level, 'depth': body.depth},
            conversation_history=body.conversation_history,
            behavioral_patterns=body.behavioral_patterns,
        )
        if result is None:
            return ReflectionResponse(
                has_opportunity=False,
                pattern_type="",
                reflection_category="",
                urgency=0.0,
                confidence=0.0,
            )
        return ReflectionResponse(
            has_opportunity=True,
            pattern_type=result.detected_pattern.pattern_type,
            reflection_category=result.reflection_category,
            urgency=result.urgency,
            confidence=result.confidence,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Reflection detection failed: {exc}")


@router.post("/questions", response_model=QuestionResponse)
async def generate_questions(body: QuestionInput) -> QuestionResponse:
    """Run the DLG-05 question generation pipeline."""
    try:
        engine = QuestionGenerationEngine()
        result = engine.process(
            {
                'engagement_level': body.engagement_level,
                'current_intent': {'confidence': body.intent_confidence},
            },
            conversation_history=body.conversation_history,
            existing_knowledge=body.existing_knowledge,
        )
        if result is None:
            return QuestionResponse(
                has_question=False,
                question_text="",
                question_type="",
                objective="",
                confidence=0.0,
            )
        return QuestionResponse(
            has_question=True,
            question_text=result.question_text,
            question_type=result.question_type.primary_type,
            objective=result.primary_objective.objective,
            confidence=result.confidence,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Question generation failed: {exc}")
