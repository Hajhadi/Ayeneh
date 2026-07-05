"""COG-04 Personal Knowledge Extraction Engine.

Extracts relatively stable, evidence-supported knowledge about an individual
from conversational evidence. Runs a four-phase pipeline:
    Evidence Aggregation → Candidate Extraction → Longitudinal Validation → Canonical Promotion.
"""

from __future__ import annotations

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.cog.knowledge.types import (
    KNOWLEDGE_CATEGORIES,
    KnowledgeExtractionResult,
    PersonalKnowledgeObject,
)

logger = structlog.get_logger(__name__)

# Minimum number of distinct evidence items to move from candidate to provisional
_MIN_EVIDENCE_FOR_PROVISIONAL = 1

# Minimum number of distinct evidence items to promote to canonical
_MIN_EVIDENCE_FOR_CANONICAL = 2

# Evidence categories that map to specific knowledge categories
_EVIDENCE_CATEGORY_MAP: dict[str, str] = {
    'identity_statement': 'personal_identity_facts',
    'self_report': 'biographical',
    'goal_statement': 'learning_objectives',
    'preference': 'preferences',
    'relationship_report': 'relationships',
    'commitment': 'projects',
    'observation_report': 'daily_routines',
    'decision_report': 'career',
}

# Keywords that hint at specific knowledge categories when category mapping is ambiguous
_CATEGORY_KEYWORD_HINTS: dict[str, list[str]] = {
    'education': ['school', 'university', 'college', 'degree', 'studied', 'course', 'class'],
    'career': ['work', 'job', 'company', 'role', 'position', 'career', 'hired', 'employee'],
    'skills': ['skill', 'know how', 'proficient', 'expert', 'can do', 'good at'],
    'languages': ['language', 'speak', 'fluent', 'bilingual', 'persian', 'english', 'french'],
    'interests': ['hobby', 'enjoy', 'like to', 'love', 'passion', 'interest'],
    'tools': ['tool', 'software', 'app', 'application', 'editor', 'IDE'],
    'technologies': ['technology', 'framework', 'library', 'stack', 'platform'],
    'health_logistics': ['health', 'doctor', 'medication', 'condition', 'medical'],
    'daily_routines': ['routine', 'every day', 'usually', 'always', 'morning', 'habit'],
    'creative_work': ['write', 'paint', 'compose', 'create', 'art', 'music', 'design'],
    'learning_objectives': ['learn', 'study', 'goal', 'plan to', 'want to know'],
    'organizations': ['organization', 'group', 'association', 'club', 'team'],
    'possessions': ['own', 'have a', 'bought', 'possession', 'car', 'house'],
    'locations': ['live in', 'from', 'city', 'country', 'location', 'address'],
    'research_topics': ['research', 'investigate', 'explore', 'thesis', 'paper'],
    'biographical': ['born', 'grew up', 'childhood', 'family', 'age', 'birthday'],
    'projects': ['project', 'working on', 'building', 'developing', 'launching'],
}


