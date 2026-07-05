"""Reference resolver for the Ayeneh COG architecture (COG-01).

Resolves pronouns, aliases, and coreferences in semantic objects to their
canonical entity forms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

from ayeneh.cog.conversation.types import ConversationSegment, Entity, SemanticObject

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Pronoun maps
# ---------------------------------------------------------------------------

SINGULAR_PRONOUNS: dict[str, str] = {
    'he': 'person', 'him': 'person', 'his': 'person',
    'she': 'person', 'her': 'person',
    'it': 'object',
    'my': 'self', 'me': 'self', 'i': 'self',
    'your': 'second_person', 'you': 'second_person',
}

PLURAL_PRONOUNS: dict[str, str] = {
    'they': 'group', 'them': 'group', 'their': 'group',
    'we': 'group', 'our': 'group', 'us': 'group',
}

DEMONSTRATIVES: dict[str, str] = {
    'this': 'near', 'that': 'far', 'these': 'near', 'those': 'far',
}

UNCERTAINTY_MARKERS: tuple[str, ...] = ('maybe', 'perhaps', 'probably', 'might', 'could')


# ---------------------------------------------------------------------------
# Coreference chain
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CoreferenceChain:
    """Tracks mentions that refer to the same entity."""

    canonical_name: str
    mentions: tuple[str, ...] = ()
    entity_type: str = 'unknown'


class ReferenceResolver:
    """Resolve pronouns and aliases to canonical entities.

    The resolver maintains a running inventory of named entities across
    segments.  When a pronoun or demonstrative is encountered, it is
    mapped to the most recently mentioned entity of the matching type.
    """

    def resolve(
        self,
        semantic_objects: list[SemanticObject],
        segments: list[ConversationSegment],
    ) -> list[SemanticObject]:
        """Return a new list of semantic objects with references resolved.

        Named entities are accumulated in document order.  Pronouns and
        demonstratives are mapped to the most recent entity whose type
        matches the pronoun class.
        """
        entity_stack: list[Entity] = []
        resolved: list[SemanticObject] = []

        # Build a segment-index lookup for quick access
        seg_index = {s.segment_id: s for s in segments}

        for obj in semantic_objects:
            # Attempt resolution for pronouns / temporal_ref FIRST
            if obj.object_type in ('entity', 'temporal_ref'):
                resolved_obj = self._try_resolve(
                    obj, entity_stack, seg_index,
                )
                resolved.append(resolved_obj)
                # Only track proper-name entities (not pronouns) in the stack
                surface_lower = obj.surface_form.lower().strip()
                is_pronoun = (
                    surface_lower in SINGULAR_PRONOUNS
                    or surface_lower in PLURAL_PRONOUNS
                    or surface_lower in DEMONSTRATIVES
                )
                if not is_pronoun:
                    entity = Entity(
                        entity_id=obj.object_id,
                        name=obj.normalized_form,
                        entity_type=self._infer_entity_type(obj),
                        confidence=obj.confidence,
                    )
                    entity_stack.append(entity)
            else:
                resolved.append(obj)

        logger.info(
            'cog.reference_resolution.complete',
            total_objects=len(semantic_objects),
            resolved=sum(1 for o in resolved if o != semantic_objects[resolved.index(o)] if resolved.index(o) < len(semantic_objects)),
            entities_tracked=len(entity_stack),
        )
        return resolved

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_resolve(
        self,
        obj: SemanticObject,
        entity_stack: list[Entity],
        seg_index: dict[str, ConversationSegment],
    ) -> SemanticObject:
        """Attempt to resolve a pronoun / demonstrative in *obj*."""
        surface = obj.surface_form.lower().strip()
        if surface in SINGULAR_PRONOUNS or surface in PLURAL_PRONOUNS or surface in DEMONSTRATIVES:
            pronoun_class = (
                SINGULAR_PRONOUNS.get(surface)
                or PLURAL_PRONOUNS.get(surface)
                or DEMONSTRATIVES.get(surface)
            )
            target_entity = self._find_matching_entity(
                entity_stack, pronoun_class, surface,
            )
            if target_entity is not None:
                return SemanticObject(
                    object_id=obj.object_id,
                    surface_form=obj.surface_form,
                    normalized_form=target_entity.name,
                    object_type='entity',
                    confidence=max(obj.confidence, 0.6),
                    offsets=obj.offsets,
                )
        return obj

    def _find_matching_entity(
        self,
        stack: list[Entity],
        pronoun_class: str,
        surface: str,
    ) -> Entity | None:
        """Find the most recent entity matching the pronoun class."""
        if surface in ('i', 'me', 'my', 'we', 'our', 'us'):
            # Self-referential: use the most recent person entity, or None
            for entity in reversed(stack):
                if entity.entity_type == 'person':
                    return entity
            return None

        if surface in ('you', 'your', 'yourself'):
            # Second person: no resolution needed
            return None

        if pronoun_class in ('person',):
            for entity in reversed(stack):
                if entity.entity_type == 'person':
                    return entity

        if pronoun_class in ('object', 'near', 'far'):
            # Fall back to most recent entity of any type
            for entity in reversed(stack):
                return entity

        return None

    @staticmethod
    def _infer_entity_type(obj: SemanticObject) -> str:
        """Guess the entity type from the surface form."""
        name = obj.normalized_form
        name_lower = name.lower()
        if name_lower.startswith(('mr.', 'mrs.', 'ms.', 'dr.', 'prof.')):
            return 'person'
        if name_lower in ('i', 'me', 'my', 'myself'):
            return 'person'
        if any(t in name_lower for t in ('inc.', 'llc', 'corp.', 'ltd.')):
            return 'organization'
        # Proper nouns (capitalised first letter) default to person
        if name and name[0].isupper():
            return 'person'
        return 'concept'

    # ------------------------------------------------------------------
    # Alias detection
    # ------------------------------------------------------------------

    @staticmethod
    def build_alias_chains(
        entities: list[Entity],
    ) -> dict[str, CoreferenceChain]:
        """Group entities by canonical name to form alias chains."""
        chains: dict[str, list[str]] = {}
        for entity in entities:
            key = entity.name.lower()
            if key not in chains:
                chains[key] = []
            chains[key].extend([entity.name, *entity.aliases])
        return {
            k: CoreferenceChain(
                canonical_name=k,
                mentions=tuple(dict.fromkeys(v)),
                entity_type='concept',
            )
            for k, v in chains.items()
        }

    @staticmethod
    def detect_uncertainty(text: str) -> tuple[str, ...]:
        """Return uncertainty markers found in *text*."""
        lower = text.lower()
        return tuple(m for m in UNCERTAINTY_MARKERS if m in lower)
