"""Cognitive Trajectory Engine — COG-13.

Models how cognitive structures evolve across months and years.
Pipeline: Evidence → Version History → Temporal Graph → Trajectories →
Developmental Model.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.cog.trajectory.phases import PhaseIdentifier
from ayeneh.cog.trajectory.types import (
    DIRECTION_TYPES,
    TARGET_TYPES,
    DevelopmentalMilestone,
    TrajectoryObject,
    TrajectoryResult,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Cognitive Trajectory Engine
# ---------------------------------------------------------------------------


class CognitiveTrajectoryEngine:
    """Models how cognitive structures evolve across months and years (COG-13).

    Pipeline:
        1. Version History — build temporal snapshots of cognitive objects
        2. Temporal Graph — connect snapshots into chronological chains
        3. Trajectory Extraction — identify directional trends
        4. Milestone Detection — find significant transition points
        5. Phase Identification — group trajectories into developmental phases
    """

    def __init__(self) -> None:
        self._trajectories: dict[str, TrajectoryObject] = {}
        self._phase_identifier = PhaseIdentifier()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        cognitive_objects: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
    ) -> TrajectoryResult:
        """Run the full COG-13 pipeline.

        Parameters
        ----------
        cognitive_objects:
            List of cognitive object dicts with ``'id'``, ``'type'``,
            ``'text'``, and optional ``'timestamp'`` keys.
        evidence:
            List of evidence dicts with ``'id'``, ``'text'``, and optional
            ``'category'`` and ``'timestamp'`` keys.
        """
        logger.info(
            'cog.trajectory.pipeline_started',
            cognitive_object_count=len(cognitive_objects),
            evidence_count=len(evidence),
        )

        # Phase 1 — Version History
        version_history = self._build_version_history(cognitive_objects)

        # Phase 2 — Temporal Graph
        temporal_graph = self._build_temporal_graph(version_history)

        # Phase 3 — Trajectory Extraction
        trajectories = self._extract_trajectories(temporal_graph, evidence)

        # Phase 4 — Milestone Detection
        milestones = self._detect_milestones(trajectories)

        # Phase 5 — Phase Identification
        phases, _ = self._phase_identifier.identify(list(trajectories.values()))

        # Store trajectories
        for traj in trajectories.values():
            self._trajectories[traj.identifier] = traj

        result = TrajectoryResult(
            trajectories=trajectories,
            milestones=milestones,
            phases=[{'phase_id': p.phase_id, 'description': p.description} for p in phases],
            total_extracted=len(trajectories),
        )

        logger.info(
            'cog.trajectory.pipeline_completed',
            total_extracted=result.total_extracted,
            milestones_found=len(milestones),
            phases_found=len(phases),
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Version History
    # ------------------------------------------------------------------

    @staticmethod
    def _build_version_history(
        cognitive_objects: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        """Build temporal snapshots grouped by cognitive object ID."""
        history: dict[str, list[dict[str, Any]]] = {}

        for obj in cognitive_objects:
            obj_id = obj.get('id', '')
            if not obj_id:
                continue

            snapshot = {
                'text': obj.get('text', ''),
                'type': obj.get('type', ''),
                'timestamp': obj.get('timestamp', ''),
                'confidence': obj.get('confidence', 0.0),
            }
            history.setdefault(obj_id, []).append(snapshot)

        # Sort each object's history by timestamp
        for obj_id in history:
            history[obj_id].sort(key=lambda s: s.get('timestamp', ''))

        logger.info('cog.trajectory.version_history_built', object_count=len(history))
        return history

    # ------------------------------------------------------------------
    # Phase 2: Temporal Graph
    # ------------------------------------------------------------------

    @staticmethod
    def _build_temporal_graph(
        version_history: dict[str, list[dict[str, Any]]],
    ) -> dict[str, dict[str, Any]]:
        """Connect snapshots into chronological chains with transition metadata."""
        graph: dict[str, dict[str, Any]] = {}

        for obj_id, versions in version_history.items():
            if len(versions) < 2:
                # Single version — no transitions
                graph[obj_id] = {
                    'versions': versions,
                    'transitions': [],
                    'version_count': len(versions),
                }
                continue

            transitions: list[dict[str, Any]] = []
            for i in range(1, len(versions)):
                prev = versions[i - 1]
                curr = versions[i]

                # Detect change type
                change_type = _detect_change_type(prev, curr)

                transition = {
                    'from_version': i - 1,
                    'to_version': i,
                    'change_type': change_type,
                    'prev_text': prev.get('text', ''),
                    'curr_text': curr.get('text', ''),
                    'timestamp': curr.get('timestamp', ''),
                }
                transitions.append(transition)

            graph[obj_id] = {
                'versions': versions,
                'transitions': transitions,
                'version_count': len(versions),
            }

        logger.info('cog.trajectory.temporal_graph_built', node_count=len(graph))
        return graph

    # ------------------------------------------------------------------
    # Phase 3: Trajectory Extraction
    # ------------------------------------------------------------------

    def _extract_trajectories(
        self,
        temporal_graph: dict[str, dict[str, Any]],
        evidence: list[dict[str, Any]],
    ) -> dict[str, TrajectoryObject]:
        """Extract directional trajectories from the temporal graph."""
        trajectories: dict[str, TrajectoryObject] = {}

        for obj_id, graph_data in temporal_graph.items():
            versions = graph_data['versions']
            transitions = graph_data['transitions']

            if not versions:
                continue

            # Determine target type from first version
            target_type = versions[0].get('type', 'belief')
            if target_type not in TARGET_TYPES:
                target_type = 'belief'

            # Compute rate of change
            rate = _compute_rate_of_change(transitions)

            # Determine direction
            direction = _determine_direction(transitions, rate)

            # Compute confidence
            version_count = len(versions)
            confidence = min(1.0, version_count * 0.2)

            # Compute historical continuity
            continuity = _compute_continuity(transitions)

            # Find supporting evidence
            supporting_evidence = _find_supporting_evidence(
                obj_id, evidence, versions,
            )

            # Build major transitions (only significant ones)
            major = _filter_major_transitions(transitions)

            traj = TrajectoryObject(
                identifier=str(uuid.uuid4()),
                target_cognitive_object=obj_id,
                target_type=target_type,
                temporal_sequence=tuple(versions),
                major_transitions=tuple(major),
                rate_of_change=rate,
                direction=direction,
                confidence=confidence,
                historical_continuity=continuity,
                lifecycle_state='candidate' if version_count < 3 else 'validated',
            )
            trajectories[traj.identifier] = traj

        logger.info('cog.trajectory.trajectories_extracted', count=len(trajectories))
        return trajectories

    # ------------------------------------------------------------------
    # Phase 4: Milestone Detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_milestones(
        trajectories: dict[str, TrajectoryObject],
    ) -> list[DevelopmentalMilestone]:
        """Detect significant transition points in trajectories."""
        milestones: list[DevelopmentalMilestone] = []

        for traj in trajectories.values():
            for transition in traj.major_transitions:
                milestone = DevelopmentalMilestone(
                    milestone_id=str(uuid.uuid4()),
                    description=(
                        f"Transition in {traj.target_type} "
                        f"{traj.target_cognitive_object}: "
                        f"{transition.get('change_type', 'unknown')}"
                    ),
                    previous_state=transition.get('prev_text', ''),
                    new_state=transition.get('curr_text', ''),
                    evidence=(traj.target_cognitive_object,),
                )
                milestones.append(milestone)

        logger.info('cog.trajectory.milestones_detected', count=len(milestones))
        return milestones

    # ------------------------------------------------------------------
    # Phase 5: Phase Identification (delegated)
    # ------------------------------------------------------------------

    def _identify_phases(
        self,
        trajectories: dict[str, TrajectoryObject],
    ) -> list[dict[str, Any]]:
        """Identify developmental phases from trajectories."""
        phases, _ = self._phase_identifier.identify(list(trajectories.values()))
        return [{'phase_id': p.phase_id, 'description': p.description} for p in phases]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _detect_change_type(
    prev: dict[str, Any],
    curr: dict[str, Any],
) -> str:
    """Detect the type of change between two versions."""
    prev_text = prev.get('text', '').lower()
    curr_text = curr.get('text', '').lower()

    if prev_text == curr_text:
        return 'unchanged'

    prev_words = set(prev_text.split())
    curr_words = set(curr_text.split())

    if not prev_words or not curr_words:
        return 'rewritten'

    overlap = prev_words & curr_words
    overlap_ratio = len(overlap) / max(len(prev_words), len(curr_words))

    if overlap_ratio >= 0.7:
        return 'refined'
    elif overlap_ratio >= 0.3:
        return 'evolved'
    else:
        return 'transformed'


def _compute_rate_of_change(transitions: list[dict[str, Any]]) -> float:
    """Compute the rate of change across transitions."""
    if not transitions:
        return 0.0

    change_scores = []
    for t in transitions:
        change_type = t.get('change_type', 'unchanged')
        score_map = {
            'unchanged': 0.0,
            'refined': 0.2,
            'evolved': 0.5,
            'transformed': 0.8,
            'rewritten': 1.0,
        }
        change_scores.append(score_map.get(change_type, 0.5))

    return sum(change_scores) / len(change_scores)


def _determine_direction(
    transitions: list[dict[str, Any]],
    rate: float,
) -> str:
    """Determine the direction of a trajectory."""
    if not transitions:
        return 'stabilizing'

    change_types = [t.get('change_type', 'unchanged') for t in transitions]

    if rate < 0.1:
        return 'stabilizing'
    elif rate > 0.7:
        return 'transforming'
    elif 'evolved' in change_types or 'transformed' in change_types:
        return 'strengthening'
    elif 'refined' in change_types:
        return 'integrating'
    else:
        return 'stabilizing'


def _compute_continuity(transitions: list[dict[str, Any]]) -> float:
    """Compute historical continuity (how much is preserved across changes)."""
    if not transitions:
        return 1.0

    continuity_scores = []
    for t in transitions:
        change_type = t.get('change_type', 'unchanged')
        score_map = {
            'unchanged': 1.0,
            'refined': 0.8,
            'evolved': 0.5,
            'transformed': 0.2,
            'rewritten': 0.1,
        }
        continuity_scores.append(score_map.get(change_type, 0.5))

    return sum(continuity_scores) / len(continuity_scores)


def _find_supporting_evidence(
    obj_id: str,
    evidence: list[dict[str, Any]],
    versions: list[dict[str, Any]],
) -> tuple[str, ...]:
    """Find evidence that supports this trajectory."""
    supporting: list[str] = []
    version_texts = {v.get('text', '').lower() for v in versions}

    for ev in evidence:
        ev_text = ev.get('text', '').lower()
        ev_id = ev.get('id', '')
        for vtext in version_texts:
            if vtext and ev_text and _words_overlap(vtext, ev_text):
                if ev_id:
                    supporting.append(ev_id)
                break

    return tuple(supporting)


def _words_overlap(text_a: str, text_b: str) -> bool:
    """Check if two texts share meaningful word overlap."""
    words_a = set(text_a.split())
    words_b = set(text_b.split())
    stop_words = {
        'i', 'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be',
        'have', 'has', 'had', 'do', 'does', 'did', 'to', 'of', 'in',
        'for', 'on', 'with', 'at', 'by', 'it', 'this', 'that', 'and',
        'or', 'but', 'not', 'my', 'me', 'we', 'our',
    }
    meaningful_a = words_a - stop_words
    meaningful_b = words_b - stop_words
    if not meaningful_a or not meaningful_b:
        return False
    return len(meaningful_a & meaningful_b) >= 1


def _filter_major_transitions(
    transitions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Filter to only significant transitions."""
    return [
        t for t in transitions
        if t.get('change_type', 'unchanged') in ('evolved', 'transformed', 'rewritten')
    ]
