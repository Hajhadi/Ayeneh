"""Tests for the retrieval subsystem (MEM-06)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from ayeneh.memo.retrieval.types import (
    DETECTED_INTENTS,
    RANKING_STRATEGIES,
    RETRIEVAL_STRATEGIES,
    AdaptiveRetrievalTrigger,
    EvidenceValidationResult,
    GraphExpansionResult,
    MultiHopRetrieval,
    RankingWeights,
    RetrievedItem,
    RetrievalRequest,
    RetrievalResult,
)
from ayeneh.memo.retrieval.engine import RetrievalEngine
from ayeneh.memo.retrieval.adaptive import (
    AdaptiveRetrievalManager,
    EvidenceValidator,
    MultiHopRetriever,
    RetrievalStrategySelector,
)


# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------


class TestRetrievalRequest:
    def test_creation(self) -> None:
        req = RetrievalRequest(
            request_identifier='req_1',
            conversation_context='What do I know about Python?',
        )
        assert req.request_identifier == 'req_1'
        assert req.detected_intent == 'recall'

    def test_has_focus(self) -> None:
        req = RetrievalRequest(
            request_identifier='req_1',
            current_cognitive_focus='learning Python',
        )
        assert req.has_focus

    def test_no_focus(self) -> None:
        req = RetrievalRequest(request_identifier='req_1')
        assert not req.has_focus

    def test_frozen(self) -> None:
        req = RetrievalRequest(request_identifier='req_1')
        with pytest.raises(AttributeError):
            req.request_identifier = 'req_2'


class TestRetrievedItem:
    def test_creation(self) -> None:
        item = RetrievedItem(
            memory_id='mem_1',
            memory_type='semantic',
        )
        assert item.memory_id == 'mem_1'
        assert item.final_score == 0.0

    def test_meets_threshold(self) -> None:
        item = RetrievedItem(
            memory_id='mem_1',
            memory_type='semantic',
            final_score=0.5,
        )
        assert item.meets_threshold

    def test_below_threshold(self) -> None:
        item = RetrievedItem(
            memory_id='mem_1',
            memory_type='semantic',
            final_score=0.2,
        )
        assert not item.meets_threshold


class TestRetrievalResult:
    def test_count(self) -> None:
        items = [
            RetrievedItem(memory_id='m1', memory_type='semantic'),
            RetrievedItem(memory_id='m2', memory_type='episodic'),
        ]
        result = RetrievalResult(
            request_id='req_1',
            retrieved_items=tuple(items),
        )
        assert result.count == 2

    def test_average_score_empty(self) -> None:
        result = RetrievalResult(request_id='req_1')
        assert result.average_score == 0.0

    def test_average_score(self) -> None:
        items = [
            RetrievedItem(memory_id='m1', memory_type='semantic', final_score=0.6),
            RetrievedItem(memory_id='m2', memory_type='episodic', final_score=0.8),
        ]
        result = RetrievalResult(
            request_id='req_1',
            retrieved_items=tuple(items),
        )
        assert abs(result.average_score - 0.7) < 1e-6


class TestMultiHopRetrieval:
    def test_creation(self) -> None:
        mh = MultiHopRetrieval(
            hop_id='mh_1',
            starting_memory_id='mem_1',
            current_memory_id='mem_1',
        )
        assert mh.hop_count == 0
        assert not mh.has_reached_limit

    def test_has_reached_limit(self) -> None:
        mh = MultiHopRetrieval(
            hop_id='mh_1',
            starting_memory_id='mem_1',
            current_memory_id='mem_3',
            hop_count=5,
            max_hops=5,
        )
        assert mh.has_reached_limit

    def test_accumulated_confidence(self) -> None:
        mh = MultiHopRetrieval(
            hop_id='mh_1',
            starting_memory_id='mem_1',
            current_memory_id='mem_2',
            hop_count=2,
            confidence_decay=0.9,
        )
        expected = 0.9 ** 2
        assert abs(mh.accumulated_confidence - expected) < 1e-6


class TestAdaptiveRetrievalTrigger:
    def test_creation(self) -> None:
        trigger = AdaptiveRetrievalTrigger(
            trigger_id='tr_1',
            trigger_reason='new_info',
            new_information='I learned about Rust',
        )
        assert trigger.trigger_id == 'tr_1'
        assert not trigger.resolved

    def test_is_high_priority(self) -> None:
        trigger = AdaptiveRetrievalTrigger(
            trigger_id='tr_1',
            trigger_reason='contradiction',
            new_information='Actually, that is wrong',
            priority=0.9,
        )
        assert trigger.is_high_priority

    def test_not_high_priority(self) -> None:
        trigger = AdaptiveRetrievalTrigger(
            trigger_id='tr_1',
            trigger_reason='minor',
            new_information='minor detail',
            priority=0.3,
        )
        assert not trigger.is_high_priority


class TestRankingWeights:
    def test_creation(self) -> None:
        weights = RankingWeights()
        assert weights.relevance == 0.4

    def test_normalize(self) -> None:
        weights = RankingWeights(relevance=2.0, recency=1.0, importance=1.0, confidence=1.0)
        normalized = weights.normalize()
        total = normalized.relevance + normalized.recency + normalized.importance + normalized.confidence
        assert abs(total - 1.0) < 1e-6

    def test_normalize_zero(self) -> None:
        weights = RankingWeights(relevance=0.0, recency=0.0, importance=0.0, confidence=0.0)
        normalized = weights.normalize()
        assert normalized.relevance == 0.25  # defaults


class TestGraphExpansionResult:
    def test_expansion_size(self) -> None:
        result = GraphExpansionResult(
            seed_id='mem_1',
            expanded_ids=('mem_2', 'mem_3', 'mem_4'),
        )
        assert result.expansion_size == 3


class TestEvidenceValidationResult:
    def test_support_ratio(self) -> None:
        result = EvidenceValidationResult(
            memory_id='mem_1',
            evidence_count=10,
            supporting_count=8,
            contradicting_count=2,
        )
        assert abs(result.support_ratio - 0.8) < 1e-6

    def test_support_ratio_empty(self) -> None:
        result = EvidenceValidationResult(memory_id='mem_1')
        assert result.support_ratio == 0.0


class TestConstants:
    def test_retrieval_strategies(self) -> None:
        assert 'evidence_first' in RETRIEVAL_STRATEGIES
        assert 'semantic_first' in RETRIEVAL_STRATEGIES
        assert 'episode_first' in RETRIEVAL_STRATEGIES
        assert 'identity_first' in RETRIEVAL_STRATEGIES
        assert 'narrative_first' in RETRIEVAL_STRATEGIES
        assert 'trajectory_first' in RETRIEVAL_STRATEGIES
        assert len(RETRIEVAL_STRATEGIES) == 7

    def test_detected_intents(self) -> None:
        assert 'recall' in DETECTED_INTENTS
        assert 'explain' in DETECTED_INTENTS
        assert 'plan' in DETECTED_INTENTS
        assert len(DETECTED_INTENTS) == 8

    def test_ranking_strategies(self) -> None:
        assert 'relevance' in RANKING_STRATEGIES
        assert 'composite' in RANKING_STRATEGIES
        assert len(RANKING_STRATEGIES) == 5


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestRetrievalEngine:
    def test_creation(self) -> None:
        engine = RetrievalEngine()
        assert engine._max_size == 20

    def test_retrieve_empty(self) -> None:
        engine = RetrievalEngine()
        result = engine.retrieve('test query')
        assert result.count == 0

    def test_retrieve_with_semantic(self) -> None:
        engine = RetrievalEngine()
        memories = [
            {'id': 'sem_1', 'content': 'I love Python programming', 'confidence': 0.8},
            {'id': 'sem_2', 'content': 'Java is also useful', 'confidence': 0.6},
        ]
        result = engine.retrieve('Python programming', semantic_memories=memories)
        assert result.count >= 1

    def test_retrieve_with_episodes(self) -> None:
        engine = RetrievalEngine()
        episodes = [
            {'id': 'ep_1', 'summary': 'Learned Python basics', 'confidence': 0.9, 'importance': 0.7},
            {'id': 'ep_2', 'summary': 'Built a web app', 'confidence': 0.8, 'importance': 0.6},
        ]
        result = engine.retrieve('Python basics', episodic_memories=episodes)
        assert result.count >= 1

    def test_retrieve_with_all_sources(self) -> None:
        engine = RetrievalEngine()
        semantic = [
            {'id': 'sem_1', 'content': 'Python is great', 'confidence': 0.8},
        ]
        episodes = [
            {'id': 'ep_1', 'summary': 'Learned Python', 'confidence': 0.9, 'importance': 0.7},
        ]
        result = engine.retrieve(
            'Python',
            semantic_memories=semantic,
            episodic_memories=episodes,
        )
        assert result.count >= 1

    def test_retrieve_max_results(self) -> None:
        engine = RetrievalEngine(max_retrieval_size=3)
        memories = [
            {'id': f'sem_{i}', 'content': f'item {i}', 'confidence': 0.8}
            for i in range(10)
        ]
        result = engine.retrieve('item', max_results=3, semantic_memories=memories)
        assert result.count <= 3

    def test_retrieve_respects_confidence_threshold(self) -> None:
        engine = RetrievalEngine(confidence_threshold=0.9)
        memories = [
            {'id': 'sem_1', 'content': 'low confidence item', 'confidence': 0.3},
        ]
        result = engine.retrieve('low confidence', semantic_memories=memories)
        assert result.count == 0

    def test_run_pipeline_basic(self) -> None:
        engine = RetrievalEngine()
        request = RetrievalRequest(
            request_identifier='req_1',
            conversation_context='What do I know?',
        )
        result = engine.run_pipeline(request)
        assert result.result is not None
        assert result.result.request_id == 'req_1'

    def test_run_pipeline_with_focus(self) -> None:
        engine = RetrievalEngine()
        request = RetrievalRequest(
            request_identifier='req_2',
            conversation_context='Tell me about my goals',
            current_cognitive_focus='goal tracking',
            relevant_projects=('proj_1',),
        )
        result = engine.run_pipeline(request)
        assert result.result is not None

    def test_retrieval_history(self) -> None:
        engine = RetrievalEngine()
        engine.retrieve('query 1')
        engine.retrieve('query 2')
        history = engine.get_retrieval_history()
        assert len(history) == 2

    def test_intent_detection_explain(self) -> None:
        engine = RetrievalEngine()
        result = engine.retrieve('Why did I choose Python?')
        assert result.request_id.startswith('req_')

    def test_intent_detection_plan(self) -> None:
        engine = RetrievalEngine()
        result = engine.retrieve('What should I do next?')
        assert result.request_id.startswith('req_')

    def test_intent_detection_reflect(self) -> None:
        engine = RetrievalEngine()
        result = engine.retrieve('Reflect on my learning journey')
        assert result.request_id.startswith('req_')

    def test_graph_expansion(self) -> None:
        engine = RetrievalEngine()
        kg = {
            'mem_1': ['mem_2', 'mem_3'],
            'mem_2': ['mem_4'],
        }
        memories = [
            {'id': 'mem_1', 'content': 'connected memory', 'confidence': 0.8},
        ]
        request = RetrievalRequest(
            request_identifier='req_1',
            conversation_context='test',
        )
        result = engine.run_pipeline(
            request,
            semantic_memories=memories,
            knowledge_graph=kg,
        )
        assert result.result is not None


# ---------------------------------------------------------------------------
# Adaptive retrieval tests
# ---------------------------------------------------------------------------


class TestMultiHopRetriever:
    def test_creation(self) -> None:
        retriever = MultiHopRetriever()
        assert retriever._max_hops == 5

    def test_retrieve_empty_graph(self) -> None:
        retriever = MultiHopRetriever()
        items, multi_hop = retriever.retrieve(
            ('mem_1',), {}, {}
        )
        assert len(items) == 0
        assert multi_hop.hop_count == 0

    def test_retrieve_single_hop(self) -> None:
        retriever = MultiHopRetriever(max_hops=2)
        kg = {'mem_1': ['mem_2', 'mem_3']}
        store = {
            'mem_2': {'type': 'semantic', 'content': 'connected', 'confidence': 0.8},
            'mem_3': {'type': 'episodic', 'content': 'also connected', 'confidence': 0.7},
        }
        items, multi_hop = retriever.retrieve(('mem_1',), kg, store)
        assert len(items) == 2
        assert multi_hop.hop_count == 1

    def test_retrieve_multi_hop(self) -> None:
        retriever = MultiHopRetriever(max_hops=3)
        kg = {
            'mem_1': ['mem_2'],
            'mem_2': ['mem_3'],
            'mem_3': ['mem_4'],
        }
        store = {
            'mem_2': {'content': 'hop1', 'confidence': 0.8},
            'mem_3': {'content': 'hop2', 'confidence': 0.7},
            'mem_4': {'content': 'hop3', 'confidence': 0.6},
        }
        items, multi_hop = retriever.retrieve(('mem_1',), kg, store)
        assert len(items) == 3
        assert multi_hop.hop_count == 3

    def test_retrieve_respects_confidence_decay(self) -> None:
        retriever = MultiHopRetriever(max_hops=10, confidence_decay=0.5, min_confidence=0.3)
        kg = {
            'mem_1': ['mem_2'],
            'mem_2': ['mem_3'],
            'mem_3': ['mem_4'],
            'mem_4': ['mem_5'],
        }
        store = {f'mem_{i}': {'content': f'item {i}', 'confidence': 0.8} for i in range(2, 6)}
        items, multi_hop = retriever.retrieve(('mem_1',), kg, store)
        # Should stop early due to confidence decay
        assert multi_hop.hop_count < 10


class TestAdaptiveRetrievalManager:
    def test_creation(self) -> None:
        mgr = AdaptiveRetrievalManager()
        assert len(mgr.get_pending_triggers()) == 0

    def test_evaluate_triggers_new_entities(self) -> None:
        mgr = AdaptiveRetrievalManager()
        current = [
            RetrievedItem(memory_id='m1', memory_type='semantic', content='hello world'),
        ]
        triggers = mgr.evaluate_triggers('Python is amazing', current)
        assert len(triggers) >= 1
        assert triggers[0].trigger_reason == 'new_entities_detected'

    def test_evaluate_triggers_contradiction(self) -> None:
        mgr = AdaptiveRetrievalManager()
        current = [
            RetrievedItem(memory_id='m1', memory_type='semantic', content='hello world'),
        ]
        triggers = mgr.evaluate_triggers('But actually that is wrong', current)
        assert any(t.trigger_reason == 'contradiction_detected' for t in triggers)

    def test_evaluate_triggers_question(self) -> None:
        mgr = AdaptiveRetrievalManager()
        current = []  # Few results
        triggers = mgr.evaluate_triggers('Why did this happen?', current)
        assert any(t.trigger_reason == 'insufficient_context_for_explanation' for t in triggers)

    def test_resolve_trigger(self) -> None:
        mgr = AdaptiveRetrievalManager()
        triggers = mgr.evaluate_triggers(
            'New info about Python',
            [RetrievedItem(memory_id='m1', memory_type='semantic', content='hello')],
        )
        if triggers:
            assert mgr.resolve_trigger(triggers[0].trigger_id)
            assert len(mgr.get_pending_triggers()) == 0

    def test_resolve_nonexistent_trigger(self) -> None:
        mgr = AdaptiveRetrievalManager()
        assert not mgr.resolve_trigger('nonexistent')

    def test_trigger_history(self) -> None:
        mgr = AdaptiveRetrievalManager()
        mgr.evaluate_triggers(
            'Python is great',
            [RetrievedItem(memory_id='m1', memory_type='semantic', content='hello')],
        )
        assert len(mgr.get_trigger_history()) >= 1


class TestRetrievalStrategySelector:
    def test_creation(self) -> None:
        selector = RetrievalStrategySelector()
        scores = selector.get_strategy_scores()
        assert 'evidence_first' in scores

    def test_select_by_intent(self) -> None:
        selector = RetrievalStrategySelector()
        request = RetrievalRequest(
            request_identifier='req_1',
            conversation_context='Why did I do this?',
            detected_intent='explain',
        )
        strategy = selector.select(request)
        assert strategy == 'evidence_first'

    def test_select_by_explicit_strategy(self) -> None:
        selector = RetrievalStrategySelector()
        request = RetrievalRequest(
            request_identifier='req_1',
            conversation_context='test',
            ranking_strategy='episode_first',
        )
        strategy = selector.select(request)
        assert strategy == 'episode_first'

    def test_select_by_focus(self) -> None:
        selector = RetrievalStrategySelector()
        request = RetrievalRequest(
            request_identifier='req_1',
            conversation_context='test',
            current_cognitive_focus='learning',
        )
        strategy = selector.select(request)
        assert strategy == 'identity_first'

    def test_select_by_episodes(self) -> None:
        selector = RetrievalStrategySelector()
        request = RetrievalRequest(
            request_identifier='req_1',
            conversation_context='test',
            relevant_episodes=('ep_1',),
        )
        strategy = selector.select(request)
        assert strategy == 'episode_first'

    def test_select_default(self) -> None:
        selector = RetrievalStrategySelector()
        request = RetrievalRequest(
            request_identifier='req_1',
            conversation_context='test',
        )
        strategy = selector.select(request)
        assert strategy in RETRIEVAL_STRATEGIES

    def test_update_scores(self) -> None:
        selector = RetrievalStrategySelector()
        initial = selector.get_strategy_scores()['evidence_first']
        selector.update_scores('evidence_first', True)
        assert selector.get_strategy_scores()['evidence_first'] > initial

    def test_update_scores_failure(self) -> None:
        selector = RetrievalStrategySelector()
        initial = selector.get_strategy_scores()['semantic_first']
        selector.update_scores('semantic_first', False)
        assert selector.get_strategy_scores()['semantic_first'] < initial


class TestEvidenceValidator:
    def test_creation(self) -> None:
        validator = EvidenceValidator()
        assert validator._min_support_ratio == 0.5

    def test_validate_with_evidence(self) -> None:
        validator = EvidenceValidator()
        items = [
            RetrievedItem(memory_id='mem_1', memory_type='semantic', confidence_score=0.8),
        ]
        evidence = {
            'mem_1': [
                {'supports': True},
                {'supports': True},
                {'supports': False},
            ],
        }
        validated, results = validator.validate(items, evidence)
        assert len(results) == 1
        assert results[0].support_ratio == 2 / 3

    def test_validate_no_evidence(self) -> None:
        validator = EvidenceValidator()
        items = [
            RetrievedItem(memory_id='mem_1', memory_type='semantic', confidence_score=0.3),
        ]
        validated, results = validator.validate(items, {})
        assert len(results) == 1
        assert not results[0].is_valid

    def test_validate_high_confidence_bypasses(self) -> None:
        validator = EvidenceValidator(min_support_ratio=0.9)
        items = [
            RetrievedItem(memory_id='mem_1', memory_type='semantic', confidence_score=0.8),
        ]
        validated, results = validator.validate(items, {})
        assert results[0].is_valid  # High confidence bypasses evidence check
