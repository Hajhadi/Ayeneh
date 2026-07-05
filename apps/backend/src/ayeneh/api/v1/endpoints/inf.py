"""INF Inference Architecture API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from ayeneh.inf.inference.engine import InferenceEngine
from ayeneh.inf.graph_reasoner.engine import GraphReasoningEngine
from ayeneh.inf.contradiction.engine import ContradictionResolver
from ayeneh.inf.hypothesis.engine import HypothesisEngine
from ayeneh.inf.multihop.engine import MultiHopReasoningEngine

router = APIRouter(prefix="/inf", tags=["inference"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class InferenceInput(BaseModel):
    user_id: str
    messages: list[dict[str, Any]]
    context_id: str = ""
    language: str = "en"


class InferenceResponse(BaseModel):
    inferences_count: int
    overall_confidence: float
    evidence_quality: float
    reasoning_steps: int
    competing_hypotheses: int
    contradictions: int


class ContradictionInput(BaseModel):
    cognitive_objects: list[dict[str, Any]]
    context: dict[str, Any] | None = None


class ContradictionResponse(BaseModel):
    contradictions_count: int
    overall_consistency: float
    classifications: list[dict[str, Any]]
    resolution_plans: list[dict[str, Any]]


class HypothesisInput(BaseModel):
    evidence: list[dict[str, Any]]
    graph: dict[str, Any] | None = None
    context: dict[str, Any] | None = None


class HypothesisResponse(BaseModel):
    hypotheses_count: int
    overall_confidence: float
    strongest_hypothesis: str
    families_count: int
    evidence_gaps: int
    predictions: int


class HypothesisEvaluateInput(BaseModel):
    new_evidence: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inference_result_to_dict(result: Any) -> dict[str, Any]:
    """Convert InferenceResult dataclass to a JSON-safe dict."""
    return {
        "inferences_count": len(result.inferences),
        "overall_confidence": result.overall_confidence,
        "evidence_quality": result.evidence_assessment.overall(),
        "reasoning_steps": len(result.reasoning_steps),
        "competing_hypotheses": len(result.competing_hypotheses),
        "contradictions": len(result.contradictions),
    }


def _contradiction_result_to_dict(result: Any) -> dict[str, Any]:
    """Convert ContradictionResult dataclass to a JSON-safe dict."""
    return {
        "contradictions_count": len(result.contradictions),
        "overall_consistency": result.overall_consistency,
        "classifications": [
            {
                "category": c.category,
                "severity": c.severity,
                "scope": c.scope,
            }
            for c in result.classifications
        ],
        "resolution_plans": [
            {
                "strategy": p.strategy,
                "expected_outcome": p.expected_outcome,
                "confidence": p.confidence,
            }
            for p in result.resolution_plans
        ],
    }


def _hypothesis_result_to_dict(result: Any) -> dict[str, Any]:
    """Convert HypothesisResult dataclass to a JSON-safe dict."""
    return {
        "hypotheses_count": len(result.hypotheses),
        "overall_confidence": result.overall_confidence,
        "strongest_hypothesis": result.strongest_hypothesis,
        "families_count": len(result.families),
        "evidence_gaps": len(result.evidence_gaps),
        "predictions": len(result.predictions),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
async def inf_health() -> dict[str, str]:
    """Health check for INF subsystem."""
    return {"status": "ok", "subsystem": "inf"}


@router.post("/analyze", response_model=InferenceResponse)
async def analyze_inference(body: InferenceInput) -> InferenceResponse:
    """Run the full INF inference pipeline on a conversation."""
    try:
        engine = InferenceEngine()
        context = {
            "context_id": body.context_id or "api-context",
            "domain": "general",
            "user_message": body.messages[-1].get("content", "") if body.messages else "",
            "conversation_history": body.messages,
        }
        result = engine.process(context, [])
        data = _inference_result_to_dict(result)
        return InferenceResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference analysis failed: {exc}")


@router.post("/contradictions", response_model=ContradictionResponse)
async def detect_contradictions(body: ContradictionInput) -> ContradictionResponse:
    """Detect contradictions among cognitive objects."""
    try:
        resolver = ContradictionResolver()
        result = resolver.process(body.cognitive_objects, body.context)
        data = _contradiction_result_to_dict(result)
        return ContradictionResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Contradiction detection failed: {exc}")


@router.post("/hypotheses", response_model=HypothesisResponse)
async def generate_hypotheses(body: HypothesisInput) -> HypothesisResponse:
    """Generate hypotheses from evidence and graph context."""
    try:
        engine = HypothesisEngine()
        result = engine.process(body.evidence, body.graph, body.context)
        data = _hypothesis_result_to_dict(result)
        return HypothesisResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Hypothesis generation failed: {exc}")


@router.get("/hypotheses/{hypothesis_id}")
async def get_hypothesis(hypothesis_id: str) -> dict[str, Any]:
    """Retrieve a specific hypothesis by ID.

    Note: In a full implementation this would query the database.
    Currently returns a placeholder for the endpoint contract.
    """
    return {
        "hypothesis_id": hypothesis_id,
        "status": "not_persisted",
        "message": "Hypothesis persistence not yet implemented",
    }


@router.post("/hypotheses/{hypothesis_id}/evaluate")
async def evaluate_hypothesis(
    hypothesis_id: str,
    body: HypothesisEvaluateInput,
) -> dict[str, Any]:
    """Evaluate a hypothesis with new evidence using Bayesian updating.

    Note: In a full implementation this would load from DB, update, and persist.
    Currently runs the engine with the new evidence and returns the result.
    """
    try:
        engine = HypothesisEngine()
        result = engine.process(body.new_evidence, None, {"hypothesis_id": hypothesis_id})
        return {
            "hypothesis_id": hypothesis_id,
            "evaluation": _hypothesis_result_to_dict(result),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Hypothesis evaluation failed: {exc}")
