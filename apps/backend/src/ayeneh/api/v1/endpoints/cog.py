"""COG Cognitive Architecture API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from ayeneh.cog.conversation.understanding import ConversationUnderstandingEngine
from ayeneh.cog.evidence.extraction import EvidenceExtractionEngine
from ayeneh.cog.knowledge.extraction import PersonalKnowledgeEngine
from ayeneh.cog.narrative.extraction import NarrativeExtractionEngine
from ayeneh.cog.belief.modeling import BeliefModelingEngine
from ayeneh.cog.value.modeling import ValueModelingEngine
from ayeneh.cog.goal.modeling import GoalModelingEngine
from ayeneh.cog.identity.graph import IdentityGraphEngine
from ayeneh.cog.decision.architecture import DecisionArchitectureEngine
from ayeneh.cog.pattern.engine import BehavioralPatternEngine
from ayeneh.cog.reflection.engine import ReflectionEngine
from ayeneh.cog.trajectory.engine import CognitiveTrajectoryEngine
from ayeneh.cog.meta_cognition.engine import MetaCognitionEngine

router = APIRouter(prefix="/cog", tags=["cognitive"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ConversationInput(BaseModel):
    user_id: str
    messages: list[dict[str, Any]]
    language: str = "en"


class CognitiveAnalysisResponse(BaseModel):
    conversation_id: str
    evidence_count: int
    beliefs_extracted: int
    narratives_extracted: int
    values_extracted: int
    goals_extracted: int
    identity_components: int
    decisions: int
    patterns: int
    reflections: int
    meta_cognitive_objects: int
    awakening_level: float
    reality_calibration: float


# ---------------------------------------------------------------------------
# Helpers — convert COG dataclass instances to plain dicts
# ---------------------------------------------------------------------------


def _evidence_to_dict(ev: Any) -> dict[str, Any]:
    """Convert an EvidenceObject (or similar dataclass) to a dict expected by downstream engines."""
    if isinstance(ev, dict):
        return ev
    return {
        "identifier": getattr(ev, "identifier", getattr(ev, "id", "")),
        "id": getattr(ev, "identifier", getattr(ev, "id", "")),
        "text": getattr(ev, "normalized_text", getattr(ev, "original_text", "")),
        "original_text": getattr(ev, "original_text", ""),
        "normalized_text": getattr(ev, "normalized_text", ""),
        "category": getattr(ev, "category", getattr(ev, "epistemic_classification", "")),
        "type": getattr(ev, "category", ""),
        "confidence": getattr(ev, "confidence", 0.0),
        "speaker": getattr(ev, "speaker", ""),
    }


def _narrative_to_dict(n: Any) -> dict[str, Any]:
    """Convert a NarrativeObject to a dict for downstream engines."""
    if isinstance(n, dict):
        return n
    return {
        "identifier": getattr(n, "identifier", ""),
        "id": getattr(n, "identifier", ""),
        "text": getattr(n, "summary", getattr(n, "title", "")),
        "statement": getattr(n, "summary", ""),
        "summary": getattr(n, "summary", ""),
        "title": getattr(n, "title", ""),
        "category": getattr(n, "narrative_type", ""),
        "type": getattr(n, "narrative_type", ""),
    }


def _belief_to_dict(b: Any) -> dict[str, Any]:
    """Convert a BeliefObject to a dict for downstream engines."""
    if isinstance(b, dict):
        return b
    return {
        "identifier": getattr(b, "identifier", ""),
        "id": getattr(b, "identifier", ""),
        "text": getattr(b, "belief_statement", ""),
        "statement": getattr(b, "belief_statement", ""),
        "belief_statement": getattr(b, "belief_statement", ""),
        "category": getattr(b, "category", ""),
        "type": getattr(b, "category", ""),
        "confidence": getattr(b, "confidence", 0.0),
    }


def _value_to_dict(v: Any) -> dict[str, Any]:
    """Convert a ValueObject to a dict for downstream engines."""
    if isinstance(v, dict):
        return v
    return {
        "identifier": getattr(v, "identifier", ""),
        "id": getattr(v, "identifier", ""),
        "text": getattr(v, "value_statement", ""),
        "statement": getattr(v, "value_statement", ""),
        "category": getattr(v, "category", ""),
        "type": getattr(v, "category", ""),
    }


def _goal_to_dict(g: Any) -> dict[str, Any]:
    """Convert a GoalObject to a dict for downstream engines."""
    if isinstance(g, dict):
        return g
    return {
        "identifier": getattr(g, "identifier", ""),
        "id": getattr(g, "identifier", ""),
        "text": getattr(g, "goal_statement", ""),
        "statement": getattr(g, "goal_statement", ""),
        "category": getattr(g, "category", ""),
        "type": getattr(g, "category", ""),
    }


def _identity_to_dict(c: Any) -> dict[str, Any]:
    """Convert an IdentityComponent to a dict for downstream engines."""
    if isinstance(c, dict):
        return c
    return {
        "identifier": getattr(c, "identifier", ""),
        "id": getattr(c, "identifier", ""),
        "text": getattr(c, "identity_statement", ""),
        "statement": getattr(c, "identity_statement", ""),
        "category": getattr(c, "lifecycle_state", ""),
    }


def _decision_to_dict(d: Any) -> dict[str, Any]:
    """Convert a DecisionObject to a dict for downstream engines."""
    if isinstance(d, dict):
        return d
    return {
        "identifier": getattr(d, "identifier", ""),
        "id": getattr(d, "identifier", ""),
        "text": getattr(d, "decision_statement", ""),
        "category": getattr(d, "context", ""),
    }


def _pattern_to_dict(p: Any) -> dict[str, Any]:
    """Convert a PatternObject to a dict for downstream engines."""
    if isinstance(p, dict):
        return p
    return {
        "identifier": getattr(p, "identifier", ""),
        "id": getattr(p, "identifier", ""),
        "text": getattr(p, "pattern_description", ""),
        "description": getattr(p, "pattern_description", ""),
        "type": getattr(p, "pattern_type", ""),
        "category": getattr(p, "pattern_type", ""),
    }


def _reflection_to_dict(r: Any) -> dict[str, Any]:
    """Convert a ReflectionObject to a dict for downstream engines."""
    if isinstance(r, dict):
        return r
    return {
        "identifier": getattr(r, "identifier", ""),
        "id": getattr(r, "identifier", ""),
        "text": getattr(r, "reflection_statement", ""),
        "reflection": getattr(r, "reflection_statement", ""),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/analyze", response_model=CognitiveAnalysisResponse)
async def analyze_conversation(input_data: ConversationInput) -> CognitiveAnalysisResponse:
    """Run the full COG cognitive pipeline on a conversation."""
    conv_id = f"conv-{hash(str(input_data.messages)) % 10000}"

    try:
        # Phase 1 — Conversation Understanding (COG-01)
        conv_engine = ConversationUnderstandingEngine()
        understanding = conv_engine.process(
            conversation_id=conv_id,
            messages=input_data.messages,
            language=input_data.language,
        )

        # Phase 2 — Evidence Extraction (COG-02)
        evidence_engine = EvidenceExtractionEngine()
        evidence_result = evidence_engine.process(understanding)
        evidence_dicts = [_evidence_to_dict(e) for e in evidence_result.evidence_objects]

        # Phase 3 — Personal Knowledge (COG-04)
        knowledge_engine = PersonalKnowledgeEngine()
        knowledge_result = knowledge_engine.process(evidence_dicts)

        # Phase 4 — Narrative Extraction (COG-05)
        narrative_engine = NarrativeExtractionEngine()
        narrative_result = narrative_engine.process(
            evidence_dicts,
            knowledge_objects=list(knowledge_result.knowledge_objects),
        )
        narrative_dicts = [_narrative_to_dict(n) for n in narrative_result.narratives]

        # Phase 5 — Belief Modeling (COG-06)
        belief_engine = BeliefModelingEngine()
        belief_result = belief_engine.process(evidence_dicts, narrative_dicts)
        belief_dicts = [_belief_to_dict(b) for b in belief_result.beliefs]

        # Phase 6 — Value Modeling (COG-07)
        value_engine = ValueModelingEngine()
        value_result = value_engine.process(evidence_dicts, belief_dicts)
        value_dicts = [_value_to_dict(v) for v in value_result.values]

        # Phase 7 — Goal Modeling (COG-08)
        goal_engine = GoalModelingEngine()
        goal_result = goal_engine.process(evidence_dicts, value_dicts, belief_dicts)
        goal_dicts = [_goal_to_dict(g) for g in goal_result.goals]

        # Phase 8 — Identity Graph (COG-09)
        identity_engine = IdentityGraphEngine()
        identity_result = identity_engine.process(
            evidence_dicts,
            beliefs=[b.identifier for b in belief_result.beliefs],
            values=[v.identifier for v in value_result.values],
            goals=[g.identifier for g in goal_result.goals],
            narratives=[n.identifier for n in narrative_result.narratives],
        )
        identity_dicts = [_identity_to_dict(c) for c in identity_result.components.values()]

        # Phase 9 — Decision Architecture (COG-10)
        decision_engine = DecisionArchitectureEngine()
        decision_result = decision_engine.process(
            evidence_dicts,
            beliefs=[b.identifier for b in belief_result.beliefs],
            values=[v.identifier for v in value_result.values],
            goals=[g.identifier for g in goal_result.goals],
            narratives=[n.identifier for n in narrative_result.narratives],
            identity=[c.identifier for c in identity_result.components.values()],
        )
        decision_dicts = [_decision_to_dict(d) for d in decision_result.decisions.values()]

        # Phase 10 — Behavioral Patterns (COG-11)
        pattern_engine = BehavioralPatternEngine()
        pattern_result = pattern_engine.process(evidence_dicts, decision_dicts)
        pattern_dicts = [_pattern_to_dict(p) for p in pattern_result.patterns.values()]

        # Phase 11 — Reflection (COG-12)
        reflection_engine = ReflectionEngine()
        reflection_result = reflection_engine.process(
            evidence_dicts,
            patterns=pattern_dicts,
            narratives=narrative_dicts,
            beliefs=belief_dicts,
            identity=identity_dicts,
        )
        reflection_dicts = [_reflection_to_dict(r) for r in reflection_result.reflections.values()]

        # Phase 12 — Cognitive Trajectory (COG-13)
        trajectory_engine = CognitiveTrajectoryEngine()
        trajectory_result = trajectory_engine.process(
            cognitive_objects=belief_dicts + value_dicts,
            evidence=evidence_dicts,
        )

        # Phase 13 — Meta-Cognition (COG-16)
        meta_engine = MetaCognitionEngine()
        meta_result = meta_engine.process(
            evidence_dicts,
            reflections=reflection_dicts,
            narratives=narrative_dicts,
            beliefs=belief_dicts,
            identity=identity_dicts,
        )

        return CognitiveAnalysisResponse(
            conversation_id=conv_id,
            evidence_count=evidence_result.total_extracted,
            beliefs_extracted=belief_result.total_extracted,
            narratives_extracted=narrative_result.total_extracted,
            values_extracted=value_result.total_extracted,
            goals_extracted=goal_result.total_extracted,
            identity_components=len(identity_result.components),
            decisions=decision_result.total_extracted,
            patterns=pattern_result.total_extracted,
            reflections=reflection_result.total_extracted,
            meta_cognitive_objects=meta_result.total_extracted,
            awakening_level=identity_result.observer_self.de_identification_level,
            reality_calibration=0.0,
        )

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
async def cog_health() -> dict[str, Any]:
    """Health check for the COG subsystem."""
    return {"status": "healthy", "modules": 15, "version": "1.0.0"}
