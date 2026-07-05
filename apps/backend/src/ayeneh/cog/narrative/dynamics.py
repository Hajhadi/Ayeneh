"""COG-05 Narrative Dynamics.

Analyzes drift, gravity, fusion, and rigidity of narratives over time.
These metrics quantify how a narrative is changing, how strongly it
pulls cognition, how fused it is with identity, and how resistant
it is to revision.
"""

from __future__ import annotations

import structlog
from typing import Any

logger = structlog.get_logger(__name__)


# ------------------------------------------------------------------
# Result dataclasses
# ------------------------------------------------------------------


from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class NarrativeDrift:
    """Measures how much a narrative has drifted from its supporting evidence."""

    narrative_id: str = ''
    evidence_mismatch_score: float = 0.0
    behavior_mismatch_score: float = 0.0
    contradiction_accumulation: float = 0.0
    overall_drift: float = 0.0


@dataclass(frozen=True)
class NarrativeGravity:
    """Measures how strongly a narrative pulls cognition and behavior."""

    narrative_id: str = ''
    repetition_strength: float = 0.0
    emotional_intensity: float = 0.0
    identity_coupling: float = 0.0
    behavioral_influence: float = 0.0
    overall_gravity: float = 0.0


@dataclass(frozen=True)
class FusionResult:
    """Result of narrative-identity fusion analysis."""

    narrative_id: str = ''
    fusion_score: float = 0.0
    fused_components: tuple[str, ...] = ()
    is_fused: bool = False


@dataclass(frozen=True)
class RigidityResult:
    """Result of narrative rigidity analysis."""

    narrative_id: str = ''
    rigidity_score: float = 0.0
    revision_count: int = 0
    average_revision_interval_days: float = 0.0
    is_rigid: bool = False


# ------------------------------------------------------------------
# Dynamic thresholds
# ------------------------------------------------------------------

_DRIFT_HIGH_THRESHOLD = 0.6
_DRIFT_LOW_THRESHOLD = 0.3
_GRAVITY_HIGH_THRESHOLD = 0.6
_FUSION_THRESHOLD = 0.5
_RIGIDITY_THRESHOLD = 0.6


