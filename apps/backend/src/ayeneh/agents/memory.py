"""MemoryAgent — extracts, stores, and retrieves memories using MEMO engines."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.agents.base import AgentOutput, BaseAgent
from ayeneh.memo.types import Observation

logger = structlog.get_logger(__name__)


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


class MemoryAgent(BaseAgent):
    """Memory agent using MEMO architecture engines.

    Responsibilities:
    - Analyze conversation observations and user messages
    - Classify memories (episodic, semantic, pattern, reflection)
    - Score importance and confidence
    - Delegate storage and consolidation to MEMO engines
    - Explain every decision in metadata
    """

    name = "memory"

    def __init__(self, policy: MemoryPolicy | None = None, repository: Any = None) -> None:
        self._policy = policy or MemoryPolicy()
        self._repo = repository
        self._episodic_engine = None
        self._semantic_engine = None
        self._working_engine = None
        self._consolidation_engine = None
        self._retrieval_engine = None
        self._ranking_engine = None

    def _init_engines(self) -> None:
        """Lazy-init MEMO engines."""
        if self._episodic_engine is None:
            from ayeneh.memo.episodic.engine import EpisodicMemoryEngine
            from ayeneh.memo.semantic.engine import SemanticMemoryEngine
            from ayeneh.memo.working.engine import WorkingMemoryEngine
            from ayeneh.memo.consolidation.engine import ConsolidationEngine
            from ayeneh.memo.retrieval.engine import RetrievalEngine
            from ayeneh.memo.ranking.engine import RankingEngine

            self._episodic_engine = EpisodicMemoryEngine()
            self._semantic_engine = SemanticMemoryEngine()
            self._working_engine = WorkingMemoryEngine()
            self._consolidation_engine = ConsolidationEngine()
            self._retrieval_engine = RetrievalEngine()
            self._ranking_engine = RankingEngine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(self, context: dict[str, Any]) -> AgentOutput:
        """Execute memory extraction and storage."""
        self._init_engines()
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

            decisions = []
            for candidate in candidates:
                decision = self._evaluate_candidate(candidate, user_id)
                if decision is not None:
                    decisions.append(decision)

            now = datetime.now(UTC)
            memo_observations = [
                Observation(
                    observation_id=f"obs_{i}",
                    content=d["content"],
                    source=d["source"],
                    timestamp=now,
                    observation_type=d["memory_type"],
                    metadata={"importance": d["importance"], "confidence": d["confidence"]},
                )
                for i, d in enumerate(decisions)
            ]

            episode_ids = tuple(f"ep_{i}" for i in range(len(memo_observations)))
            conv_id = context.get("conversation_id", "")

            episodic_result = self._episodic_engine.run_pipeline(memo_observations)
            semantic_result = self._semantic_engine.run_pipeline(
                memo_observations,
                episode_ids=episode_ids,
                conversation_ids=(conv_id,) if conv_id else (),
            )

            wm_items = [
                {
                    "id": ep.identifier,
                    "source": "episodic",
                    "score": ep.confidence,
                    "evidence": list(ep.supporting_evidence),
                }
                for ep in episodic_result.episodes
            ]
            for sm in semantic_result.semantic_objects:
                wm_items.append({
                    "id": sm.identifier,
                    "source": "semantic",
                    "score": sm.confidence,
                    "evidence": list(sm.supporting_evidence),
                })

            consolidation_result = self._consolidation_engine.run_pipeline(
                wm_items,
                episodes=[ep.identifier for ep in episodic_result.episodes],
            )

            stored_episodes: list[str] = []
            stored_semantics: list[str] = []
            if self._repo is not None:
                for ep in episodic_result.episodes:
                    try:
                        ep_id = await self._repo.save_episode(user_id, self._episode_to_dict(ep))
                        stored_episodes.append(ep_id)
                    except Exception as exc:
                        logger.warning("episode_store_failed", error=str(exc))
                for sm in semantic_result.semantic_objects:
                    try:
                        sm_id = await self._repo.save_semantic(user_id, self._semantic_to_dict(sm))
                        stored_semantics.append(sm_id)
                    except Exception as exc:
                        logger.warning("semantic_store_failed", error=str(exc))

            latency_ms = (time.monotonic() - start_time) * 1000

            new_memories = [
                {"id": eid, "type": "episodic", "content": ep.title}
                for eid, ep in zip(stored_episodes, episodic_result.episodes)
            ]
            new_memories += [
                {"id": sid, "type": "semantic", "content": sm.knowledge_statement}
                for sid, sm in zip(stored_semantics, semantic_result.semantic_objects)
            ]

            events = [
                {"event_type": "MemoryStored", "memory_id": m["id"], "memory_type": m["type"]}
                for m in new_memories
            ]

            logger.info(
                "memory_extraction_completed",
                user_id=user_id,
                candidates=len(candidates),
                stored=len(new_memories),
                latency_ms=round(latency_ms, 2),
            )

            return AgentOutput(
                status="success",
                data={
                    "new_memories": new_memories,
                    "new_insights": [],
                },
                metadata={
                    "candidates_evaluated": len(candidates),
                    "memories_stored": len(new_memories),
                    "latency_ms": round(latency_ms, 2),
                    "decisions": [
                        {
                            "content": d["content"][:100],
                            "type": d["memory_type"],
                            "importance": round(d["importance"], 3),
                            "confidence": round(d["confidence"], 3),
                            "reasoning": d["reasoning"],
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
        self, candidate: dict[str, Any], user_id: str,
    ) -> dict[str, Any] | None:
        """Evaluate a single candidate and produce a decision dict."""
        content = candidate.get("content", "").strip()
        if not content or len(content) < 10:
            return None

        memory_type = self._classify_type(content, candidate.get("source", ""))
        importance = self._score_importance(content, candidate.get("source", ""))
        confidence = self._score_confidence(content, candidate.get("source", ""))

        if importance < self._policy.min_importance and confidence < self._policy.min_confidence:
            return None

        reasoning_parts = [f"classified as {memory_type}"]
        reasoning_parts.append(f"importance={importance:.2f}, confidence={confidence:.2f}")

        return {
            "content": content,
            "memory_type": memory_type,
            "importance": importance,
            "confidence": confidence,
            "source": candidate.get("source", ""),
            "source_ids": candidate.get("source_ids", []),
            "reasoning": "; ".join(reasoning_parts),
        }

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def _classify_type(self, content: str, source: str) -> str:
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
            "episodic": episodic_score,
            "semantic": semantic_score,
            "pattern": pattern_score,
            "reflection": reflection_score,
        }

        best_type = max(scores, key=lambda k: scores[k])
        if scores[best_type] == 0:
            if len(content.split()) > 15:
                return "semantic"
            return "episodic"

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
    # MEMO object conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _episode_to_dict(ep: Any) -> dict[str, Any]:
        """Convert an EpisodeObject to a dict for repository persistence."""
        return {
            "identifier": ep.identifier,
            "title": ep.title,
            "summary": ep.summary,
            "category": ep.category,
            "state": ep.state,
            "start_time": ep.start_time,
            "end_time": ep.end_time,
            "estimated_duration_s": ep.estimated_duration,
            "confidence": ep.confidence,
            "primary_context": ep.primary_context,
            "supporting_evidence": list(ep.supporting_evidence),
        }

    @staticmethod
    def _semantic_to_dict(sm: Any) -> dict[str, Any]:
        """Convert a SemanticMemoryObject to a dict for repository persistence."""
        return {
            "identifier": sm.identifier,
            "knowledge_statement": sm.knowledge_statement,
            "knowledge_category": sm.knowledge_category,
            "confidence": sm.confidence,
            "importance": sm.importance,
            "temporal_stability": sm.temporal_stability,
            "supporting_evidence": list(sm.supporting_evidence),
            "supporting_episodes": list(sm.supporting_episodes),
        }
