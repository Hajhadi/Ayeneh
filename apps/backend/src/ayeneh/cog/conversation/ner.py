"""Named Entity Recognition for COG conversation understanding.

Uses heuristic patterns + optional LLM for better entity extraction."""

from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Entity type patterns
# ---------------------------------------------------------------------------

PERSON_PATTERNS = [
    r'\b[A-Z][a-z]+\s[A-Z][a-z]+\b',  # Full names (capitalized)
    r'\b(?:Mr|Mrs|Ms|Dr|Prof)\.\s+[A-Z][a-z]+\b',  # Titles
    r'\bmy\s+(?:mother|father|sister|brother|friend|teacher|boss|partner|wife|husband|child|son|daughter)\b',  # Kinship
]

# Common English words to exclude from person detection
_COMMON_WORDS = frozenset({
    'hello', 'world', 'good', 'morning', 'evening', 'night', 'thank',
    'please', 'sorry', 'yes', 'no', 'well', 'just', 'like', 'have',
    'been', 'here', 'there', 'what', 'when', 'where', 'which', 'this',
    'that', 'with', 'from', 'your', 'mine', ' ours', 'theirs',
})

ORGANIZATION_PATTERNS = [
    r'\b[A-Z][a-z]+\s+(?:Inc|Corp|Ltd|LLC|Company|Organization|University|School|Hospital)\b',
    r'\b(?:the\s+)?[A-Z][a-z]+\s+(?:Team|Group|Department|Division)\b',
]

LOCATION_PATTERNS = [
    r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
    r'\bat\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
    r'\b(?:city|country|town|village|state|province|region)\s+of\s+([A-Z][a-z]+)\b',
]


class EntityRecognizer:
    """Extract named entities from text using pattern matching + heuristics."""

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router

    def recognize(self, text: str) -> list[dict[str, Any]]:
        """Extract entities from text."""
        entities: list[dict[str, Any]] = []
        entities.extend(self._extract_by_patterns(text))
        entities = self._deduplicate(entities)
        return entities

    def _extract_by_patterns(self, text: str) -> list[dict[str, Any]]:
        """Run all pattern extractors and merge results."""
        entities: list[dict[str, Any]] = []
        entities.extend(self._extract_persons(text))
        entities.extend(self._extract_organizations(text))
        entities.extend(self._extract_locations(text))
        return entities

    def _extract_persons(self, text: str) -> list[dict[str, Any]]:
        """Extract person entities from text."""
        entities: list[dict[str, Any]] = []
        # Case-sensitive patterns for proper names
        for pattern in PERSON_PATTERNS[:2]:
            for match in re.finditer(pattern, text):
                name = match.group(0)
                start = match.start()
                end = match.end()

                entities.append({
                    'text': name,
                    'type': 'person',
                    'start': start,
                    'end': end,
                })

        # Case-insensitive pattern for kinship references
        for pattern in PERSON_PATTERNS[2:]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = match.group(0)
                start = match.start()
                end = match.end()

                # Skip common words that aren't real names
                lower_name = name.lower()
                if lower_name in _COMMON_WORDS:
                    continue

                # Resolve kinship references to 'person' type
                entity_type = 'person'
                if lower_name.startswith('my ') and any(
                    kin in lower_name for kin in (
                        'mother', 'father', 'sister', 'brother',
                        'friend', 'teacher', 'boss', 'partner',
                        'wife', 'husband', 'child', 'son', 'daughter',
                    )
                ):
                    entity_type = 'kinship'

                entities.append({
                    'text': name,
                    'type': entity_type,
                    'start': start,
                    'end': end,
                })
        return entities

    def _extract_organizations(self, text: str) -> list[dict[str, Any]]:
        """Extract organization entities from text."""
        entities: list[dict[str, Any]] = []
        for pattern in ORGANIZATION_PATTERNS:
            for match in re.finditer(pattern, text):
                name = match.group(0)
                entities.append({
                    'text': name,
                    'type': 'organization',
                    'start': match.start(),
                    'end': match.end(),
                })
        return entities

    def _extract_locations(self, text: str) -> list[dict[str, Any]]:
        """Extract location entities from text."""
        entities: list[dict[str, Any]] = []
        for pattern in LOCATION_PATTERNS:
            for match in re.finditer(pattern, text):
                name = match.group(1) if match.lastindex else match.group(0)
                entities.append({
                    'text': name,
                    'type': 'location',
                    'start': match.start(1) if match.lastindex else match.start(),
                    'end': match.end(1) if match.lastindex else match.end(),
                })
        return entities

    @staticmethod
    def _deduplicate(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate entities, keeping the first occurrence."""
        seen: set[tuple[str, str]] = set()
        result: list[dict[str, Any]] = []
        for ent in entities:
            key = (ent['text'].lower(), ent['type'])
            if key not in seen:
                seen.add(key)
                result.append(ent)
        return result
