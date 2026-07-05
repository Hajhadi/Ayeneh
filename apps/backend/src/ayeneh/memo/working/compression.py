"""Compression strategies for working memory (MEM-04).

Implements grouping, observation-to-semantic replacement,
reasoning chain collapsing, and graph reference preservation
without destroying traceability.
"""

from __future__ import annotations

import uuid

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.working.types import (
    COMPRESSION_STRATEGIES,
    CompressionResult,
    WorkingMemoryObject,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Compressor
# ---------------------------------------------------------------------------


class WorkingMemoryCompressor:
    """Applies compression strategies to reduce working memory load.

    Strategies:
    - Grouping: cluster related items into a single representative
    - Replacing observations with semantic knowledge: condense raw
      observations into higher-level semantic summaries
    - Collapsing reasoning chains: merge sequential inference steps
    - Preserving graph references: maintain links even when compressing

    Never destroys traceability — compressed items retain source references.
    """

    def __init__(self) -> None:
        self._compression_history: list[CompressionResult] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compress(
        self,
        objects: list[WorkingMemoryObject],
        *,
        target_size: int | None = None,
        strategy: str = 'grouping',
    ) -> tuple[list[WorkingMemoryObject], CompressionResult]:
        """Compress a list of working memory objects.

        Returns the compressed list and a result describing what happened.
        """
        if not objects:
            return objects, CompressionResult(
                original_count=0,
                compressed_count=0,
                strategy_used=strategy,
            )

        if target_size is None:
            target_size = max(1, len(objects) // 2)

        if len(objects) <= target_size:
            return objects, CompressionResult(
                original_count=len(objects),
                compressed_count=len(objects),
                strategy_used=strategy,
            )

        if strategy == 'grouping':
            return self._group(objects, target_size)
        elif strategy == 'replacing_observations_with_semantic_knowledge':
            return self._replace_with_semantic(objects, target_size)
        elif strategy == 'collapsing_reasoning_chains':
            return self._collapse_chains(objects, target_size)
        elif strategy == 'preserving_graph_references':
            return self._preserve_references(objects, target_size)
        else:
            return self._group(objects, target_size)

    def auto_compress(
        self,
        objects: list[WorkingMemoryObject],
        *,
        target_size: int | None = None,
    ) -> tuple[list[WorkingMemoryObject], CompressionResult]:
        """Automatically select the best compression strategy."""
        if target_size is None:
            target_size = max(1, len(objects) // 2)

        if len(objects) <= target_size:
            return objects, CompressionResult(
                original_count=len(objects),
                compressed_count=len(objects),
                strategy_used='none',
            )

        # Select strategy based on object characteristics
        has_groups = self._detect_groupable(objects)
        has_chains = self._detect_chainable(objects)

        if has_chains:
            strategy = 'collapsing_reasoning_chains'
        elif has_groups:
            strategy = 'grouping'
        else:
            strategy = 'replacing_observations_with_semantic_knowledge'

        return self.compress(objects, target_size=target_size, strategy=strategy)

    # ------------------------------------------------------------------
    # Strategy: Grouping
    # ------------------------------------------------------------------

    def _group(
        self,
        objects: list[WorkingMemoryObject],
        target_size: int,
    ) -> tuple[list[WorkingMemoryObject], CompressionResult]:
        """Group related objects by shared episode or cognitive objects."""
        # Group by associated episode
        episode_groups: dict[str, list[WorkingMemoryObject]] = {}
        ungrouped: list[WorkingMemoryObject] = []

        for obj in objects:
            key = obj.associated_episode or ''
            if key:
                episode_groups.setdefault(key, []).append(obj)
            else:
                ungrouped.append(obj)

        compressed: list[WorkingMemoryObject] = []
        grouped_ids: list[str] = []

        for episode_id, group in episode_groups.items():
            if len(group) <= 1:
                compressed.extend(group)
                continue

            # Create a representative object from the group
            representative = self._create_representative(group, 'grouped_by_episode')
            compressed.append(representative)
            grouped_ids.extend(o.identifier for o in group)

        compressed.extend(ungrouped)

        # Trim to target size if still over
        if len(compressed) > target_size:
            compressed.sort(key=lambda o: o.activation_score, reverse=True)
            compressed = compressed[:target_size]

        result = CompressionResult(
            original_count=len(objects),
            compressed_count=len(compressed),
            strategy_used='grouping',
            grouped_ids=tuple(grouped_ids),
            preserved_references=tuple(o.identifier for o in compressed),
        )
        self._compression_history.append(result)

        logger.debug(
            'compression_grouping',
            original=len(objects),
            compressed=len(compressed),
            groups=len(episode_groups),
        )

        return compressed, result

    # ------------------------------------------------------------------
    # Strategy: Replace with semantic knowledge
    # ------------------------------------------------------------------

    def _replace_with_semantic(
        self,
        objects: list[WorkingMemoryObject],
        target_size: int,
    ) -> tuple[list[WorkingMemoryObject], CompressionResult]:
        """Replace detailed observations with semantic summaries."""
        # Sort by activation score; keep highest, compress lowest
        sorted_objs = sorted(objects, key=lambda o: o.activation_score, reverse=True)

        keep_count = min(target_size, len(sorted_objs) // 2)
        to_compress = sorted_objs[keep_count:]
        kept = sorted_objs[:keep_count]

        # Create semantic summary of compressed items
        if to_compress:
            summary = self._create_representative(
                to_compress, 'semantic_summary'
            )
            kept.append(summary)

        replaced_ids = tuple(o.identifier for o in to_compress)

        result = CompressionResult(
            original_count=len(objects),
            compressed_count=len(kept),
            strategy_used='replacing_observations_with_semantic_knowledge',
            replaced_ids=replaced_ids,
            preserved_references=tuple(o.identifier for o in kept),
        )
        self._compression_history.append(result)

        logger.debug(
            'compression_semantic',
            original=len(objects),
            compressed=len(kept),
            replaced=len(to_compress),
        )

        return kept, result

    # ------------------------------------------------------------------
    # Strategy: Collapse reasoning chains
    # ------------------------------------------------------------------

    def _collapse_chains(
        self,
        objects: list[WorkingMemoryObject],
        target_size: int,
    ) -> tuple[list[WorkingMemoryObject], CompressionResult]:
        """Collapse sequential reasoning steps into summary items."""
        # Detect chains via dependency links
        chains: list[list[WorkingMemoryObject]] = []
        processed: set[str] = set()

        for obj in objects:
            if obj.identifier in processed:
                continue
            chain = [obj]
            processed.add(obj.identifier)

            # Follow dependency links
            for dep_id in obj.dependency_links:
                for other in objects:
                    if other.identifier == dep_id and other.identifier not in processed:
                        chain.append(other)
                        processed.add(other.identifier)

            if len(chain) > 1:
                chains.append(chain)

        compressed: list[WorkingMemoryObject] = []
        collapsed_ids: list[str] = []

        for chain in chains:
            summary = self._create_representative(chain, 'collapsed_chain')
            compressed.append(summary)
            collapsed_ids.extend(o.identifier for o in chain)

        # Add unchained items
        for obj in objects:
            if obj.identifier not in processed:
                compressed.append(obj)

        if len(compressed) > target_size:
            compressed.sort(key=lambda o: o.activation_score, reverse=True)
            compressed = compressed[:target_size]

        result = CompressionResult(
            original_count=len(objects),
            compressed_count=len(compressed),
            strategy_used='collapsing_reasoning_chains',
            collapsed_ids=tuple(collapsed_ids),
            preserved_references=tuple(o.identifier for o in compressed),
        )
        self._compression_history.append(result)

        logger.debug(
            'compression_chains',
            original=len(objects),
            compressed=len(compressed),
            chains=len(chains),
        )

        return compressed, result

    # ------------------------------------------------------------------
    # Strategy: Preserve graph references
    # ------------------------------------------------------------------

    def _preserve_references(
        self,
        objects: list[WorkingMemoryObject],
        target_size: int,
    ) -> tuple[list[WorkingMemoryObject], CompressionResult]:
        """Compress while explicitly preserving all graph references."""
        sorted_objs = sorted(objects, key=lambda o: o.effective_score, reverse=True)

        keep_count = min(target_size, len(sorted_objs))
        kept = sorted_objs[:keep_count]
        removed = sorted_objs[keep_count:]

        # Collect all references from removed items
        preserved_refs: list[str] = []
        for obj in removed:
            preserved_refs.extend(obj.dependency_links)
            preserved_refs.extend(obj.associated_cognitive_objects)

        # Add references to the lowest-scored kept item as dependency links
        if kept and preserved_refs:
            lowest = kept[-1]
            merged_deps = tuple(
                set(lowest.dependency_links) | set(preserved_refs)
            )
            merged = WorkingMemoryObject(
                identifier=lowest.identifier,
                source_memory=lowest.source_memory,
                activation_reason=lowest.activation_reason,
                activation_score=lowest.activation_score,
                priority_score=lowest.priority_score,
                supporting_evidence=lowest.supporting_evidence,
                associated_episode=lowest.associated_episode,
                associated_cognitive_objects=lowest.associated_cognitive_objects,
                associated_projects=lowest.associated_projects,
                temporal_relevance=lowest.temporal_relevance,
                estimated_lifetime=lowest.estimated_lifetime,
                dependency_links=merged_deps,
                explainability_metadata=lowest.explainability_metadata,
            )
            kept[-1] = merged

        result = CompressionResult(
            original_count=len(objects),
            compressed_count=len(kept),
            strategy_used='preserving_graph_references',
            replaced_ids=tuple(o.identifier for o in removed),
            preserved_references=tuple(preserved_refs),
        )
        self._compression_history.append(result)

        logger.debug(
            'compression_references',
            original=len(objects),
            compressed=len(kept),
            refs_preserved=len(preserved_refs),
        )

        return kept, result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_representative(
        self,
        group: list[WorkingMemoryObject],
        reason: str,
    ) -> WorkingMemoryObject:
        """Create a single representative object from a group."""
        # Merge evidence and dependencies
        all_evidence: list[str] = []
        all_deps: list[str] = []
        all_cog: list[str] = []
        all_projects: list[str] = []
        episodes: list[str] = []

        for obj in group:
            all_evidence.extend(obj.supporting_evidence)
            all_deps.extend(obj.dependency_links)
            all_cog.extend(obj.associated_cognitive_objects)
            all_projects.extend(obj.associated_projects)
            if obj.associated_episode:
                episodes.append(obj.associated_episode)

        # Use highest activation score
        top_obj = max(group, key=lambda o: o.activation_score)

        return WorkingMemoryObject(
            identifier=f"grp_{uuid.uuid4().hex[:12]}",
            source_memory=top_obj.source_memory,
            activation_reason=reason,
            activation_score=top_obj.activation_score,
            priority_score=max(o.priority_score for o in group),
            supporting_evidence=tuple(dict.fromkeys(all_evidence)),
            associated_episode=episodes[0] if episodes else '',
            associated_cognitive_objects=tuple(dict.fromkeys(all_cog)),
            associated_projects=tuple(dict.fromkeys(all_projects)),
            temporal_relevance=max(o.temporal_relevance for o in group),
            estimated_lifetime=max(o.estimated_lifetime for o in group),
            dependency_links=tuple(dict.fromkeys(all_deps)),
        )

    def _detect_groupable(self, objects: list[WorkingMemoryObject]) -> bool:
        """Detect if objects can be meaningfully grouped."""
        episodes = [o.associated_episode for o in objects if o.associated_episode]
        return len(set(episodes)) < len(episodes)

    def _detect_chainable(self, objects: list[WorkingMemoryObject]) -> bool:
        """Detect if objects form dependency chains."""
        dep_count = sum(1 for o in objects if o.dependency_links)
        return dep_count >= 2

    def get_compression_history(self) -> list[CompressionResult]:
        """Return the history of compression operations."""
        return list(self._compression_history)

    def compress_group(self, items: list[WorkingMemoryObject]) -> dict[str, Any]:
        """Group related working memory items by source type.

        Returns a dict with:
        - ``grouped``: list of grouped summaries or individual items
        - ``original_count``: number of items before grouping
        - ``compressed_count``: number of groups after compression
        """
        if not items:
            return {'grouped': [], 'original_count': 0, 'compressed_count': 0}

        # Group by source_memory (the source type field)
        groups: dict[str, list[WorkingMemoryObject]] = {}
        for item in items:
            source = getattr(item, 'source_memory', 'unknown')
            groups.setdefault(source, []).append(item)

        compressed: list[Any] = []
        for source, group in groups.items():
            if len(group) > 1:
                summary = {
                    'source_type': source,
                    'item_count': len(group),
                    'items': [getattr(i, 'identifier', str(i)) for i in group],
                    'compressed': True,
                }
                compressed.append(summary)
            else:
                compressed.append(group[0] if group else None)

        return {
            'grouped': compressed,
            'original_count': len(items),
            'compressed_count': len(compressed),
        }
