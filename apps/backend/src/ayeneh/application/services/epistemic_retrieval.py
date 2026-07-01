"""Epistemic Retrieval Strategy — ranks knowledge sources by epistemic suitability.

This is an independent strategy layer. RetrievalService remains generic.
The strategy owns every epistemic decision.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog

from ayeneh.domain.knowledge_epistemics.entities import EpistemicProfile
from ayeneh.domain.knowledge_epistemics.enums import (
    EvidenceLevel,
    EpistemicFramework,
    KnowledgeAuthority,
    KnowledgeDomain,
    ReasoningStyle,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Score components
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoreBreakdown:
    """Independent score components for a single epistemic match."""

    semantic_score: float = 0.0
    domain_score: float = 0.0
    authority_score: float = 0.0
    applicability_score: float = 0.0
    scope_score: float = 0.0
    reasoning_style_score: float = 0.0
    citation_score: float = 0.0
    confidence_score: float = 0.0
    supported_questions_score: float = 0.0
    unsupported_questions_penalty: float = 0.0

    @property
    def final_score(self) -> float:
        """Weighted combination of all score components."""
        return (
            self.semantic_score * 0.20
            + self.domain_score * 0.15
            + self.authority_score * 0.10
            + self.applicability_score * 0.15
            + self.scope_score * 0.10
            + self.reasoning_style_score * 0.10
            + self.citation_score * 0.05
            + self.confidence_score * 0.05
            + self.supported_questions_score * 0.10
            - self.unsupported_questions_penalty * 0.10
        )


# ---------------------------------------------------------------------------
# Ranking weights (configurable)
# ---------------------------------------------------------------------------


@dataclass
class RankingWeights:
    """Configurable weights for the ranking pipeline."""

    semantic: float = 0.20
    domain: float = 0.15
    authority: float = 0.10
    applicability: float = 0.15
    scope: float = 0.10
    reasoning_style: float = 0.10
    citation: float = 0.05
    confidence: float = 0.05
    supported_questions: float = 0.10
    unsupported_penalty: float = 0.10


# ---------------------------------------------------------------------------
# Request analysis
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RequestAnalysis:
    """Inferred epistemic requirements from the user's query."""

    query: str
    inferred_domains: list[str] = field(default_factory=list)
    inferred_reasoning_style: str = "deductive"
    inferred_evidence_level: str = "philosophical"
    uncertainty_required: bool = False
    requires_ambiguity_tolerance: bool = False


# ---------------------------------------------------------------------------
# Match metadata
# ---------------------------------------------------------------------------


@dataclass
class EpistemicMatch:
    """A single source ranked by epistemic suitability."""

    profile: EpistemicProfile
    scores: ScoreBreakdown
    final_score: float
    selected: bool = False
    selection_reason: str = ""
    outranking_reason: str = ""
    epistemic_properties_used: list[str] = field(default_factory=list)
    limitations_considered: list[str] = field(default_factory=list)
    confidence_explanation: str = ""
    applicability_explanation: str = ""


# ---------------------------------------------------------------------------
# Ranking result
# ---------------------------------------------------------------------------


@dataclass
class EpistemicRankingResult:
    """Complete result from epistemic ranking."""

    matches: list[EpistemicMatch] = field(default_factory=list)
    request_analysis: RequestAnalysis | None = None
    scope_filtered_count: int = 0
    total_profiles_evaluated: int = 0
    ranking_latency_ms: float = 0.0
    domain_distribution: dict[str, int] = field(default_factory=dict)
    authority_distribution: dict[str, int] = field(default_factory=dict)
    selection_reasons: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Epistemic Retrieval Strategy
# ---------------------------------------------------------------------------


