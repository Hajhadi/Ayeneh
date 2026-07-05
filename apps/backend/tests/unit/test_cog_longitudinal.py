"""Longitudinal tests — behavior across multiple sessions.

Tests temporal evolution of beliefs, narratives, identity, and the full
cognitive pipeline when evidence arrives incrementally over time.
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class _FakeEvidence:
    """Lightweight object with attributes for engines that use getattr()."""
    identifier: str = ''
    original_text: str = ''
    normalized_text: str = ''
    category: str = ''


def _ev(identifier: str, text: str, category: str = 'self_report') -> _FakeEvidence:
    """Shorthand to build a _FakeEvidence for narrative extraction tests."""
    return _FakeEvidence(identifier=identifier, original_text=text, normalized_text=text, category=category)

def _evidence_to_dicts(evidence_objects: tuple) -> list[dict]:
    """Convert EvidenceObject tuple to list of dicts for downstream engines."""
    return [
        {
            'identifier': ev.identifier,
            'type': ev.category,
            'category': ev.category,
            'text': ev.original_text,
            'original_text': ev.original_text,
            'normalized_text': ev.normalized_text,
            'speaker': ev.speaker,
            'confidence': ev.confidence,
        }
        for ev in evidence_objects
    ]


def _narrative_to_dicts(narratives: tuple) -> list[dict]:
    """Convert NarrativeObject tuple to list of dicts for downstream engines."""
    return [
        {
            'identifier': n.identifier,
            'type': n.narrative_type,
            'category': n.narrative_type,
            'text': n.summary,
            'title': n.title,
            'statement': n.summary,
            'template': n.template,
            'influence_score': n.influence_score,
            'confidence': n.confidence,
            'supporting_evidence': n.supporting_evidence,
        }
        for n in narratives
    ]


# ===========================================================================
# Longitudinal Belief Tests (COG-06)
# ===========================================================================


class TestLongitudinalBeliefs:
    """Test belief evolution across multiple evidence batches."""

    def test_belief_strengthens_with_evidence(self):
        """Repeated evidence about the same theme strengthens beliefs."""
        from ayeneh.cog.belief.modeling import BeliefModelingEngine

        # Session 1: single piece of evidence
        session1 = [
            {'identifier': 'ev-s1', 'type': 'self_report', 'text':
             'I deeply believe that anxiety controls my life'},
        ]
        # Session 2: add more evidence
        session2 = session1 + [
            {'identifier': 'ev-s2', 'type': 'self_report', 'text':
             'I believe that anxiety is always present'},
        ]
        # Session 3: even more evidence
        session3 = session2 + [
            {'identifier': 'ev-s3', 'type': 'self_report', 'text':
             'I believe that anxiety never goes away'},
        ]

        r1 = BeliefModelingEngine().process(session1)
        r2 = BeliefModelingEngine().process(session2)
        r3 = BeliefModelingEngine().process(session3)

        if r1.total_extracted > 0 and r3.total_extracted > 0:
            # More evidence → higher max confidence across beliefs
            max_conf_1 = max(b.confidence for b in r1.beliefs)
            max_conf_3 = max(b.confidence for b in r3.beliefs)
            assert max_conf_3 >= max_conf_1

    def test_belief_count_increases_with_diverse_evidence(self):
        """More diverse evidence topics produce more distinct beliefs."""
        from ayeneh.cog.belief.modeling import BeliefModelingEngine

        session1 = [
            {'identifier': 'ev-1', 'type': 'self_report', 'text':
             'I believe that honesty matters'},
        ]
        session2 = session1 + [
            {'identifier': 'ev-2', 'type': 'self_report', 'text':
             'I think that courage is essential'},
            {'identifier': 'ev-3', 'type': 'self_report', 'text':
             'I believe that wisdom comes from experience'},
        ]
        r1 = BeliefModelingEngine().process(session1)
        r2 = BeliefModelingEngine().process(session2)
        assert r2.total_extracted >= r1.total_extracted

    def test_belief_network_grows(self):
        """Belief network edges grow as more same-category beliefs appear."""
        from ayeneh.cog.belief.modeling import BeliefModelingEngine

        session1 = [
            {'identifier': 'ev-1', 'type': 'self_report', 'text':
             'I believe in the power of kindness'},
        ]
        session2 = session1 + [
            {'identifier': 'ev-2', 'type': 'self_report', 'text':
             'I believe that compassion heals'},
            {'identifier': 'ev-3', 'type': 'self_report', 'text':
             'I think empathy is crucial'},
        ]
        r1 = BeliefModelingEngine().process(session1)
        r2 = BeliefModelingEngine().process(session2)
        assert len(r2.network.edges) >= len(r1.network.edges)

    def test_belief_metrics_stable_across_sessions(self):
        """Same evidence across sessions produces consistent metrics."""
        from ayeneh.cog.belief.modeling import BeliefModelingEngine

        evidence = [
            {'identifier': 'ev-1', 'type': 'self_report', 'text':
             'I believe that integrity is fundamental'},
        ]
        r1 = BeliefModelingEngine().process(evidence)
        r2 = BeliefModelingEngine().process(evidence)
        if r1.total_extracted > 0 and r2.total_extracted > 0:
            b1, b2 = r1.beliefs[0], r2.beliefs[0]
            assert abs(b1.confidence - b2.confidence) < 0.001
            assert abs(b1.strength - b2.strength) < 0.001

    def test_belief_by_category_tracking(self):
        """by_category dict accurately tracks belief counts per category."""
        from ayeneh.cog.belief.modeling import BeliefModelingEngine

        evidence = [
            {'identifier': 'ev-1', 'type': 'self_report', 'text':
             'I believe that self-awareness is important'},
            {'identifier': 'ev-2', 'type': 'value_statement', 'text':
             'I believe that honesty is a moral duty'},
        ]
        result = BeliefModelingEngine().process(evidence)
        total_from_cats = sum(result.by_category.values())
        assert total_from_cats == result.total_extracted


# ===========================================================================
# Longitudinal Narrative Tests (COG-05)
# ===========================================================================


class TestLongitudinalNarratives:
    """Test narrative evolution across multiple evidence batches.

    The NarrativeExtractionEngine uses ``getattr(ev, 'original_text', '')``
    so evidence must be objects with attributes, not plain dicts.
    """

    def test_narrative_lifecycle_advances(self):
        """Narrative lifecycle advances from candidate to provisional to validated."""
        from ayeneh.cog.narrative.extraction import NarrativeExtractionEngine

        batch1 = [_ev('ev-1', 'I failed at the project again')]
        batch2 = batch1 + [_ev('ev-2', 'The project failed completely')]
        batch3 = batch2 + [_ev('ev-3', 'I could not succeed at anything')]

        r1 = NarrativeExtractionEngine().process(batch1)
        r2 = NarrativeExtractionEngine().process(batch2)
        r3 = NarrativeExtractionEngine().process(batch3)

        states1 = {n.lifecycle_state for n in r1.narratives}
        states2 = {n.lifecycle_state for n in r2.narratives}
        states3 = {n.lifecycle_state for n in r3.narratives}

        assert 'candidate' in states1
        assert 'provisional' in states2 or 'validated' in states3
        assert 'validated' in states3

    def test_narrative_confidence_grows(self):
        """Narrative confidence increases with more supporting evidence."""
        from ayeneh.cog.narrative.extraction import NarrativeExtractionEngine

        few = [
            _ev('ev-1', 'I failed at the exam'),
            _ev('ev-2', 'I failed the test as well'),
        ]
        many = few + [
            _ev('ev-3', 'I failed the interview too'),
            _ev('ev-4', 'I failed at the project deadline'),
        ]
        r_few = NarrativeExtractionEngine().process(few)
        r_many = NarrativeExtractionEngine().process(many)

        if r_few.narratives and r_many.narratives:
            max_conf_few = max(n.confidence for n in r_few.narratives)
            max_conf_many = max(n.confidence for n in r_many.narratives)
            assert max_conf_many >= max_conf_few

    def test_narrative_influence_grows(self):
        """Narrative influence score grows as evidence accumulates."""
        from ayeneh.cog.narrative.extraction import NarrativeExtractionEngine

        batch1 = [
            _ev('ev-1', 'I always fail at everything'),
            _ev('ev-2', 'Nothing works out for me'),
        ]
        batch2 = batch1 + [
            _ev('ev-3', 'I fail every single time'),
            _ev('ev-4', 'Failure follows me everywhere'),
        ]
        r1 = NarrativeExtractionEngine().process(batch1)
        r2 = NarrativeExtractionEngine().process(batch2)

        if r1.narratives and r2.narratives:
            max_inf_1 = max(n.influence_score for n in r1.narratives)
            max_inf_2 = max(n.influence_score for n in r2.narratives)
            assert max_inf_2 >= max_inf_1

    def test_narrative_network_expands(self):
        """Narrative network nodes and edges expand with more evidence."""
        from ayeneh.cog.narrative.extraction import NarrativeExtractionEngine

        batch1 = [
            _ev('ev-1', 'I failed at the project'),
            _ev('ev-2', 'I could not finish the work'),
        ]
        batch2 = batch1 + [
            _ev('ev-3', 'I learned from the failure and grew'),
            _ev('ev-4', 'I overcame the challenge eventually'),
        ]
        r1 = NarrativeExtractionEngine().process(batch1)
        r2 = NarrativeExtractionEngine().process(batch2)

        assert len(r2.network.nodes) >= len(r1.network.nodes)

    def test_narrative_by_category_accuracy(self):
        """by_category accurately reflects narrative distribution."""
        from ayeneh.cog.narrative.extraction import NarrativeExtractionEngine

        evidence = [
            _ev('ev-1', 'I failed at everything I tried'),
            _ev('ev-2', 'I never succeeded at anything'),
            _ev('ev-3', 'I failed once more at the task'),
        ]
        result = NarrativeExtractionEngine().process(evidence)
        total_from_cats = sum(result.by_category.values())
        assert total_from_cats == result.total_extracted


# ===========================================================================
# Longitudinal Identity Tests (COG-09)
# ===========================================================================


class TestLongitudinalIdentity:
    """Test identity evolution across multiple evidence batches."""

    def test_identity_components_grow(self):
        """More identity-relevant evidence produces more components."""
        from ayeneh.cog.identity.graph import IdentityGraphEngine

        batch1 = [
            {'id': 'ev-1', 'text': 'I am a creative person',
             'category': 'identity_statement'},
        ]
        batch2 = batch1 + [
            {'id': 'ev-2', 'text': 'I am the kind of person who never gives up',
             'category': 'self_report'},
            {'id': 'ev-3', 'text': 'I am a leader at heart',
             'category': 'identity_statement'},
        ]
        r1 = IdentityGraphEngine().process(batch1)
        r2 = IdentityGraphEngine().process(batch2)
        assert r2.total_components >= r1.total_components

    def test_identity_coherence_with_growing_cross_references(self):
        """Pipeline completes with cross-references and produces valid coherence."""
        from ayeneh.cog.identity.graph import IdentityGraphEngine

        evidence = [
            {'id': 'ev-1', 'text': 'I am a compassionate leader',
             'category': 'identity_statement'},
            {'id': 'ev-2', 'text': 'I am the kind of person who cares',
             'category': 'self_report'},
        ]
        r_alone = IdentityGraphEngine().process(evidence)
        r_with_refs = IdentityGraphEngine().process(
            evidence, beliefs=['b1', 'b2'], values=['v1'],
            goals=['g1'], narratives=['n1'],
        )
        # Both produce valid results with non-negative coherence
        assert r_alone.coherence_score >= 0.0
        assert r_with_refs.coherence_score >= 0.0
        assert r_with_refs.total_components == r_alone.total_components

    def test_observer_self_growth(self):
        """Observer-self capacity grows with meta-cognitive evidence."""
        from ayeneh.cog.identity.graph import IdentityGraphEngine

        batch1 = [
            {'id': 'ev-1', 'text': 'I am a thoughtful person',
             'category': 'identity_statement'},
        ]
        batch2 = batch1 + [
            {'id': 'ev-2', 'text': 'I notice that I tend to overthink',
             'category': 'meta_cognitive_report'},
            {'id': 'ev-3', 'text': 'I realize that my thoughts are just thoughts',
             'category': 'meta_cognitive_report'},
        ]
        r1 = IdentityGraphEngine().process(batch1)
        r2 = IdentityGraphEngine().process(batch2)
        assert (r2.observer_self.de_identification_level
                >= r1.observer_self.de_identification_level)
        assert r2.observer_self.observation_episodes >= r1.observer_self.observation_episodes

    def test_lifecycle_summary_tracking(self):
        """Lifecycle summary accurately counts component states."""
        from ayeneh.cog.identity.graph import IdentityGraphEngine

        evidence = [
            {'id': 'ev-1', 'text': 'I am a creative person',
             'category': 'identity_statement'},
            {'id': 'ev-2', 'text': 'I am the kind of person who perseveres',
             'category': 'self_report'},
        ]
        result = IdentityGraphEngine().process(evidence)
        total_from_summary = sum(result.lifecycle_summary.values())
        assert total_from_summary == result.total_components

    def test_identity_stability_grows_with_evidence(self):
        """Identity component stability increases with more supporting evidence."""
        from ayeneh.cog.identity.graph import IdentityGraphEngine

        batch1 = [
            {'id': 'ev-1', 'text': 'I am a resilient person',
             'category': 'identity_statement'},
        ]
        batch2 = batch1 + [
            {'id': 'ev-2', 'text': 'I never give up no matter what',
             'category': 'self_report'},
            {'id': 'ev-3', 'text': 'I am the kind of person who bounces back',
             'category': 'identity_statement'},
        ]
        r1 = IdentityGraphEngine().process(batch1)
        r2 = IdentityGraphEngine().process(batch2)

        if r1.components and r2.components:
            # Components in batch2 should have equal or higher stability
            max_stab_1 = max(c.stability for c in r1.components.values())
            max_stab_2 = max(c.stability for c in r2.components.values())
            assert max_stab_2 >= max_stab_1


# ===========================================================================
# Longitudinal Reality Calibration Tests (COG-15)
# ===========================================================================


class TestLongitudinalRealityCalibration:
    """Test reality calibration evolution across sessions."""

    def test_awakening_index_grows_with_meta_evidence(self):
        """More meta-cognitive evidence increases the awakening index."""
        from ayeneh.cog.reality_calibration.engine import RealityCalibrationEngine

        batch1 = [
            {'identifier': 'ev-1', 'type': 'observation',
             'text': 'I noticed a pattern in my behavior'},
        ]
        batch2 = batch1 + [
            {'identifier': 'ev-2', 'type': 'meta_cognitive_report',
             'text': 'I realize that my thoughts create my reality'},
            {'identifier': 'ev-3', 'type': 'meta_cognitive_report',
             'text': 'I am aware that I tend to catastrophize'},
        ]
        r1 = RealityCalibrationEngine().process(batch1)
        r2 = RealityCalibrationEngine().process(batch2)
        assert r2.awakening_index >= r1.awakening_index

    def test_calibration_count_matches_evidence(self):
        """Each evidence item produces exactly one calibration."""
        from ayeneh.cog.reality_calibration.engine import RealityCalibrationEngine

        evidence = [
            {'identifier': f'ev-{i}', 'type': 'self_report',
             'text': f'I feel anxious about item {i}'}
            for i in range(5)
        ]
        result = RealityCalibrationEngine().process(evidence)
        assert len(result.calibrations) == 5

    def test_mental_stories_grow_with_narratives(self):
        """More narratives produce more mental stories."""
        from ayeneh.cog.reality_calibration.engine import RealityCalibrationEngine

        evidence = [{'identifier': 'ev-1', 'type': 'observation',
                     'text': 'Something happened'}]
        narr1 = [{'identifier': 'narr-1', 'text': 'I always fail',
                   'summary': 'I always fail at work'}]
        narr2 = narr1 + [
            {'identifier': 'narr-2', 'text': 'Nobody understands me',
             'summary': 'People never understand my perspective'},
        ]
        r1 = RealityCalibrationEngine().process(evidence, narratives=narr1)
        r2 = RealityCalibrationEngine().process(evidence, narratives=narr2)
        assert len(r2.mental_stories) >= len(r1.mental_stories)

    def test_narrative_gravity_grows(self):
        """Narrative gravity increases with more evidence grounding."""
        from ayeneh.cog.reality_calibration.engine import RealityCalibrationEngine

        evidence = [
            {'identifier': 'ev-1', 'type': 'observation',
             'text': 'I failed at the project'},
        ]
        narr_no_ev = [{'identifier': 'narr-1', 'text': 'I always fail',
                        'summary': 'I always fail at everything',
                        'influence_score': 0.5, 'confidence': 0.5}]
        narr_with_ev = [{'identifier': 'narr-1', 'text': 'I always fail',
                          'summary': 'I always fail at everything',
                          'influence_score': 0.5, 'confidence': 0.5,
                          'supporting_evidence': ('ev-1',)}]

        r_no = RealityCalibrationEngine().process(evidence, narratives=narr_no_ev)
        r_with = RealityCalibrationEngine().process(evidence, narratives=narr_with_ev)
        g_no = r_no.narrative_gravities.get('narr-1', 0)
        g_with = r_with.narrative_gravities.get('narr-1', 0)
        assert g_with >= g_no


# ===========================================================================
# Longitudinal Cross-Module Tests
# ===========================================================================


class TestLongitudinalCrossModule:
    """Test end-to-end pipeline across simulated sessions."""

    def test_incremental_pipeline_growth(self):
        """Pipeline produces more output as evidence accumulates."""
        from ayeneh.cog.conversation.understanding import (
            ConversationUnderstandingEngine,
        )
        from ayeneh.cog.evidence.extraction import EvidenceExtractionEngine
        from ayeneh.cog.narrative.extraction import NarrativeExtractionEngine
        from ayeneh.cog.belief.modeling import BeliefModelingEngine

        # Session 1: minimal evidence
        session1_msgs = [
            {'role': 'user', 'content': 'I believe that growth is important.'},
        ]
        # Session 2: accumulated evidence
        session2_msgs = session1_msgs + [
            {'role': 'user', 'content': 'I always learn from my failures.'},
            {'role': 'user', 'content': 'I think that persistence pays off.'},
        ]

        conv = ConversationUnderstandingEngine()
        ev_eng = EvidenceExtractionEngine()
        nar_eng = NarrativeExtractionEngine()
        bel_eng = BeliefModelingEngine()

        # Session 1 pipeline
        u1 = conv.process('s1', session1_msgs)
        e1 = ev_eng.process(u1)
        # NarrativeExtractionEngine needs attribute objects
        eo1 = [_ev(ev.identifier, ev.original_text, ev.category)
                for ev in e1.evidence_objects]
        ed1 = _evidence_to_dicts(e1.evidence_objects)
        n1 = nar_eng.process(eo1)
        b1 = bel_eng.process(ed1, narratives=_narrative_to_dicts(n1.narratives))

        # Session 2 pipeline
        u2 = conv.process('s2', session2_msgs)
        e2 = ev_eng.process(u2)
        eo2 = [_ev(ev.identifier, ev.original_text, ev.category)
                for ev in e2.evidence_objects]
        ed2 = _evidence_to_dicts(e2.evidence_objects)
        n2 = nar_eng.process(eo2)
        b2 = bel_eng.process(ed2, narratives=_narrative_to_dicts(n2.narratives))

        # Session 2 should have more evidence
        assert e2.total_extracted >= e1.total_extracted
        # More evidence should produce equal or more beliefs
        assert b2.total_extracted >= b1.total_extracted

    def test_full_pipeline_reflects_belief_narrative_interaction(self):
        """Full pipeline: beliefs and narratives feed into reflection."""
        from ayeneh.cog.conversation.understanding import (
            ConversationUnderstandingEngine,
        )
        from ayeneh.cog.evidence.extraction import EvidenceExtractionEngine
        from ayeneh.cog.narrative.extraction import NarrativeExtractionEngine
        from ayeneh.cog.belief.modeling import BeliefModelingEngine
        from ayeneh.cog.reflection.engine import ReflectionEngine

        messages = [
            {'role': 'user', 'content': 'I always fail at everything.'},
            {'role': 'user', 'content': 'I believe that I am not capable.'},
            {'role': 'user', 'content': 'Nothing ever works out for me.'},
        ]

        conv = ConversationUnderstandingEngine()
        understanding = conv.process('reflect-e2e', messages)
        ev = EvidenceExtractionEngine()
        ev_result = ev.process(understanding)

        # NarrativeExtractionEngine needs attribute objects
        ev_objs = [_ev(ev.identifier, ev.original_text, ev.category)
                    for ev in ev_result.evidence_objects]
        ev_dicts = _evidence_to_dicts(ev_result.evidence_objects)

        nar = NarrativeExtractionEngine()
        nar_result = nar.process(ev_objs)
        nar_dicts = _narrative_to_dicts(nar_result.narratives)

        bel = BeliefModelingEngine()
        bel_result = bel.process(ev_dicts, narratives=nar_dicts)
        bel_dicts = [
            {'id': b.identifier, 'statement': b.belief_statement,
             'confidence': b.confidence}
            for b in bel_result.beliefs
        ]

        ref = ReflectionEngine()
        ref_result = ref.process(
            ev_dicts, narratives=nar_dicts, beliefs=bel_dicts,
        )

        assert ref_result.total_extracted > 0

    def test_determinism_across_sessions(self):
        """Same session data processed twice gives identical results."""
        from ayeneh.cog.conversation.understanding import (
            ConversationUnderstandingEngine,
        )
        from ayeneh.cog.evidence.extraction import EvidenceExtractionEngine

        messages = [
            {'role': 'user', 'content': 'I believe that growth comes from failure.'},
            {'role': 'user', 'content': 'I want to become a better person.'},
        ]

        def run_pipeline():
            conv = ConversationUnderstandingEngine()
            u = conv.process('det', messages)
            ev = EvidenceExtractionEngine()
            return ev.process(u)

        r1 = run_pipeline()
        r2 = run_pipeline()
        assert r1.total_extracted == r2.total_extracted
        assert len(r1.evidence_objects) == len(r2.evidence_objects)
        for o1, o2 in zip(r1.evidence_objects, r2.evidence_objects):
            assert o1.category == o2.category
            assert o1.epistemic_classification == o2.epistemic_classification

    def test_pipeline_with_persian_across_sessions(self):
        """Persian conversation produces consistent results across runs."""
        from ayeneh.cog.conversation.understanding import (
            ConversationUnderstandingEngine,
        )
        from ayeneh.cog.evidence.extraction import EvidenceExtractionEngine

        messages = [
            {'role': 'user', 'content': 'من همیشه فکر می‌کنم که نمی‌تونم'},
            {'role': 'user', 'content': 'هیچوقت چیزی درست نمی‌شه'},
        ]

        conv1 = ConversationUnderstandingEngine()
        conv2 = ConversationUnderstandingEngine()
        u1 = conv1.process('fa-1', messages, language='fa')
        u2 = conv2.process('fa-2', messages, language='fa')
        assert len(u1.segments) == len(u2.segments)

        ev1 = EvidenceExtractionEngine().process(u1)
        ev2 = EvidenceExtractionEngine().process(u2)
        assert ev1.total_extracted == ev2.total_extracted
