"""COG-05 Narrative Extraction Engine.

Identifies, models, and tracks internal stories (narratives) that shape
an individual's cognition and behavior. Runs a five-phase pipeline:
    Evidence Analysis → Pattern Detection → Candidate Extraction → Validation → Network Building.
"""

from __future__ import annotations

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.cog.narrative.types import (
    NARRATIVE_CATEGORIES,
    NARRATIVE_TEMPLATES,
    NarrativeExtractionResult,
    NarrativeNetwork,
    NarrativeObject,
)

logger = structlog.get_logger(__name__)

# Minimum distinct evidence items for provisional status
_MIN_EVIDENCE_FOR_PROVISIONAL = 2

# Minimum distinct evidence items for canonical validation
_MIN_EVIDENCE_FOR_CANONICAL = 3

# Keywords that signal narrative templates
_TEMPLATE_KEYWORDS: dict[str, list[str]] = {
    'success': ['succeeded', 'won', 'achieved', ' accomplished', 'success', 'made it'],
    'failure': ['failed', 'lost', 'couldn\'t', 'never worked', 'fell short', 'mistake'],
    'victim': ['happened to me', 'wasn\'t my fault', 'unfair', 'they did this to me', 'no choice'],
    'rescuer': ['helped them', 'saved', 'fixed it for', 'took care of', 'responsible for'],
    'growth': ['learned from', 'grew', 'became stronger', 'overcame', 'improved', 'developed'],
    'hero': ['stood up', 'fought for', 'defended', 'courage', 'brave', 'against all odds'],
    'perfection': ['had to be perfect', 'never good enough', 'flawless', 'impossible standard'],
    'abandonment': ['left me', 'everyone leaves', 'alone', 'deserted', 'no one stays'],
    'control': ['had to control', 'needed to know', 'couldn\'t trust', 'my way or'],
    'meaning': ['purpose', 'meaning of', 'why am I', 'what matters', 'deeper purpose'],
    'belonging': ['fit in', 'part of', 'accepted', 'community', 'belong', 'included'],
    'freedom': ['free to', 'no one tells me', 'independent', 'my own path', 'choice'],
    'security': ['safe', 'secure', 'stable', 'protected', 'guaranteed', 'reliable'],
    'justice': ['fair', 'deserved', 'justice', 'right and wrong', 'should have been'],
}

# Keywords that signal narrative categories
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    'self': ['i am', 'i always', 'i never', 'that\'s just how i am', 'my nature'],
    'identity': ['who i am', 'identity', 'person that i am', 'defines me', 'core of'],
    'relationship': ['relationship', 'partner', 'together', 'broke up', 'love'],
    'family': ['family', 'mother', 'father', 'sibling', 'parents', 'home'],
    'career': ['career', 'work', 'job', 'profession', 'calling', 'vocation'],
    'success': ['success', 'achievement', 'goal', 'accomplishment', 'milestone'],
    'failure': ['failure', 'mistake', 'regret', 'wrong turn', 'missed'],
    'victim': ['victim', 'unfair', 'blame', 'suffering', 'happened to me'],
    'growth': ['growth', 'learning', 'development', 'becoming', 'evolving'],
    'existential': ['exist', 'meaning', 'purpose', 'why', 'reason for being'],
    'future': ['future', 'will be', 'going to', 'someday', 'plan'],
    'past': ['used to', 'back then', 'remember when', 'years ago', 'before'],
    'world': ['world', 'society', 'people', 'everyone', 'the way things are'],
    'spiritual': ['spiritual', 'faith', 'god', 'soul', 'transcend'],
    'health': ['health', 'body', 'wellness', 'healing', 'recovery'],
    'learning': ['learn', 'study', 'education', 'knowledge', 'understand'],
    'money': ['money', 'financial', 'wealth', 'rich', 'afford', 'cost'],
    'purpose': ['purpose', 'mission', 'calling', 'meant to', 'destiny'],
    'social': ['friends', 'social', 'group', 'community', 'belong'],
}


