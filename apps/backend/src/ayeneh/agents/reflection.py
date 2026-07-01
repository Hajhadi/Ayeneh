"""ReflectionAgent — synthesizes longitudinal reflections from all evidence."""

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
class ReflectionConfig:
    """Configuration for reflection generation."""

    min_memories: int = 3
    min_patterns: int = 1
    min_confidence: float = 0.3
    max_reflections_per_run: int = 5
    evidence_diversity_threshold: float = 0.3
    uncertainty_threshold: float = 0.4


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------

@dataclass
class ReflectionOutput:
    """Structured reflection output from the LLM."""

    title: str = ""
    summary: str = ""
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)
    related_patterns: list[dict[str, Any]] = field(default_factory=list)
    related_memories: list[dict[str, Any]] = field(default_factory=list)
    supporting_citations: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5
    actionable_questions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    interpretations: list[dict[str, Any]] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    growth_areas: list[str] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)


@dataclass
class ReflectionDecision:
    """A single reflection generation decision."""

    reflection: ReflectionOutput
    confidence: float
    evidence_count: int
    memory_count: int
    pattern_count: int
    citation_count: int
    reasoning: str = ""
    is_valid: bool = True


# ---------------------------------------------------------------------------
# Abstract ports
# ---------------------------------------------------------------------------