class EpistemicRetrievalStrategy:
    """Strategy that ranks knowledge sources by epistemic suitability.

    This is an independent layer. RetrievalService remains generic.
    The strategy owns every epistemic decision.
    """

    def __init__(
        self,
        *,
        weights: RankingWeights | None = None,
        scope_filter_enabled: bool = True,
    ) -> None:
        self._weights = weights or RankingWeights()
        self._scope_filter_enabled = scope_filter_enabled

    def analyze_request(self, query: str) -> RequestAnalysis:
        """Infer epistemic requirements from the user's query."""
        query_lower = query.lower()

        domains = self._infer_domains(query_lower)
        reasoning = self._infer_reasoning_style(query_lower)
        evidence = self._infer_evidence_level(query_lower)
        uncertainty = self._requires_uncertainty(query_lower)
        ambiguity = self._requires_ambiguity_tolerance(query_lower)

        return RequestAnalysis(
            query=query,
            inferred_domains=domains,
            inferred_reasoning_style=reasoning,
            inferred_evidence_level=evidence,
            uncertainty_required=uncertainty,
            requires_ambiguity_tolerance=ambiguity,
        )

    def rank(
        self,
        profiles: list[EpistemicProfile],
        analysis: RequestAnalysis,
        *,
        semantic_scores: dict[uuid.UUID, float] | None = None,
    ) -> EpistemicRankingResult:
        """Rank all profiles by epistemic suitability."""
        import time

        start = time.monotonic()

        result = EpistemicRankingResult(
            request_analysis=analysis,
            total_profiles_evaluated=len(profiles),
        )

        # Step 1: Scope filtering
        if self._scope_filter_enabled:
            candidates = self._apply_scope_filter(profiles, analysis)
            result.scope_filtered_count = len(profiles) - len(candidates)
        else:
            candidates = profiles

        # Step 2: Score each candidate
        matches: list[EpistemicMatch] = []
        for profile in candidates:
            match = self._score_profile(profile, analysis, semantic_scores)
            matches.append(match)

        # Step 3: Sort by final score
        matches.sort(key=lambda m: m.final_score, reverse=True)

        # Step 4: Build selection metadata
        self._assign_selection_metadata(matches)

        result.matches = matches

        # Step 5: Aggregate stats
        result.domain_distribution = self._aggregate_domains(matches)
        result.authority_distribution = self._aggregate_authorities(matches)
        result.selection_reasons = [
            m.selection_reason for m in matches if m.selected
        ]

        result.ranking_latency_ms = (time.monotonic() - start) * 1000

        logger.info(
            "epistemic_ranking_completed",
            total=len(profiles),
            candidates=len(candidates),
            filtered=result.scope_filtered_count,
            latency_ms=round(result.ranking_latency_ms, 2),
        )

        return result

    # ------------------------------------------------------------------
    # Scope filtering
    # ------------------------------------------------------------------

    def _apply_scope_filter(
        self,
        profiles: list[EpistemicProfile],
        analysis: RequestAnalysis,
    ) -> list[EpistemicProfile]:
        """Remove sources that are explicitly outside their epistemic scope."""
        candidates: list[EpistemicProfile] = []
        for profile in profiles:
            if self._is_in_scope(profile, analysis):
                candidates.append(profile)
            else:
                logger.debug(
                    "epistemic_scope_filtered",
                    book_id=str(profile.book_id),
                    discipline=profile.discipline,
                )
        return candidates

    def _is_in_scope(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> bool:
        """Check if a profile is within epistemic scope for the query.

        A source is excluded if the query matches its excluded topics or
        contraindications using word overlap (not just exact substring).
        """
        import re
        query_words = set(re.findall(r'\b\w+\b', analysis.query.lower()))
        query_words = {w for w in query_words if len(w) > 2}

        # Check excluded topics
        for excluded in profile.scope_boundary.excluded_topics:
            excluded_words = set(re.findall(r'\b\w+\b', excluded.lower()))
            overlap = query_words & excluded_words
            if overlap and len(overlap) >= max(1, len(excluded_words) // 2):
                if not self._has_applicability_match(profile, analysis):
                    return False

        # Check contraindications
        for contra in profile.applicability.contraindications:
            contra_words = set(re.findall(r'\b\w+\b', contra.lower()))
            overlap = query_words & contra_words
            if overlap and len(overlap) >= max(1, len(contra_words) // 2):
                return False

        return True

    def _has_applicability_match(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> bool:
        """Check if profile's applicability contexts match the request."""
        query_lower = analysis.query.lower()
        for ctx in profile.applicability.contexts:
            if ctx.lower() in query_lower:
                return True
        for cond in profile.applicability.conditions:
            if cond.lower() in query_lower:
                return True
        return False

    def _supports_question_type(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> bool:
        """Check if profile supports the type of question being asked."""
        query_lower = analysis.query.lower()
        for q in profile.supported_questions:
            if q.lower() in query_lower or any(
                word in query_lower for word in q.lower().split() if len(word) > 3
            ):
                return True
        return False

    # ------------------------------------------------------------------
    # Scoring pipeline
    # ------------------------------------------------------------------

    def _score_profile(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
        semantic_scores: dict[uuid.UUID, float] | None = None,
    ) -> EpistemicMatch:
        """Score a single profile against the request analysis."""
        semantic = (semantic_scores or {}).get(profile.book_id, 0.0)

        scores = ScoreBreakdown(
            semantic_score=semantic,
            domain_score=self._score_domain(profile, analysis),
            authority_score=self._score_authority(profile),
            applicability_score=self._score_applicability(profile, analysis),
            scope_score=self._score_scope(profile, analysis),
            reasoning_style_score=self._score_reasoning_style(profile, analysis),
            citation_score=self._score_citation(profile, analysis),
            confidence_score=self._score_confidence(profile, analysis),
            supported_questions_score=self._score_supported_questions(profile, analysis),
            unsupported_questions_penalty=self._score_unsupported_questions(profile, analysis),
        )

        properties_used = self._identify_properties_used(profile, analysis)
        limitations = [lim.description for lim in profile.limitations]
        conf_explanation = self._build_confidence_explanation(profile, analysis)
        applicability_explanation = self._build_applicability_explanation(profile, analysis)

        return EpistemicMatch(
            profile=profile,
            scores=scores,
            final_score=scores.final_score,
            epistemic_properties_used=properties_used,
            limitations_considered=limitations,
            confidence_explanation=conf_explanation,
            applicability_explanation=applicability_explanation,
        )

    def _score_domain(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> float:
        """Score domain alignment."""
        if not analysis.inferred_domains:
            return 0.5  # Neutral when no domain inferred

        if profile.discipline in analysis.inferred_domains:
            return 1.0

        if profile.discipline == KnowledgeDomain.INTERDISCIPLINARY:
            return 0.7

        # Partial match for related domains
        related = self._related_domains(profile.discipline)
        for d in analysis.inferred_domains:
            if d in related:
                return 0.5

        return 0.1

    def _related_domains(self, domain: str) -> list[str]:
        """Return domains related to the given domain."""
        relations: dict[str, list[str]] = {
            KnowledgeDomain.PHILOSOPHY: [
                KnowledgeDomain.SPIRITUALITY,
                KnowledgeDomain.PSYCHOLOGY,
            ],
            KnowledgeDomain.PSYCHOLOGY: [
                KnowledgeDomain.PHILOSOPHY,
                KnowledgeDomain.SOCIAL_SCIENCE,
            ],
            KnowledgeDomain.SPIRITUALITY: [
                KnowledgeDomain.PHILOSOPHY,
                KnowledgeDomain.LITERATURE,
            ],
            KnowledgeDomain.SOCIAL_SCIENCE: [
                KnowledgeDomain.PSYCHOLOGY,
                KnowledgeDomain.HISTORY,
            ],
        }
        return relations.get(domain, [])

    def _score_authority(self, profile: EpistemicProfile) -> float:
        """Score source authority."""
        authority_scores: dict[str, float] = {
            KnowledgeAuthority.PRIMARY: 1.0,
            KnowledgeAuthority.SECONDARY: 0.7,
            KnowledgeAuthority.COMMENTARY: 0.5,
            KnowledgeAuthority.REFERENCE: 0.6,
            KnowledgeAuthority.CORROBORATING: 0.6,
            KnowledgeAuthority.CONTRARIAN: 0.3,
        }
        return authority_scores.get(profile.authority, 0.5)

    def _score_applicability(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> float:
        """Score how applicable the source is to the request."""
        score = 0.3  # Base applicability

        query_lower = analysis.query.lower()

        # Check context matches
        for ctx in profile.applicability.contexts:
            if ctx.lower() in query_lower:
                score += 0.4
                break

        # Check condition matches
        for cond in profile.applicability.conditions:
            if cond.lower() in query_lower:
                score += 0.3
                break

        # Penalize contraindications
        for contra in profile.applicability.contraindications:
            if contra.lower() in query_lower:
                score -= 0.3

        return max(0.0, min(1.0, score))

    def _score_scope(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> float:
        """Score scope boundary alignment."""
        query_lower = analysis.query.lower()
        score = 0.5  # Neutral

        # Bonus for included topics
        for topic in profile.scope_boundary.included_topics:
            if topic.lower() in query_lower:
                score += 0.3
                break

        # Bonus for overlap notes
        for note in profile.scope_boundary.overlap_notes:
            if any(word in query_lower for word in note.lower().split() if len(word) > 3):
                score += 0.2
                break

        return min(1.0, score)

    def _score_reasoning_style(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> float:
        """Score reasoning style compatibility."""
        if profile.reasoning_style == analysis.inferred_reasoning_style:
            return 1.0

        # Compatible reasoning styles
        compatible: dict[str, list[str]] = {
            ReasoningStyle.DEDUCTIVE: [ReasoningStyle.INDUCTIVE, ReasoningStyle.ANALOGICAL],
            ReasoningStyle.INDUCTIVE: [ReasoningStyle.DEDUCTIVE, ReasoningStyle.ABDUCTIVE],
            ReasoningStyle.ABDUCTIVE: [ReasoningStyle.INDUCTIVE, ReasoningStyle.INTUITIVE],
            ReasoningStyle.DIALECTICAL: [ReasoningStyle.ANALOGICAL, ReasoningStyle.NARRATIVE],
            ReasoningStyle.CONTEMPLATIVE: [ReasoningStyle.INTUITIVE, ReasoningStyle.NARRATIVE],
            ReasoningStyle.INTUITIVE: [ReasoningStyle.CONTEMPLATIVE, ReasoningStyle.ABDUCTIVE],
        }

        if analysis.inferred_reasoning_style in compatible.get(
            profile.reasoning_style, []
        ):
            return 0.6

        return 0.3

    def _score_citation(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> float:
        """Score citation policy alignment."""
        if analysis.uncertainty_required and profile.citation_policy.required:
            return 1.0
        if profile.citation_policy.required:
            return 0.7
        return 0.3

    def _score_confidence(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> float:
        """Score confidence policy alignment."""
        if not analysis.uncertainty_required:
            return 0.7

        # When uncertainty is required, prefer sources with confidence policies
        if profile.confidence_policy:
            return 0.9
        return 0.4

    def _score_supported_questions(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> float:
        """Score how well the profile supports the query's question type."""
        if not profile.supported_questions:
            return 0.5

        query_lower = analysis.query.lower()
        for q in profile.supported_questions:
            if q.lower() in query_lower:
                return 1.0
            # Partial word overlap
            q_words = set(q.lower().split())
            query_words = set(query_lower.split())
            overlap = q_words & query_words
            if len(overlap) >= 2:
                return 0.7

        return 0.2

    def _score_unsupported_questions(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> float:
        """Penalize profiles that explicitly don't support the query type."""
        if not profile.unsupported_questions:
            return 0.0

        query_lower = analysis.query.lower()
        for q in profile.unsupported_questions:
            if q.lower() in query_lower:
                return 1.0  # Full penalty
            q_words = set(q.lower().split())
            query_words = set(query_lower.split())
            overlap = q_words & query_words
            if len(overlap) >= 2:
                return 0.5  # Partial penalty

        return 0.0

    # ------------------------------------------------------------------
    # Selection metadata
    # ------------------------------------------------------------------

    def _assign_selection_metadata(self, matches: list[EpistemicMatch]) -> None:
        """Assign selection reasons and outranking explanations."""
        if not matches:
            return

        # Select top matches (at least 1, up to 5 with score > 0.3)
        threshold = 0.3
        selected_count = 0
        for match in matches:
            if match.final_score >= threshold and selected_count < 5:
                match.selected = True
                match.selection_reason = self._build_selection_reason(match)
                match.outranking_reason = self._build_outranking_reason(match, matches)
                selected_count += 1

    def _build_selection_reason(self, match: EpistemicMatch) -> str:
        """Build a human-readable selection reason."""
        profile = match.profile
        parts: list[str] = []

        if match.scores.domain_score >= 0.8:
            parts.append(f"specializes in {profile.discipline}")

        if match.scores.reasoning_style_score >= 0.8:
            parts.append(f"uses {profile.reasoning_style} reasoning")

        if match.scores.authority_score >= 0.8:
            parts.append(f"primary authority on {profile.tradition}")

        if match.scores.supported_questions_score >= 0.8:
            parts.append("directly addresses this question type")

        if not parts:
            parts.append("epistemically suitable for this query")

        return f"Selected because source {' and '.join(parts)}."

    def _build_outranking_reason(
        self,
        match: EpistemicMatch,
        all_matches: list[EpistemicMatch],
    ) -> str:
        """Build an outranking explanation."""
        profile = match.profile

        reasons: list[str] = []
        if match.scores.domain_score >= 0.8:
            reasons.append(f"stronger domain alignment ({profile.discipline})")
        if match.scores.authority_score >= 0.8:
            reasons.append("higher source authority")
        if match.scores.supported_questions_score >= 0.8:
            reasons.append("better question support")

        if not reasons:
            reasons.append("higher overall epistemic suitability")

        return f"Outranked other sources due to {', '.join(reasons)}."

    def _identify_properties_used(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> list[str]:
        """Identify which epistemic properties contributed to the ranking."""
        properties: list[str] = []
        scores = self._score_profile_components(profile, analysis)

        if scores.domain_score >= 0.5:
            properties.append("discipline")
        if scores.authority_score >= 0.5:
            properties.append("authority")
        if scores.applicability_score >= 0.5:
            properties.append("applicability")
        if scores.scope_score >= 0.5:
            properties.append("scope_boundary")
        if scores.reasoning_style_score >= 0.5:
            properties.append("reasoning_style")
        if scores.citation_score >= 0.5:
            properties.append("citation_policy")
        if scores.supported_questions_score >= 0.5:
            properties.append("supported_questions")

        return properties

    def _score_profile_components(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> ScoreBreakdown:
        """Compute score components without creating a full match."""
        return ScoreBreakdown(
            domain_score=self._score_domain(profile, analysis),
            authority_score=self._score_authority(profile),
            applicability_score=self._score_applicability(profile, analysis),
            scope_score=self._score_scope(profile, analysis),
            reasoning_style_score=self._score_reasoning_style(profile, analysis),
            citation_score=self._score_citation(profile, analysis),
            confidence_score=self._score_confidence(profile, analysis),
            supported_questions_score=self._score_supported_questions(profile, analysis),
            unsupported_questions_penalty=self._score_unsupported_questions(profile, analysis),
        )

    def _build_confidence_explanation(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> str:
        """Build confidence explanation."""
        parts: list[str] = []

        if profile.source_reliability.score >= 0.8:
            parts.append(f"high reliability ({profile.source_reliability.basis})")
        elif profile.source_reliability.score >= 0.5:
            parts.append(f"moderate reliability ({profile.source_reliability.basis})")
        else:
            parts.append(f"lower reliability ({profile.source_reliability.basis})")

        if analysis.uncertainty_required and profile.confidence_policy:
            parts.append("has explicit confidence policy")

        return "; ".join(parts) if parts else "default confidence assessment"

    def _build_applicability_explanation(
        self,
        profile: EpistemicProfile,
        analysis: RequestAnalysis,
    ) -> str:
        """Build applicability explanation."""
        parts: list[str] = []

        if profile.applicability.contexts:
            parts.append(f"applicable in contexts: {', '.join(profile.applicability.contexts[:3])}")

        if profile.applicability.conditions:
            parts.append(f"conditions: {', '.join(profile.applicability.conditions[:3])}")

        if profile.applicability.contraindications:
            parts.append(f"contraindicated: {', '.join(profile.applicability.contraindications[:2])}")

        return "; ".join(parts) if parts else "general applicability"

    # ------------------------------------------------------------------
    # Domain inference
    # ------------------------------------------------------------------

    def _infer_domains(self, query_lower: str) -> list[str]:
        """Infer knowledge domains from the query."""
        domains: list[str] = []

        domain_keywords: dict[str, list[str]] = {
            KnowledgeDomain.PHILOSOPHY: [
                "truth", "reality", "existence", "meaning", "ethics", "logic",
                "metaphysics", "epistemology", "ontology", "consciousness",
                "being", "essence", "virtue", "justice", "beauty",
            ],
            KnowledgeDomain.PSYCHOLOGY: [
                "mind", "behavior", "emotion", "cognitive", "therapy",
                "anxiety", "depression", "mental", "psychology", "habit",
                "pattern", "belief", "perception", "motivation", "trauma",
            ],
            KnowledgeDomain.SPIRITUALITY: [
                "spiritual", "contemplation", "meditation", "prayer",
                "mysticism", "sufi", "divine", "sacred", "transcendence",
                "fana", "bhakti", "zen", "awareness", "presence",
            ],
            KnowledgeDomain.SOCIAL_SCIENCE: [
                "society", "culture", "community", "social", "power",
                "injustice", "systemic", "structural", "inequality",
            ],
            KnowledgeDomain.SCIENCE: [
                "research", "study", "data", "evidence", "empirical",
                "experiment", "hypothesis", "neuroscience", "brain",
            ],
            KnowledgeDomain.LITERATURE: [
                "story", "narrative", "poetry", "metaphor", "symbol",
                "literary", "author", "text", "reading",
            ],
        }

        for domain, keywords in domain_keywords.items():
            for kw in keywords:
                if kw in query_lower:
                    if domain not in domains:
                        domains.append(domain)
                    break

        return domains

    def _infer_reasoning_style(self, query_lower: str) -> str:
        """Infer the required reasoning style from the query."""
        if any(w in query_lower for w in ["why", "cause", "reason", "because", "therefore"]):
            return ReasoningStyle.DEDUCTIVE
        if any(w in query_lower for w in ["pattern", "trend", "observe", "notice", "usually"]):
            return ReasoningStyle.INDUCTIVE
        if any(w in query_lower for w in ["hypothesis", "suggest", "might", "possibly", "guess"]):
            return ReasoningStyle.ABDUCTIVE
        if any(w in query_lower for w in ["similar", "like", "as if", "metaphor", "compare"]):
            return ReasoningStyle.ANALOGICAL
        if any(w in query_lower for w in ["contradiction", "tension", "paradox", "dialectic"]):
            return ReasoningStyle.DIALECTICAL
        if any(w in query_lower for w in [
            "feel", "sense", "intuit", "inner", "contemplat",
        ]):
            return ReasoningStyle.CONTEMPLATIVE
        if any(w in query_lower for w in ["story", "narrative", "once", "journey", "experience"]):
            return ReasoningStyle.NARRATIVE
        if any(w in query_lower for w in ["insight", "intuition", "inner knowing"]):
            return ReasoningStyle.INTUITIVE
        return ReasoningStyle.DEDUCTIVE

    def _infer_evidence_level(self, query_lower: str) -> str:
        """Infer the expected evidence level from the query."""
        if any(w in query_lower for w in ["research", "study", "data", "evidence"]):
            return EvidenceLevel.EMPIRICAL
        if any(w in query_lower for w in ["feel", "experience", "personal", "lived"]):
            return EvidenceLevel.EXPERIENTIAL
        if any(w in query_lower for w in ["tradition", "teach", "sacred", "ancient"]):
            return EvidenceLevel.TRADITIONAL
        if any(w in query_lower for w in ["philosophy", "logic", "reason", "truth"]):
            return EvidenceLevel.PHILOSOPHICAL
        return EvidenceLevel.PHILOSOPHICAL

    def _requires_uncertainty(self, query_lower: str) -> bool:
        """Check if the query implies uncertainty handling is needed."""
        return any(
            w in query_lower
            for w in ["uncertain", "doubt", "maybe", "possibly", "not sure", "ambiguity"]
        )

    def _requires_ambiguity_tolerance(self, query_lower: str) -> bool:
        """Check if the query requires tolerance for ambiguity."""
        return any(
            w in query_lower
            for w in ["paradox", "contradiction", "tension", "complexity", "nuance"]
        )

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _aggregate_domains(
        self,
        matches: list[EpistemicMatch],
    ) -> dict[str, int]:
        """Aggregate domain distribution of selected matches."""
        dist: dict[str, int] = {}
        for m in matches:
            if m.selected:
                d = m.profile.discipline
                dist[d] = dist.get(d, 0) + 1
        return dist

    def _aggregate_authorities(
        self,
        matches: list[EpistemicMatch],
    ) -> dict[str, int]:
        """Aggregate authority distribution of selected matches."""
        dist: dict[str, int] = {}
        for m in matches:
            if m.selected:
                a = m.profile.authority
                dist[a] = dist.get(a, 0) + 1
        return dist
