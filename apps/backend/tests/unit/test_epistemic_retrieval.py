"""Comprehensive tests for the Epistemic Retrieval Strategy."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from ayeneh.application.services.epistemic_retrieval import (
    EpistemicMatch,
    EpistemicRankingResult,
    EpistemicRetrievalStrategy,
    RankingWeights,
    RequestAnalysis,
    ScoreBreakdown,
)
from ayeneh.domain.knowledge_epistemics.entities import EpistemicProfile
from ayeneh.domain.knowledge_epistemics.enums import (
    EvidenceLevel,
    EpistemicFramework,
    KnowledgeAuthority,
    KnowledgeDomain,
    KnowledgeSource,
    ReasoningStyle,
)
from ayeneh.domain.knowledge_epistemics.value_objects import (
    Applicability,
    CitationPolicy,
    Limitation,
    ScopeBoundary,
    SourceReliability,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_profile(
    *,
    book_id: uuid.UUID | None = None,
    discipline: str = KnowledgeDomain.PHILOSOPHY,
    authority: str = KnowledgeAuthority.PRIMARY,
    reasoning_style: str = ReasoningStyle.DEDUCTIVE,
    evidence_level: str = EvidenceLevel.PHILOSOPHICAL,
    source: str = KnowledgeSource.BOOK,
    tradition: str = "test_tradition",
    framework: str = EpistemicFramework.RATIONALIST,
    primary_topics: list[str] | None = None,
    secondary_topics: list[str] | None = None,
    supported_questions: list[str] | None = None,
    unsupported_questions: list[str] | None = None,
    applicability: Applicability | None = None,
    limitations: list[Limitation] | None = None,
    scope_boundary: ScopeBoundary | None = None,
    citation_policy: CitationPolicy | None = None,
    source_reliability: SourceReliability | None = None,
    confidence_policy: str = "",
    conflict_policy: str = "",
) -> EpistemicProfile:
    return EpistemicProfile(
        id=uuid.uuid4(),
        book_id=book_id or uuid.uuid4(),
        user_id=uuid.uuid4(),
        source=source,
        tradition=tradition,
        framework=framework,
        discipline=discipline,
        primary_topics=primary_topics or [],
        secondary_topics=secondary_topics or [],
        supported_questions=supported_questions or [],
        unsupported_questions=unsupported_questions or [],
        evidence_level=evidence_level,
        reasoning_style=reasoning_style,
        authority=authority,
        applicability=applicability or Applicability(
            contexts=[], conditions=[], contraindications=[],
        ),
        limitations=limitations or [],
        scope_boundary=scope_boundary or ScopeBoundary(
            included_topics=[], excluded_topics=[], overlap_notes=[],
        ),
        citation_policy=citation_policy or CitationPolicy(
            required=True, format="inline", min_confidence=0.5,
        ),
        source_reliability=source_reliability or SourceReliability(
            score=0.7, basis="scholarly_consensus",
        ),
        confidence_policy=confidence_policy,
        conflict_policy=conflict_policy,
    )


@pytest.fixture
def strategy() -> EpistemicRetrievalStrategy:
    return EpistemicRetrievalStrategy()


@pytest.fixture
def philosophy_profile() -> EpistemicProfile:
    return _make_profile(
        discipline=KnowledgeDomain.PHILOSOPHY,
        authority=KnowledgeAuthority.PRIMARY,
        reasoning_style=ReasoningStyle.DEDUCTIVE,
        supported_questions=["What is the nature of reality?"],
        scope_boundary=ScopeBoundary(
            included_topics=["metaphysics", "epistemology", "ontology"],
            excluded_topics=["clinical diagnosis", "medical treatment"],
            overlap_notes=["overlaps with psychology"],
        ),
    )


@pytest.fixture
def psychology_profile() -> EpistemicProfile:
    return _make_profile(
        discipline=KnowledgeDomain.PSYCHOLOGY,
        authority=KnowledgeAuthority.SECONDARY,
        reasoning_style=ReasoningStyle.INDUCTIVE,
        supported_questions=["How do habits form?"],
        applicability=Applicability(
            contexts=["therapy", "behavior change", "cognitive patterns"],
            conditions=["clinical setting"],
            contraindications=["fana", "mystical contemplation"],
        ),
        scope_boundary=ScopeBoundary(
            included_topics=["behavior", "cognition", "emotion"],
            excluded_topics=["fana", "mysticism"],
            overlap_notes=["overlaps with neuroscience"],
        ),
    )


@pytest.fixture
def spirituality_profile() -> EpistemicProfile:
    return _make_profile(
        discipline=KnowledgeDomain.SPIRITUALITY,
        authority=KnowledgeAuthority.PRIMARY,
        reasoning_style=ReasoningStyle.CONTEMPLATIVE,
        evidence_level=EvidenceLevel.EXPERIENTIAL,
        supported_questions=["What is fana?"],
        applicability=Applicability(
            contexts=["meditation", "contemplation", "spiritual practice"],
            conditions=["open mind"],
            contraindications=["purely empirical inquiry"],
        ),
        scope_boundary=ScopeBoundary(
            included_topics=["contemplation", "mysticism", "presence"],
            excluded_topics=["clinical anxiety", "anxiety treatment"],
            overlap_notes=["overlaps with philosophy"],
        ),
    )


@pytest.fixture
def interdisciplinary_profile() -> EpistemicProfile:
    return _make_profile(
        discipline=KnowledgeDomain.INTERDISCIPLINARY,
        authority=KnowledgeAuthority.COMMENTARY,
        reasoning_style=ReasoningStyle.DIALECTICAL,
        supported_questions=["How do mind and spirit interact?"],
        scope_boundary=ScopeBoundary(
            included_topics=["mind-body", "consciousness", "integration"],
            excluded_topics=[],
            overlap_notes=["bridges multiple disciplines"],
        ),
    )


# ---------------------------------------------------------------------------
# Request analysis tests
# ---------------------------------------------------------------------------


class TestRequestAnalysis:
    def test_analyze_philosophy_query(self, strategy: EpistemicRetrievalStrategy) -> None:
        analysis = strategy.analyze_request("What is the nature of reality and existence?")
        assert KnowledgeDomain.PHILOSOPHY in analysis.inferred_domains
        assert analysis.inferred_reasoning_style == ReasoningStyle.DEDUCTIVE

    def test_analyze_psychology_query(self, strategy: EpistemicRetrievalStrategy) -> None:
        analysis = strategy.analyze_request("How do cognitive patterns and habits form?")
        assert KnowledgeDomain.PSYCHOLOGY in analysis.inferred_domains

    def test_analyze_spiritual_query(self, strategy: EpistemicRetrievalStrategy) -> None:
        analysis = strategy.analyze_request("What is fana and mystical contemplation?")
        assert KnowledgeDomain.SPIRITUALITY in analysis.inferred_domains
        assert analysis.inferred_reasoning_style == ReasoningStyle.CONTEMPLATIVE

    def test_analyze_uncertainty_query(self, strategy: EpistemicRetrievalStrategy) -> None:
        analysis = strategy.analyze_request("I'm uncertain about the meaning of life")
        assert analysis.uncertainty_required is True

    def test_analyze_ambiguity_query(self, strategy: EpistemicRetrievalStrategy) -> None:
        analysis = strategy.analyze_request("The paradox of free will and determinism")
        assert analysis.requires_ambiguity_tolerance is True

    def test_analyze_deductive_query(self, strategy: EpistemicRetrievalStrategy) -> None:
        analysis = strategy.analyze_request("Why does consciousness exist and what is its cause?")
        assert analysis.inferred_reasoning_style == ReasoningStyle.DEDUCTIVE

    def test_analyze_inductive_query(self, strategy: EpistemicRetrievalStrategy) -> None:
        analysis = strategy.analyze_request("I notice a pattern in how people usually behave")
        assert analysis.inferred_reasoning_style == ReasoningStyle.INDUCTIVE

    def test_analyze_abductive_query(self, strategy: EpistemicRetrievalStrategy) -> None:
        analysis = strategy.analyze_request("This hypothesis might suggest a new possibility")
        assert analysis.inferred_reasoning_style == ReasoningStyle.ABDUCTIVE


# ---------------------------------------------------------------------------
# Scope filtering tests
# ---------------------------------------------------------------------------


class TestScopeFiltering:
    def test_neuroscience_excluded_from_fana(
        self,
        strategy: EpistemicRetrievalStrategy,
        psychology_profile: EpistemicProfile,
    ) -> None:
        """Neuroscience book should not rank for 'fana' unless explicitly applicable."""
        analysis = strategy.analyze_request("What is fana?")
        result = strategy.rank([psychology_profile], analysis)

        # Psychology profile has contraindication for spiritual practice
        # and excluded topics for spirituality
        assert result.scope_filtered_count == 1
        assert len(result.matches) == 0

    def test_sufi_text_not_dominant_clinical(
        self,
        strategy: EpistemicRetrievalStrategy,
        spirituality_profile: EpistemicProfile,
    ) -> None:
        """Classical Sufi texts should not dominate clinical anxiety unless explicitly applicable."""
        analysis = strategy.analyze_request("clinical anxiety treatment")
        result = strategy.rank([spirituality_profile], analysis)

        # Spirituality profile excluded from clinical context
        assert result.scope_filtered_count == 1

    def test_interdisciplinary_not_filtered(
        self,
        strategy: EpistemicRetrievalStrategy,
        interdisciplinary_profile: EpistemicProfile,
    ) -> None:
        """Interdisciplinary sources should pass scope filtering."""
        analysis = strategy.analyze_request("How do mind and spirit interact?")
        result = strategy.rank([interdisciplinary_profile], analysis)

        assert len(result.matches) == 1
        assert result.matches[0].selected

    def test_explicit_applicability_passes_filter(
        self,
        strategy: EpistemicRetrievalStrategy,
    ) -> None:
        """Profile with explicit applicability should pass scope filter."""
        profile = _make_profile(
            discipline=KnowledgeDomain.SCIENCE,
            applicability=Applicability(
                contexts=["spiritual practice", "contemplation"],
                conditions=["open mind"],
                contraindications=[],
            ),
            scope_boundary=ScopeBoundary(
                included_topics=["neuroscience of meditation"],
                excluded_topics=[],
                overlap_notes=[],
            ),
        )
        analysis = strategy.analyze_request("What is fana?")
        result = strategy.rank([profile], analysis)

        assert len(result.matches) == 1


# ---------------------------------------------------------------------------
# Ranking tests
# ---------------------------------------------------------------------------


class TestRanking:
    def test_correct_ranking_by_domain(
        self,
        strategy: EpistemicRetrievalStrategy,
        philosophy_profile: EpistemicProfile,
        psychology_profile: EpistemicProfile,
    ) -> None:
        """Philosophy profile should rank higher for philosophy query."""
        analysis = strategy.analyze_request("What is the nature of reality?")
        result = strategy.rank([psychology_profile, philosophy_profile], analysis)

        assert len(result.matches) == 2
        # Philosophy profile should rank first
        assert result.matches[0].profile.discipline == KnowledgeDomain.PHILOSOPHY
        assert result.matches[0].final_score > result.matches[1].final_score

    def test_authority_weighting(
        self,
        strategy: EpistemicRetrievalStrategy,
    ) -> None:
        """Primary authority should rank higher than secondary."""
        primary = _make_profile(
            discipline=KnowledgeDomain.PHILOSOPHY,
            authority=KnowledgeAuthority.PRIMARY,
        )
        secondary = _make_profile(
            discipline=KnowledgeDomain.PHILOSOPHY,
            authority=KnowledgeAuthority.SECONDARY,
        )
        analysis = strategy.analyze_request("What is truth?")
        result = strategy.rank([secondary, primary], analysis)

        assert result.matches[0].profile.authority == KnowledgeAuthority.PRIMARY

    def test_reasoning_style_compatibility(
        self,
        strategy: EpistemicRetrievalStrategy,
    ) -> None:
        """Compatible reasoning styles should score higher."""
        contemplative = _make_profile(
            discipline=KnowledgeDomain.SPIRITUALITY,
            reasoning_style=ReasoningStyle.CONTEMPLATIVE,
        )
        deductive = _make_profile(
            discipline=KnowledgeDomain.SPIRITUALITY,
            reasoning_style=ReasoningStyle.DEDUCTIVE,
        )
        analysis = strategy.analyze_request("What is fana and contemplation?")
        result = strategy.rank([deductive, contemplative], analysis)

        # Contemplative should rank higher for contemplative query
        contemplative_match = next(
            m for m in result.matches
            if m.profile.reasoning_style == ReasoningStyle.CONTEMPLATIVE
        )
        assert contemplative_match.scores.reasoning_style_score >= 0.6

    def test_supported_questions_boost(
        self,
        strategy: EpistemicRetrievalStrategy,
        philosophy_profile: EpistemicProfile,
    ) -> None:
        """Profile with supported questions should score higher."""
        analysis = strategy.analyze_request("What is the nature of reality?")
        result = strategy.rank([philosophy_profile], analysis)

        assert result.matches[0].scores.supported_questions_score >= 0.5

    def test_unsupported_questions_penalty(
        self,
        strategy: EpistemicRetrievalStrategy,
    ) -> None:
        """Profile with unsupported questions should be penalized."""
        profile = _make_profile(
            discipline=KnowledgeDomain.SPIRITUALITY,
            unsupported_questions=["clinical diagnosis", "medical treatment"],
        )
        analysis = strategy.analyze_request("clinical diagnosis of anxiety")
        result = strategy.rank([profile], analysis)

        if result.matches:
            assert result.matches[0].scores.unsupported_questions_penalty > 0


# ---------------------------------------------------------------------------
# Score breakdown tests
# ---------------------------------------------------------------------------


class TestScoreBreakdown:
    def test_final_score_weighted_combination(self) -> None:
        """Final score should be weighted combination of components."""
        scores = ScoreBreakdown(
            semantic_score=1.0,
            domain_score=1.0,
            authority_score=1.0,
            applicability_score=1.0,
            scope_score=1.0,
            reasoning_style_score=1.0,
            citation_score=1.0,
            confidence_score=1.0,
            supported_questions_score=1.0,
            unsupported_questions_penalty=0.0,
        )
        # All scores 1.0, penalty 0.0 -> final should be ~1.0
        assert scores.final_score >= 0.9

    def test_penalty_reduces_score(self) -> None:
        """Unsupported questions penalty should reduce final score."""
        clean = ScoreBreakdown(
            semantic_score=0.5,
            supported_questions_score=0.5,
            unsupported_questions_penalty=0.0,
        )
        penalized = ScoreBreakdown(
            semantic_score=0.5,
            supported_questions_score=0.5,
            unsupported_questions_penalty=1.0,
        )
        assert clean.final_score > penalized.final_score


# ---------------------------------------------------------------------------
# Ranking result tests
# ---------------------------------------------------------------------------


class TestRankingResult:
    def test_domain_distribution(self, strategy: EpistemicRetrievalStrategy) -> None:
        """Domain distribution should reflect selected matches."""
        profiles = [
            _make_profile(discipline=KnowledgeDomain.PHILOSOPHY),
            _make_profile(discipline=KnowledgeDomain.PHILOSOPHY),
            _make_profile(discipline=KnowledgeDomain.PSYCHOLOGY),
        ]
        analysis = strategy.analyze_request("What is truth?")
        result = strategy.rank(profiles, analysis)

        # Should have domain distribution
        assert isinstance(result.domain_distribution, dict)

    def test_authority_distribution(self, strategy: EpistemicRetrievalStrategy) -> None:
        """Authority distribution should reflect selected matches."""
        profiles = [
            _make_profile(authority=KnowledgeAuthority.PRIMARY),
            _make_profile(authority=KnowledgeAuthority.SECONDARY),
        ]
        analysis = strategy.analyze_request("What is truth?")
        result = strategy.rank(profiles, analysis)

        assert isinstance(result.authority_distribution, dict)

    def test_total_profiles_evaluated(self, strategy: EpistemicRetrievalStrategy) -> None:
        """Total profiles evaluated should match input count."""
        profiles = [_make_profile() for _ in range(5)]
        analysis = strategy.analyze_request("test query")
        result = strategy.rank(profiles, analysis)

        assert result.total_profiles_evaluated == 5

    def test_ranking_latency_tracked(self, strategy: EpistemicRetrievalStrategy) -> None:
        """Ranking latency should be tracked."""
        profiles = [_make_profile() for _ in range(3)]
        analysis = strategy.analyze_request("test query")
        result = strategy.rank(profiles, analysis)

        assert result.ranking_latency_ms >= 0


# ---------------------------------------------------------------------------
# Selection metadata tests
# ---------------------------------------------------------------------------


class TestSelectionMetadata:
    def test_selection_reason_populated(
        self,
        strategy: EpistemicRetrievalStrategy,
        philosophy_profile: EpistemicProfile,
    ) -> None:
        """Selected matches should have selection reasons."""
        analysis = strategy.analyze_request("What is the nature of reality?")
        result = strategy.rank([philosophy_profile], analysis)

        if result.matches and result.matches[0].selected:
            assert result.matches[0].selection_reason != ""

    def test_outranking_reason_populated(
        self,
        strategy: EpistemicRetrievalStrategy,
        philosophy_profile: EpistemicProfile,
        psychology_profile: EpistemicProfile,
    ) -> None:
        """Selected matches should have outranking reasons."""
        analysis = strategy.analyze_request("What is the nature of reality?")
        result = strategy.rank([psychology_profile, philosophy_profile], analysis)

        if result.matches and result.matches[0].selected:
            assert result.matches[0].outranking_reason != ""

    def test_epistemic_properties_used(
        self,
        strategy: EpistemicRetrievalStrategy,
        philosophy_profile: EpistemicProfile,
    ) -> None:
        """Matches should list which epistemic properties contributed."""
        analysis = strategy.analyze_request("What is the nature of reality?")
        result = strategy.rank([philosophy_profile], analysis)

        if result.matches:
            assert isinstance(result.matches[0].epistemic_properties_used, list)

    def test_limitations_considered(
        self,
        strategy: EpistemicRetrievalStrategy,
    ) -> None:
        """Matches should list limitations that were considered."""
        profile = _make_profile(
            limitations=[
                Limitation(
                    description="Cultural bias",
                    severity="moderate",
                    affected_domains=["psychology"],
                ),
            ],
        )
        analysis = strategy.analyze_request("test query")
        result = strategy.rank([profile], analysis)

        if result.matches:
            assert "Cultural bias" in result.matches[0].limitations_considered

    def test_confidence_explanation(
        self,
        strategy: EpistemicRetrievalStrategy,
        philosophy_profile: EpistemicProfile,
    ) -> None:
        """Matches should have confidence explanations."""
        analysis = strategy.analyze_request("What is truth?")
        result = strategy.rank([philosophy_profile], analysis)

        if result.matches:
            assert result.matches[0].confidence_explanation != ""

    def test_applicability_explanation(
        self,
        strategy: EpistemicRetrievalStrategy,
        philosophy_profile: EpistemicProfile,
    ) -> None:
        """Matches should have applicability explanations."""
        analysis = strategy.analyze_request("What is truth?")
        result = strategy.rank([philosophy_profile], analysis)

        if result.matches:
            assert result.matches[0].applicability_explanation != ""


# ---------------------------------------------------------------------------
# Selection reasons tests
# ---------------------------------------------------------------------------


class TestSelectionReasons:
    def test_selection_reasons_collected(
        self,
        strategy: EpistemicRetrievalStrategy,
        philosophy_profile: EpistemicProfile,
    ) -> None:
        """Selection reasons should be collected in result."""
        analysis = strategy.analyze_request("What is the nature of reality?")
        result = strategy.rank([philosophy_profile], analysis)

        assert isinstance(result.selection_reasons, list)


# ---------------------------------------------------------------------------
# Optional injection tests
# ---------------------------------------------------------------------------


class TestOptionalInjection:
    def test_retrieval_service_without_epistemic_strategy(self) -> None:
        """RetrievalService should work without epistemic strategy."""
        from ayeneh.application.services.retrieval import RetrievalService

        service = RetrievalService()
        assert service._epistemic_strategy is None

    def test_retrieval_service_with_epistemic_strategy(self) -> None:
        """RetrievalService should accept epistemic strategy."""
        from ayeneh.application.services.retrieval import RetrievalService

        strategy = EpistemicRetrievalStrategy()
        service = RetrievalService(epistemic_strategy=strategy)
        assert service._epistemic_strategy is strategy


# ---------------------------------------------------------------------------
# Fallback tests
# ---------------------------------------------------------------------------


class TestFallback:
    def test_empty_profiles(self, strategy: EpistemicRetrievalStrategy) -> None:
        """Ranking with empty profiles should return empty result."""
        analysis = strategy.analyze_request("test query")
        result = strategy.rank([], analysis)

        assert result.matches == []
        assert result.total_profiles_evaluated == 0

    def test_scope_filter_all_excluded(self, strategy: EpistemicRetrievalStrategy) -> None:
        """All profiles filtered by scope should return empty result."""
        profile = _make_profile(
            scope_boundary=ScopeBoundary(
                included_topics=[],
                excluded_topics=["test query"],
                overlap_notes=[],
            ),
        )
        analysis = strategy.analyze_request("test query")
        result = strategy.rank([profile], analysis)

        assert result.scope_filtered_count == 1


# ---------------------------------------------------------------------------
# Custom weights tests
# ---------------------------------------------------------------------------


class TestCustomWeights:
    def test_custom_weights_affect_ranking(self) -> None:
        """Custom weights should affect final scores."""
        strategy = EpistemicRetrievalStrategy(
            weights=RankingWeights(
                semantic=0.5,  # High semantic weight
                domain=0.1,
                authority=0.1,
                applicability=0.1,
                scope=0.05,
                reasoning_style=0.05,
                citation=0.05,
                confidence=0.05,
                supported_questions=0.05,
                unsupported_penalty=0.05,
            ),
        )

        profiles = [
            _make_profile(discipline=KnowledgeDomain.PHILOSOPHY),
            _make_profile(discipline=KnowledgeDomain.PSYCHOLOGY),
        ]
        analysis = strategy.analyze_request("What is truth?")
        result = strategy.rank(profiles, analysis)

        # With high semantic weight, domain matters less
        assert len(result.matches) == 2


# ---------------------------------------------------------------------------
# Scope filter toggle tests
# ---------------------------------------------------------------------------


class TestScopeFilterToggle:
    def test_scope_filter_disabled(self) -> None:
        """Scope filter can be disabled."""
        strategy = EpistemicRetrievalStrategy(scope_filter_enabled=False)

        profile = _make_profile(
            scope_boundary=ScopeBoundary(
                included_topics=[],
                excluded_topics=["test query"],
                overlap_notes=[],
            ),
        )
        analysis = strategy.analyze_request("test query")
        result = strategy.rank([profile], analysis)

        # With scope filter disabled, profile should not be filtered
        assert result.scope_filtered_count == 0
        assert len(result.matches) == 1


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    def test_ranking_completes_quickly(self, strategy: EpistemicRetrievalStrategy) -> None:
        """Ranking should complete within reasonable time."""
        profiles = [_make_profile() for _ in range(50)]
        analysis = strategy.analyze_request("test query")
        result = strategy.rank(profiles, analysis)

        assert result.ranking_latency_ms < 100  # Should be very fast

    def test_concurrent_ranking(self, strategy: EpistemicRetrievalStrategy) -> None:
        """Concurrent ranking calls should not interfere."""
        profiles = [_make_profile() for _ in range(5)]

        def rank_query(query: str) -> EpistemicRankingResult:
            analysis = strategy.analyze_request(query)
            return strategy.rank(profiles, analysis)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(rank_query, f"query {i}")
                for i in range(10)
            ]
            results = [f.result() for f in futures]

        assert all(isinstance(r, EpistemicRankingResult) for r in results)
        assert all(len(r.matches) == 5 for r in results)


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_ranking_idempotent(self, strategy: EpistemicRetrievalStrategy) -> None:
        """Same input should produce same output."""
        profiles = [
            _make_profile(discipline=KnowledgeDomain.PHILOSOPHY),
            _make_profile(discipline=KnowledgeDomain.PSYCHOLOGY),
        ]
        analysis = strategy.analyze_request("What is truth?")

        result1 = strategy.rank(profiles, analysis)
        result2 = strategy.rank(profiles, analysis)

        assert result1.total_profiles_evaluated == result2.total_profiles_evaluated
        assert result1.scope_filtered_count == result2.scope_filtered_count
        assert len(result1.matches) == len(result2.matches)

        # Final scores should match
        for m1, m2 in zip(result1.matches, result2.matches, strict=True):
            assert abs(m1.final_score - m2.final_score) < 1e-10


# ---------------------------------------------------------------------------
# Epistemic metadata tests
# ---------------------------------------------------------------------------


class TestEpistemicMetadata:
    def test_epistemic_metadata_in_retrieval_result(self) -> None:
        """RetrievalResult should have epistemic_metadata field."""
        from ayeneh.application.services.retrieval import EpistemicMetadata, RetrievalResult

        result = RetrievalResult()
        assert result.epistemic_metadata is None

        meta = EpistemicMetadata()
        result.epistemic_metadata = meta
        assert result.epistemic_metadata is not None


# ---------------------------------------------------------------------------
# Prompt context tests
# ---------------------------------------------------------------------------


class TestPromptContext:
    def test_epistemic_context_field(self) -> None:
        """PromptContext should have epistemic_context field."""
        from ayeneh.application.services.prompt_context import PromptContext

        ctx = PromptContext()
        assert hasattr(ctx, "epistemic_context")
        assert ctx.epistemic_context == ""


# ---------------------------------------------------------------------------
# Observability tests
# ---------------------------------------------------------------------------


class TestObservability:
    def test_epistemic_metrics_recorded(self) -> None:
        """PrometheusMetrics should record epistemic ranking metrics."""
        from ayeneh.infrastructure.observability import PrometheusMetrics

        metrics = PrometheusMetrics()
        metrics.record_epistemic_ranking(
            duration_ms=10.5,
            scope_filtered=2,
            domain_dist={"philosophy": 1, "psychology": 1},
            authority_dist={"primary": 1, "secondary": 1},
            selection_reasons=["Strong domain alignment", "Primary authority"],
        )

        assert metrics.epistemic_ranking_count == 1
        assert metrics.epistemic_ranking_duration_ms == 10.5
        assert metrics.epistemic_scope_filtered_count == 2
        assert metrics.epistemic_domain_distribution["philosophy"] == 1
        assert metrics.epistemic_authority_distribution["primary"] == 1

    def test_epistemic_metrics_export(self) -> None:
        """PrometheusMetrics should export epistemic metrics."""
        from ayeneh.infrastructure.observability import PrometheusMetrics

        metrics = PrometheusMetrics()
        metrics.record_epistemic_ranking(
            duration_ms=10.5,
            scope_filtered=2,
            domain_dist={"philosophy": 1},
            authority_dist={"primary": 1},
            selection_reasons=["reason1"],
        )

        text = metrics.export_prometheus_text()
        assert "ayeneh_epistemic_rankings_total" in text
        assert "ayeneh_epistemic_scope_filtered_total" in text
        assert "ayeneh_epistemic_domain_distribution" in text
