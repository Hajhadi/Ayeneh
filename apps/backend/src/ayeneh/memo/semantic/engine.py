"""Semantic personal memory engine (MEM-03).

Six-phase pipeline:
1. Evidence Aggregation
2. Repeated Observation Detection
3. Cross-Episode Validation
4. Semantic Candidate Formation
5. Consolidation
6. Knowledge Graph Integration
"""

from __future__ import annotations

import uuid

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.base import make_version_record
from ayeneh.memo.semantic.types import (
    KNOWLEDGE_CATEGORIES,
    KnowledgeEdge,
    KnowledgeNode,
    SemanticMemoryObject,
    SemanticVersionRecord,
)
from ayeneh.memo.types import Event, EvidenceRecord, Observation

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_REPETITION_THRESHOLD: int = 3
DEFAULT_VALIDATION_MIN_EPISODES: int = 2
DEFAULT_CONSOLIDATION_CONFIDENCE_THRESHOLD: float = 0.6

# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------


class SemanticPipelineResult:
    """Result of running the semantic memory pipeline."""

    __slots__ = ('semantic_objects', 'knowledge_nodes', 'knowledge_edges', 'metadata')

    def __init__(self) -> None:
        self.semantic_objects: list[SemanticMemoryObject] = []
        self.knowledge_nodes: list[KnowledgeNode] = []
        self.knowledge_edges: list[KnowledgeEdge] = []
        self.metadata: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class SemanticMemoryEngine:
    """Six-phase semantic personal memory pipeline.

    Processes observations, episodes, and conversations into stable
    semantic knowledge objects.
    """

    def __init__(
        self,
        repetition_threshold: int = DEFAULT_REPETITION_THRESHOLD,
        validation_min_episodes: int = DEFAULT_VALIDATION_MIN_EPISODES,
        consolidation_confidence_threshold: float = DEFAULT_CONSOLIDATION_CONFIDENCE_THRESHOLD,
        ai_router: Any = None,
    ) -> None:
        self._repetition_threshold = repetition_threshold
        self._validation_min_episodes = validation_min_episodes
        self._consolidation_threshold = consolidation_confidence_threshold
        self._ai_router = ai_router
        self._semantic_store: list[SemanticMemoryObject] = []
        self._knowledge_nodes: list[KnowledgeNode] = []
        self._knowledge_edges: list[KnowledgeEdge] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_pipeline(
        self,
        observations: list[Observation],
        episode_ids: tuple[str, ...] = (),
        conversation_ids: tuple[str, ...] = (),
    ) -> SemanticPipelineResult:
        """Run the full 6-phase pipeline."""
        result = SemanticPipelineResult()

        if not observations:
            return result

        # Phase 1: Evidence Aggregation
        evidence_records = self._aggregate_evidence(observations)
        logger.debug('phase_1_evidence_aggregated', count=len(evidence_records))

        # Phase 2: Repeated Observation Detection
        repeated = self._detect_repeated_observations(evidence_records)
        logger.debug('phase_2_repeated_detected', count=len(repeated))

        # Phase 3: Cross-Episode Validation
        validated = self._cross_episode_validation(repeated, episode_ids)
        logger.debug('phase_3_validated', count=len(validated))

        # Phase 4: Semantic Candidate Formation
        candidates = self._form_candidates(validated, episode_ids, conversation_ids)
        logger.debug('phase_4_candidates_formed', count=len(candidates))

        # Phase 5: Consolidation
        consolidated = self._consolidate(candidates)
        result.semantic_objects = consolidated
        logger.debug('phase_5_consolidated', count=len(consolidated))

        # Phase 6: Knowledge Graph Integration
        nodes, edges = self._integrate_knowledge_graph(consolidated)
        result.knowledge_nodes = nodes
        result.knowledge_edges = edges
        logger.debug('phase_6_integrated', nodes=len(nodes), edges=len(edges))

        return result

    def get_semantic_object(self, object_id: str) -> SemanticMemoryObject | None:
        """Retrieve a semantic object by ID."""
        for obj in self._semantic_store:
            if obj.identifier == object_id:
                return obj
        return None

    def list_by_category(self, category: str) -> list[SemanticMemoryObject]:
        """List all semantic objects in a given category."""
        return [obj for obj in self._semantic_store if obj.knowledge_category == category]

    def list_stable(self) -> list[SemanticMemoryObject]:
        """List all stable semantic objects."""
        return [obj for obj in self._semantic_store if obj.is_stable]

    # ------------------------------------------------------------------
    # Phase 1: Evidence Aggregation
    # ------------------------------------------------------------------

    def _aggregate_evidence(self, observations: list[Observation]) -> list[EvidenceRecord]:
        """Transform observations into evidence records."""
        records: list[EvidenceRecord] = []
        for obs in observations:
            record = EvidenceRecord(
                evidence_id=f"sev_{obs.observation_id}",
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
    # Phase 2: Repeated Observation Detection
    # ------------------------------------------------------------------

    def _detect_repeated_observations(
        self,
        evidence: list[EvidenceRecord],
    ) -> list[dict[str, Any]]:
        """Find patterns that appear repeatedly across evidence."""
        # Try LLM-assisted extraction first for richer patterns
        if len(evidence) >= self._repetition_threshold:
            llm_patterns = self._try_llm_semantic_extraction(evidence)
            if llm_patterns:
                llm_repeated: list[dict[str, Any]] = []
                for pat in llm_patterns:
                    pattern_text = pat.get('pattern', '')
                    if pattern_text:
                        matching = [e for e in evidence if pattern_text.lower() in e.content.lower()]
                        if len(matching) >= self._repetition_threshold:
                            llm_repeated.append({
                                'pattern': pattern_text,
                                'count': len(matching),
                                'evidence': tuple(r.evidence_id for r in matching),
                                'sources': tuple({r.source for r in matching}),
                                'first_observed': min(r.timestamp for r in matching),
                                'last_observed': max(r.timestamp for r in matching),
                            })
                if llm_repeated:
                    return llm_repeated

        # Group by content similarity (simple keyword-based)
        keyword_groups: dict[str, list[EvidenceRecord]] = {}

        for rec in evidence:
            keywords = self._extract_keywords(rec.content)
            for kw in keywords:
                if kw not in keyword_groups:
                    keyword_groups[kw] = []
                keyword_groups[kw].append(rec)

        repeated: list[dict[str, Any]] = []
        for keyword, recs in keyword_groups.items():
            if len(recs) >= self._repetition_threshold:
                unique_sources = list({r.source for r in recs})
                repeated.append({
                    'pattern': keyword,
                    'count': len(recs),
                    'evidence': tuple(r.evidence_id for r in recs),
                    'sources': tuple(unique_sources),
                    'first_observed': min(r.timestamp for r in recs),
                    'last_observed': max(r.timestamp for r in recs),
                })

        return repeated

    def _extract_keywords(self, content: str) -> list[str]:
        """Extract meaningful keywords from content."""
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'shall',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'as', 'into', 'through', 'during', 'before', 'after', 'and',
            'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either',
            'neither', 'each', 'every', 'all', 'any', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'only', 'own', 'same',
            'than', 'too', 'very', 'just', 'because', 'that', 'this',
            'these', 'those', 'it', 'its', 'i', 'me', 'my', 'we', 'our',
            'you', 'your', 'he', 'him', 'his', 'she', 'her', 'they',
            'them', 'their', 'what', 'which', 'who', 'whom',
        }
        words = content.lower().split()
        return [w for w in words if len(w) > 3 and w.isalpha() and w not in stopwords]

    def _try_llm_semantic_extraction(self, evidence: list[EvidenceRecord]) -> list[dict[str, Any]] | None:
        """Attempt LLM-assisted semantic knowledge extraction."""
        if self._ai_router is None:
            return None
        try:
            import asyncio
            from ayeneh.ai_router.types import AITask, AITaskType
            evidence_summary = '; '.join(e.content[:80] for e in evidence[:10])
            prompt = (
                'Analyze the following evidence and extract semantic knowledge patterns. '
                'Return a JSON list of objects with keys: pattern, category, confidence.\n\n'
                f'Evidence:\n{evidence_summary}'
            )
            task = AITask(
                task_type=AITaskType.CONVERSATION_GENERATION,
                content=prompt,
                max_tokens=1024,
                temperature=0.3,
            )
            messages = [
                {'role': 'system', 'content': 'You are a memory analysis assistant.'},
                {'role': 'user', 'content': prompt},
            ]
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return None
            result = loop.run_until_complete(self._ai_router.chat(task, messages))
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            return self._parse_llm_response(content)
        except Exception:
            return None

    def _parse_llm_response(self, content: str) -> list[dict[str, Any]] | None:
        """Parse LLM JSON response into structured data."""
        import json
        try:
            start = content.find('[')
            end = content.rfind(']') + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    # ------------------------------------------------------------------
    # Phase 3: Cross-Episode Validation
    # ------------------------------------------------------------------

    def _cross_episode_validation(
        self,
        repeated: list[dict[str, Any]],
        episode_ids: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        """Validate repeated patterns against episode context."""
        validated: list[dict[str, Any]] = []

        for pattern in repeated:
            # Patterns with more sources and higher counts are more valid
            source_diversity = len(pattern['sources'])
            count = pattern['count']

            validation_score = min(1.0, (source_diversity * 0.3) + (count / (self._repetition_threshold * 3) * 0.7))

            if validation_score >= 0.3:
                validated.append({
                    **pattern,
                    'validation_score': validation_score,
                    'episode_support': len(episode_ids),
                })

        return validated

    # ------------------------------------------------------------------
    # Phase 4: Semantic Candidate Formation
    # ------------------------------------------------------------------

    def _form_candidates(
        self,
        validated: list[dict[str, Any]],
        episode_ids: tuple[str, ...],
        conversation_ids: tuple[str, ...],
    ) -> list[SemanticMemoryObject]:
        """Form semantic memory candidates from validated patterns."""
        candidates: list[SemanticMemoryObject] = []

        for pattern in validated:
            category = self._infer_category(pattern['pattern'])
            confidence = pattern['validation_score']

            candidate = SemanticMemoryObject(
                identifier=f"sem_{uuid.uuid4().hex[:12]}",
                knowledge_statement=f"Pattern observed: {pattern['pattern']} (repeated {pattern['count']} times)",
                knowledge_category=category,
                supporting_evidence=pattern['evidence'],
                supporting_episodes=episode_ids,
                supporting_conversations=conversation_ids,
                confidence=confidence,
                importance=confidence * 0.8,
                temporal_stability='medium_term',
                creation_time=pattern['first_observed'],
                last_confirmation=pattern['last_observed'],
            )
            candidates.append(candidate)

        return candidates

    def _infer_category(self, pattern: str) -> str:
        """Infer knowledge category from a pattern keyword."""
        category_keywords = {
            'skills': ('skill', 'expert', 'proficient', 'know', 'ability'),
            'expertise': ('expert', 'specialist', 'authority', 'deep'),
            'personal_interests': ('interest', 'passion', 'enjoy', 'love', 'fascinated'),
            'learning_preferences': ('learn', 'study', 'prefer', 'style'),
            'communication_style': ('communicate', 'explain', 'discuss', 'write'),
            'decision_style': ('decide', 'choose', 'prefer', 'approach'),
            'behavioral_tendencies': ('tend', 'usually', 'always', 'often', 'habit'),
            'core_values': ('value', 'believe', 'principle', 'important'),
            'stable_beliefs': ('believe', 'think', 'opinion', 'view'),
            'identity_themes': ('identity', 'who i am', 'self', 'person'),
            'preferred_tools': ('tool', 'use', 'prefer', 'software', 'framework'),
            'languages': ('language', 'speak', 'write', 'fluently'),
            'health_practices': ('health', 'exercise', 'diet', 'sleep', 'practice'),
            'research_domains': ('research', 'study', 'domain', 'field', 'area'),
            'long_term_goals': ('goal', 'plan', 'future', 'aspire', 'want'),
            'relationships': ('relationship', 'friend', 'colleague', 'family'),
            'recurring_projects': ('project', 'ongoing', 'recurring', 'regular'),
        }

        pattern_lower = pattern.lower()
        scores: dict[str, int] = {}

        for category, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw in pattern_lower)
            if score > 0:
                scores[category] = score

        if scores:
            return max(scores, key=lambda k: scores[k])  # type: ignore[return-value]
        return 'personal_interests'

    # ------------------------------------------------------------------
    # Phase 5: Consolidation
    # ------------------------------------------------------------------

    def _consolidate(
        self,
        candidates: list[SemanticMemoryObject],
    ) -> list[SemanticMemoryObject]:
        """Consolidate candidates into stable semantic objects."""
        consolidated: list[SemanticMemoryObject] = []

        for candidate in candidates:
            # Check for existing similar semantic objects
            merged = self._try_merge(candidate)
            if merged is not None:
                consolidated.append(merged)
            elif candidate.confidence >= self._consolidation_threshold:
                # Create a new stable semantic object
                version = SemanticVersionRecord(
                    version_number=1,
                    changed_fields={'confidence': candidate.confidence},
                    change_reason='initial consolidation',
                )
                stable = SemanticMemoryObject(
                    identifier=candidate.identifier,
                    knowledge_statement=candidate.knowledge_statement,
                    knowledge_category=candidate.knowledge_category,
                    supporting_evidence=candidate.supporting_evidence,
                    supporting_episodes=candidate.supporting_episodes,
                    supporting_conversations=candidate.supporting_conversations,
                    contradictory_evidence=candidate.contradictory_evidence,
                    confidence=candidate.confidence,
                    importance=candidate.importance,
                    temporal_stability='long_term',
                    creation_time=candidate.creation_time,
                    last_confirmation=candidate.last_confirmation,
                    revision_history=(version,),
                    associated_cognitive_objects=candidate.associated_cognitive_objects,
                    explainability_metadata=candidate.explainability_metadata,
                )
                self._semantic_store.append(stable)
                consolidated.append(stable)

        return consolidated

    def _try_merge(self, candidate: SemanticMemoryObject) -> SemanticMemoryObject | None:
        """Try to merge a candidate with an existing semantic object."""
        for existing in self._semantic_store:
            if existing.knowledge_category != candidate.knowledge_category:
                continue

            # Simple keyword overlap check
            existing_words = set(existing.knowledge_statement.lower().split())
            candidate_words = set(candidate.knowledge_statement.lower().split())
            overlap = existing_words & candidate_words

            if len(overlap) >= 2:
                # Merge: combine evidence, update confidence
                all_evidence = tuple(
                    set(existing.supporting_evidence + candidate.supporting_evidence)
                )
                all_episodes = tuple(
                    set(existing.supporting_episodes + candidate.supporting_episodes)
                )
                merged_confidence = min(1.0, (existing.confidence + candidate.confidence) / 2 + 0.1)

                version = SemanticVersionRecord(
                    version_number=len(existing.revision_history) + 1,
                    changed_fields={
                        'supporting_evidence': len(all_evidence),
                        'confidence': merged_confidence,
                    },
                    change_reason='merged with similar candidate',
                )

                merged = SemanticMemoryObject(
                    identifier=existing.identifier,
                    knowledge_statement=existing.knowledge_statement,
                    knowledge_category=existing.knowledge_category,
                    supporting_evidence=all_evidence,
                    supporting_episodes=all_episodes,
                    supporting_conversations=existing.supporting_conversations,
                    contradictory_evidence=existing.contradictory_evidence,
                    confidence=merged_confidence,
                    importance=max(existing.importance, candidate.importance),
                    temporal_stability=existing.temporal_stability,
                    creation_time=existing.creation_time,
                    last_confirmation=max(existing.last_confirmation, candidate.last_confirmation),
                    revision_history=existing.revision_history + (version,),
                    associated_cognitive_objects=existing.associated_cognitive_objects,
                    explainability_metadata=existing.explainability_metadata,
                )

                # Update store
                idx = self._semantic_store.index(existing)
                self._semantic_store[idx] = merged
                return merged

        return None

    # ------------------------------------------------------------------
    # Phase 6: Knowledge Graph Integration
    # ------------------------------------------------------------------

    def _integrate_knowledge_graph(
        self,
        semantic_objects: list[SemanticMemoryObject],
    ) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:
        """Build knowledge graph nodes and edges from semantic objects."""
        nodes: list[KnowledgeNode] = []
        edges: list[KnowledgeEdge] = []
        node_map: dict[str, KnowledgeNode] = {}

        # Create nodes per category
        for obj in semantic_objects:
            node_id = f"kn_{obj.knowledge_category}"
            if node_id not in node_map:
                node = KnowledgeNode(
                    node_id=node_id,
                    label=obj.knowledge_category.replace('_', ' ').title(),
                    category=obj.knowledge_category,
                    semantic_memory_ids=(obj.identifier,),
                )
                node_map[node_id] = node
                nodes.append(node)
            else:
                existing = node_map[node_id]
                updated = KnowledgeNode(
                    node_id=existing.node_id,
                    label=existing.label,
                    category=existing.category,
                    semantic_memory_ids=existing.semantic_memory_ids + (obj.identifier,),
                    metadata=existing.metadata,
                )
                node_map[node_id] = updated
                idx = nodes.index(existing)
                nodes[idx] = updated

        # Create edges between categories that share evidence
        category_evidence: dict[str, set[str]] = {}
        for obj in semantic_objects:
            if obj.knowledge_category not in category_evidence:
                category_evidence[obj.knowledge_category] = set()
            category_evidence[obj.knowledge_category].update(obj.supporting_evidence)

        categories = list(category_evidence.keys())
        for i in range(len(categories)):
            for j in range(i + 1, len(categories)):
                cat_a = categories[i]
                cat_b = categories[j]
                shared = category_evidence[cat_a] & category_evidence[cat_b]
                if shared:
                    edge = KnowledgeEdge(
                        source_node_id=f"kn_{cat_a}",
                        target_node_id=f"kn_{cat_b}",
                        edge_type='related_to',
                        weight=min(1.0, len(shared) / 5.0),
                        metadata={'shared_evidence_count': len(shared)},
                    )
                    edges.append(edge)

        self._knowledge_nodes.extend(nodes)
        self._knowledge_edges.extend(edges)

        return nodes, edges
