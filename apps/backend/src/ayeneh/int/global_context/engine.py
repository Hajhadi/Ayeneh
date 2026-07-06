"""INT-02 Global Context Manager — 7-phase context management pipeline."""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog

from ayeneh.int.global_context.types import (
    CONTEXT_DIMENSIONS,
    ContextConflict,
    ContextDistribution,
    ContextEntry,
    ContextPriority,
    ExplainabilityMetadata,
    GlobalContextObject,
    GlobalContextResult,
)

logger = structlog.get_logger(__name__)


class GlobalContextManager:
    """Manages global context across all cognitive modules through a 7-phase pipeline.

    Phases:
        1. ContextExtraction     — extract context from various sources
        2. ContextIntegration    — merge extracted context into a unified view
        3. ConflictDetection     — identify contradictions and inconsistencies
        4. ContextPrioritization  — rank context entries by relevance and recency
        5. GlobalContextState    — build the unified global context object
        6. ContextDistribution   — distribute relevant context to modules
        7. ModuleExecution       — apply context to module execution
    """

    def __init__(self) -> None:
        self._registered_modules: list[str] = []

    def register_module(self, module_id: str) -> None:
        if module_id not in self._registered_modules:
            self._registered_modules.append(module_id)

    def manage_context(
        self,
        context_sources: dict[str, Any] | None = None,
        context_id: str = '',
        goals: list[str] | None = None,
        session_id: str = '',
        target_modules: list[str] | None = None,
    ) -> GlobalContextResult:
        start = time.monotonic()
        sources = context_sources or {}
        errors: list[str] = []

        if not context_id:
            context_id = str(uuid.uuid4())

        logger.info(
            "context_management_started",
            context_id=context_id,
            session_id=session_id,
        )

        # Phase 1: ContextExtraction
        entries = self._phase_context_extraction(sources, errors)

        # Phase 2: ContextIntegration
        integrated = self._phase_context_integration(entries, errors)

        # Phase 3: ConflictDetection
        conflicts = self._phase_conflict_detection(integrated, errors)

        # Phase 4: ContextPrioritization
        priorities = self._phase_context_prioritization(integrated, goals or [], errors)

        # Phase 5: GlobalContextState
        context_obj = self._phase_global_context_state(
            context_id, integrated, goals or [], priorities, errors,
        )

        # Phase 6: ContextDistribution
        distributions = self._phase_context_distribution(
            context_obj, target_modules or self._registered_modules, errors,
        )

        # Phase 7: ModuleExecution
        final_obj = self._phase_module_execution(context_obj, distributions, errors)

        duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            "context_management_completed",
            context_id=context_id,
            entries=len(integrated),
            conflicts=len(conflicts),
            duration_ms=duration_ms,
        )

        return GlobalContextResult(
            context_id=context_id,
            context_object=final_obj,
            entries=tuple(integrated),
            conflicts=tuple(conflicts),
            priorities=tuple(priorities),
            distributions=tuple(distributions),
            confidence=final_obj.confidence,
            duration_ms=duration_ms,
            errors=tuple(errors),
        )

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    def _phase_context_extraction(
        self,
        sources: dict[str, Any],
        errors: list[str],
    ) -> list[ContextEntry]:
        """Phase 1: Extract context from various sources."""
        try:
            entries: list[ContextEntry] = []

            # Extract from explicit source types
            if 'goals' in sources:
                entries.append(ContextEntry(
                    entry_id=str(uuid.uuid4()),
                    dimension='strategic',
                    level='project',
                    persistence='workflow',
                    content={'goals': sources['goals']},
                    source_module='context_manager',
                    confidence=0.9,
                ))

            if 'dialogue_state' in sources:
                entries.append(ContextEntry(
                    entry_id=str(uuid.uuid4()),
                    dimension='conversational',
                    level='immediate',
                    persistence='transient',
                    content={'state': sources['dialogue_state']},
                    source_module='dialogue',
                    confidence=0.85,
                ))

            if 'temporal' in sources:
                entries.append(ContextEntry(
                    entry_id=str(uuid.uuid4()),
                    dimension='temporal',
                    level='task',
                    persistence='session',
                    content=sources['temporal'] if isinstance(sources['temporal'], dict) else {'value': sources['temporal']},
                    source_module='context_manager',
                    confidence=0.8,
                ))

            if 'environment' in sources:
                entries.append(ContextEntry(
                    entry_id=str(uuid.uuid4()),
                    dimension='environmental',
                    level='domain',
                    persistence='persistent',
                    content=sources['environment'] if isinstance(sources['environment'], dict) else {'value': sources['environment']},
                    source_module='context_manager',
                    confidence=0.7,
                ))

            if 'memory_references' in sources:
                entries.append(ContextEntry(
                    entry_id=str(uuid.uuid4()),
                    dimension='operational',
                    level='workflow',
                    persistence='persistent',
                    content={'references': sources['memory_references']},
                    source_module='memory',
                    confidence=0.75,
                ))

            # Generic fallback: wrap remaining keys as operational entries
            extracted_keys = {'goals', 'dialogue_state', 'temporal', 'environment', 'memory_references'}
            for key, value in sources.items():
                if key not in extracted_keys:
                    entries.append(ContextEntry(
                        entry_id=str(uuid.uuid4()),
                        dimension='operational',
                        level='task',
                        persistence='session',
                        content={key: value},
                        source_module='context_manager',
                        confidence=0.6,
                    ))

            # Ensure at least one entry
            if not entries:
                entries.append(ContextEntry(
                    entry_id=str(uuid.uuid4()),
                    dimension='operational',
                    level='global',
                    persistence='session',
                    content={'status': 'empty_context'},
                    source_module='context_manager',
                    confidence=0.3,
                ))

            logger.debug("phase_context_extraction_completed", count=len(entries))
            return entries
        except Exception as exc:
            errors.append(f"Phase 1 (ContextExtraction) error: {exc}")
            return [ContextEntry(
                entry_id=str(uuid.uuid4()),
                dimension='operational',
                level='global',
                content={'error': str(exc)},
            )]

    def _phase_context_integration(
        self,
        entries: list[ContextEntry],
        errors: list[str],
    ) -> list[ContextEntry]:
        """Phase 2: Merge extracted context into a unified view."""
        try:
            # Group by dimension, keep highest confidence per dimension
            by_dim: dict[str, list[ContextEntry]] = {}
            for entry in entries:
                by_dim.setdefault(entry.dimension, []).append(entry)

            integrated: list[ContextEntry] = []
            for dim, group in by_dim.items():
                # Sort by confidence descending, take the best
                best = max(group, key=lambda e: e.confidence)
                # Merge content from same-dimension entries
                merged_content: dict[str, Any] = {}
                for entry in group:
                    merged_content.update(entry.content)

                integrated.append(ContextEntry(
                    entry_id=best.entry_id,
                    dimension=dim,
                    level=best.level,
                    persistence=best.persistence,
                    content=merged_content,
                    source_module=best.source_module,
                    confidence=best.confidence,
                ))

            logger.debug("phase_context_integration_completed", count=len(integrated))
            return integrated
        except Exception as exc:
            errors.append(f"Phase 2 (ContextIntegration) error: {exc}")
            return entries

    def _phase_conflict_detection(
        self,
        entries: list[ContextEntry],
        errors: list[str],
    ) -> list[ContextConflict]:
        """Phase 3: Identify contradictions and inconsistencies."""
        try:
            conflicts: list[ContextConflict] = []
            for i, a in enumerate(entries):
                for b in entries[i + 1:]:
                    # Check for overlapping content keys with different values
                    overlap = set(a.content.keys()) & set(b.content.keys())
                    for key in overlap:
                        if a.content[key] != b.content[key]:
                            conflicts.append(ContextConflict(
                                conflict_id=str(uuid.uuid4()),
                                entry_a_id=a.entry_id,
                                entry_b_id=b.entry_id,
                                conflict_type='contradiction',
                                dimension=a.dimension,
                                severity='medium',
                                resolution_strategy='highest_confidence',
                                description=f"Conflicting values for '{key}' between {a.source_module} and {b.source_module}",
                            ))

                    # Check for temporal ordering issues
                    if a.dimension == 'temporal' and b.dimension == 'temporal':
                        if a.content != b.content:
                            conflicts.append(ContextConflict(
                                conflict_id=str(uuid.uuid4()),
                                entry_a_id=a.entry_id,
                                entry_b_id=b.entry_id,
                                conflict_type='ambiguous',
                                dimension='temporal',
                                severity='low',
                                resolution_strategy='most_recent',
                                description='Multiple temporal context entries',
                            ))

            logger.debug("phase_conflict_detection_completed", count=len(conflicts))
            return conflicts
        except Exception as exc:
            errors.append(f"Phase 3 (ConflictDetection) error: {exc}")
            return []

    def _phase_context_prioritization(
        self,
        entries: list[ContextEntry],
        goals: list[str],
        errors: list[str],
    ) -> list[ContextPriority]:
        """Phase 4: Rank context entries by relevance and recency."""
        try:
            priorities: list[ContextPriority] = []
            for entry in entries:
                # Score based on confidence, level relevance, and goal alignment
                level_weights = {
                    'immediate': 1.0,
                    'task': 0.9,
                    'workflow': 0.8,
                    'project': 0.7,
                    'domain': 0.6,
                    'global': 0.5,
                }
                level_score = level_weights.get(entry.level, 0.5)

                # Goal alignment: check if content values appear in goals
                content_str = str(entry.content).lower()
                goal_overlap = sum(1 for g in goals if g.lower() in content_str)
                goal_score = min(goal_overlap / max(len(goals), 1), 1.0)

                priority_score = (
                    entry.confidence * 0.4
                    + level_score * 0.3
                    + goal_score * 0.3
                )

                priorities.append(ContextPriority(
                    entry_id=entry.entry_id,
                    priority_score=priority_score,
                    reason=f"confidence={entry.confidence:.2f}, level={entry.level}, goal_overlap={goal_score:.2f}",
                    factor_breakdown={
                        'confidence': entry.confidence,
                        'level_weight': level_score,
                        'goal_alignment': goal_score,
                    },
                ))

            priorities.sort(key=lambda p: p.priority_score, reverse=True)
            logger.debug("phase_context_prioritization_completed", count=len(priorities))
            return priorities
        except Exception as exc:
            errors.append(f"Phase 4 (ContextPrioritization) error: {exc}")
            return [ContextPriority(entry_id=e.entry_id, priority_score=0.5) for e in entries]

    def _phase_global_context_state(
        self,
        context_id: str,
        entries: list[ContextEntry],
        goals: list[str],
        priorities: list[ContextPriority],
        errors: list[str],
    ) -> GlobalContextObject:
        """Phase 5: Build the unified global context object."""
        try:
            priority_map = {p.entry_id: p.priority_score for p in priorities}
            avg_confidence = sum(e.confidence for e in entries) / max(len(entries), 1)

            # Extract specific context fields
            temporal_entries = [e for e in entries if e.dimension == 'temporal']
            env_entries = [e for e in entries if e.dimension == 'environmental']
            task_entries = [e for e in entries if e.dimension == 'operational']

            temporal_ctx = {}
            for e in temporal_entries:
                temporal_ctx.update(e.content)

            env_ctx = {}
            for e in env_entries:
                env_ctx.update(e.content)

            task_ctx = {}
            for e in task_entries:
                task_ctx.update(e.content)

            # Find dialogue state
            conv_entries = [e for e in entries if e.dimension == 'conversational']
            dialogue_state = ''
            for e in conv_entries:
                dialogue_state = str(e.content.get('state', ''))

            explainability = ExplainabilityMetadata(
                reasoning_chain=(
                    f"Extracted {len(entries)} context entries",
                    f"Detected {len(set(e.dimension for e in entries))} dimensions",
                    f"Average confidence: {avg_confidence:.2f}",
                ),
                contributing_factors=tuple(
                    {'entry_id': e.entry_id, 'dimension': e.dimension, 'confidence': e.confidence}
                    for e in entries
                ),
                confidence_decomposition={
                    'extraction_confidence': avg_confidence,
                    'integration_coverage': len(entries) / max(len(CONTEXT_DIMENSIONS), 1),
                },
            )

            obj = GlobalContextObject(
                context_id=context_id,
                current_goals=tuple(goals),
                dialogue_state=dialogue_state,
                environmental_context=env_ctx,
                temporal_context=temporal_ctx,
                task_context=task_ctx,
                priority_map=priority_map,
                confidence=avg_confidence,
                explainability_metadata={
                    'reasoning_chain': explainability.reasoning_chain,
                    'contributing_factors': explainability.contributing_factors,
                    'confidence_decomposition': explainability.confidence_decomposition,
                },
            )

            logger.debug("phase_global_context_state_completed")
            return obj
        except Exception as exc:
            errors.append(f"Phase 5 (GlobalContextState) error: {exc}")
            return GlobalContextObject(context_id=context_id)

    def _phase_context_distribution(
        self,
        context_obj: GlobalContextObject,
        target_modules: list[str],
        errors: list[str],
    ) -> list[ContextDistribution]:
        """Phase 6: Distribute relevant context to modules."""
        try:
            distributions: list[ContextDistribution] = []
            for module_id in target_modules:
                # Each module gets all context (filtered distribution can be added later)
                distributions.append(ContextDistribution(
                    module_id=module_id,
                    entries=(context_obj.context_id,),
                    acknowledgement=False,
                ))

            logger.debug("phase_context_distribution_completed", count=len(distributions))
            return distributions
        except Exception as exc:
            errors.append(f"Phase 6 (ContextDistribution) error: {exc}")
            return []

    def _phase_module_execution(
        self,
        context_obj: GlobalContextObject,
        distributions: list[ContextDistribution],
        errors: list[str],
    ) -> GlobalContextObject:
        """Phase 7: Apply context to module execution (update context with distribution results)."""
        try:
            distributed_modules = tuple(d.module_id for d in distributions)
            all_acknowledged = all(d.acknowledgement for d in distributions) if distributions else True

            # Update context with distribution metadata
            updated_metadata = dict(context_obj.explainability_metadata)
            updated_metadata['distribution'] = {
                'modules': distributed_modules,
                'all_acknowledged': all_acknowledged,
                'distribution_count': len(distributions),
            }

            # Rebuild object with updated metadata (frozen dataclass)
            updated_obj = GlobalContextObject(
                context_id=context_obj.context_id,
                current_goals=context_obj.current_goals,
                active_workflows=context_obj.active_workflows,
                relevant_memory_references=context_obj.relevant_memory_references,
                dialogue_state=context_obj.dialogue_state,
                environmental_context=context_obj.environmental_context,
                temporal_context=context_obj.temporal_context,
                task_context=context_obj.task_context,
                priority_map=context_obj.priority_map,
                known_constraints=context_obj.known_constraints,
                confidence=context_obj.confidence,
                revision_history=context_obj.revision_history,
                creation_timestamp=context_obj.creation_timestamp,
                explainability_metadata=updated_metadata,
            )

            logger.debug("phase_module_execution_completed")
            return updated_obj
        except Exception as exc:
            errors.append(f"Phase 7 (ModuleExecution) error: {exc}")
            return context_obj