class ReflectionRepository:
    """Abstract reflection persistence interface."""

    async def create(self, reflection: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    async def list_by_user(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        raise NotImplementedError


class KnowledgeRetriever:
    """Abstract knowledge retrieval interface for the reflection agent."""

    async def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        raise NotImplementedError


class LLMGateway:
    """Abstract LLM interface."""

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
    """Abstract prompt assembly interface."""

    async def build(self, task_type: str, **kwargs: Any) -> Any:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# ReflectionAgent
# ---------------------------------------------------------------------------

class ReflectionAgent(BaseAgent):
    """Production-grade reflection synthesis agent.

    Responsibilities:
    - Analyze retrieved memories, patterns, and long-term changes
    - Detect conflicts, strengths, growth, protective factors, unresolved questions
    - Retrieve supporting knowledge
    - Call the LLM for synthesis
    - Validate structured output
    - Produce Reflection objects grounded in evidence
    """

    name = "reflection"

    def __init__(
        self,
        llm: LLMGateway | None = None,
        prompt_builder: PromptBuilder | None = None,
        reflection_repo: ReflectionRepository | None = None,
        knowledge_retriever: KnowledgeRetriever | None = None,
        config: ReflectionConfig | None = None,
        model: str = "gpt-4o-mini",
        max_retries: int = 2,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        self._llm = llm
        self._prompt_builder = prompt_builder
        self._repo = reflection_repo
        self._knowledge = knowledge_retriever
        self._config = config or ReflectionConfig()
        self._model = model
        self._max_retries = max_retries
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def execute(self, context: dict[str, Any]) -> AgentOutput:
        """Execute reflection synthesis."""
        start_time = time.monotonic()

        try:
            user_id = context.get("user_id", "")
            if not user_id:
                return self._fail("No user_id in context", start_time)

            memories = self._collect_memories(context)
            patterns = self._collect_patterns(context)
            existing = context.get("existing_reflections", [])

            if len(memories) < self._config.min_memories and len(patterns) < self._config.min_patterns:
                return self._success_empty(user_id, len(memories), len(patterns), start_time)

            knowledge = await self._retrieve_knowledge(memories, patterns)

            decision = await self._generate_reflection(
                user_id=user_id,
                memories=memories,
                patterns=patterns,
                existing=existing,
                knowledge=knowledge,
            )

            if not decision.is_valid:
                return self._fail(decision.reasoning or "Invalid reflection", start_time)

            stored = await self._store_reflection(decision, user_id)

            latency_ms = (time.monotonic() - start_time) * 1000

            events = []
            if stored:
                events.append({
                    "event_type": "ReflectionGenerated",
                    "reflection_id": stored.get("id", ""),
                    "confidence": round(decision.confidence, 3),
                })

            logger.info(
                "reflection_completed",
                user_id=user_id,
                confidence=round(decision.confidence, 3),
                evidence_count=decision.evidence_count,
                latency_ms=round(latency_ms, 2),
            )

            return AgentOutput(
                status="success",
                data={
                    "reflection": stored or self._decision_to_dict(decision),
                    "title": decision.reflection.title,
                    "summary": decision.reflection.summary,
                    "confidence": round(decision.confidence, 3),
                },
                metadata={
                    "evidence_count": decision.evidence_count,
                    "memory_count": decision.memory_count,
                    "pattern_count": decision.pattern_count,
                    "citation_count": decision.citation_count,
                    "strengths": decision.reflection.strengths,
                    "growth_areas": decision.reflection.growth_areas,
                    "unresolved_questions": decision.reflection.unresolved_questions,
                    "limitations": decision.reflection.limitations,
                    "latency_ms": round(latency_ms, 2),
                    "reasoning": decision.reasoning,
                },
                events=events,
            )

        except Exception as exc:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.exception("reflection_failed", user_id=context.get("user_id", ""), latency_ms=round(latency_ms, 2))
            return AgentOutput(
                status="failed",
                data={"error": str(exc), "reflection": {}},
                metadata={"latency_ms": round(latency_ms, 2)},
                events=[{"event_type": "ReflectionFailed", "error": str(exc)}],
            )

    # ------------------------------------------------------------------
    # Collection
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

    async def _retrieve_knowledge(
        self, memories: list[Memory], patterns: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
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

    def _build_knowledge_query(
        self, memories: list[Memory], patterns: list[dict[str, Any]]
    ) -> str:
        parts: list[str] = []
        if memories:
            contents = [m.content[:100] for m in memories[:5]]
            parts.append("User experiences: " + "; ".join(contents))
        if patterns:
            names = [p.get("name", "unknown") for p in patterns[:3]]
            parts.append("Patterns: " + ", ".join(names))
        return " ".join(parts)[:500]

    # ------------------------------------------------------------------
    # Reflection generation
    # ------------------------------------------------------------------

    async def _generate_reflection(
        self,
        user_id: str,
        memories: list[Memory],
        patterns: list[dict[str, Any]],
        existing: list[dict[str, Any]],
        knowledge: list[dict[str, Any]],
    ) -> ReflectionDecision:
        analysis = self._analyze_evidence(memories, patterns, existing, knowledge)

        if self._llm is not None:
            try:
                llm_result = await self._call_llm(analysis, memories, patterns, knowledge)
                if llm_result:
                    return llm_result
            except Exception as exc:
                logger.warning("llm_reflection_failed", error=str(exc))

        return self._fallback_reflection(analysis)

    def _analyze_evidence(
        self,
        memories: list[Memory],
        patterns: list[dict[str, Any]],
        existing: list[dict[str, Any]],
        knowledge: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Deterministic analysis of all evidence."""
        now = datetime.now(UTC)

        memory_types: dict[str, int] = {}
        for m in memories:
            memory_types[m.type.value] = memory_types.get(m.type.value, 0) + 1

        time_span_days = (now - min(m.created_at for m in memories)).days if memories else 0

        conflicts = self._detect_conflicts(memories, patterns)
        strengths = self._detect_strengths(memories, patterns)
        growth = self._detect_growth(memories, existing)
        protective = self._detect_protective_factors(memories, patterns)
        unresolved = self._detect_unresolved(memories, patterns)

        return {
            "memory_count": len(memories),
            "pattern_count": len(patterns),
            "memory_types": memory_types,
            "time_span_days": time_span_days,
            "conflicts": conflicts,
            "strengths": strengths,
            "growth": growth,
            "protective_factors": protective,
            "unresolved_questions": unresolved,
            "existing_reflection_count": len(existing),
            "knowledge_count": len(knowledge),
        }

    # ------------------------------------------------------------------
    # Deterministic detection
    # ------------------------------------------------------------------

    def _detect_conflicts(self, memories: list[Memory], patterns: list[dict[str, Any]]) -> list[str]:
        conflicts: list[str] = []

        positive = {"happy", "grateful", "proud", "accomplished", "confident", "hopeful", "calm"}
        negative = {"sad", "anxious", "angry", "frustrated", "lonely", "scared", "worried", "stressed"}

        pos_count = sum(1 for m in memories if any(w in m.content.lower() for w in positive))
        neg_count = sum(1 for m in memories if any(w in m.content.lower() for w in negative))

        if pos_count > 0 and neg_count > 0 and abs(pos_count - neg_count) <= 2:
            conflicts.append("Mixed emotional signals across memories")

        for pat in patterns:
            name = pat.get("name", "").lower()
            if "avoidance" in name and any("confront" in m.content.lower() or "assert" in m.content.lower() for m in memories):
                conflicts.append("Conflict between avoidance pattern and assertive behavior")

        return conflicts

    def _detect_strengths(self, memories: list[Memory], patterns: list[dict[str, Any]]) -> list[str]:
        strengths: list[str] = []
        positive_words = {"grateful", "proud", "accomplished", "resilient", "growth", "learn", "improve", "strong"}
        pos_count = sum(1 for m in memories if any(w in m.content.lower() for w in positive_words))
        if pos_count >= 2:
            strengths.append("Demonstrates capacity for positive reflection and growth")

        for pat in patterns:
            if "positive" in pat.get("name", "").lower() or "growth" in pat.get("name", "").lower():
                strengths.append(f"Positive pattern detected: {pat.get('name', 'unknown')}")

        return strengths

    def _detect_growth(self, memories: list[Memory], existing: list[dict[str, Any]]) -> list[str]:
        growth: list[str] = []
        now = datetime.now(UTC)

        recent = [m for m in memories if (now - m.created_at).days <= 30]
        older = [m for m in memories if (now - m.created_at).days > 30]

        recent_positive = sum(1 for m in recent if any(w in m.content.lower() for w in {"learn", "grow", "improve", "progress", "hopeful"}))
        older_positive = sum(1 for m in older if any(w in m.content.lower() for w in {"learn", "grow", "improve", "progress", "hopeful"}))

        if recent_positive > older_positive:
            growth.append("Increasing positive self-reflection in recent period")

        if len(existing) > 0:
            growth.append("Continued engagement with self-reflection process")

        return growth

    def _detect_protective_factors(self, memories: list[Memory], patterns: list[dict[str, Any]]) -> list[str]:
        factors: list[str] = []
        positive_words = {"support", "friend", "family", "community", "routine", "exercise", "meditation", "therapy"}
        for m in memories:
            found = [w for w in positive_words if w in m.content.lower()]
            if found:
                factors.append(f"Protective factor: {found[0]} mentioned in recent memory")
                break
        return factors

    def _detect_unresolved(self, memories: list[Memory], patterns: list[dict[str, Any]]) -> list[str]:
        questions: list[str] = []
        for pat in patterns:
            if pat.get("trend") in ("increasing", "emerging"):
                questions.append(f"What is driving the increasing {pat.get('name', 'pattern')}?")

        recent_conflict_words = {"confused", "uncertain", "unsure", "don't know", "conflicted"}
        for m in memories[-5:]:
            found = [w for w in recent_conflict_words if w in m.content.lower()]
            if found:
                questions.append("What does this uncertainty mean for the user?")
                break

        return questions

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    async def _call_llm(
        self,
        analysis: dict[str, Any],
        memories: list[Memory],
        patterns: list[dict[str, Any]],
        knowledge: list[dict[str, Any]],
    ) -> ReflectionDecision | None:
        if self._llm is None:
            return None

        prompt = self._build_llm_prompt(analysis, memories, patterns, knowledge)

        for attempt in range(self._max_retries + 1):
            try:
                result = await self._llm.chat(
                    prompt,
                    model=self._model,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                )
                content = self._extract_content(result)
                return self._parse_llm_output(content, analysis)
            except Exception as exc:
                logger.warning("llm_call_retry", attempt=attempt + 1, error=str(exc))
                if attempt < self._max_retries:
                    import asyncio
                    await asyncio.sleep(0.5 * (2 ** attempt))

        return None

    def _build_llm_prompt(
        self,
        analysis: dict[str, Any],
        memories: list[Memory],
        patterns: list[dict[str, Any]],
        knowledge: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        memory_summaries = "\n".join(
            f"- [{m.type.value}] {m.content[:200]} (confidence: {m.confidence:.2f})"
            for m in memories[:20]
        )
        pattern_summaries = "\n".join(
            f"- {p.get('name', 'unknown')}: {p.get('description', '')[:150]}"
            for p in patterns[:10]
        )
        knowledge_summaries = "\n".join(
            f"- {k.get('content', '')[:200]}"
            for k in knowledge[:5]
        ) if knowledge else "No relevant knowledge found."

        system = (
            "You are Ayeneh's ReflectionAgent. Your job is to synthesize everything "
            "known about a user into a reflective insight. You must be grounded in evidence. "
            "Never invent user traits. Clearly distinguish observations from interpretations. "
            "Include uncertainty when confidence is low.\n\n"
            "Respond with a JSON object containing: title, summary, supporting_evidence (list of dicts with memory_id and content), "
            "related_patterns (list of dicts with name and description), related_memories (list of dicts with id and content), "
            "supporting_citations (list of dicts with source and excerpt), confidence (0-1), "
            "actionable_questions (list of strings), limitations (list of strings), "
            "strengths (list of strings), growth_areas (list of strings), unresolved_questions (list of strings)."
        )

        user_msg = (
            f"Analyze the following evidence and produce a reflection:\n\n"
            f"Memories ({analysis['memory_count']} total):\n{memory_summaries}\n\n"
            f"Patterns ({analysis['pattern_count']} total):\n{pattern_summaries}\n\n"
            f"Conflicts detected: {analysis['conflicts']}\n"
            f"Strengths detected: {analysis['strengths']}\n"
            f"Growth areas: {analysis['growth']}\n"
            f"Protective factors: {analysis['protective_factors']}\n"
            f"Unresolved questions: {analysis['unresolved_questions']}\n\n"
            f"Knowledge context:\n{knowledge_summaries}\n\n"
            f"Time span: {analysis['time_span_days']} days of data."
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

    def _parse_llm_output(self, raw_text: str, analysis: dict[str, Any]) -> ReflectionDecision | None:
        text = raw_text.strip()
        if not text:
            return None

        try:
            parsed = json.loads(text)
            reflection = ReflectionOutput(
                title=parsed.get("title", "Reflection"),
                summary=parsed.get("summary", ""),
                supporting_evidence=parsed.get("supporting_evidence", []),
                related_patterns=parsed.get("related_patterns", []),
                related_memories=parsed.get("related_memories", []),
                supporting_citations=parsed.get("supporting_citations", []),
                confidence=min(1.0, max(0.0, parsed.get("confidence", 0.5))),
                actionable_questions=parsed.get("actionable_questions", []),
                limitations=parsed.get("limitations", []),
                strengths=parsed.get("strengths", []),
                growth_areas=parsed.get("growth_areas", []),
                unresolved_questions=parsed.get("unresolved_questions", []),
            )
        except (json.JSONDecodeError, KeyError):
            reflection = ReflectionOutput(
                title="Reflection",
                summary=text[:500],
                confidence=0.3,
                limitations=["Could not parse structured output from LLM"],
            )

        confidence = self._compute_confidence(reflection, analysis)

        return ReflectionDecision(
            reflection=reflection,
            confidence=confidence,
            evidence_count=analysis["memory_count"] + analysis["pattern_count"],
            memory_count=analysis["memory_count"],
            pattern_count=analysis["pattern_count"],
            citation_count=len(reflection.supporting_citations),
            reasoning=f"Generated reflection from {analysis['memory_count']} memories and {analysis['pattern_count']} patterns",
            is_valid=bool(reflection.summary),
        )

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _compute_confidence(self, reflection: ReflectionOutput, analysis: dict[str, Any]) -> float:
        score = 0.3

        if analysis["memory_count"] >= self._config.min_memories:
            score += min(0.2, analysis["memory_count"] * 0.03)

        if analysis["pattern_count"] >= self._config.min_patterns:
            score += min(0.15, analysis["pattern_count"] * 0.05)

        if reflection.supporting_evidence:
            score += min(0.15, len(reflection.supporting_evidence) * 0.03)

        if reflection.supporting_citations:
            score += min(0.1, len(reflection.supporting_citations) * 0.05)

        if analysis["time_span_days"] > 30:
            score += 0.1

        if reflection.limitations:
            score -= 0.05

        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------
    # Fallback (no LLM)
    # ------------------------------------------------------------------

    def _fallback_reflection(self, analysis: dict[str, Any]) -> ReflectionDecision:
        memory_summaries = []
        for m in sorted(
            self._collect_memories_from_analysis(analysis),
            key=lambda m: m.confidence,
            reverse=True,
        )[:10]:
            memory_summaries.append(f"- {m.content[:150]}")

        [
            f"- {p.get('name', 'unknown')}: {p.get('description', '')[:100]}"
            for p in analysis.get("patterns", [])[:5]
        ]

        title = f"Reflection on {analysis['memory_count']} memories across {analysis['time_span_days']} days"
        summary = (
            f"Based on {analysis['memory_count']} memories and {analysis['pattern_count']} patterns "
            f"spanning {analysis['time_span_days']} days, several themes emerge. "
        )
        if analysis["strengths"]:
            summary += f"Strengths include: {'; '.join(analysis['strengths'][:3])}. "
        if analysis["growth"]:
            summary += f"Growth areas: {'; '.join(analysis['growth'][:3])}. "
        if analysis["conflicts"]:
            summary += f"Conflicts noted: {'; '.join(analysis['conflicts'][:2])}. "

        reflection = ReflectionOutput(
            title=title,
            summary=summary,
            supporting_evidence=[{"content": s} for s in memory_summaries],
            related_patterns=[{"name": p.get("name", ""), "description": p.get("description", "")} for p in analysis.get("patterns", [])[:5]],
            confidence=0.4,
            actionable_questions=analysis.get("unresolved_questions", [])[:3],
            limitations=["Generated without LLM synthesis", "Limited cross-reference analysis"],
            strengths=analysis.get("strengths", []),
            growth_areas=analysis.get("growth", []),
            unresolved_questions=analysis.get("unresolved_questions", []),
        )

        confidence = self._compute_confidence(reflection, analysis)

        return ReflectionDecision(
            reflection=reflection,
            confidence=confidence,
            evidence_count=analysis["memory_count"] + analysis["pattern_count"],
            memory_count=analysis["memory_count"],
            pattern_count=analysis["pattern_count"],
            citation_count=0,
            reasoning="Fallback reflection generated without LLM",
            is_valid=True,
        )

    def _collect_memories_from_analysis(self, analysis: dict[str, Any]) -> list[Memory]:
        return []

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    async def _store_reflection(self, decision: ReflectionDecision, user_id: str) -> dict[str, Any] | None:
        if self._repo is None:
            logger.warning("no_reflection_repo")
            return None

        try:
            reflection_data = self._decision_to_dict(decision)
            reflection_data["user_id"] = user_id
            return await self._repo.create(reflection_data)
        except Exception as exc:
            logger.warning("reflection_store_failed", error=str(exc))
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _decision_to_dict(self, decision: ReflectionDecision) -> dict[str, Any]:
        r = decision.reflection
        return {
            "id": str(uuid.uuid4()),
            "title": r.title,
            "summary": r.summary,
            "supporting_evidence": r.supporting_evidence,
            "related_patterns": r.related_patterns,
            "related_memories": r.related_memories,
            "supporting_citations": r.supporting_citations,
            "confidence": round(decision.confidence, 3),
            "actionable_questions": r.actionable_questions,
            "limitations": r.limitations,
            "strengths": r.strengths,
            "growth_areas": r.growth_areas,
            "unresolved_questions": r.unresolved_questions,
            "evidence_count": decision.evidence_count,
            "memory_count": decision.memory_count,
            "pattern_count": decision.pattern_count,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def _success_empty(
        self, user_id: str, mem_count: int, pat_count: int, start_time: float
    ) -> AgentOutput:
        latency_ms = (time.monotonic() - start_time) * 1000
        return AgentOutput(
            status="success",
            data={"reflection": {}, "title": "", "summary": "", "confidence": 0.0},
            metadata={
                "evidence_count": 0,
                "memory_count": mem_count,
                "pattern_count": pat_count,
                "reasoning": "Insufficient evidence for reflection",
                "latency_ms": round(latency_ms, 2),
            },
            events=[],
        )

    def _fail(self, error: str, start_time: float) -> AgentOutput:
        latency_ms = (time.monotonic() - start_time) * 1000
        return AgentOutput(
            status="failed",
            data={"error": error, "reflection": {}},
            metadata={"latency_ms": round(latency_ms, 2)},
            events=[{"event_type": "ReflectionFailed", "error": error}],
        )
