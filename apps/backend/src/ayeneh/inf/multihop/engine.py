"""INF-03 Multi-Hop Reasoning Engine.

Recursive reasoning chains across cognitive dimensions:
1. Observation → Behavioral Inference
2. Behavioral → Identity Inference
3. Identity → Narrative Inference
4. Narrative → Meta-Cognitive Inference
5. Meta-Cognitive → Reality Calibration
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.inf.multihop.loops import NarrativeLoopDetector
from ayeneh.inf.multihop.types import (
    HOP_TYPES,
    REASONING_DIMENSIONS,
    HiddenPattern,
    MultiHopChain,
    MultiHopResult,
    NarrativeLoop,
    ReasoningHop,
)

logger = structlog.get_logger(__name__)

# Hop transition map: source dimension → target dimension
HOP_TRANSITIONS: dict[str, str] = {
    'observation': 'behavioral',
    'behavioral': 'identity',
    'identity': 'narrative',
    'narrative': 'meta_cognitive',
    'meta_cognitive': 'reality_calibration',
}


class MultiHopReasoningEngine:
    """Recursive reasoning chain engine (INF-03).

    Pipeline:
        1. Observation → Behavioral Inference
        2. Behavioral → Identity Inference
        3. Identity → Narrative Inference
        4. Narrative → Meta-Cognitive Inference
        5. Meta-Cognitive → Reality Calibration

    Each hop transforms evidence from one cognitive dimension to the next,
    building deeper understanding through recursive inference.
    """

    def __init__(self) -> None:
        self._chains: dict[str, MultiHopChain] = {}
        self._loop_detector = NarrativeLoopDetector()

    def process(
        self,
        observations: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
        max_depth: int = 5,
    ) -> MultiHopResult:
        """Run the full INF-03 pipeline.

        Parameters
        ----------
        observations:
            List of observation dicts with ``'id'``, ``'content'``, and
            optional ``'type'`` and ``'confidence'`` keys.
        context:
            Optional context dict with ``'context_id'`` and ``'domain'``.
        max_depth:
            Maximum number of hops in each chain (default 5).
        """
        context = context or {}
        logger.info(
            'inf.multihop.pipeline_started',
            context_id=context.get('context_id', ''),
            observation_count=len(observations),
            max_depth=max_depth,
        )

        # Build reasoning chains from observations
        chains: list[MultiHopChain] = []
        for obs in observations:
            chain = self._build_chain(obs, max_depth)
            if chain:
                chains.append(chain)

        # Detect narrative loops
        all_hops = []
        for chain in chains:
            for hop_dict in chain.hops:
                all_hops.append(hop_dict)

        loops = self._loop_detector.detect_loops(all_hops, observations)

        # Discover hidden patterns
        hidden = self._discover_hidden_patterns(chains, loops)

        # Calculate overall confidence
        overall = self._calculate_overall_confidence(chains, hidden)

        # Calibration notes
        notes = self._generate_calibration_notes(chains, loops, hidden)

        result = MultiHopResult(
            chains=tuple(chains),
            narrative_loops=tuple(loops),
            hidden_patterns=tuple(hidden),
            overall_confidence=round(overall, 4),
            calibration_notes=tuple(notes),
            processing_metadata={
                'chain_count': len(chains),
                'loop_count': len(loops),
                'pattern_count': len(hidden),
                'observation_count': len(observations),
            },
        )

        logger.info(
            'inf.multihop.pipeline_completed',
            chain_count=len(chains),
            loop_count=len(loops),
            confidence=overall,
        )

        return result

    # ------------------------------------------------------------------
    # Chain building
    # ------------------------------------------------------------------

    def _build_chain(
        self,
        observation: dict[str, Any],
        max_depth: int,
    ) -> MultiHopChain | None:
        """Build a multi-hop reasoning chain from an observation."""
        obs_content = observation.get('content', '')
        if not obs_content:
            return None

        chain_id = str(uuid.uuid4())
        hops: list[dict[str, Any]] = []
        current_statement = obs_content
        current_dimension = 'observation'
        confidences: list[float] = []

        for depth in range(max_depth):
            target_dim = HOP_TRANSITIONS.get(current_dimension)
            if not target_dim:
                break

            hop = self._execute_hop(
                chain_id=chain_id,
                hop_number=depth,
                source_dim=current_dimension,
                target_dim=target_dim,
                source_statement=current_statement,
            )

            if hop:
                hops.append({
                    'hop_id': hop.hop_id,
                    'hop_type': hop.hop_type,
                    'source_dimension': hop.source_dimension,
                    'target_dimension': hop.target_dimension,
                    'source_statement': hop.source_statement,
                    'target_statement': hop.target_statement,
                    'confidence': hop.confidence,
                })
                confidences.append(hop.confidence)
                current_statement = hop.target_statement
                current_dimension = target_dim

        if not hops:
            return None

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        chain = MultiHopChain(
            chain_id=chain_id,
            starting_observation=obs_content,
            hops=tuple(hops),
            confidence=round(avg_confidence, 4),
            depth=len(hops),
        )

        self._chains[chain_id] = chain
        return chain

    def _execute_hop(
        self,
        chain_id: str,
        hop_number: int,
        source_dim: str,
        target_dim: str,
        source_statement: str,
    ) -> ReasoningHop | None:
        """Execute a single reasoning hop."""
        hop_type = f'{source_dim}_to_{target_dim}'
        if hop_type not in HOP_TYPES:
            return None

        # Generate the target statement based on the transition
        target_statement = self._transform_statement(
            source_dim, target_dim, source_statement,
        )

        if not target_statement:
            return None

        # Confidence decreases slightly with each hop
        base_confidence = 0.8 - (hop_number * 0.05)

        return ReasoningHop(
            hop_id=str(uuid.uuid4()),
            hop_type=hop_type,
            source_dimension=source_dim,
            target_dimension=target_dim,
            source_statement=source_statement,
            target_statement=target_statement,
            confidence=max(base_confidence, 0.3),
            reasoning_method='dimensional_transform',
        )

    def _transform_statement(
        self,
        source_dim: str,
        target_dim: str,
        statement: str,
    ) -> str:
        """Transform a statement from one cognitive dimension to another."""
        transformers = {
            ('observation', 'behavioral'): self._obs_to_behavioral,
            ('behavioral', 'identity'): self._behavioral_to_identity,
            ('identity', 'narrative'): self._identity_to_narrative,
            ('narrative', 'meta_cognitive'): self._narrative_to_meta_cognitive,
            ('meta_cognitive', 'reality_calibration'): self._meta_to_reality,
        }

        transformer = transformers.get((source_dim, target_dim))
        if transformer:
            return transformer(statement)
        return ''

    def _obs_to_behavioral(self, statement: str) -> str:
        """Transform observation to behavioral inference."""
        return f"Behavioral pattern inferred from observation: {statement}"

    def _behavioral_to_identity(self, statement: str) -> str:
        """Transform behavioral inference to identity inference."""
        return f"Identity aspect reflected in behavior: {statement}"

    def _identity_to_narrative(self, statement: str) -> str:
        """Transform identity inference to narrative inference."""
        return f"Narrative framework incorporating identity: {statement}"

    def _narrative_to_meta_cognitive(self, statement: str) -> str:
        """Transform narrative to meta-cognitive inference."""
        return f"Meta-cognitive awareness of narrative: {statement}"

    def _meta_to_reality(self, statement: str) -> str:
        """Transform meta-cognitive to reality calibration."""
        return f"Reality calibration assessment: {statement}"

    # ------------------------------------------------------------------
    # Pattern discovery
    # ------------------------------------------------------------------

    def _discover_hidden_patterns(
        self,
        chains: list[MultiHopChain],
        loops: list[NarrativeLoop],
    ) -> list[HiddenPattern]:
        """Discover hidden patterns across chains and loops."""
        patterns: list[HiddenPattern] = []

        # Pattern: chains that converge on similar conclusions
        if len(chains) >= 2:
            convergence = self._check_convergence(chains)
            if convergence:
                patterns.append(convergence)

        # Pattern: loops that reinforce chain conclusions
        if chains and loops:
            reinforcement = self._check_reinforcement(chains, loops)
            if reinforcement:
                patterns.append(reinforcement)

        # Pattern: deep chains (many hops with maintained confidence)
        for chain in chains:
            if chain.depth >= 4 and chain.confidence > 0.5:
                patterns.append(HiddenPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type='deep_reasoning_chain',
                    description=f'Deep reasoning chain with {chain.depth} hops at confidence {chain.confidence:.2f}',
                    confidence=chain.confidence,
                    hop_ids=tuple(
                        h.get('hop_id', '') for h in chain.hops
                    ),
                ))

        return patterns

    def _check_convergence(
        self,
        chains: list[MultiHopChain],
    ) -> HiddenPattern | None:
        """Check if multiple chains converge on similar conclusions."""
        # Simple convergence: chains that end with similar final statements
        final_statements = []
        for chain in chains:
            if chain.hops:
                last_hop = chain.hops[-1]
                final_statements.append(last_hop.get('target_statement', ''))

        if len(final_statements) < 2:
            return None

        # Check pairwise similarity (simple word overlap)
        for i, s1 in enumerate(final_statements):
            for s2 in final_statements[i + 1:]:
                words1 = set(s1.lower().split())
                words2 = set(s2.lower().split())
                overlap = len(words1 & words2) / max(len(words1 | words2), 1)
                if overlap > 0.3:
                    return HiddenPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type='convergent_reasoning',
                        description='Multiple reasoning chains converge on similar conclusions',
                        confidence=overlap,
                    )

        return None

    def _check_reinforcement(
        self,
        chains: list[MultiHopChain],
        loops: list[NarrativeLoop],
    ) -> HiddenPattern | None:
        """Check if loops reinforce chain conclusions."""
        if not loops:
            return None

        max_reinforcement = max(l.reinforcement_strength for l in loops)
        if max_reinforcement > 0.6:
            return HiddenPattern(
                pattern_id=str(uuid.uuid4()),
                pattern_type='loop_reinforced_reasoning',
                description='Narrative loops reinforce reasoning chain conclusions',
                confidence=max_reinforcement,
            )

        return None

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def _calculate_overall_confidence(
        self,
        chains: list[MultiHopChain],
        patterns: list[HiddenPattern],
    ) -> float:
        """Calculate overall confidence across all chains and patterns."""
        all_confidences: list[float] = []

        for chain in chains:
            all_confidences.append(chain.confidence)
        for pattern in patterns:
            all_confidences.append(pattern.confidence)

        if not all_confidences:
            return 0.0

        return sum(all_confidences) / len(all_confidences)

    def _generate_calibration_notes(
        self,
        chains: list[MultiHopChain],
        loops: list[NarrativeLoop],
        patterns: list[HiddenPattern],
    ) -> list[str]:
        """Generate calibration notes."""
        notes: list[str] = []

        if not chains:
            notes.append('No reasoning chains generated')
        else:
            avg_depth = sum(c.depth for c in chains) / len(chains)
            notes.append(f'Average chain depth: {avg_depth:.1f}')

        if loops:
            notes.append(f'Detected {len(loops)} narrative loop(s)')

        if patterns:
            notes.append(f'Discovered {len(patterns)} hidden pattern(s)')

        return notes

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_chain(self, chain_id: str) -> MultiHopChain | None:
        """Retrieve a chain by ID."""
        return self._chains.get(chain_id)

    def get_all_chains(self) -> list[MultiHopChain]:
        """Retrieve all chains."""
        return list(self._chains.values())
