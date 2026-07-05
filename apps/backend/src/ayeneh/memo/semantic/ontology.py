"""Personal ontology for semantic memory (MEM-03).

Tracks stable knowledge domains: research domains, long-term projects,
frequently used concepts, programming frameworks, books, people,
organizations, places, practices, and identity themes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Ontology domain types
# ---------------------------------------------------------------------------

ONTOLOGY_DOMAINS: list[str] = [
    'research_domains',
    'long_term_projects',
    'frequently_used_concepts',
    'programming_frameworks',
    'books',
    'people',
    'organizations',
    'places',
    'practices',
    'identity_themes',
]

# ---------------------------------------------------------------------------
# Ontology entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OntologyEntry:
    """A single entry in the personal ontology."""

    entry_id: str
    domain: str
    label: str
    description: str = ''
    aliases: tuple[str, ...] = ()
    semantic_memory_ids: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(UTC))
    access_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Ontology relationship
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OntologyRelationship:
    """A relationship between two ontology entries."""

    source_entry_id: str
    target_entry_id: str
    relationship_type: str  # 'related_to', 'part_of', 'depends_on', 'contradicts'
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Personal ontology
# ---------------------------------------------------------------------------


class PersonalOntology:
    """Tracks stable knowledge domains for the personal ontology.

    Provides lookup, addition, and relationship management for the
    person's known concepts, tools, people, places, and themes.
    """

    def __init__(self) -> None:
        self._entries: dict[str, OntologyEntry] = {}
        self._relationships: list[OntologyRelationship] = []
        self._domain_index: dict[str, list[str]] = {d: [] for d in ONTOLOGY_DOMAINS}

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    @property
    def relationship_count(self) -> int:
        return len(self._relationships)

    # ------------------------------------------------------------------
    # Entry management
    # ------------------------------------------------------------------

    def add_entry(
        self,
        entry_id: str,
        domain: str,
        label: str,
        description: str = '',
        aliases: tuple[str, ...] = (),
        semantic_memory_ids: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> OntologyEntry:
        """Add or update an ontology entry."""
        entry = OntologyEntry(
            entry_id=entry_id,
            domain=domain,
            label=label,
            description=description,
            aliases=aliases,
            semantic_memory_ids=semantic_memory_ids,
            metadata=metadata or {},
        )
        self._entries[entry_id] = entry
        if domain in self._domain_index and entry_id not in self._domain_index[domain]:
            self._domain_index[domain].append(entry_id)
        return entry

    def get_entry(self, entry_id: str) -> OntologyEntry | None:
        """Retrieve an entry by ID."""
        return self._entries.get(entry_id)

    def find_by_label(self, label: str) -> list[OntologyEntry]:
        """Find entries matching a label (case-insensitive)."""
        label_lower = label.lower()
        return [
            e for e in self._entries.values()
            if label_lower in e.label.lower() or label_lower in e.description.lower()
            or any(label_lower in a.lower() for a in e.aliases)
        ]

    def find_by_domain(self, domain: str) -> list[OntologyEntry]:
        """List all entries in a domain."""
        entry_ids = self._domain_index.get(domain, [])
        return [self._entries[eid] for eid in entry_ids if eid in self._entries]

    def remove_entry(self, entry_id: str) -> bool:
        """Remove an entry and its relationships."""
        entry = self._entries.pop(entry_id, None)
        if entry is None:
            return False
        if entry.domain in self._domain_index:
            self._domain_index[entry.domain] = [
                eid for eid in self._domain_index[entry.domain] if eid != entry_id
            ]
        self._relationships = [
            r for r in self._relationships
            if r.source_entry_id != entry_id and r.target_entry_id != entry_id
        ]
        return True

    # ------------------------------------------------------------------
    # Relationship management
    # ------------------------------------------------------------------

    def add_relationship(
        self,
        source_entry_id: str,
        target_entry_id: str,
        relationship_type: str,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> OntologyRelationship:
        """Add a relationship between two ontology entries."""
        rel = OntologyRelationship(
            source_entry_id=source_entry_id,
            target_entry_id=target_entry_id,
            relationship_type=relationship_type,
            weight=weight,
            metadata=metadata or {},
        )
        self._relationships.append(rel)
        return rel

    def get_related(self, entry_id: str) -> list[OntologyRelationship]:
        """Get all relationships involving an entry."""
        return [
            r for r in self._relationships
            if r.source_entry_id == entry_id or r.target_entry_id == entry_id
        ]

    def get_relationships_by_type(self, relationship_type: str) -> list[OntologyRelationship]:
        """Get all relationships of a given type."""
        return [r for r in self._relationships if r.relationship_type == relationship_type]

    # ------------------------------------------------------------------
    # Access tracking
    # ------------------------------------------------------------------

    def record_access(self, entry_id: str) -> None:
        """Record that an entry was accessed (updates timestamp and count)."""
        entry = self._entries.get(entry_id)
        if entry is None:
            return
        updated = OntologyEntry(
            entry_id=entry.entry_id,
            domain=entry.domain,
            label=entry.label,
            description=entry.description,
            aliases=entry.aliases,
            semantic_memory_ids=entry.semantic_memory_ids,
            created_at=entry.created_at,
            last_accessed=datetime.now(UTC),
            access_count=entry.access_count + 1,
            metadata=entry.metadata,
        )
        self._entries[entry_id] = updated

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Return a summary of the ontology."""
        domain_counts = {}
        for domain, entry_ids in self._domain_index.items():
            if entry_ids:
                domain_counts[domain] = len(entry_ids)
        return {
            'total_entries': self.entry_count,
            'total_relationships': self.relationship_count,
            'domain_counts': domain_counts,
        }
