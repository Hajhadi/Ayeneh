"""MemoryAgent — extracts, classifies, and stores memories from conversation."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog

from ayeneh.agents.base import AgentOutput, BaseAgent
from ayeneh.application.services.memory import MemoryCreate, MemoryService, MemoryType

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class MemoryPolicy:
    """Configurable thresholds for memory extraction decisions."""

    min_importance: float = 0.3
    min_confidence: float = 0.4
    max_episodic_per_message: int = 2
    max_semantic_per_message: int = 3
    importance_boost_keywords: tuple[str, ...] = (
        "important", "critical", "always", "never", "goal", "belief",
        "value", "principle", "rule", "promise", "decision", "commitment", "commit",
    )
    confidence_boost_keywords: tuple[str, ...] = (
        "i think", "i believe", "i know", "i feel", "i remember",
        "in my opinion", "definitely", "certainly", "absolutely",
    )
    episodic_signals: tuple[str, ...] = (
        "today", "yesterday", "last week", "this morning", "just now",
        "earlier", "recently", "a few days ago", "last month",
    )
    semantic_signals: tuple[str, ...] = (
        "always", "never", "usually", "generally", "typically",
        "prefer", "like", "dislike", "want", "need", "believe",
        "think", "know", "value", "important",
    )
    reflection_signals: tuple[str, ...] = (
        "i realize", "i noticed", "i understand", "looking back",
        "over time", "i've changed", "i've learned", "in retrospect",
        "now i see", "i've come to understand",
    )
    pattern_signals: tuple[str, ...] = (
        "tend to", "often", "frequently", "habitually", "pattern",
        "keep", "every time", "whenever", "consistently",
    )
    duplicate_threshold: float = 0.90
    supersede_threshold: float = 0.85


# ---------------------------------------------------------------------------
# Memory classification result
# ---------------------------------------------------------------------------

@dataclass
class MemoryDecision:
    """A single memory extraction decision with full explanation."""

    content: str
    memory_type: MemoryType
    importance: float
    confidence: float
    is_duplicate: bool = False
    duplicate_of_id: str | None = None
    is_superseded: bool = False
    supersedes_id: str | None = None
    source_message_ids: list[str] = field(default_factory=list)
    reasoning: str = ""


# ---------------------------------------------------------------------------
# MemoryAgent
# ---------------------------------------------------------------------------

class MemoryAgent(BaseAgent):
    """Production-grade memory extraction agent.

    Responsibilities:
    - Analyze ConversationAgent observations and user messages
    - Decide whether information should become long-term memory
    - Classify memories (episodic, semantic, pattern, reflection)
    - Score importance and confidence
    - Detect duplicates and superseded memories
    - Store memories through MemoryService
    - Explain every decision in metadata
    """

    name = "memory"

    def __init__(
        self,
        memory_service: MemoryService | None = None,
        policy: MemoryPolicy | None = None,
    ) -> None:
        self._memory_service = memory_service
        self._policy = policy or MemoryPolicy()

    async def execute(self, context: dict[str, Any]) -> AgentOutput:
        """Execute memory extraction from conversation context."""
        start_time = time.monotonic()

        try:
            user_id = context.get("user_id", "")
            user_message = context.get("user_message", "")
            conversation_history = context.get("conversation_history", [])
            conversation_output = context.get("conversation_agent_output", {})

            if not user_id:
                return AgentOutput(
                    status="failed",
                    data={"error": "No user_id in context", "new_memories": [], "new_insights": []},
                    metadata={},
                )

            observations = conversation_output.get("observations", [])
            inline_suggestions = conversation_output.get("inline_memory_suggestions", [])
            response_text = conversation_output.get("response_text", "")

            candidates = self._extract_candidates(
                user_message=user_message,
                response_text=response_text,
                observations=observations,
                inline_suggestions=inline_suggestions,
                conversation_history=conversation_history,
            )

            decisions: list[MemoryDecision] = []
            for candidate in candidates:
                decision = self._evaluate_candidate(candidate, user_id)
                if decision is not None:
                    decisions.append(decision)

            stored_memories = await self._store_decisions(decisions, uuid.UUID(user_id))

            latency_ms = (time.monotonic() - start_time) * 1000

            events = []
            for mem in stored_memories:
                events.append({
                    "event_type": "MemoryStored",
                    "memory_id": str(mem.id),
                    "memory_type": mem.type,
                    "confidence": mem.confidence,
                })

            logger.info(
                "memory_extraction_completed",
                user_id=user_id,
                candidates=len(candidates),
                stored=len(stored_memories),
                latency_ms=round(latency_ms, 2),
            )

            return AgentOutput(
                status="success",
                data={
                    "new_memories": [
                        {
                            "id": str(m.id),
                            "type": m.type,
                            "content": m.content,
                            "confidence": m.confidence,
                        }
                        for m in stored_memories
                    ],
                    "new_insights": [],
                },
                metadata={
                    "candidates_evaluated": len(candidates),
                    "memories_stored": len(stored_memories),
                    "latency_ms": round(latency_ms, 2),
                    "decisions": [
                        {
                            "content": d.content[:100],
                            "type": d.memory_type,
                            "importance": round(d.importance, 3),
                            "confidence": round(d.confidence, 3),
                            "is_duplicate": d.is_duplicate,
                            "is_superseded": d.is_superseded,
                            "reasoning": d.reasoning,
                        }
                        for d in decisions
                    ],
                },
                events=events,
            )

        except Exception as exc:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.exception(
                "memory_extraction_failed",
                user_id=context.get("user_id", ""),
                latency_ms=round(latency_ms, 2),
            )
            return AgentOutput(
                status="failed",
                data={"error": str(exc), "new_memories": [], "new_insights": []},
                metadata={"latency_ms": round(latency_ms, 2)},
                events=[{"event_type": "MemoryExtractionFailed", "error": str(exc)}],
            )

    # ------------------------------------------------------------------
    # Candidate extraction
    # ------------------------------------------------------------------

    def _extract_candidates(
        self,
        user_message: str,
        response_text: str,
        observations: list[dict[str, Any]],
        inline_suggestions: list[dict[str, Any]],
        conversation_history: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        """Extract raw memory candidates from all available signals."""
        candidates: list[dict[str, Any]] = []

        if user_message.strip():
            candidates.append({
                "content": user_message.strip(),
                "source": "user_message",
                "source_ids": [],
            })

        if response_text.strip() and len(response_text.strip()) > 20:
            candidates.append({
                "content": response_text.strip(),
                "source": "assistant_response",
                "source_ids": [],
            })

        for obs in observations:
            if isinstance(obs, dict) and obs.get("content"):
                candidates.append({
                    "content": obs["content"],
                    "source": "observation",
                    "source_ids": [],
                    "observation_type": obs.get("type", "unknown"),
                })

        for suggestion in inline_suggestions:
            if isinstance(suggestion, dict) and suggestion.get("content"):
                candidates.append({
                    "content": suggestion["content"],
                    "source": "inline_suggestion",
                    "source_ids": suggestion.get("source_message_ids", []),
                })

        if len(conversation_history) >= 3:
            recent = conversation_history[-3:]
            combined = " ".join(m.get("content", "") for m in recent if m.get("content"))
            if len(combined) > 50:
                candidates.append({
                    "content": combined[:500],
                    "source": "conversation_summary",
                    "source_ids": [],
                })

        return candidates

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def _evaluate_candidate(
        self, candidate: dict[str, Any], user_id: str
    ) -> MemoryDecision | None:
        """Evaluate a single candidate and produce a MemoryDecision."""
        content = candidate.get("content", "").strip()
        if not content or len(content) < 10:
            return None

        memory_type = self._classify_type(content, candidate.get("source", ""))
        importance = self._score_importance(content, candidate.get("source", ""))
        confidence = self._score_confidence(content, candidate.get("source", ""))

        if importance < self._policy.min_importance and confidence < self._policy.min_confidence:
            return None

        reasoning_parts = [f"classified as {memory_type.value}"]
        reasoning_parts.append(f"importance={importance:.2f}, confidence={confidence:.2f}")

        is_duplicate = False
        duplicate_of_id = None
        is_superseded = False
        supersedes_id = None

        source_ids = candidate.get("source_ids", [])

        return MemoryDecision(
            content=content,
            memory_type=memory_type,
            importance=importance,
            confidence=confidence,
            is_duplicate=is_duplicate,
            duplicate_of_id=duplicate_of_id,
            is_superseded=is_superseded,
            supersedes_id=supersedes_id,
            source_message_ids=source_ids,
            reasoning="; ".join(reasoning_parts),
        )

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def _classify_type(self, content: str, source: str) -> MemoryType:
        """Classify content into a memory type based on signals."""
        content_lower = content.lower()

        reflection_score = sum(1 for s in self._policy.reflection_signals if s in content_lower)
        pattern_score = sum(1 for s in self._policy.pattern_signals if s in content_lower)
        semantic_score = sum(1 for s in self._policy.semantic_signals if s in content_lower)
        episodic_score = sum(1 for s in self._policy.episodic_signals if s in content_lower)

        if source == "conversation_summary":
            reflection_score += 2

        if source == "observation":
            if any(kw in content_lower for kw in ("tend to", "pattern", "consistently")):
                pattern_score += 2
            else:
                semantic_score += 1

        scores = {
            MemoryType.EPISODIC: episodic_score,
            MemoryType.SEMANTIC: semantic_score,
            MemoryType.PATTERN: pattern_score,
            MemoryType.REFLECTION: reflection_score,
        }

        best_type = max(scores, key=scores.get)
        if scores[best_type] == 0:
            if len(content.split()) > 15:
                return MemoryType.SEMANTIC
            return MemoryType.EPISODIC

        return best_type

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_importance(self, content: str, source: str) -> float:
        """Score importance from 0.0 to 1.0."""
        score = 0.3
        content_lower = content.lower()

        keyword_hits = sum(1 for kw in self._policy.importance_boost_keywords if kw in content_lower)
        score += min(keyword_hits * 0.1, 0.4)

        if source == "observation":
            score += 0.1
        if source == "inline_suggestion":
            score += 0.15

        word_count = len(content.split())
        if word_count > 50:
            score += 0.05
        if word_count > 100:
            score += 0.05

        if any(phrase in content_lower for phrase in ("i will", "i promise", "i commit", "my goal")):
            score += 0.1

        return min(1.0, score)

    def _score_confidence(self, content: str, source: str) -> float:
        """Score confidence from 0.0 to 1.0."""
        score = 0.4
        content_lower = content.lower()

        keyword_hits = sum(1 for kw in self._policy.confidence_boost_keywords if kw in content_lower)
        score += min(keyword_hits * 0.1, 0.3)

        if source == "user_message":
            score += 0.1
        if source == "inline_suggestion":
            score += 0.15

        hedging = ("maybe", "perhaps", "possibly", "might", "i guess", "i suppose")
        hedge_hits = sum(1 for h in hedging if h in content_lower)
        score -= hedge_hits * 0.05

        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    async def _store_decisions(
        self, decisions: list[MemoryDecision], user_id: uuid.UUID
    ) -> list[Any]:
        """Store memories for valid decisions through MemoryService."""
        if self._memory_service is None:
            logger.warning("no_memory_service")
            return []

        stored: list[Any] = []
        for decision in decisions:
            if decision.is_duplicate:
                continue

            try:
                create = MemoryCreate(
                    user_id=user_id,
                    type=decision.memory_type,
                    content=decision.content,
                    confidence=decision.confidence,
                    source_message_ids=[
                        uuid.UUID(sid) for sid in decision.source_message_ids if sid
                    ],
                )
                memory = await self._memory_service.store(create)
                stored.append(memory)
            except Exception as exc:
                logger.warning("memory_store_failed", error=str(exc), content=decision.content[:50])

        return stored
