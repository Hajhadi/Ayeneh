"""BlindSpotAgent — identifies blind spots in the user's thinking."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.agents.base import AgentOutput, BaseAgent
from ayeneh.application.services.memory import Memory, MemoryType

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class BlindSpotConfig:
    """Configuration thresholds for blind spot detection."""

    min_evidence: int = 2
    min_confidence: float = 0.3
    max_blind_spots_per_run: int = 10
    contradiction_weight: float = 0.4
    inconsistency_weight: float = 0.3
    gap_weight: float = 0.2
    assumption_weight: float = 0.1


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------

class BlindSpotSeverity(str):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class BlindSpotOutput:
    """Structured blind spot output from the LLM."""

    title: str = ""
    description: str = ""
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)
    supporting_patterns: list[dict[str, Any]] = field(default_factory=list)
    supporting_reflections: list[dict[str, Any]] = field(default_factory=list)
    supporting_citations: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5
    alternative_interpretations: list[str] = field(default_factory=list)
    reflective_questions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    severity: str = "low"


@dataclass
class BlindSpotDecision:
    """A single blind spot detection decision."""

    blind_spot: BlindSpotOutput
    confidence: float
    severity: str
    evidence_count: int
    reasoning: str = ""
    is_valid: bool = True


# ---------------------------------------------------------------------------
# Abstract ports
# ---------------------------------------------------------------------------

class LLMGateway:
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        raise NotImplementedError


class PromptBuilder:
    async def build(self, task_type: str, **kwargs: Any) -> Any:
        raise NotImplementedError


class KnowledgeRetriever:
    async def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        raise NotImplementedError


class BlindSpotRepository:
    async def create(self, blind_spot: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    async def list_by_user(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# BlindSpotAgent
# ---------------------------------------------------------------------------

class BlindSpotAgent(BaseAgent):
    """Production-grade blind spot detection agent.

    Identifies inconsistencies, reasoning errors, biases, and gaps
    in the user's cognitive model. Never diagnoses or labels.
    """

    name = "blind_spot"

    def __init__(
        self,
        llm: LLMGateway | None = None,
        prompt_builder: PromptBuilder | None = None,
        repo: BlindSpotRepository | None = None,
        knowledge_retriever: KnowledgeRetriever | None = None,
        config: BlindSpotConfig | None = None,
        model: str = "gpt-4o-mini",
        max_retries: int = 2,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        self._llm = llm
        self._prompt_builder = prompt_builder
        self._repo = repo
        self._knowledge = knowledge_retriever
        self._config = config or BlindSpotConfig()
        self._model = model
        self._max_retries = max_retries
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def execute(self, context: dict[str, Any]) -> AgentOutput:
        """Execute blind spot detection."""
        start_time = time.monotonic()

        try:
            user_id = context.get("user_id", "")
            if not user_id:
                return self._fail("No user_id", start_time)

            memories = self._collect_memories(context)
            patterns = self._collect_patterns(context)
            reflections = context.get("reflections", [])

            if len(memories) < self._config.min_evidence and not patterns:
                return self._success_empty(user_id, start_time)

            knowledge = await self._retrieve_knowledge(memories, patterns)

            candidates = self._detect_blind_spots(memories, patterns, reflections, knowledge)

            if self._llm is not None:
                try:
                    llm_spots = await self._llm_enhance(candidates, memories, patterns, reflections, knowledge)
                    candidates.extend(llm_spots)
                except Exception as exc:
                    logger.warning("llm_enhancement_failed", error=str(exc))

            validated = [c for c in candidates if c.is_valid and c.confidence >= self._config.min_confidence]
            validated.sort(key=lambda d: d.confidence, reverse=True)
            validated = validated[: self._config.max_blind_spots_per_run]

            stored = await self._store_blind_spots(validated, user_id)
            latency_ms = (time.monotonic() - start_time) * 1000

            events = []
            for bs in stored:
                events.append({
                    "event_type": "BlindSpotDetected",
                    "blind_spot_id": bs.get("id", ""),
                    "title": bs.get("title", ""),
                    "severity": bs.get("severity", "low"),
                })

            logger.info(
                "blind_spot_completed",
                user_id=user_id,
                candidates=len(candidates),
                validated=len(validated),
                stored=len(stored),
                latency_ms=round(latency_ms, 2),
            )

            return AgentOutput(
                status="success",
                data={
                    "blind_spots": stored or [self._decision_to_dict(d) for d in validated],
                    "total_detected": len(validated),
                },
                metadata={
                    "candidates_detected": len(candidates),
                    "validated_count": len(validated),
                    "stored_count": len(stored),
                    "latency_ms": round(latency_ms, 2),
                    "evidence_analyzed": len(memories),
                    "patterns_analyzed": len(patterns),
                    "reflections_analyzed": len(reflections),
                },
                events=events,
            )

        except Exception as exc:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.exception("blind_spot_failed", user_id=context.get("user_id", ""), latency_ms=round(latency_ms, 2))
            return AgentOutput(
                status="failed",
                data={"error": str(exc), "blind_spots": []},
                metadata={"latency_ms": round(latency_ms, 2)},
                events=[{"event_type": "BlindSpotFailed", "error": str(exc)}],
            )

    # ------------------------------------------------------------------
    # Evidence collection
    # ------------------------------------------------------------------

    def _collect_memories(self, context: dict[str, Any]) -> list[Memory]:
        memories: list[Memory] = []
        for key in ("episodic_memories", "semantic_memories", "pattern_memories", "reflection_memories"):
            for item in context.get(key, []):
                if isinstance(item, Memory):
                    memories.append(item)
                elif isinstance(item, dict):
                    try:
                        memories.append(Memory(
                            id=uuid.UUID(item.get("id", str(uuid.uuid4()))),
                            user_id=uuid.UUID(item.get("user_id", "00000000-0000-0000-0000-000000000000")),
                            type=MemoryType(item.get("type", "semantic")),
                            content=item.get("content", ""),
                            confidence=float(item.get("confidence", 0.5)),
                            created_at=datetime.fromisoformat(item["created_at"]) if "created_at" in item else datetime.now(UTC),
                        ))
                    except (ValueError, KeyError):
                        continue
        return memories

    def _collect_patterns(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        return [p for p in context.get("patterns", []) if isinstance(p, dict)]

    # ------------------------------------------------------------------
    # Knowledge retrieval
    # ------------------------------------------------------------------

    async def _retrieve_knowledge(self, memories: list[Memory], patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self._knowledge is None:
            return []
        query = self._build_knowledge_query(memories, patterns)
        if not query:
            return []
        try:
            return await self._knowledge.search(query, limit=5)
        except Exception as exc:
            logger.warning("knowledge_retrieval_failed", error=str(exc))
            return []

    def _build_knowledge_query(self, memories: list[Memory], patterns: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        if memories:
            parts.append("User experiences: " + "; ".join(m.content[:80] for m in memories[:5]))
        if patterns:
            parts.append("Patterns: " + ", ".join(p.get("name", "") for p in patterns[:3]))
        return " ".join(parts)[:500]

    # ------------------------------------------------------------------
    # Blind spot detection
    # ------------------------------------------------------------------

    def _detect_blind_spots(
        self,
        memories: list[Memory],
        patterns: list[dict[str, Any]],
        reflections: list[dict[str, Any]],
        knowledge: list[dict[str, Any]],
    ) -> list[BlindSpotDecision]:
        candidates: list[BlindSpotDecision] = []

        candidates.extend(self._detect_contradictions(memories, patterns))
        candidates.extend(self._detect_confirmation_bias(memories))
        candidates.extend(self._detect_avoidance_loops(memories, patterns))
        candidates.extend(self._detect_self_defeating(memories))
        candidates.extend(self._detect_value_conflicts(memories, patterns))
        candidates.extend(self._detect_emotional_blind_spots(memories))
        candidates.extend(self._detect_confidence_imbalances(memories))
        candidates.extend(self._detect_weak_assumptions(memories, patterns))
        candidates.extend(self._detect_reasoning_errors(memories, patterns))

        return candidates

    # ------------------------------------------------------------------
    # Detection methods
    # ------------------------------------------------------------------

    def _detect_contradictions(self, memories: list[Memory], patterns: list[dict[str, Any]]) -> list[BlindSpotDecision]:
        candidates: list[BlindSpotDecision] = []

        positive = {"happy", "grateful", "proud", "accomplished", "confident", "hopeful", "calm", "content"}
        negative = {"sad", "anxious", "angry", "frustrated", "lonely", "scared", "worried", "stressed", "depressed"}

        pos_memories = [m for m in memories if any(w in m.content.lower() for w in positive)]
        neg_memories = [m for m in memories if any(w in m.content.lower() for w in negative)]

        if pos_memories and neg_memories:
            recent_pos = [m for m in pos_memories if (datetime.now(UTC) - m.created_at).days <= 14]
            recent_neg = [m for m in neg_memories if (datetime.now(UTC) - m.created_at).days <= 14]

            if recent_pos and recent_neg:
                evidence = [{"memory_id": str(m.id), "content": m.content[:100]} for m in recent_pos[:2] + recent_neg[:2]]
                confidence = min(1.0, 0.3 + len(evidence) * 0.1)
                candidates.append(BlindSpotDecision(
                    blind_spot=BlindSpotOutput(
                        title="Mixed emotional signals",
                        description=f"Recent memories show both positive ({len(recent_pos)}) and negative ({len(recent_neg)}) emotional content. This may indicate a conflict between reported feelings and underlying experiences.",
                        supporting_evidence=evidence,
                        confidence=confidence,
                        alternative_interpretations=["The user may be processing complex emotions simultaneously", "Different contexts may trigger different emotional responses"],
                        reflective_questions=["What might explain the coexistence of these feelings?", "Are there specific situations that trigger each feeling?"],
                        severity="medium",
                    ),
                    confidence=confidence,
                    severity="medium",
                    evidence_count=len(evidence),
                    reasoning=f"Detected {len(recent_pos)} positive and {len(recent_neg)} negative memories in recent period",
                ))

        for pat in patterns:
            name = pat.get("name", "").lower()
            if "avoidance" in name:
                avoid_memories = [m for m in memories if any(w in m.content.lower() for w in {"avoid", "avoiding", "postpone", "delay"})]
                confront_memories = [m for m in memories if any(w in m.content.lower() for w in {"confront", "assert", "speak up", "address"})]
                if avoid_memories and confront_memories:
                    evidence = [{"memory_id": str(m.id), "content": m.content[:100]} for m in avoid_memories[:2] + confront_memories[:2]]
                    candidates.append(BlindSpotDecision(
                        blind_spot=BlindSpotOutput(
                            title="Avoidance vs. confrontation tension",
                            description="User displays both avoidance tendencies and moments of confrontation, suggesting an unresolved internal conflict.",
                            supporting_evidence=evidence,
                            supporting_patterns=[{"name": pat.get("name", ""), "description": pat.get("description", "")}],
                            confidence=0.5,
                            alternative_interpretations=["Different life domains may require different approaches", "Growth may be happening unevenly"],
                            reflective_questions=["When does the user choose avoidance vs. confrontation?", "What makes the difference?"],
                            severity="medium",
                        ),
                        confidence=0.5,
                        severity="medium",
                        evidence_count=len(evidence),
                        reasoning="Avoidance pattern coexists with confrontation behavior",
                    ))

        return candidates

    def _detect_confirmation_bias(self, memories: list[Memory]) -> list[BlindSpotDecision]:
        candidates: list[BlindSpotDecision] = []

        belief_words = {"believe", "think", "feel", "know", "assume", "expect", "sure", "certain"}
        belief_memories = [m for m in memories if any(w in m.content.lower() for w in belief_words)]

        if len(belief_memories) >= 3:
            " ".join(m.content.lower() for m in belief_memories)
            unique_beliefs = set()
            for m in belief_memories:
                words = [w for w in m.content.lower().split() if w in belief_words]
                unique_beliefs.update(words)

            if len(unique_beliefs) >= 2:
                evidence = [{"memory_id": str(m.id), "content": m.content[:100]} for m in belief_memories[:3]]
                candidates.append(BlindSpotDecision(
                    blind_spot=BlindSpotOutput(
                        title="Concentration of belief statements",
                        description=f"User expresses {len(belief_memories)} belief-oriented statements. This may indicate confirmation bias if contradictory evidence is being overlooked.",
                        supporting_evidence=evidence,
                        confidence=0.4,
                        alternative_interpretations=["Strong self-awareness may naturally produce many belief statements", "The user may be selectively reporting beliefs"],
                        reflective_questions=["Are there beliefs the user holds that are not well-supported by experience?"],
                        severity="low",
                    ),
                    confidence=0.4,
                    severity="low",
                    evidence_count=len(evidence),
                    reasoning=f"{len(belief_memories)} belief statements detected across memories",
                ))

        return candidates

    def _detect_avoidance_loops(self, memories: list[Memory], patterns: list[dict[str, Any]]) -> list[BlindSpotDecision]:
        candidates: list[BlindSpotDecision] = []

        avoid_words = {"avoid", "avoiding", "postpone", "procrastinate", "delay", "escape", "ignore", "withdraw"}
        avoid_memories = [m for m in memories if any(w in m.content.lower() for w in avoid_words)]

        if len(avoid_memories) >= 2:
            time_span = (max(m.created_at for m in avoid_memories) - min(m.created_at for m in avoid_memories)).days
            if time_span > 7:
                evidence = [{"memory_id": str(m.id), "content": m.content[:100]} for m in avoid_memories[:3]]
                candidates.append(BlindSpotDecision(
                    blind_spot=BlindSpotOutput(
                        title="Recurring avoidance pattern",
                        description=f"Avoidance behavior appears across {len(avoid_memories)} memories spanning {time_span} days. This may indicate a persistent avoidance loop.",
                        supporting_evidence=evidence,
                        confidence=min(1.0, 0.3 + len(avoid_memories) * 0.1),
                        alternative_interpretations=["The user may be strategically prioritizing", "Different avoidance may serve different purposes"],
                        reflective_questions=["What is being avoided and why?", "What would change if the avoidance stopped?"],
                        severity="medium" if len(avoid_memories) >= 3 else "low",
                    ),
                    confidence=min(1.0, 0.3 + len(avoid_memories) * 0.1),
                    severity="medium" if len(avoid_memories) >= 3 else "low",
                    evidence_count=len(evidence),
                    reasoning=f"Avoidance detected across {len(avoid_memories)} memories over {time_span} days",
                ))

        return candidates

    def _detect_self_defeating(self, memories: list[Memory]) -> list[BlindSpotDecision]:
        candidates: list[BlindSpotDecision] = []

        defeat_words = {"but i still", "even though", "despite knowing", "i know but", "i should but", "i can't seem to"}
        defeat_memories = [m for m in memories if any(w in m.content.lower() for w in defeat_words)]

        if len(defeat_memories) >= 2:
            evidence = [{"memory_id": str(m.id), "content": m.content[:100]} for m in defeat_memories[:3]]
            candidates.append(BlindSpotDecision(
                blind_spot=BlindSpotOutput(
                    title="Self-defeating pattern",
                    description=f"User shows {len(defeat_memories)} instances of knowing what to do but not following through. This may indicate a self-defeating strategy.",
                    supporting_evidence=evidence,
                    confidence=min(1.0, 0.3 + len(defeat_memories) * 0.15),
                    alternative_interpretations=["The gap between knowing and doing is normal", "External constraints may be limiting follow-through"],
                    reflective_questions=["What prevents translating knowledge into action?", "Are there systemic barriers being overlooked?"],
                    severity="medium",
                ),
                confidence=min(1.0, 0.3 + len(defeat_memories) * 0.15),
                severity="medium",
                evidence_count=len(evidence),
                reasoning=f"{len(defeat_memories)} self-defeating instances detected",
            ))

        return candidates

    def _detect_value_conflicts(self, memories: list[Memory], patterns: list[dict[str, Any]]) -> list[BlindSpotDecision]:
        candidates: list[BlindSpotDecision] = []

        value_words = {"value", "important", "matter", "care about", "priority", "meaningful"}
        value_memories = [m for m in memories if any(w in m.content.lower() for w in value_words)]

        behavior_words = {"avoid", "procrastinate", "delay", "skip", "ignore", "neglect"}
        behavior_memories = [m for m in memories if any(w in m.content.lower() for w in behavior_words)]

        if value_memories and behavior_memories:
            evidence = [{"memory_id": str(m.id), "content": m.content[:100]} for m in value_memories[:2] + behavior_memories[:2]]
            candidates.append(BlindSpotDecision(
                blind_spot=BlindSpotOutput(
                    title="Potential value-behavior gap",
                    description=f"User expresses {len(value_memories)} values but also shows {len(behavior_memories)} avoidance behaviors. There may be a gap between stated values and observed actions.",
                    supporting_evidence=evidence,
                    confidence=min(1.0, 0.3 + len(evidence) * 0.1),
                    alternative_interpretations=["Values and behaviors may apply to different life domains", "The user may be in transition between value systems"],
                    reflective_questions=["How do the user's stated values align with their daily choices?"],
                    severity="medium",
                ),
                confidence=min(1.0, 0.3 + len(evidence) * 0.1),
                severity="medium",
                evidence_count=len(evidence),
                reasoning=f"{len(value_memories)} value statements vs {len(behavior_memories)} avoidance behaviors",
            ))

        return candidates

    def _detect_emotional_blind_spots(self, memories: list[Memory]) -> list[BlindSpotDecision]:
        candidates: list[BlindSpotDecision] = []

        emotional_words = {"feel", "emotion", "mood", "anxious", "sad", "angry", "happy", "scared", "lonely"}
        emotional_memories = [m for m in memories if any(w in m.content.lower() for w in emotional_words)]

        non_emotional = [m for m in memories if not any(w in m.content.lower() for w in emotional_words)]

        if len(emotional_memories) > 0 and len(non_emotional) > len(emotional_memories) * 2:
            evidence = [{"memory_id": str(m.id), "content": m.content[:100]} for m in non_emotional[:3]]
            candidates.append(BlindSpotDecision(
                blind_spot=BlindSpotOutput(
                    title="Limited emotional exploration",
                    description=f"Most memories ({len(non_emotional)}) focus on events or facts rather than emotional experience. Only {len(emotional_memories)} mention feelings. This may indicate emotional blind spots.",
                    supporting_evidence=evidence,
                    confidence=0.35,
                    alternative_interpretations=["The user may process emotions differently", "Emotional content may be underreported in this sample"],
                    reflective_questions=["What feelings might be present but unacknowledged?"],
                    severity="low",
                ),
                confidence=0.35,
                severity="low",
                evidence_count=len(evidence),
                reasoning=f"{len(non_emotional)} non-emotional vs {len(emotional_memories)} emotional memories",
            ))

        return candidates

    def _detect_confidence_imbalances(self, memories: list[Memory]) -> list[BlindSpotDecision]:
        candidates: list[BlindSpotDecision] = []

        high_conf = [m for m in memories if m.confidence > 0.8]
        low_conf = [m for m in memories if m.confidence < 0.3]

        if high_conf and low_conf and len(high_conf) > len(low_conf) * 3:
            evidence = [{"memory_id": str(m.id), "content": m.content[:100], "confidence": m.confidence} for m in high_conf[:2] + low_conf[:2]]
            candidates.append(BlindSpotDecision(
                blind_spot=BlindSpotOutput(
                    title="Overconfidence pattern",
                    description=f"User expresses high confidence in {len(high_conf)} memories but low confidence in only {len(low_conf)}. This imbalance may indicate overconfidence or selective reporting.",
                    supporting_evidence=evidence,
                    confidence=0.4,
                    alternative_interpretations=["The user may be naturally confident in this domain", "Low-confidence memories may be less frequently reported"],
                    reflective_questions=["Are there areas where the user might benefit from more uncertainty?"],
                    severity="low",
                ),
                confidence=0.4,
                severity="low",
                evidence_count=len(evidence),
                reasoning=f"{len(high_conf)} high-confidence vs {len(low_conf)} low-confidence memories",
            ))

        return candidates

    def _detect_weak_assumptions(self, memories: list[Memory], patterns: list[dict[str, Any]]) -> list[BlindSpotDecision]:
        candidates: list[BlindSpotDecision] = []

        assumption_words = {"assume", "probably", "must be", "definitely", "always", "never", "everyone", "nobody"}
        assumption_memories = [m for m in memories if any(w in m.content.lower() for w in assumption_words)]

        if len(assumption_memories) >= 2:
            evidence = [{"memory_id": str(m.id), "content": m.content[:100]} for m in assumption_memories[:3]]
            candidates.append(BlindSpotDecision(
                blind_spot=BlindSpotOutput(
                    title="Frequent assumption-making",
                    description=f"User makes {len(assumption_memories)} assumption-oriented statements. Some assumptions may lack sufficient supporting evidence.",
                    supporting_evidence=evidence,
                    confidence=0.35,
                    alternative_interpretations=["Assumptions may be well-founded in experience", "The user may be using shorthand for nuanced beliefs"],
                    reflective_questions=["Which assumptions could benefit from more evidence?"],
                    severity="low",
                ),
                confidence=0.35,
                severity="low",
                evidence_count=len(evidence),
                reasoning=f"{len(assumption_memories)} assumption statements detected",
            ))

        return candidates

    def _detect_reasoning_errors(self, memories: list[Memory], patterns: list[dict[str, Any]]) -> list[BlindSpotDecision]:
        candidates: list[BlindSpotDecision] = []

        distortion_words = {"always", "never", "every time", "nobody", "everyone", "nothing", "everything", "ruined", "perfect", "impossible"}
        distortion_memories = [m for m in memories if any(w in m.content.lower() for w in distortion_words)]

        if len(distortion_memories) >= 2:
            evidence = [{"memory_id": str(m.id), "content": m.content[:100]} for m in distortion_memories[:3]]
            candidates.append(BlindSpotDecision(
                blind_spot=BlindSpotOutput(
                    title="Recurring reasoning patterns",
                    description=f"User shows {len(distortion_memories)} instances of absolute or extreme language. These may indicate cognitive distortions worth examining.",
                    supporting_evidence=evidence,
                    confidence=min(1.0, 0.3 + len(distortion_memories) * 0.1),
                    alternative_interpretations=["The user may be using natural language hyperbole", "Context may warrant strong language"],
                    reflective_questions=["Are these absolute statements accurate?", "What would a more nuanced version look like?"],
                    severity="low" if len(distortion_memories) < 3 else "medium",
                ),
                confidence=min(1.0, 0.3 + len(distortion_memories) * 0.1),
                severity="low" if len(distortion_memories) < 3 else "medium",
                evidence_count=len(evidence),
                reasoning=f"{len(distortion_memories)} reasoning pattern instances detected",
            ))

        return candidates

    # ------------------------------------------------------------------
    # LLM enhancement
    # ------------------------------------------------------------------

    async def _llm_enhance(
        self,
        candidates: list[BlindSpotDecision],
        memories: list[Memory],
        patterns: list[dict[str, Any]],
        reflections: list[dict[str, Any]],
        knowledge: list[dict[str, Any]],
    ) -> list[BlindSpotDecision]:
        if self._llm is None:
            return []

        prompt = self._build_llm_prompt(candidates, memories, patterns, reflections, knowledge)

        for attempt in range(self._max_retries + 1):
            try:
                result = await self._llm.chat(prompt, model=self._model, temperature=self._temperature, max_tokens=self._max_tokens)
                content = self._extract_content(result)
                return self._parse_llm_output(content)
            except Exception as exc:
                logger.warning("llm_blind_spot_retry", attempt=attempt + 1, error=str(exc))
                if attempt < self._max_retries:
                    import asyncio
                    await asyncio.sleep(0.5 * (2 ** attempt))

        return []

    def _build_llm_prompt(
        self,
        candidates: list[BlindSpotDecision],
        memories: list[Memory],
        patterns: list[dict[str, Any]],
        reflections: list[dict[str, Any]],
        knowledge: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        existing_titles = [c.blind_spot.title for c in candidates]
        memory_summary = "\n".join(f"- [{m.type.value}] {m.content[:150]}" for m in memories[:15])
        pattern_summary = "\n".join(f"- {p.get('name', '')}: {p.get('description', '')[:100]}" for p in patterns[:5])
        reflection_summary = "\n".join(f"- {r.get('summary', '')[:150]}" for r in reflections[:3]) if reflections else "No reflections available."
        knowledge_summary = "\n".join(f"- {k.get('content', '')[:150]}" for k in knowledge[:3]) if knowledge else "No relevant knowledge."

        system = (
            "You are Ayeneh's BlindSpotAgent. Your job is to identify blind spots in the user's thinking. "
            "You must NEVER diagnose, label, or make clinical claims. You are not a therapist. "
            "Separate facts from interpretations. Express uncertainty when confidence is limited. "
            "Never fabricate evidence. Never infer stable personality traits without repeated evidence.\n\n"
            "Respond with a JSON array of blind spot objects, each containing: title, description, "
            "supporting_evidence (list of dicts with memory_id and content), confidence (0-1), "
            "alternative_interpretations (list of strings), reflective_questions (list of strings), "
            "limitations (list of strings), severity ('low', 'medium', or 'high')."
        )

        user_msg = (
            f"Existing blind spots already detected: {existing_titles}\n\n"
            f"Memories ({len(memories)} total):\n{memory_summary}\n\n"
            f"Patterns:\n{pattern_summary}\n\n"
            f"Reflections:\n{reflection_summary}\n\n"
            f"Knowledge:\n{knowledge_summary}\n\n"
            "Identify any ADDITIONAL blind spots not in the existing list. "
            "Focus on contradictions, reasoning errors, biases, value-behavior gaps, and emotional blind spots."
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ]

    def _extract_content(self, result: dict[str, Any]) -> str:
        choices = result.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "")

    def _parse_llm_output(self, raw_text: str) -> list[BlindSpotDecision]:
        text = raw_text.strip()
        if not text:
            return []

        try:
            parsed = json.loads(text)
            if not isinstance(parsed, list):
                parsed = [parsed] if isinstance(parsed, dict) else []

            decisions: list[BlindSpotDecision] = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                bs = BlindSpotOutput(
                    title=item.get("title", "Untitled"),
                    description=item.get("description", ""),
                    supporting_evidence=item.get("supporting_evidence", []),
                    confidence=min(1.0, max(0.0, item.get("confidence", 0.5))),
                    alternative_interpretations=item.get("alternative_interpretations", []),
                    reflective_questions=item.get("reflective_questions", []),
                    limitations=item.get("limitations", []),
                    severity=item.get("severity", "low"),
                )
                decisions.append(BlindSpotDecision(
                    blind_spot=bs,
                    confidence=bs.confidence,
                    severity=bs.severity,
                    evidence_count=len(bs.supporting_evidence),
                    reasoning="LLM-enhanced blind spot detection",
                    is_valid=bool(bs.description),
                ))
            return decisions

        except (json.JSONDecodeError, KeyError):
            return [BlindSpotDecision(
                blind_spot=BlindSpotOutput(title="LLM output", description=text[:500], confidence=0.3, severity="low", limitations=["Could not parse structured output"]),
                confidence=0.3,
                severity="low",
                evidence_count=0,
                reasoning="Fallback from unparseable LLM output",
                is_valid=True,
            )]

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    async def _store_blind_spots(self, decisions: list[BlindSpotDecision], user_id: str) -> list[dict[str, Any]]:
        if self._repo is None:
            return []
        stored: list[dict[str, Any]] = []
        for d in decisions:
            try:
                data = self._decision_to_dict(d)
                data["user_id"] = user_id
                result = await self._repo.create(data)
                stored.append(result)
            except Exception as exc:
                logger.warning("blind_spot_store_failed", error=str(exc))
        return stored

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _decision_to_dict(self, d: BlindSpotDecision) -> dict[str, Any]:
        bs = d.blind_spot
        return {
            "id": str(uuid.uuid4()),
            "title": bs.title,
            "description": bs.description,
            "supporting_evidence": bs.supporting_evidence,
            "supporting_patterns": bs.supporting_patterns,
            "supporting_reflections": bs.supporting_reflections,
            "supporting_citations": bs.supporting_citations,
            "confidence": round(d.confidence, 3),
            "alternative_interpretations": bs.alternative_interpretations,
            "reflective_questions": bs.reflective_questions,
            "limitations": bs.limitations,
            "severity": d.severity,
            "evidence_count": d.evidence_count,
            "reasoning": d.reasoning,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def _success_empty(self, user_id: str, start_time: float) -> AgentOutput:
        latency_ms = (time.monotonic() - start_time) * 1000
        return AgentOutput(
            status="success",
            data={"blind_spots": [], "total_detected": 0},
            metadata={"reasoning": "Insufficient evidence for blind spot detection", "latency_ms": round(latency_ms, 2)},
            events=[],
        )

    def _fail(self, error: str, start_time: float) -> AgentOutput:
        latency_ms = (time.monotonic() - start_time) * 1000
        return AgentOutput(
            status="failed",
            data={"error": error, "blind_spots": []},
            metadata={"latency_ms": round(latency_ms, 2)},
            events=[{"event_type": "BlindSpotFailed", "error": error}],
        )
