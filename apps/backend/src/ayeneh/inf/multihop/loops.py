"""INF-03 Narrative Loop Detector.

Detects self-reinforcing loops in reasoning:
- Observation → Interpretation → Narrative → Behavior →
  Selective Attention → New Observation → Strengthened Narrative
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.inf.multihop.types import (
    LOOP_TYPES,
    NarrativeLoop,
)

logger = structlog.get_logger(__name__)


class NarrativeLoopDetector:
    """Detects self-reinforcing narrative loops (INF-03 helper).

    Analyzes reasoning hops and observations to identify loops where:
    - An observation leads to an interpretation
    - The interpretation reinforces a narrative
    - The narrative influences behavior
    - The behavior creates selective attention
    - Selective attention produces new observations
    - These observations further strengthen the original narrative
    """

    def detect_loops(
        self,
        hops: list[dict[str, Any]],
        observations: list[dict[str, Any]],
    ) -> list[NarrativeLoop]:
        """Detect narrative loops from hops and observations."""
        logger.debug(
            'inf.multihop.loops.detect_loops',
            hop_count=len(hops),
            observation_count=len(observations),
        )

        loops: list[NarrativeLoop] = []

        loops.extend(self._detect_interpretation_loops(hops))
        loops.extend(self._detect_narrative_behavior_loops(hops))
        loops.extend(self._detect_belief_confirmation_loops(hops))
        loops.extend(self._detect_identity_reinforcement_loops(hops))

        return loops

    # ------------------------------------------------------------------
    # Loop detectors
    # ------------------------------------------------------------------

    def _detect_interpretation_loops(
        self,
        hops: list[dict[str, Any]],
    ) -> list[NarrativeLoop]:
        """Detect observation → interpretation → narrative loops."""
        loops: list[NarrativeLoop] = []

        # Find hops that go observation → behavioral → narrative
        obs_beh_hops = [
            h for h in hops
            if h.get('hop_type') == 'observation_to_behavioral'
        ]
        beh_id_hops = [
            h for h in hops
            if h.get('hop_type') == 'behavioral_to_identity'
        ]
        id_nar_hops = [
            h for h in hops
            if h.get('hop_type') == 'identity_to_narrative'
        ]

        # Check if narrative hops reference back to observations
        for nar_hop in id_nar_hops:
            nar_statement = nar_hop.get('target_statement', '')
            for obs_hop in obs_beh_hops:
                obs_statement = obs_hop.get('source_statement', '')
                # Simple check: if narrative references observation keywords
                obs_words = set(obs_statement.lower().split())
                nar_words = set(nar_statement.lower().split())
                overlap = len(obs_words & nar_words) / max(len(obs_words | nar_words), 1)

                if overlap > 0.2:
                    loops.append(NarrativeLoop(
                        loop_id=str(uuid.uuid4()),
                        loop_type='observation_interpretation_loop',
                        node_ids=(
                            obs_hop.get('hop_id', ''),
                            nar_hop.get('hop_id', ''),
                        ),
                        statements=(obs_statement, nar_statement),
                        reinforcement_strength=overlap,
                        description=(
                            f'Observation "{obs_statement[:50]}..." interpreted '
                            f'and reinforcing narrative "{nar_statement[:50]}..."'
                        ),
                        evidence_count=2,
                    ))

        return loops

    def _detect_narrative_behavior_loops(
        self,
        hops: list[dict[str, Any]],
    ) -> list[NarrativeLoop]:
        """Detect narrative → behavior → observation loops."""
        loops: list[NarrativeLoop] = []

        nar_mc_hops = [
            h for h in hops
            if h.get('hop_type') == 'narrative_to_meta_cognitive'
        ]
        obs_beh_hops = [
            h for h in hops
            if h.get('hop_type') == 'observation_to_behavioral'
        ]

        for nar_hop in nar_mc_hops:
            for obs_hop in obs_beh_hops:
                nar_target = nar_hop.get('target_statement', '')
                obs_source = obs_hop.get('source_statement', '')

                words1 = set(nar_target.lower().split())
                words2 = set(obs_source.lower().split())
                overlap = len(words1 & words2) / max(len(words1 | words2), 1)

                if overlap > 0.2:
                    loops.append(NarrativeLoop(
                        loop_id=str(uuid.uuid4()),
                        loop_type='narrative_behavior_loop',
                        node_ids=(
                            nar_hop.get('hop_id', ''),
                            obs_hop.get('hop_id', ''),
                        ),
                        statements=(nar_target, obs_source),
                        reinforcement_strength=overlap * 0.8,
                        description=(
                            f'Narrative influencing behavior, creating new observations'
                        ),
                        evidence_count=2,
                    ))

        return loops

    def _detect_belief_confirmation_loops(
        self,
        hops: list[dict[str, Any]],
    ) -> list[NarrativeLoop]:
        """Detect belief confirmation loops."""
        loops: list[NarrativeLoop] = []

        # Find identity hops that reference similar content
        id_hops = [
            h for h in hops
            if h.get('target_dimension') == 'identity'
        ]

        for i, hop_a in enumerate(id_hops):
            for hop_b in id_hops[i + 1:]:
                stmt_a = hop_a.get('target_statement', '')
                stmt_b = hop_b.get('target_statement', '')

                words_a = set(stmt_a.lower().split())
                words_b = set(stmt_b.lower().split())
                overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)

                if overlap > 0.3:
                    loops.append(NarrativeLoop(
                        loop_id=str(uuid.uuid4()),
                        loop_type='belief_confirmation_loop',
                        node_ids=(
                            hop_a.get('hop_id', ''),
                            hop_b.get('hop_id', ''),
                        ),
                        statements=(stmt_a, stmt_b),
                        reinforcement_strength=overlap,
                        description='Belief confirmation through repeated identity inference',
                        evidence_count=2,
                    ))

        return loops

    def _detect_identity_reinforcement_loops(
        self,
        hops: list[dict[str, Any]],
    ) -> list[NarrativeLoop]:
        """Detect identity reinforcement loops."""
        loops: list[NarrativeLoop] = []

        # Find chains where identity → narrative → meta_cognitive
        # reinforces the same identity concept
        id_hops = {
            h.get('hop_id', ''): h
            for h in hops
            if h.get('hop_type') == 'behavioral_to_identity'
        }
        nar_hops = {
            h.get('hop_id', ''): h
            for h in hops
            if h.get('hop_type') == 'identity_to_narrative'
        }

        for id_hop_id, id_hop in id_hops.items():
            id_statement = id_hop.get('target_statement', '')

            for nar_hop in nar_hops.values():
                nar_source = nar_hop.get('source_statement', '')
                # Check if narrative starts from same identity
                words_id = set(id_statement.lower().split())
                words_nar = set(nar_source.lower().split())
                overlap = len(words_id & words_nar) / max(len(words_id | words_nar), 1)

                if overlap > 0.3:
                    loops.append(NarrativeLoop(
                        loop_id=str(uuid.uuid4()),
                        loop_type='identity_reinforcement_loop',
                        node_ids=(id_hop_id, nar_hop.get('hop_id', '')),
                        statements=(id_statement, nar_source),
                        reinforcement_strength=overlap * 0.9,
                        description='Identity concept reinforced through narrative framework',
                        evidence_count=2,
                    ))

        return loops
