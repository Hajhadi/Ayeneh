"""PatternAgent — detects recurring cognitive patterns from memories."""

from __future__ import annotations

import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from ayeneh.agents.base import AgentOutput, BaseAgent
from ayeneh.application.services.memory import Memory, MemoryType

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Pattern domain
# ---------------------------------------------------------------------------

class PatternCategory(str):
    COGNITIVE = "cognitive"
    BEHAVIORAL = "behavioral"
    EMOTIONAL = "emotional"
    THEMATIC = "thematic"


class TrendDirection(str):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    EMERGING = "emerging"


@dataclass
class DetectedPattern:
    """A fully described detected pattern."""

    pattern_id: str
    name: str
    description: str
    category: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    trend: str = TrendDirection.STABLE
    first_seen: str = ""
    last_seen: str = ""
    occurrence_count: int = 0
    importance: float = 0.0
    supporting_memories: list[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class PatternConfig:
    """Configuration thresholds for pattern detection."""

    min_occurrences: int = 2
    min_confidence: float = 0.3
    min_importance: float = 0.2
    similarity_threshold: float = 0.7
    trend_window_days: int = 30
    max_patterns_per_run: int = 20
    time_decay_half_life_days: int = 60


# ---------------------------------------------------------------------------
# Keyword dictionaries
# ---------------------------------------------------------------------------

AVOIDANCE_KEYWORDS: frozenset[str] = frozenset({
    "avoid", "avoiding", "postpone", "procrastinate", "delay",
    "escape", "escape from", "run from", "put off", "ignore",
    "distract", "numb", "shut down", "withdraw", "isolate",
})

PERFECTIONISM_KEYWORDS: frozenset[str] = frozenset({
    "perfect", "perfectly", "flawless", "no mistakes", "can't fail",
    "must be right", "good enough", "never good enough", "standards",
    "impossible standard", "all or nothing", "black and white",
})

REASSURANCE_KEYWORDS: frozenset[str] = frozenset({
    "reassure", "reassurance", "am i okay", "is this normal",
    "do you think", "do you agree", "does that make sense",
    "am i overreacting", "should i worry", "is it bad that",
})

CATASTROPHIZING_KEYWORDS: frozenset[str] = frozenset({
    "worst case", "disaster", "terrible", "horrible", "end of",
    "ruined", "never recover", "falling apart", "catastrophe",
    "everything will go wrong", "doomed", " hopeless", "no way out",
})

COGNITIVE_DISTORTION_PATTERNS: frozenset[str] = frozenset({
    "always", "never", "every time", "nobody", "everyone",
    "nothing", "everything", "worst", "best", "ruined",
    "should have", "must be", "can't stand", "no point",
})

POSITIVE_KEYWORDS: frozenset[str] = frozenset({
    "grateful", "appreciate", "enjoy", "love", "happy",
    "proud", "accomplished", "growth", "learn", "improve",
    "progress", "success", "strength", "resilient", "hopeful",
})


# ---------------------------------------------------------------------------
# PatternAgent
# ---------------------------------------------------------------------------

class PatternAgent(BaseAgent):
    """Production-grade pattern detection agent.

    Responsibilities:
    - Analyze retrieved memories for recurring patterns
    - Detect cognitive, behavioral, emotional, and thematic patterns
    - Detect specific patterns (avoidance, perfectionism, reassurance, catastrophizing, distortions)
    - Measure trend strength and confidence
    - Link supporting evidence
    - Create, update, merge, and retire patterns
    """

    name = "pattern"

    def __init__(self, config: PatternConfig | None = None) -> None:
        self._config = config or PatternConfig()

    async def execute(self, context: dict[str, Any]) -> AgentOutput:
        """Execute pattern detection from retrieved memories."""
        start_time = time.monotonic()

        try:
            user_id = context.get("user_id", "")
            if not user_id:
                return AgentOutput(
                    status="failed",
                    data={"error": "No user_id", "new_patterns": [], "updated_patterns": [], "retired_patterns": []},
                    metadata={},
                    events=[{"event_type": "PatternDetectionFailed", "error": "No user_id"}],
                )

            all_memories = self._collect_memories(context)
            existing_patterns = self._collect_existing_patterns(context)

            if not all_memories:
                return AgentOutput(
                    status="success",
                    data={"new_patterns": [], "updated_patterns": [], "retired_patterns": []},
                    metadata={"memories_analyzed": 0, "patterns_found": 0},
                )

            raw_candidates = self._extract_pattern_candidates(all_memories)
            validated = self._validate_candidates(raw_candidates, all_memories)
            merged = self._merge_with_existing(validated, existing_patterns)
            retired = self._retire_stale(existing_patterns, all_memories)

            output_patterns = merged[:self._config.max_patterns_per_run]

            latency_ms = (time.monotonic() - start_time) * 1000

            events = []
            for p in output_patterns:
                events.append({
                    "event_type": "PatternDetected",
                    "pattern_id": p.pattern_id,
                    "name": p.name,
                    "category": p.category,
                    "confidence": round(p.confidence, 3),
                })

            logger.info(
                "pattern_detection_completed",
                user_id=user_id,
                memories_analyzed=len(all_memories),
                candidates=len(raw_candidates),
                validated=len(validated),
                output=len(output_patterns),
                retired=len(retired),
                latency_ms=round(latency_ms, 2),
            )

            return AgentOutput(
                status="success",
                data={
                    "new_patterns": [self._pattern_to_dict(p) for p in output_patterns if p.occurrence_count <= self._config.min_occurrences],
                    "updated_patterns": [self._pattern_to_dict(p) for p in output_patterns if p.occurrence_count > self._config.min_occurrences],
                    "retired_patterns": [self._pattern_to_dict(p) for p in retired],
                },
                metadata={
                    "memories_analyzed": len(all_memories),
                    "candidates_extracted": len(raw_candidates),
                    "candidates_validated": len(validated),
                    "patterns_output": len(output_patterns),
                    "patterns_retired": len(retired),
                    "latency_ms": round(latency_ms, 2),
                    "config": {
                        "min_occurrences": self._config.min_occurrences,
                        "min_confidence": self._config.min_confidence,
                        "similarity_threshold": self._config.similarity_threshold,
                    },
                },
                events=events,
            )

        except Exception as exc:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.exception("pattern_detection_failed", user_id=context.get("user_id", ""), latency_ms=round(latency_ms, 2))
            return AgentOutput(
                status="failed",
                data={"error": str(exc), "new_patterns": [], "updated_patterns": [], "retired_patterns": []},
                metadata={"latency_ms": round(latency_ms, 2)},
                events=[{"event_type": "PatternDetectionFailed", "error": str(exc)}],
            )

    # ------------------------------------------------------------------
    # Memory collection
    # ------------------------------------------------------------------

    def _collect_memories(self, context: dict[str, Any]) -> list[Memory]:
        """Gather all memories from the context."""
        memories: list[Memory] = []
        for key in ("episodic_memories", "semantic_memories", "pattern_memories", "reflection_memories"):
            for item in context.get(key, []):
                if isinstance(item, Memory):
                    memories.append(item)
                elif isinstance(item, dict):
                    memories.append(Memory(
                        id=uuid.UUID(item.get("id", str(uuid.uuid4()))),
                        user_id=uuid.UUID(item.get("user_id", "00000000-0000-0000-0000-000000000000")),
                        type=MemoryType(item.get("type", "semantic")),
                        content=item.get("content", ""),
                        confidence=float(item.get("confidence", 0.5)),
                        created_at=datetime.fromisoformat(item["created_at"]) if "created_at" in item else datetime.now(UTC),
                    ))
        return memories

    def _collect_existing_patterns(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Gather existing patterns from the context."""
        return context.get("existing_patterns", [])

    # ------------------------------------------------------------------
    # Candidate extraction
    # ------------------------------------------------------------------

    def _extract_pattern_candidates(self, memories: list[Memory]) -> list[dict[str, Any]]:
        """Extract raw pattern candidates from memories."""
        candidates: list[dict[str, Any]] = []

        category_signals = self._detect_category_clusters(memories)
        for category, cluster in category_signals.items():
            if len(cluster) >= self._config.min_occurrences:
                candidate = self._build_candidate_from_cluster(category, cluster)
                if candidate:
                    candidates.append(candidate)

        thematic = self._detect_themes(memories)
        candidates.extend(thematic)

        specific = self._detect_specific_patterns(memories)
        candidates.extend(specific)

        return candidates

    def _detect_category_clusters(self, memories: list[Memory]) -> dict[str, list[Memory]]:
        """Group memories into category clusters."""
        clusters: dict[str, list[Memory]] = defaultdict(list)

        for mem in memories:
            text = mem.content.lower()

            if any(kw in text for kw in AVOIDANCE_KEYWORDS):
                clusters["avoidance"].append(mem)

            if any(kw in text for kw in PERFECTIONISM_KEYWORDS):
                clusters["perfectionism"].append(mem)

            if any(kw in text for kw in REASSURANCE_KEYWORDS):
                clusters["reassurance_seeking"].append(mem)

            if any(kw in text for kw in CATASTROPHIZING_KEYWORDS):
                clusters["catastrophizing"].append(mem)

            if any(kw in text for kw in COGNITIVE_DISTORTION_PATTERNS):
                clusters["cognitive_distortion"].append(mem)

            if any(kw in text for kw in POSITIVE_KEYWORDS):
                clusters["positive_trend"].append(mem)

            emotional_words = {"sad", "anxious", "angry", "frustrated", "lonely", "scared", "worried", "stressed", "happy", "calm", "excited", "grateful"}
            found_emotions = [w for w in emotional_words if w in text]
            if found_emotions:
                clusters[f"emotional:{found_emotions[0]}"].append(mem)

        return clusters

    def _build_candidate_from_cluster(self, category: str, memories: list[Memory]) -> dict[str, Any] | None:
        """Build a pattern candidate from a cluster of memories."""
        if len(memories) < self._config.min_occurrences:
            return None

        contents = [m.content for m in memories]
        description = self._generate_description(category, contents)

        return {
            "category": category,
            "name": self._generate_name(category),
            "description": description,
            "memories": memories,
            "occurrence_count": len(memories),
            "first_seen": min(m.created_at for m in memories).isoformat(),
            "last_seen": max(m.created_at for m in memories).isoformat(),
        }

    def _detect_themes(self, memories: list[Memory]) -> list[dict[str, Any]]:
        """Detect recurring themes across memories."""
        word_counts: Counter[str] = Counter()
        for mem in memories:
            words = [w.lower() for w in mem.content.split() if len(w) > 3]
            word_counts.update(words)

        themes: list[dict[str, Any]] = []
        for word, count in word_counts.most_common(5):
            if count >= self._config.min_occurrences:
                related = [m for m in memories if word in m.content.lower()]
                if len(related) >= self._config.min_occurrences:
                    themes.append({
                        "category": PatternCategory.THEMATIC,
                        "name": f"theme:{word}",
                        "description": f"Recurring theme around '{word}' across {count} memories",
                        "memories": related,
                        "occurrence_count": count,
                        "first_seen": min(m.created_at for m in related).isoformat(),
                        "last_seen": max(m.created_at for m in related).isoformat(),
                    })

        return themes

    def _detect_specific_patterns(self, memories: list[Memory]) -> list[dict[str, Any]]:
        """Detect specific cognitive and behavioral patterns."""
        candidates: list[dict[str, Any]] = []

        word_freq: Counter[str] = Counter()
        for mem in memories:
            word_freq.update(w.lower() for w in mem.content.split() if len(w) > 3)

        cognitive_words = {"think", "believe", "feel", "assume", "expect", "interpret", "judge", "decide"}
        cognitive_count = sum(word_freq.get(w, 0) for w in cognitive_words)
        if cognitive_count >= self._config.min_occurrences:
            related = [m for m in memories if any(w in m.content.lower() for w in cognitive_words)]
            if len(related) >= self._config.min_occurrences:
                candidates.append({
                    "category": PatternCategory.COGNITIVE,
                    "name": "cognitive_style",
                    "description": f"Recurring cognitive processing pattern across {len(related)} memories",
                    "memories": related,
                    "occurrence_count": len(related),
                    "first_seen": min(m.created_at for m in related).isoformat(),
                    "last_seen": max(m.created_at for m in related).isoformat(),
                })

        temporal_words = {"always", "never", "every", "constant", "routine", "habit", "daily", "weekly"}
        temporal_count = sum(word_freq.get(w, 0) for w in temporal_words)
        if temporal_count >= self._config.min_occurrences:
            related = [m for m in memories if any(w in m.content.lower() for w in temporal_words)]
            if len(related) >= self._config.min_occurrences:
                candidates.append({
                    "category": PatternCategory.BEHAVIORAL,
                    "name": "behavioral_routine",
                    "description": f"Recurring behavioral pattern across {len(related)} memories",
                    "memories": related,
                    "occurrence_count": len(related),
                    "first_seen": min(m.created_at for m in related).isoformat(),
                    "last_seen": max(m.created_at for m in related).isoformat(),
                })

        return candidates

    # ------------------------------------------------------------------
    # Description generation
    # ------------------------------------------------------------------

    def _generate_name(self, category: str) -> str:
        names = {
            "avoidance": "avoidance_pattern",
            "perfectionism": "perfectionism_pattern",
            "reassurance_seeking": "reassurance_seeking",
            "catastrophizing": "catastrophizing_tendency",
            "cognitive_distortion": "cognitive_distortion",
            "positive_trend": "positive_cognitive_trend",
        }
        return names.get(category, f"pattern:{category}")

    def _generate_description(self, category: str, contents: list[str]) -> str:
        count = len(contents)
        first_excerpt = contents[0][:80] if contents else ""
        descriptions = {
            "avoidance": f"User shows avoidance behavior across {count} instances. First example: '{first_excerpt}'",
            "perfectionism": f"User displays perfectionistic tendencies in {count} instances. Example: '{first_excerpt}'",
            "reassurance_seeking": f"User seeks reassurance across {count} interactions. Example: '{first_excerpt}'",
            "catastrophizing": f"User exhibits catastrophizing in {count} instances. Example: '{first_excerpt}'",
            "cognitive_distortion": f"Cognitive distortion detected across {count} memories. Example: '{first_excerpt}'",
            "positive_trend": f"Positive cognitive trend across {count} instances. Example: '{first_excerpt}'",
        }
        return descriptions.get(category, f"Pattern detected across {count} memories. Example: '{first_excerpt}'")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_candidates(self, candidates: list[dict[str, Any]], memories: list[Memory]) -> list[DetectedPattern]:
        """Validate candidates and produce DetectedPattern objects."""
        validated: list[DetectedPattern] = []

        for cand in candidates:
            mems = cand["memories"]
            if len(mems) < self._config.min_occurrences:
                continue

            confidence = self._compute_confidence(mems, cand["category"])
            if confidence < self._config.min_confidence:
                continue

            importance = self._compute_importance(mems, cand["category"])
            if importance < self._config.min_importance:
                continue

            trend = self._compute_trend(mems)

            pattern = DetectedPattern(
                pattern_id=str(uuid.uuid4()),
                name=cand["name"],
                description=cand["description"],
                category=cand["category"],
                evidence=[{"memory_id": str(m.id), "content": m.content[:100], "confidence": m.confidence, "created_at": m.created_at.isoformat()} for m in mems],
                confidence=confidence,
                trend=trend,
                first_seen=cand["first_seen"],
                last_seen=cand["last_seen"],
                occurrence_count=cand["occurrence_count"],
                importance=importance,
                supporting_memories=[str(m.id) for m in mems],
                reasoning=f"Detected {cand['category']} pattern across {len(mems)} memories with confidence {confidence:.2f}",
            )
            validated.append(pattern)

        return validated

    # ------------------------------------------------------------------
    # Confidence & importance
    # ------------------------------------------------------------------

    def _compute_confidence(self, memories: list[Memory], category: str) -> float:
        """Compute confidence for a pattern."""
        if not memories:
            return 0.0

        avg_confidence = sum(m.confidence for m in memories) / len(memories)

        count_bonus = min(0.2, (len(memories) - self._config.min_occurrences) * 0.05)

        time_span = (max(m.created_at for m in memories) - min(m.created_at for m in memories)).days
        temporal_bonus = min(0.15, time_span / 100)

        category_bonus = 0.1 if category in ("cognitive", "behavioral") else 0.05

        return min(1.0, avg_confidence * 0.5 + count_bonus + temporal_bonus + category_bonus)

    def _compute_importance(self, memories: list[Memory], category: str) -> float:
        """Compute importance for a pattern."""
        base = 0.3

        high_confidence_count = sum(1 for m in memories if m.confidence > 0.7)
        confidence_bonus = min(0.3, high_confidence_count * 0.05)

        category_importance = {
            "avoidance": 0.15,
            "perfectionism": 0.15,
            "catastrophizing": 0.2,
            "cognitive_distortion": 0.15,
            "reassurance_seeking": 0.1,
            "positive_trend": 0.05,
            "cognitive": 0.1,
            "behavioral": 0.1,
            "emotional": 0.05,
            "thematic": 0.05,
        }
        cat_bonus = category_importance.get(category, 0.05)

        recency_bonus = 0.0
        now = datetime.now(UTC)
        for m in memories:
            days_ago = (now - m.created_at).days
            if days_ago < 7:
                recency_bonus += 0.02

        return min(1.0, base + confidence_bonus + cat_bonus + min(0.15, recency_bonus))

    # ------------------------------------------------------------------
    # Trend computation
    # ------------------------------------------------------------------

    def _compute_trend(self, memories: list[Memory]) -> str:
        """Compute trend direction from memory timestamps."""
        if len(memories) < 2:
            return TrendDirection.STABLE

        now = datetime.now(UTC)
        timedelta(days=self._config.trend_window_days)
        half = self._config.time_decay_half_life_days

        recent_weight = 0.0
        older_weight = 0.0

        for mem in memories:
            age_days = (now - mem.created_at).days
            weight = 0.5 ** (age_days / half)

            if age_days <= self._config.trend_window_days:
                recent_weight += weight
            else:
                older_weight += weight

        if recent_weight > older_weight * 1.5:
            return TrendDirection.INCREASING
        elif older_weight > recent_weight * 1.5:
            return TrendDirection.DECREASING
        elif len(memories) >= 2 and (max(m.created_at for m in memories) - min(m.created_at for m in memories)).days < 7:
            return TrendDirection.EMERGING
        else:
            return TrendDirection.STABLE

    # ------------------------------------------------------------------
    # Merge & retire
    # ------------------------------------------------------------------

    def _merge_with_existing(self, new_patterns: list[DetectedPattern], existing: list[dict[str, Any]]) -> list[DetectedPattern]:
        """Merge new patterns with existing ones."""
        merged: list[DetectedPattern] = []

        for pattern in new_patterns:
            best_match: dict[str, Any] | None = None
            best_score = 0.0

            for ex in existing:
                score = self._similarity_score(pattern.name, ex.get("name", ""))
                if score > best_score:
                    best_score = score
                    best_match = ex

            if best_match and best_score >= self._config.similarity_threshold:
                pattern.occurrence_count = max(pattern.occurrence_count, best_match.get("occurrence_count", 0) + 1)
                pattern.pattern_id = best_match.get("pattern_id", pattern.pattern_id)
                pattern.confidence = min(1.0, pattern.confidence + 0.05)

            merged.append(pattern)

        return merged

    def _retire_stale(self, existing: list[dict[str, Any]], all_memories: list[Memory]) -> list[DetectedPattern]:
        """Retire patterns with no supporting evidence in current memories."""
        retired: list[DetectedPattern] = []
        memory_ids = {str(m.id) for m in all_memories}

        for ex in existing:
            evidence_ids = set(ex.get("supporting_memory_ids", []))
            if evidence_ids and not evidence_ids & memory_ids:
                retired.append(DetectedPattern(
                    pattern_id=ex.get("pattern_id", ""),
                    name=ex.get("name", ""),
                    description=ex.get("description", ""),
                    category=ex.get("category", ""),
                    confidence=0.0,
                    trend=TrendDirection.DECREASING,
                    reasoning="No supporting evidence in current memory set",
                ))

        return retired

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _similarity_score(a: str, b: str) -> float:
        words_a = set(a.lower().replace(":", " ").replace("_", " ").split())
        words_b = set(b.lower().replace(":", " ").replace("_", " ").split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    @staticmethod
    def _pattern_to_dict(p: DetectedPattern) -> dict[str, Any]:
        return {
            "pattern_id": p.pattern_id,
            "name": p.name,
            "description": p.description,
            "category": p.category,
            "evidence": p.evidence,
            "confidence": round(p.confidence, 3),
            "trend": p.trend,
            "first_seen": p.first_seen,
            "last_seen": p.last_seen,
            "occurrence_count": p.occurrence_count,
            "importance": round(p.importance, 3),
            "supporting_memories": p.supporting_memories,
            "reasoning": p.reasoning,
        }