class NarrativeDynamicsAnalyzer:
    """Analyzes dynamic properties of narratives: drift, gravity, fusion, and rigidity.

    Each analysis method takes a narrative object (or related data) and
    evidence/history lists and returns a frozen result dataclass.
    """

    def analyze_drift(
        self,
        narrative: Any,
        evidence: list[Any],
    ) -> NarrativeDrift:
        """Analyze how much a narrative has drifted from its evidence base.

        Drift is computed from:
        - Evidence mismatch: ratio of contradictory to supporting evidence
        - Behavior mismatch: evidence that contradicts behavioral expectations
        - Contradiction accumulation: total contradictions relative to support
        """
        supporting = getattr(narrative, 'supporting_evidence', ())
        contradictory = getattr(narrative, 'contradictory_evidence', ())
        behavioral = getattr(narrative, 'behavioral_evidence', ())

        support_count = max(len(supporting), 1)
        contradiction_count = len(contradictory)
        behavioral_count = len(behavioral)

        # Evidence mismatch: contradictions relative to support
        evidence_mismatch = min(contradiction_count / support_count, 1.0)

        # Behavior mismatch: behavioral contradictions relative to total behavioral evidence
        total_behavioral = behavioral_count + contradiction_count
        behavior_mismatch = (
            min(contradiction_count / max(total_behavioral, 1), 1.0)
            if total_behavioral > 0
            else 0.0
        )

        # Contradiction accumulation: raw contradiction density
        total_evidence = support_count + contradiction_count
        contradiction_accumulation = contradiction_count / max(total_evidence, 1)

        # Overall drift: weighted combination
        overall = (
            evidence_mismatch * 0.4
            + behavior_mismatch * 0.3
            + contradiction_accumulation * 0.3
        )

        return NarrativeDrift(
            narrative_id=getattr(narrative, 'identifier', ''),
            evidence_mismatch_score=round(evidence_mismatch, 4),
            behavior_mismatch_score=round(behavior_mismatch, 4),
            contradiction_accumulation=round(contradiction_accumulation, 4),
            overall_drift=round(overall, 4),
        )

    def analyze_gravity(
        self,
        narrative: Any,
        evidence: list[Any],
    ) -> NarrativeGravity:
        """Analyze how strongly a narrative pulls cognition and behavior.

        Gravity is computed from:
        - Repetition strength: how often the narrative theme recurs in evidence
        - Emotional intensity: emotional associations attached to the narrative
        - Identity coupling: how strongly the narrative is linked to identity
        - Behavioral influence: how much the narrative affects behavior
        """
        supporting = getattr(narrative, 'supporting_evidence', ())
        emotional = getattr(narrative, 'emotional_associations', ())
        identity_impl = getattr(narrative, 'identity_implications', ())
        behavioral = getattr(narrative, 'behavioral_consequences', ())

        total_evidence = max(len(evidence), 1)

        # Repetition strength: supporting evidence relative to total evidence
        repetition = min(len(supporting) / total_evidence, 1.0)

        # Emotional intensity: emotional associations count, normalized
        emotional_intensity = min(len(emotional) / 5.0, 1.0)

        # Identity coupling: identity implications count, normalized
        identity_coupling = min(len(identity_impl) / 4.0, 1.0)

        # Behavioral influence: behavioral consequences count, normalized
        behavioral_influence = min(len(behavioral) / 4.0, 1.0)

        # Overall gravity: weighted combination
        overall = (
            repetition * 0.3
            + emotional_intensity * 0.25
            + identity_coupling * 0.25
            + behavioral_influence * 0.2
        )

        return NarrativeGravity(
            narrative_id=getattr(narrative, 'identifier', ''),
            repetition_strength=round(repetition, 4),
            emotional_intensity=round(emotional_intensity, 4),
            identity_coupling=round(identity_coupling, 4),
            behavioral_influence=round(behavioral_influence, 4),
            overall_gravity=round(overall, 4),
        )

    def detect_fusion(
        self,
        narrative: Any,
        identity_components: list[Any],
    ) -> float:
        """Detect how fused a narrative is with the individual's identity.

        Fusion is high when the narrative's identity implications overlap
        strongly with known identity components.

        Returns a fusion score between 0.0 and 1.0.
        """
        identity_impl = set(getattr(narrative, 'identity_implications', ()))
        if not identity_impl:
            return 0.0

        # Extract names/text from identity components
        component_texts: set[str] = set()
        for comp in identity_components:
            text = (
                getattr(comp, 'statement', '')
                or getattr(comp, 'text', '')
                or getattr(comp, 'summary', '')
                or str(comp)
            ).lower()
            if text:
                component_texts.add(text)

        if not component_texts:
            return 0.0

        # Compute overlap between narrative identity implications and components
        matched = 0
        for impl in identity_impl:
            impl_lower = impl.lower()
            for ct in component_texts:
                if impl_lower in ct or ct in impl_lower:
                    matched += 1
                    break

        return round(matched / len(identity_impl), 4)

    def detect_rigidity(
        self,
        narrative: Any,
        revision_history: list[Any],
    ) -> float:
        """Detect how resistant a narrative is to revision.

        Rigidity is high when:
        - The narrative has few revisions relative to its age
        - Revisions are infrequent (long intervals between changes)
        - The narrative has high confidence despite contradictions

        Returns a rigidity score between 0.0 and 1.0.
        """
        revision_count = len(revision_history)

        # Fewer revisions = more rigid (normalized against a reference of 5 revisions)
        revision_rigidity = max(0.0, 1.0 - revision_count / 5.0)

        # Confidence relative to contradictions
        confidence = getattr(narrative, 'confidence', 0.0)
        contradiction_count = len(getattr(narrative, 'contradictory_evidence', ()))
        support_count = max(len(getattr(narrative, 'supporting_evidence', ())), 1)

        # High confidence despite contradictions = rigid
        contradiction_ratio = contradiction_count / support_count
        confidence_persistence = confidence * (1.0 + contradiction_ratio)

        # Combine
        rigidity = (revision_rigidity * 0.5 + min(confidence_persistence, 1.0) * 0.5)

        return round(min(rigidity, 1.0), 4)