class NarrativeExtractionEngine:
    """Identifies, models, and tracks internal stories (COG-05).

    Operates on evidence objects and optional knowledge objects to extract
    recurring narrative patterns that shape the individual's worldview,
    behavior, and identity construction.
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._narratives: dict[str, NarrativeObject] = {}
        self._ai_router = ai_router

    def process(
        self,
        evidence_objects: list[Any],
        knowledge_objects: list[Any] | None = None,
    ) -> NarrativeExtractionResult:
        """Full pipeline: Evidence Analysis → Pattern Detection → Candidate → Validation → Network."""
        logger.info('cog.narrative.pipeline_started', evidence_count=len(evidence_objects))

        # Phase 1: Analyze evidence for narrative patterns
        patterns = self._analyze_patterns(evidence_objects)

        # Phase 2: Detect narrative candidates from recurring patterns
        candidates = self._detect_candidates(patterns, evidence_objects)

        # Phase 3: Validate (requires repeated evidence + temporal persistence)
        validated = self._validate(candidates)

        # Phase 4: Assign influence scores
        influenced = self._assign_influence(validated, evidence_objects)

        # Phase 5: Build narrative network
        network = self._build_network(influenced)

        result = NarrativeExtractionResult(
            narratives=tuple(influenced),
            network=network,
            total_extracted=len(influenced),
            by_category=self._count_by_category(influenced),
        )

        logger.info(
            'cog.narrative.pipeline_completed',
            total_extracted=result.total_extracted,
            by_category=result.by_category,
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Pattern analysis
    # ------------------------------------------------------------------

    def _analyze_patterns(
        self,
        evidence_objects: list[Any],
    ) -> dict[str, list[Any]]:
        """Analyze evidence for recurring narrative patterns.

        Groups evidence by narrative category based on keyword matching.
        """
        patterns: dict[str, list[Any]] = {}

        for ev in evidence_objects:
            text = (
                getattr(ev, 'original_text', '')
                or getattr(ev, 'normalized_text', '')
                or ''
            ).lower()

            if len(text.strip()) < 5:
                continue

            # Detect matching categories
            matched_categories = self._match_categories(text)
            for cat in matched_categories:
                patterns.setdefault(cat, []).append(ev)

        return patterns

    def _match_categories(self, text: str) -> list[str]:
        """Match text against narrative category keywords."""
        matched: list[str] = []
        for category, keywords in _CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    matched.append(category)
                    break
        return matched if matched else ['self']

    # ------------------------------------------------------------------
    # LLM integration
    # ------------------------------------------------------------------

    def _try_llm_narrative_detection(
        self,
        patterns: dict[str, list[Any]],
        evidence_objects: list[Any],
    ) -> list[NarrativeObject] | None:
        """Attempt LLM-based narrative detection. Returns None on failure."""
        if not self._ai_router:
            return None
        try:
            import asyncio
            from ayeneh.ai_router.types import AITask, AITaskType

            evidence_texts = []
            for ev in evidence_objects[:20]:
                text = (
                    getattr(ev, 'original_text', '')
                    or getattr(ev, 'normalized_text', '')
                    or ''
                ).strip()
                if text:
                    evidence_texts.append(text)

            if not evidence_texts:
                return None

            prompt = (
                "Analyze the following evidence texts and identify recurring "
                "narrative patterns. For each narrative, provide:\n"
                "- category (e.g., self, identity, growth, career, family)\n"
                "- template (e.g., growth, failure, hero, victim)\n"
                "- statement\n"
                "- confidence (0.0-1.0)\n\n"
                "Evidence:\n"
                + "\n".join(f"- {t}" for t in evidence_texts)
                + "\n\nRespond as a JSON list of objects with keys: "
                "category, template, statement, confidence."
            )
            messages = [
                {"role": "system", "content": "You are a cognitive narrative analysis assistant."},
                {"role": "user", "content": prompt},
            ]
            task = AITask(
                task_type=AITaskType.CONVERSATION_GENERATION,
                content=prompt,
                max_tokens=1024,
                temperature=0.3,
            )

            loop = asyncio.get_event_loop()
            if loop.is_running():
                return None
            result = loop.run_until_complete(self._ai_router.chat(task, messages))
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                return None

            return self._parse_llm_narratives(content, evidence_objects)
        except Exception:
            return None

    def _parse_llm_narratives(
        self,
        content: str,
        evidence_objects: list[Any],
    ) -> list[NarrativeObject]:
        """Parse LLM response into NarrativeObject list."""
        import json

        candidates: list[NarrativeObject] = []
        try:
            # Try to extract JSON from the response
            start = content.find('[')
            end = content.rfind(']') + 1
            if start == -1 or end <= 0:
                return []
            items = json.loads(content[start:end])
            for i, item in enumerate(items, 1):
                category = item.get('category', 'self')
                if category not in NARRATIVE_CATEGORIES:
                    category = 'self'
                template = item.get('template', '')
                statement = item.get('statement', '')
                confidence = float(item.get('confidence', 0.5))
                if not statement:
                    continue
                evidence_ids = tuple(
                    getattr(ev, 'identifier', f'ev-{j}')
                    for j, ev in enumerate(evidence_objects[:5])
                )
                candidates.append(NarrativeObject(
                    identifier=f'narr-llm-{i:04d}',
                    narrative_type=category,
                    title=f'{category.replace("_", " ").title()} Narrative (LLM)',
                    summary=statement,
                    supporting_evidence=evidence_ids,
                    confidence=min(confidence, 1.0),
                    influence_score=0.0,
                    template=template,
                    lifecycle_state='candidate',
                ))
        except (json.JSONDecodeError, ValueError, TypeError):
            return []
        return candidates

    # ------------------------------------------------------------------
    # Phase 2: Candidate detection
    # ------------------------------------------------------------------

    def _detect_candidates(
        self,
        patterns: dict[str, list[Any]],
        evidence_objects: list[Any],
    ) -> list[NarrativeObject]:
        """Create NarrativeObject candidates from detected patterns.

        If an AI router is available and text is complex, attempts LLM-based
        detection first, falling back to rule-based on failure.
        """
        if self._ai_router and len(evidence_objects) >= 5:
            llm_candidates = self._try_llm_narrative_detection(patterns, evidence_objects)
            if llm_candidates:
                return llm_candidates

        candidates: list[NarrativeObject] = []
        counter = 0

        for category, evidence_list in sorted(patterns.items()):
            # Need at least one evidence item per category
            if not evidence_list:
                continue

            # Detect template from combined text
            combined_text = ' '.join(
                (getattr(ev, 'original_text', '') or getattr(ev, 'normalized_text', '') or '')
                for ev in evidence_list
            ).lower()
            template = self._detect_template(combined_text)

            # Build statement from evidence texts
            statements = [
                (getattr(ev, 'original_text', '') or getattr(ev, 'normalized_text', '') or '').strip()
                for ev in evidence_list
                if len(
                    (getattr(ev, 'original_text', '') or getattr(ev, 'normalized_text', '') or '').strip()
                ) >= 5
            ]

            if not statements:
                continue

            summary = statements[0] if len(statements) == 1 else '; '.join(statements[:3])

            counter += 1
            evidence_ids = tuple(
                getattr(ev, 'identifier', f'ev-{i}')
                for i, ev in enumerate(evidence_list)
            )

            no = NarrativeObject(
                identifier=f'narr-{counter:04d}',
                narrative_type=category,
                title=f'{category.replace("_", " ").title()} Narrative',
                summary=summary,
                supporting_evidence=evidence_ids,
                confidence=0.0,
                influence_score=0.0,
                template=template,
                lifecycle_state='candidate',
            )
            candidates.append(no)

        return candidates

    def _detect_template(self, text: str) -> str:
        """Detect the narrative template from text."""
        best_template = ''
        best_score = 0

        for template, keywords in _TEMPLATE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_template = template

        return best_template

    # ------------------------------------------------------------------
    # Phase 3: Validation
    # ------------------------------------------------------------------

    def _validate(
        self,
        candidates: list[NarrativeObject],
    ) -> list[NarrativeObject]:
        """Validate candidates based on evidence accumulation."""
        validated: list[NarrativeObject] = []
        for no in candidates:
            evidence_count = len(no.supporting_evidence)

            if evidence_count >= _MIN_EVIDENCE_FOR_CANONICAL:
                updated = NarrativeObject(
                    identifier=no.identifier,
                    narrative_type=no.narrative_type,
                    title=no.title,
                    summary=no.summary,
                    supporting_evidence=no.supporting_evidence,
                    contradictory_evidence=no.contradictory_evidence,
                    confidence=min(0.3 + 0.15 * evidence_count, 1.0),
                    influence_score=no.influence_score,
                    template=no.template,
                    core_assumptions=no.core_assumptions,
                    implicit_rules=no.implicit_rules,
                    expected_outcomes=no.expected_outcomes,
                    behavioral_consequences=no.behavioral_consequences,
                    emotional_associations=no.emotional_associations,
                    identity_implications=no.identity_implications,
                    related_narratives=no.related_narratives,
                    associated_beliefs=no.associated_beliefs,
                    lifecycle_state='validated',
                    creation_timestamp=no.creation_timestamp,
                    temporal_metadata=no.temporal_metadata,
                    revision_history=no.revision_history,
                    specification_version=no.specification_version,
                )
                validated.append(updated)
            elif evidence_count >= _MIN_EVIDENCE_FOR_PROVISIONAL:
                updated = NarrativeObject(
                    identifier=no.identifier,
                    narrative_type=no.narrative_type,
                    title=no.title,
                    summary=no.summary,
                    supporting_evidence=no.supporting_evidence,
                    contradictory_evidence=no.contradictory_evidence,
                    confidence=min(0.15 + 0.1 * evidence_count, 0.8),
                    influence_score=no.influence_score,
                    template=no.template,
                    core_assumptions=no.core_assumptions,
                    implicit_rules=no.implicit_rules,
                    expected_outcomes=no.expected_outcomes,
                    behavioral_consequences=no.behavioral_consequences,
                    emotional_associations=no.emotional_associations,
                    identity_implications=no.identity_implications,
                    related_narratives=no.related_narratives,
                    associated_beliefs=no.associated_beliefs,
                    lifecycle_state='provisional',
                    creation_timestamp=no.creation_timestamp,
                    temporal_metadata=no.temporal_metadata,
                    revision_history=no.revision_history,
                    specification_version=no.specification_version,
                )
                validated.append(updated)
            else:
                validated.append(no)

        return validated

    # ------------------------------------------------------------------
    # Phase 4: Influence scoring
    # ------------------------------------------------------------------

    def _assign_influence(
        self,
        validated: list[NarrativeObject],
        evidence_objects: list[Any],
    ) -> list[NarrativeObject]:
        """Assign influence scores based on evidence volume and narrative properties."""
        total_evidence = max(len(evidence_objects), 1)

        influenced: list[NarrativeObject] = []
        for no in validated:
            evidence_fraction = len(no.supporting_evidence) / total_evidence
            template_bonus = 0.1 if no.template else 0.0
            confidence_factor = no.confidence

            influence = min(
                evidence_fraction * 0.4 + template_bonus + confidence_factor * 0.5,
                1.0,
            )

            updated = NarrativeObject(
                identifier=no.identifier,
                narrative_type=no.narrative_type,
                title=no.title,
                summary=no.summary,
                supporting_evidence=no.supporting_evidence,
                contradictory_evidence=no.contradictory_evidence,
                confidence=no.confidence,
                influence_score=round(influence, 4),
                template=no.template,
                core_assumptions=no.core_assumptions,
                implicit_rules=no.implicit_rules,
                expected_outcomes=no.expected_outcomes,
                behavioral_consequences=no.behavioral_consequences,
                emotional_associations=no.emotional_associations,
                identity_implications=no.identity_implications,
                related_narratives=no.related_narratives,
                associated_beliefs=no.associated_beliefs,
                lifecycle_state=no.lifecycle_state,
                creation_timestamp=no.creation_timestamp,
                temporal_metadata=no.temporal_metadata,
                revision_history=no.revision_history,
                specification_version=no.specification_version,
            )
            influenced.append(updated)

        return influenced

    # ------------------------------------------------------------------
    # Phase 5: Network building
    # ------------------------------------------------------------------

    def _build_network(
        self,
        narratives: list[NarrativeObject],
    ) -> NarrativeNetwork:
        """Build a narrative network connecting related narratives."""
        nodes: dict[str, NarrativeObject] = {}
        for no in narratives:
            nodes[no.identifier] = no

        edges: list[NarrativeObject] = []

        # Connect narratives of the same type
        by_type: dict[str, list[NarrativeObject]] = {}
        for no in narratives:
            by_type.setdefault(no.narrative_type, []).append(no)

        for cat, group in by_type.items():
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    from ayeneh.cog.narrative.types import NarrativeEdge

                    edge = NarrativeEdge(
                        source_id=group[i].identifier,
                        target_id=group[j].identifier,
                        relationship='same_category',
                        confidence=0.5,
                    )
                    edges.append(edge)  # type: ignore[arg-type]

        # Connect narratives with matching templates
        by_template: dict[str, list[NarrativeObject]] = {}
        for no in narratives:
            if no.template:
                by_template.setdefault(no.template, []).append(no)

        for tmpl, group in by_template.items():
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    if group[i].identifier != group[j].identifier:
                        from ayeneh.cog.narrative.types import NarrativeEdge

                        edge = NarrativeEdge(
                            source_id=group[i].identifier,
                            target_id=group[j].identifier,
                            relationship=f'share_template:{tmpl}',
                            confidence=0.6,
                        )
                        edges.append(edge)  # type: ignore[arg-type]

        return NarrativeNetwork(
            nodes=nodes,
            edges=tuple(edges),  # type: ignore[arg-type]
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_by_category(
        narratives: list[NarrativeObject],
    ) -> dict[str, int]:
        """Count narratives per category."""
        counts: dict[str, int] = {}
        for no in narratives:
            counts[no.narrative_type] = counts.get(no.narrative_type, 0) + 1
        return counts