class PersonalKnowledgeEngine:
    """Extracts relatively stable, evidence-supported knowledge about an individual (COG-04).

    Operates on a list of evidence objects (typically EvidenceObject instances) and
    produces PersonalKnowledgeObject instances that represent durable facts, preferences,
    or biographical details about a person.
    """

    def __init__(self) -> None:
        self._knowledge: dict[str, PersonalKnowledgeObject] = {}

    def process(
        self,
        evidence_objects: list[Any],
    ) -> KnowledgeExtractionResult:
        """Full pipeline: Evidence Aggregation → Candidate Extraction → Validation → Canonical."""
        logger.info('cog.knowledge.pipeline_started', evidence_count=len(evidence_objects))

        # Phase 1: Aggregate evidence by inferred knowledge category
        aggregated = self._aggregate_by_category(evidence_objects)

        # Phase 2: Extract knowledge candidates from aggregated evidence
        candidates = self._extract_candidates(aggregated)

        # Phase 3: Longitudinal validation (requires repeated evidence)
        validated = self._validate_longitudinal(candidates)

        # Phase 4: Promote validated items to canonical
        canonical = self._promote_canonical(validated)

        result = KnowledgeExtractionResult(
            knowledge_objects=tuple(canonical),
            total_extracted=len(canonical),
            by_category=self._count_by_category(canonical),
        )

        logger.info(
            'cog.knowledge.pipeline_completed',
            total_extracted=result.total_extracted,
            by_category=result.by_category,
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Aggregate evidence by knowledge category
    # ------------------------------------------------------------------

    def _aggregate_by_category(
        self,
        evidence_objects: list[Any],
    ) -> dict[str, list[Any]]:
        """Group evidence objects by their inferred knowledge category."""
        aggregated: dict[str, list[Any]] = {}
        for ev in evidence_objects:
            category = self._infer_knowledge_category(ev)
            aggregated.setdefault(category, []).append(ev)
        return aggregated

    def _infer_knowledge_category(self, evidence: Any) -> str:
        """Infer the knowledge category for a single evidence object."""
        text = (
            getattr(evidence, 'original_text', '')
            or getattr(evidence, 'normalized_text', '')
            or ''
        ).lower()

        # Check keyword hints first for specificity — these override generic
        # evidence category mappings (e.g. self_report → biographical).
        for knowledge_cat, keywords in _CATEGORY_KEYWORD_HINTS.items():
            for keyword in keywords:
                if keyword in text:
                    return knowledge_cat

        # Fall back to explicit evidence category mapping
        ev_category = getattr(evidence, 'category', '')
        if ev_category in _EVIDENCE_CATEGORY_MAP:
            return _EVIDENCE_CATEGORY_MAP[ev_category]

        return 'other'

    # ------------------------------------------------------------------
    # Phase 2: Extract knowledge candidates
    # ------------------------------------------------------------------

    def _extract_candidates(
        self,
        aggregated: dict[str, list[Any]],
    ) -> list[PersonalKnowledgeObject]:
        """Create PersonalKnowledgeObject candidates from aggregated evidence."""
        candidates: list[PersonalKnowledgeObject] = []
        counter = 0

        for category, evidence_list in sorted(aggregated.items()):
            for ev in evidence_list:
                ev_id = getattr(evidence, 'identifier', '') if (evidence := ev) else ''
                text = (
                    getattr(ev, 'original_text', '')
                    or getattr(ev, 'normalized_text', '')
                    or ''
                )

                # Skip empty or trivially short text
                if len(text.strip()) < 3:
                    continue

                counter += 1
                pko = PersonalKnowledgeObject(
                    identifier=f'pk-{counter:04d}',
                    knowledge_category=category,
                    statement=text.strip(),
                    confidence=getattr(ev, 'confidence', 0.0),
                    supporting_evidence=(ev_id,) if ev_id else (),
                    lifecycle_state='candidate',
                    validation_status='pending',
                )
                candidates.append(pko)

        return candidates

    # ------------------------------------------------------------------
    # Phase 3: Longitudinal validation
    # ------------------------------------------------------------------

    def _validate_longitudinal(
        self,
        candidates: list[PersonalKnowledgeObject],
    ) -> list[PersonalKnowledgeObject]:
        """Validate candidates by checking evidence accumulation.

        A single piece of evidence keeps a candidate provisional.
        Repeated independent evidence strengthens the claim.
        """
        validated: list[PersonalKnowledgeObject] = []
        for pko in candidates:
            evidence_count = len(pko.supporting_evidence)
            if evidence_count >= _MIN_EVIDENCE_FOR_PROVISIONAL:
                # Promote from candidate to provisional
                updated = PersonalKnowledgeObject(
                    identifier=pko.identifier,
                    knowledge_category=pko.knowledge_category,
                    statement=pko.statement,
                    confidence=min(pko.confidence + 0.1 * evidence_count, 1.0),
                    supporting_evidence=pko.supporting_evidence,
                    contradictory_evidence=pko.contradictory_evidence,
                    behavioral_evidence=pko.behavioral_evidence,
                    lifecycle_state='provisional',
                    creation_timestamp=pko.creation_timestamp,
                    temporal_metadata=pko.temporal_metadata,
                    revision_history=pko.revision_history,
                    validation_status='validated',
                    specification_version=pko.specification_version,
                )
                validated.append(updated)
            else:
                validated.append(pko)

        return validated

    # ------------------------------------------------------------------
    # Phase 4: Promote to canonical
    # ------------------------------------------------------------------

    def _promote_canonical(
        self,
        validated: list[PersonalKnowledgeObject],
    ) -> list[PersonalKnowledgeObject]:
        """Promote validated provisional items to canonical when evidence is sufficient."""
        canonical: list[PersonalKnowledgeObject] = []
        for pko in validated:
            evidence_count = len(pko.supporting_evidence)
            if (
                pko.lifecycle_state == 'provisional'
                and evidence_count >= _MIN_EVIDENCE_FOR_CANONICAL
            ):
                updated = PersonalKnowledgeObject(
                    identifier=pko.identifier,
                    knowledge_category=pko.knowledge_category,
                    statement=pko.statement,
                    confidence=min(pko.confidence + 0.15, 1.0),
                    supporting_evidence=pko.supporting_evidence,
                    contradictory_evidence=pko.contradictory_evidence,
                    behavioral_evidence=pko.behavioral_evidence,
                    lifecycle_state='canonical',
                    creation_timestamp=pko.creation_timestamp,
                    temporal_metadata=pko.temporal_metadata,
                    revision_history=pko.revision_history,
                    validation_status='validated',
                    specification_version=pko.specification_version,
                )
                canonical.append(updated)
            else:
                canonical.append(pko)

        return canonical

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_by_category(
        knowledge_objects: list[PersonalKnowledgeObject],
    ) -> dict[str, int]:
        """Count knowledge objects per category."""
        counts: dict[str, int] = {}
        for pko in knowledge_objects:
            counts[pko.knowledge_category] = counts.get(pko.knowledge_category, 0) + 1
        return counts
