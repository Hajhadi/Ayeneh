"""Episodic memory engine (MEM-02).

Eight-phase pipeline:
1. Evidence Collection
2. Event Extraction
3. Temporal Clustering
4. Episode Candidate Detection
5. Boundary Detection
6. Validation
7. Episode Publication
8. Longitudinal Integration
"""

from __future__ import annotations

import uuid

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.base import (
    make_version_record,
    RELATIONSHIP_TYPES,
)
from ayeneh.memo.episodic.boundaries import EpisodeBoundaryDetector
from ayeneh.memo.episodic.emotional_landscape import EmotionalLandscape
from ayeneh.memo.episodic.types import (
    EPISODE_CATEGORIES,
    EPISODE_OUTCOMES,
    EPISODE_RELATIONSHIPS,
    EPISODE_STATES,
    EpisodeObject,
    EpisodeRelationship,
    LifeChapter,
    MilestoneObject,
)
from ayeneh.memo.types import Event, EvidenceRecord, Observation

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_CLUSTER_WINDOW_SECONDS: float = 3600.0  # 1 hour
DEFAULT_MIN_EVENTS_PER_EPISODE: int = 2


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------


class PipelineResult:
    """Result of running the episodic memory pipeline."""

    __slots__ = ('episodes', 'milestones', 'boundaries', 'emotional_landscapes', 'metadata')

    def __init__(self) -> None:
        self.episodes: list[EpisodeObject] = []
        self.milestones: list[MilestoneObject] = []
        self.boundaries: list[Any] = []
        self.emotional_landscapes: dict[str, EmotionalLandscape] = {}
        self.metadata: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class EpisodicMemoryEngine:
    """Eight-phase episodic memory pipeline.

    Processes raw observations into validated, published episodes with
    milestones, emotional landscapes, and longitudinal integration.
    """

    def __init__(
        self,
        cluster_window_seconds: float = DEFAULT_CLUSTER_WINDOW_SECONDS,
        min_events_per_episode: int = DEFAULT_MIN_EVENTS_PER_EPISODE,
    ) -> None:
        self._cluster_window = cluster_window_seconds
        self._min_events = min_events_per_episode
        self._boundary_detector = EpisodeBoundaryDetector()
        self._published_episodes: list[EpisodeObject] = []
        self._emotional_landscapes: dict[str, EmotionalLandscape] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_pipeline(self, observations: list[Observation]) -> PipelineResult:
        """Run the full 8-phase pipeline on a list of observations."""
        result = PipelineResult()

        if not observations:
            return result

        sorted_obs = sorted(observations, key=lambda o: o.timestamp)

        # Phase 1: Evidence Collection
        evidence_records = self._collect_evidence(sorted_obs)
        logger.debug('phase_1_evidence_collected', count=len(evidence_records))

        # Phase 2: Event Extraction
        events = self._extract_events(sorted_obs, evidence_records)
        logger.debug('phase_2_events_extracted', count=len(events))

        # Phase 3: Temporal Clustering
        clusters = self._temporal_clustering(events)
        logger.debug('phase_3_clusters_formed', count=len(clusters))

        # Phase 4: Episode Candidate Detection
        candidates = self._detect_candidates(clusters)
        logger.debug('phase_4_candidates_detected', count=len(candidates))

        # Phase 5: Boundary Detection
        boundaries = self._boundary_detector.detect_boundaries(events)
        result.boundaries = boundaries
        logger.debug('phase_5_boundaries_detected', count=len(boundaries))

        # Phase 6: Validation
        validated = self._validate(candidates, evidence_records)
        logger.debug('phase_6_validated', count=len(validated))

        # Phase 7: Episode Publication
        published = self._publish(validated)
        result.episodes = published
        logger.debug('phase_7_published', count=len(published))

        # Phase 8: Longitudinal Integration
        self._longitudinal_integration(published)
        result.emotional_landscapes = dict(self._emotional_landscapes)

        return result

    def get_episode(self, episode_id: str) -> EpisodeObject | None:
        """Retrieve a published episode by ID."""
        for ep in self._published_episodes:
            if ep.identifier == episode_id:
                return ep
        return None

    def get_emotional_landscape(self, episode_id: str) -> EmotionalLandscape | None:
        """Return the emotional landscape for a given episode."""
        return self._emotional_landscapes.get(episode_id)

    def list_episodes(
        self,
        category: str | None = None,
        state: str | None = None,
    ) -> list[EpisodeObject]:
        """List published episodes with optional filters."""
        episodes = self._published_episodes
        if category is not None:
            episodes = [e for e in episodes if e.category == category]
        if state is not None:
            episodes = [e for e in episodes if e.state == state]
        return list(episodes)

    # ------------------------------------------------------------------
    # Phase 1: Evidence Collection
    # ------------------------------------------------------------------

    def _collect_evidence(self, observations: list[Observation]) -> list[EvidenceRecord]:
        """Transform raw observations into evidence records."""
        records: list[EvidenceRecord] = []
        for obs in observations:
            record = EvidenceRecord(
                evidence_id=f"ev_{obs.observation_id}",
                evidence_type=obs.observation_type,
                source=obs.source,
                content=obs.content,
                timestamp=obs.timestamp,
                confidence=obs.metadata.get('confidence', 1.0),
                metadata=obs.metadata,
            )
            records.append(record)
        return records

    # ------------------------------------------------------------------
    # Phase 2: Event Extraction
    # ------------------------------------------------------------------

    def _extract_events(
        self,
        observations: list[Observation],
        evidence_records: list[EvidenceRecord],
    ) -> list[Event]:
        """Extract discrete events from observations."""
        events: list[Event] = []
        evidence_map = {e.evidence_id: e for e in evidence_records}

        for obs in observations:
            ev_id = f"ev_{obs.observation_id}"
            ev_type = self._classify_event_type(obs)
            event = Event(
                event_id=f"evt_{obs.observation_id}",
                description=obs.content,
                timestamp=obs.timestamp,
                event_type=ev_type,
                confidence=evidence_map[ev_id].confidence if ev_id in evidence_map else 1.0,
                source_observations=(obs.observation_id,),
                metadata=obs.metadata,
            )
            events.append(event)
        return events

    def _classify_event_type(self, obs: Observation) -> str:
        """Classify an observation into an event type."""
        content_lower = obs.content.lower()
        if any(kw in content_lower for kw in ('decided', 'decision', 'chose')):
            return 'decision'
        if any(kw in content_lower for kw in ('learned', 'realized', 'understood')):
            return 'insight'
        if any(kw in content_lower for kw in ('started', 'began', 'initiated')):
            return 'action'
        if any(kw in content_lower for kw in ('completed', 'finished', 'done')):
            return 'completion'
        if any(kw in content_lower for kw in ('reflected', 'thought about', 'considered')):
            return 'reflection'
        return obs.observation_type or 'behavior'

    # ------------------------------------------------------------------
    # Phase 3: Temporal Clustering
    # ------------------------------------------------------------------

    def _temporal_clustering(self, events: list[Event]) -> list[list[Event]]:
        """Group events into temporal clusters based on time proximity."""
        if not events:
            return []

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        clusters: list[list[Event]] = [[sorted_events[0]]]

        for event in sorted_events[1:]:
            current_cluster = clusters[-1]
            last_event = current_cluster[-1]
            gap = (event.timestamp - last_event.timestamp).total_seconds()

            if gap <= self._cluster_window:
                current_cluster.append(event)
            else:
                clusters.append([event])

        return clusters

    # ------------------------------------------------------------------
    # Phase 4: Episode Candidate Detection
    # ------------------------------------------------------------------

    def _detect_candidates(self, clusters: list[list[Event]]) -> list[EpisodeObject]:
        """Turn temporal clusters into episode candidates."""
        candidates: list[EpisodeObject] = []

        for i, cluster in enumerate(clusters):
            if len(cluster) < self._min_events:
                continue

            start_time = cluster[0].timestamp
            end_time = cluster[-1].timestamp
            duration = (end_time - start_time).total_seconds()

            descriptions = [e.description for e in cluster]
            summary = '; '.join(descriptions[:5])
            if len(descriptions) > 5:
                summary += f' (+{len(descriptions) - 5} more)'

            # Determine category from event types
            event_types = [e.event_type for e in cluster]
            category = self._infer_category(event_types, cluster)

            # Determine primary context
            sources = [e.metadata.get('source_context', '') for e in cluster]
            primary_context = max(set(sources), key=sources.count) if sources else ''

            episode_id = f"ep_{uuid.uuid4().hex[:12]}"
            candidate = EpisodeObject(
                identifier=episode_id,
                title=f'Episode {i + 1}: {cluster[0].description[:60]}',
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                estimated_duration=duration,
                primary_context=primary_context,
                supporting_evidence=tuple(
                    eid for e in cluster for eid in e.source_observations
                ),
                state='candidate',
                category=category,
                confidence=len(cluster) / max(self._min_events * 3, 1),
            )
            candidates.append(candidate)

        return candidates

    def _infer_category(self, event_types: list[str], cluster: list[Event]) -> str:
        """Infer episode category from event types and content."""
        type_counts: dict[str, int] = {}
        for et in event_types:
            type_counts[et] = type_counts.get(et, 0) + 1

        # Map event type patterns to episode categories
        if type_counts.get('insight', 0) > 0:
            return 'learning'
        if type_counts.get('decision', 0) > 1:
            return 'career'
        if type_counts.get('reflection', 0) > len(event_types) * 0.5:
            return 'spiritual_practice'

        return 'learning'

    # ------------------------------------------------------------------
    # Phase 5: Boundary Detection (delegated)
    # ------------------------------------------------------------------

    # Implemented via self._boundary_detector.detect_boundaries() above.

    # ------------------------------------------------------------------
    # Phase 6: Validation
    # ------------------------------------------------------------------

    def _validate(
        self,
        candidates: list[EpisodeObject],
        evidence: list[EvidenceRecord],
    ) -> list[EpisodeObject]:
        """Validate episode candidates based on evidence and confidence."""
        validated: list[EpisodeObject] = []
        evidence_ids = {e.evidence_id for e in evidence}

        for candidate in candidates:
            # Check evidence alignment
            matching_evidence = sum(
                1 for ev_id in candidate.supporting_evidence
                if ev_id in evidence_ids
            )
            evidence_ratio = (
                matching_evidence / len(candidate.supporting_evidence)
                if candidate.supporting_evidence else 0.0
            )

            # Promote confidence
            new_confidence = min(1.0, candidate.confidence * 0.6 + evidence_ratio * 0.4)

            if new_confidence >= 0.3:
                version = make_version_record(
                    version_number=1,
                    changed_fields={'state': 'candidate', 'confidence': new_confidence},
                    change_reason='validated by evidence',
                )
                validated_candidate = object.__new__(EpisodeObject)
                for slot in EpisodeObject.__slots__ if hasattr(EpisodeObject, '__slots__') else []:
                    pass
                # Use dataclass-like construction
                validated_candidate = EpisodeObject(
                    identifier=candidate.identifier,
                    title=candidate.title,
                    summary=candidate.summary,
                    start_time=candidate.start_time,
                    end_time=candidate.end_time,
                    estimated_duration=candidate.estimated_duration,
                    primary_context=candidate.primary_context,
                    primary_project=candidate.primary_project,
                    primary_people=candidate.primary_people,
                    primary_places=candidate.primary_places,
                    supporting_conversations=candidate.supporting_conversations,
                    supporting_evidence=candidate.supporting_evidence,
                    major_decisions=candidate.major_decisions,
                    major_behaviors=candidate.major_behaviors,
                    major_reflections=candidate.major_reflections,
                    associated_narratives=candidate.associated_narratives,
                    associated_beliefs=candidate.associated_beliefs,
                    associated_goals=candidate.associated_goals,
                    associated_identity_components=candidate.associated_identity_components,
                    outcome=candidate.outcome,
                    open_questions=candidate.open_questions,
                    confidence=new_confidence,
                    version_history=(version,),
                    state='candidate',
                    category=candidate.category,
                    episode_relationships=candidate.episode_relationships,
                    milestones=candidate.milestones,
                    explainability_metadata=candidate.explainability_metadata,
                )
                validated.append(validated_candidate)

        return validated

    # ------------------------------------------------------------------
    # Phase 7: Episode Publication
    # ------------------------------------------------------------------

    def _publish(self, validated: list[EpisodeObject]) -> list[EpisodeObject]:
        """Publish validated episodes into the long-term store."""
        published: list[EpisodeObject] = []

        for ep in validated:
            version = make_version_record(
                version_number=len(ep.version_history) + 1,
                changed_fields={'state': 'active'},
                change_reason='published',
            )
            published_ep = EpisodeObject(
                identifier=ep.identifier,
                title=ep.title,
                summary=ep.summary,
                start_time=ep.start_time,
                end_time=ep.end_time,
                estimated_duration=ep.estimated_duration,
                primary_context=ep.primary_context,
                primary_project=ep.primary_project,
                primary_people=ep.primary_people,
                primary_places=ep.primary_places,
                supporting_conversations=ep.supporting_conversations,
                supporting_evidence=ep.supporting_evidence,
                major_decisions=ep.major_decisions,
                major_behaviors=ep.major_behaviors,
                major_reflections=ep.major_reflections,
                associated_narratives=ep.associated_narratives,
                associated_beliefs=ep.associated_beliefs,
                associated_goals=ep.associated_goals,
                associated_identity_components=ep.associated_identity_components,
                outcome=ep.outcome,
                open_questions=ep.open_questions,
                confidence=ep.confidence,
                version_history=ep.version_history + (version,),
                state='active',
                category=ep.category,
                episode_relationships=ep.episode_relationships,
                milestones=ep.milestones,
                explainability_metadata=ep.explainability_metadata,
            )
            self._published_episodes.append(published_ep)
            published.append(published_ep)

        return published

    # ------------------------------------------------------------------
    # Phase 8: Longitudinal Integration
    # ------------------------------------------------------------------

    def _longitudinal_integration(self, published: list[EpisodeObject]) -> None:
        """Integrate newly published episodes with the longitudinal store.

        Detects relationships between new and existing episodes, creates
        milestones, and initializes emotional landscapes.
        """
        for ep in published:
            # Initialize emotional landscape
            landscape = EmotionalLandscape()
            self._emotional_landscapes[ep.identifier] = landscape

            # Detect relationships with existing episodes
            for existing in self._published_episodes:
                if existing.identifier == ep.identifier:
                    continue
                rel = self._detect_relationship(existing, ep)
                if rel is not None:
                    logger.info(
                        'episode_relationship_detected',
                        source=existing.identifier,
                        target=ep.identifier,
                        relationship=rel.relationship_type,
                    )

    def _detect_relationship(
        self,
        existing: EpisodeObject,
        new: EpisodeObject,
    ) -> EpisodeRelationship | None:
        """Detect a relationship between an existing and a new episode."""
        # Temporal: new follows existing
        if new.start_time > (existing.end_time or existing.start_time):
            gap = (new.start_time - (existing.end_time or existing.start_time)).total_seconds()
            if gap < self._cluster_window * 2:
                return EpisodeRelationship(
                    source_episode_id=existing.identifier,
                    target_episode_id=new.identifier,
                    relationship_type='follows',
                    weight=max(0.0, 1.0 - gap / (self._cluster_window * 10)),
                )

        # Category overlap
        if existing.category == new.category and existing.category != 'learning':
            return EpisodeRelationship(
                source_episode_id=existing.identifier,
                target_episode_id=new.identifier,
                relationship_type='extends',
                weight=0.5,
            )

        return None
