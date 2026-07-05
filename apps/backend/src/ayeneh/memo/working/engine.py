"""Working memory engine (MEM-04).

Ten-phase pipeline:
1. UserInput
2. IntentAnalysis
3. ContextDetection
4. MemoryRetrieval
5. RelevanceScoring
6. ConflictResolution
7. Assembly
8. Inference
9. DialogueGeneration
10. Update
"""

from __future__ import annotations

import uuid

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.working.types import (
    CONTEXT_WINDOWS,
    OPEN_LOOP_CATEGORIES,
    CompressionResult,
    ContextSwitch,
    ContextWindow,
    ExplainabilityMetadata,
    OpenLoop,
    WorkingMemoryObject,
    WorkingMemorySnapshot,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MAX_WORKING_MEMORY: int = 30
DEFAULT_CONTEXT_WINDOW_CAPACITY: int = 20
DEFAULT_DECAY_RATE: float = 0.1
DEFAULT_CONFIDENCE_THRESHOLD: float = 0.3


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------


class WorkingMemoryPipelineResult:
    """Result of running the working memory pipeline."""

    __slots__ = (
        'activated_objects',
        'deactivated_objects',
        'context_switches',
        'open_loops',
        'snapshot',
        'metadata',
    )

    def __init__(self) -> None:
        self.activated_objects: list[WorkingMemoryObject] = []
        self.deactivated_objects: list[WorkingMemoryObject] = []
        self.context_switches: list[ContextSwitch] = []
        self.open_loops: list[OpenLoop] = []
        self.snapshot: WorkingMemorySnapshot | None = None
        self.metadata: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class WorkingMemoryEngine:
    """Ten-phase working memory pipeline.

    Manages the activation, maintenance, and decay of working memory items
    across multiple context windows.
    """

    def __init__(
        self,
        max_capacity: int = DEFAULT_MAX_WORKING_MEMORY,
        decay_rate: float = DEFAULT_DECAY_RATE,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self._max_capacity = max_capacity
        self._decay_rate = decay_rate
        self._confidence_threshold = confidence_threshold
        self._active_objects: dict[str, WorkingMemoryObject] = {}
        self._context_windows: dict[str, ContextWindow] = {}
        self._open_loops: dict[str, OpenLoop] = {}
        self._context_history: list[ContextSwitch] = []
        self._snapshot_counter = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_pipeline(
        self,
        user_input: str,
        *,
        intent: str = 'recall',
        cognitive_focus: str = '',
        retrieved_memories: list[dict[str, Any]] | None = None,
        recent_conversation: list[str] | None = None,
    ) -> WorkingMemoryPipelineResult:
        """Run the full 10-phase working memory pipeline."""
        result = WorkingMemoryPipelineResult()

        # Phase 1: UserInput — captured as user_input param

        # Phase 2: IntentAnalysis
        analyzed_intent = self._analyze_intent(user_input, intent)
        logger.debug('phase_2_intent_analyzed', intent=analyzed_intent)

        # Phase 3: ContextDetection
        detected_context = self._detect_context(
            user_input, analyzed_intent, cognitive_focus
        )
        logger.debug('phase_3_context_detected', context=detected_context)

        # Phase 4: MemoryRetrieval
        candidates = self._retrieve_candidates(
            user_input, detected_context, retrieved_memories, recent_conversation
        )
        logger.debug('phase_4_candidates_retrieved', count=len(candidates))

        # Phase 5: RelevanceScoring
        scored = self._score_relevance(candidates, user_input, analyzed_intent)
        logger.debug('phase_5_relevance_scored', count=len(scored))

        # Phase 6: ConflictResolution
        resolved = self._resolve_conflicts(scored)
        logger.debug('phase_6_conflicts_resolved', count=len(resolved))

        # Phase 7: Assembly
        assembled = self._assemble(resolved)
        result.activated_objects = list(assembled)
        logger.debug('phase_7_assembled', count=len(assembled))

        # Phase 8: Inference
        inferences = self._infer(assembled)
        logger.debug('phase_8_inferences', count=len(inferences))

        # Phase 9: DialogueGeneration
        dialogue_context = self._generate_dialogue_context(assembled, inferences)
        result.metadata['dialogue_context'] = dialogue_context

        # Phase 10: Update
        self._update(assembled)
        result.open_loops = list(self._open_loops.values())
        result.snapshot = self._take_snapshot()
        result.context_switches = list(self._context_history[-5:])

        return result

    def activate(
        self,
        source_memory: str,
        activation_reason: str,
        *,
        activation_score: float = 0.5,
        priority_score: float = 0.5,
        supporting_evidence: tuple[str, ...] = (),
        associated_episode: str = '',
        associated_cognitive_objects: tuple[str, ...] = (),
        associated_projects: tuple[str, ...] = (),
        temporal_relevance: float = 0.5,
        estimated_lifetime: float = 300.0,
        dependency_links: tuple[str, ...] = (),
    ) -> WorkingMemoryObject:
        """Activate a new item in working memory."""
        obj_id = f"wm_{uuid.uuid4().hex[:12]}"
        obj = WorkingMemoryObject(
            identifier=obj_id,
            source_memory=source_memory,
            activation_reason=activation_reason,
            activation_score=activation_score,
            priority_score=priority_score,
            supporting_evidence=supporting_evidence,
            associated_episode=associated_episode,
            associated_cognitive_objects=associated_cognitive_objects,
            associated_projects=associated_projects,
            temporal_relevance=temporal_relevance,
            estimated_lifetime=estimated_lifetime,
            dependency_links=dependency_links,
        )

        # Enforce capacity by evicting lowest-scored items
        if len(self._active_objects) >= self._max_capacity:
            self._evict_lowest()

        self._active_objects[obj_id] = obj
        logger.debug('working_memory_activated', object_id=obj_id, reason=activation_reason)
        return obj

    def deactivate(self, object_id: str) -> bool:
        """Remove an item from working memory."""
        if object_id in self._active_objects:
            del self._active_objects[object_id]
            logger.debug('working_memory_deactivated', object_id=object_id)
            return True
        return False

    def get_active_objects(self) -> list[WorkingMemoryObject]:
        """Return all currently active working memory objects."""
        return list(self._active_objects.values())

    def get_open_loops(self) -> list[OpenLoop]:
        """Return all unresolved open loops."""
        return [loop for loop in self._open_loops.values() if not loop.resolved]

    def register_open_loop(
        self,
        category: str,
        description: str,
        *,
        associated_memory_ids: tuple[str, ...] = (),
        priority: float = 0.5,
    ) -> OpenLoop:
        """Register a new open loop."""
        loop_id = f"ol_{uuid.uuid4().hex[:12]}"
        loop = OpenLoop(
            loop_id=loop_id,
            category=category,
            description=description,
            associated_memory_ids=associated_memory_ids,
            priority=priority,
        )
        self._open_loops[loop_id] = loop
        logger.debug('open_loop_registered', loop_id=loop_id, category=category)
        return loop

    def resolve_open_loop(self, loop_id: str, resolution_memory_id: str = '') -> bool:
        """Resolve an open loop."""
        loop = self._open_loops.get(loop_id)
        if loop is None:
            return False
        # Frozen dataclass — replace
        resolved = OpenLoop(
            loop_id=loop.loop_id,
            category=loop.category,
            description=loop.description,
            created_at=loop.created_at,
            associated_memory_ids=loop.associated_memory_ids,
            priority=loop.priority,
            resolved=True,
            resolution_memory_id=resolution_memory_id,
        )
        self._open_loops[loop_id] = resolved
        logger.debug('open_loop_resolved', loop_id=loop_id)
        return True

    def take_snapshot(self) -> WorkingMemorySnapshot:
        """Take and return a snapshot of current working memory state."""
        return self._take_snapshot()

    def decay_all(self) -> int:
        """Apply decay to all active objects. Returns count of objects expired."""
        expired_ids: list[str] = []
        for obj_id, obj in self._active_objects.items():
            new_lifetime = obj.estimated_lifetime - self._decay_rate
            if new_lifetime <= 0.0:
                expired_ids.append(obj_id)
            else:
                # Rebuild with reduced lifetime
                decayed = WorkingMemoryObject(
                    identifier=obj.identifier,
                    source_memory=obj.source_memory,
                    activation_reason=obj.activation_reason,
                    activation_score=obj.activation_score * (1.0 - self._decay_rate),
                    priority_score=obj.priority_score,
                    supporting_evidence=obj.supporting_evidence,
                    associated_episode=obj.associated_episode,
                    associated_cognitive_objects=obj.associated_cognitive_objects,
                    associated_projects=obj.associated_projects,
                    temporal_relevance=obj.temporal_relevance * (1.0 - self._decay_rate),
                    estimated_lifetime=new_lifetime,
                    dependency_links=obj.dependency_links,
                    explainability_metadata=obj.explainability_metadata,
                )
                self._active_objects[obj_id] = decayed

        for oid in expired_ids:
            del self._active_objects[oid]

        if expired_ids:
            logger.debug('working_memory_decay', expired_count=len(expired_ids))
        return len(expired_ids)

    def create_context_window(
        self,
        window_type: str,
        *,
        max_capacity: int = DEFAULT_CONTEXT_WINDOW_CAPACITY,
    ) -> ContextWindow:
        """Create a new context window."""
        window_id = f"cw_{uuid.uuid4().hex[:12]}"
        window = ContextWindow(
            window_type=window_type,
            window_id=window_id,
            max_capacity=max_capacity,
        )
        self._context_windows[window_id] = window
        return window

    # ------------------------------------------------------------------
    # Phase 2: IntentAnalysis
    # ------------------------------------------------------------------

    def _analyze_intent(self, user_input: str, explicit_intent: str) -> str:
        """Analyze user input to determine the intent."""
        if explicit_intent and explicit_intent != 'recall':
            return explicit_intent

        lower = user_input.lower()
        if any(kw in lower for kw in ('why', 'explain', 'reason')):
            return 'explain'
        if any(kw in lower for kw in ('compare', 'difference', 'versus')):
            return 'compare'
        if any(kw in lower for kw in ('plan', 'should i', 'next step')):
            return 'plan'
        if any(kw in lower for kw in ('remember', 'recall', 'what did')):
            return 'recall'
        if any(kw in lower for kw in ('reflect', 'think about', 'consider')):
            return 'reflect'
        if any(kw in lower for kw in ('check', 'verify', 'confirm')):
            return 'verify'
        return 'recall'

    # ------------------------------------------------------------------
    # Phase 3: ContextDetection
    # ------------------------------------------------------------------

    def _detect_context(
        self,
        user_input: str,
        intent: str,
        cognitive_focus: str,
    ) -> str:
        """Detect the appropriate context window."""
        if cognitive_focus:
            return 'project'
        if intent in ('recall', 'explain'):
            return 'session'
        if intent == 'reflect':
            return 'episode'
        if intent == 'plan':
            return 'longitudinal'
        return 'immediate'

    # ------------------------------------------------------------------
    # Phase 4: MemoryRetrieval
    # ------------------------------------------------------------------

    def _retrieve_candidates(
        self,
        user_input: str,
        context: str,
        retrieved_memories: list[dict[str, Any]] | None,
        recent_conversation: list[str] | None,
    ) -> list[WorkingMemoryObject]:
        """Retrieve candidate memories for working memory activation."""
        candidates: list[WorkingMemoryObject] = []

        # From explicit retrieved memories
        if retrieved_memories:
            for mem in retrieved_memories:
                obj = WorkingMemoryObject(
                    identifier=mem.get('id', f"wm_{uuid.uuid4().hex[:8]}"),
                    source_memory=mem.get('source', 'episodic_memory'),
                    activation_reason=mem.get('reason', 'retrieved'),
                    activation_score=mem.get('score', 0.5),
                    priority_score=mem.get('priority', 0.5),
                    supporting_evidence=tuple(mem.get('evidence', [])),
                    associated_episode=mem.get('episode', ''),
                )
                candidates.append(obj)

        # From recent conversation
        if recent_conversation:
            for i, turn in enumerate(recent_conversation[-5:]):
                obj = WorkingMemoryObject(
                    identifier=f"rc_{uuid.uuid4().hex[:8]}",
                    source_memory='recent_conversation',
                    activation_reason='recent_context',
                    activation_score=0.8 - (i * 0.1),
                    priority_score=0.6,
                )
                candidates.append(obj)

        # From currently active working memory (carry forward relevant items)
        for obj in self._active_objects.values():
            if obj.temporal_relevance > 0.3:
                candidates.append(obj)

        return candidates

    # ------------------------------------------------------------------
    # Phase 5: RelevanceScoring
    # ------------------------------------------------------------------

    def _score_relevance(
        self,
        candidates: list[WorkingMemoryObject],
        user_input: str,
        intent: str,
    ) -> list[WorkingMemoryObject]:
        """Score each candidate for relevance to the current context."""
        scored: list[WorkingMemoryObject] = []
        input_words = set(user_input.lower().split())

        for obj in candidates:
            # Base score from activation
            base_score = obj.effective_score

            # Boost for matching source
            source_boost = 0.0
            if obj.source_memory == 'current_conversation':
                source_boost = 0.2
            elif obj.source_memory == 'recent_conversation':
                source_boost = 0.15

            # Boost for supporting evidence
            evidence_boost = min(0.15, len(obj.supporting_evidence) * 0.05)

            final_score = min(1.0, base_score + source_boost + evidence_boost)

            scored_obj = WorkingMemoryObject(
                identifier=obj.identifier,
                source_memory=obj.source_memory,
                activation_reason=obj.activation_reason,
                activation_score=final_score,
                priority_score=obj.priority_score,
                supporting_evidence=obj.supporting_evidence,
                associated_episode=obj.associated_episode,
                associated_cognitive_objects=obj.associated_cognitive_objects,
                associated_projects=obj.associated_projects,
                temporal_relevance=obj.temporal_relevance,
                estimated_lifetime=obj.estimated_lifetime,
                dependency_links=obj.dependency_links,
                explainability_metadata=obj.explainability_metadata,
            )
            scored.append(scored_obj)

        # Sort by score descending
        scored.sort(key=lambda o: o.activation_score, reverse=True)
        return scored

    # ------------------------------------------------------------------
    # Phase 6: ConflictResolution
    # ------------------------------------------------------------------

    def _resolve_conflicts(
        self,
        scored: list[WorkingMemoryObject],
    ) -> list[WorkingMemoryObject]:
        """Resolve conflicts between competing working memory items."""
        if not scored:
            return scored

        # Group by source memory to detect duplicates
        seen_sources: dict[str, WorkingMemoryObject] = {}
        resolved: list[WorkingMemoryObject] = []

        for obj in scored:
            source_key = obj.source_memory
            if source_key in seen_sources:
                # Keep the one with higher score
                existing = seen_sources[source_key]
                if obj.activation_score > existing.activation_score:
                    seen_sources[source_key] = obj
            else:
                seen_sources[source_key] = obj

        resolved = list(seen_sources.values())
        resolved.sort(key=lambda o: o.activation_score, reverse=True)
        return resolved

    # ------------------------------------------------------------------
    # Phase 7: Assembly
    # ------------------------------------------------------------------

    def _assemble(
        self,
        resolved: list[WorkingMemoryObject],
    ) -> list[WorkingMemoryObject]:
        """Assemble the final working memory set within capacity limits."""
        assembled: list[WorkingMemoryObject] = []
        remaining_capacity = self._max_capacity

        for obj in resolved:
            if remaining_capacity <= 0:
                break
            assembled.append(obj)
            remaining_capacity -= 1

        return assembled

    # ------------------------------------------------------------------
    # Phase 8: Inference
    # ------------------------------------------------------------------

    def _infer(
        self,
        assembled: list[WorkingMemoryObject],
    ) -> list[dict[str, Any]]:
        """Generate inferences from the assembled working memory."""
        inferences: list[dict[str, Any]] = []

        # Detect potential connections between items
        for i, obj_a in enumerate(assembled):
            for obj_b in assembled[i + 1:]:
                # Check for shared episodes
                if (
                    obj_a.associated_episode
                    and obj_a.associated_episode == obj_b.associated_episode
                ):
                    inferences.append({
                        'type': 'episode_connection',
                        'source': obj_a.identifier,
                        'target': obj_b.identifier,
                        'episode': obj_a.associated_episode,
                    })

                # Check for shared cognitive objects
                shared = set(obj_a.associated_cognitive_objects) & set(
                    obj_b.associated_cognitive_objects
                )
                if shared:
                    inferences.append({
                        'type': 'cognitive_connection',
                        'source': obj_a.identifier,
                        'target': obj_b.identifier,
                        'shared_objects': tuple(shared),
                    })

        return inferences

    # ------------------------------------------------------------------
    # Phase 9: DialogueGeneration
    # ------------------------------------------------------------------

    def _generate_dialogue_context(
        self,
        assembled: list[WorkingMemoryObject],
        inferences: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate context for dialogue generation."""
        return {
            'active_memory_count': len(assembled),
            'inference_count': len(inferences),
            'top_sources': [
                obj.source_memory for obj in assembled[:5]
            ],
            'open_loop_count': len(self.get_open_loops()),
        }

    # ------------------------------------------------------------------
    # Phase 10: Update
    # ------------------------------------------------------------------

    def _update(self, assembled: list[WorkingMemoryObject]) -> None:
        """Update working memory state with assembled objects."""
        # Record context switch
        previous_state = tuple(self._active_objects.values())
        new_activation = tuple(assembled)

        switch = ContextSwitch(
            previous_state=previous_state,
            reason='pipeline_update',
            new_activation_set=new_activation,
        )
        self._context_history.append(switch)

        # Replace active objects
        self._active_objects.clear()
        for obj in assembled:
            self._active_objects[obj.identifier] = obj

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _evict_lowest(self) -> WorkingMemoryObject | None:
        """Evict the lowest-scored active object."""
        if not self._active_objects:
            return None
        lowest_id = min(
            self._active_objects,
            key=lambda k: self._active_objects[k].effective_score,
        )
        return self._active_objects.pop(lowest_id)

    def _take_snapshot(self) -> WorkingMemorySnapshot:
        """Create a snapshot of current working memory state."""
        self._snapshot_counter += 1
        return WorkingMemorySnapshot(
            snapshot_id=f"snap_{self._snapshot_counter}",
            active_objects=tuple(self._active_objects.values()),
            context_windows=tuple(self._context_windows.values()),
            open_loops=tuple(self._open_loops.values()),
            timestamp=datetime.now(UTC),
        )
