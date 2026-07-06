"""DEC-02 Goal Hierarchy Manager.

Manages the 6-level goal hierarchy: life_purpose → domain_goal →
project_goal → milestone → task → action.
"""

from __future__ import annotations

import structlog

from ayeneh.dec.goal_management.types import (
    GOAL_HIERARCHY_LEVELS,
    GoalHierarchy,
    GoalObject,
)

logger = structlog.get_logger(__name__)

# Allowed parent→child level transitions
_VALID_TRANSITIONS: dict[str, str | None] = {
    'life_purpose': 'domain_goal',
    'domain_goal': 'project_goal',
    'project_goal': 'milestone',
    'milestone': 'task',
    'task': 'action',
    'action': None,
}


class GoalHierarchyManager:
    """Manages the 6-level goal hierarchy.

    Supports:
    - Validating hierarchy integrity
    - Finding ancestors and descendants
    - Computing depth and path between goals
    - Listing goals at each level
    """

    def __init__(self) -> None:
        self._hierarchy = GoalHierarchy()

    def load(self, hierarchy: GoalHierarchy) -> None:
        """Load a goal hierarchy."""
        self._hierarchy = hierarchy
        logger.debug(
            'dec.goal_hierarchy.loaded',
            root_count=len(hierarchy.root_goals),
            total_nodes=len(hierarchy.level_map),
        )

    def validate(self) -> tuple[str, ...]:
        """Validate hierarchy integrity.

        Returns a list of validation error messages (empty if valid).
        """
        errors: list[str] = []

        # Check all children point back to valid parents
        for parent_id, children in self._hierarchy.children_map.items():
            for child_id in children:
                recorded_parent = self._hierarchy.parent_map.get(child_id)
                if recorded_parent != parent_id:
                    errors.append(
                        f'Child {child_id} parent mismatch: '
                        f'expected {parent_id}, got {recorded_parent}'
                    )

        # Check level transitions are valid
        for goal_id, level in self._hierarchy.level_map.items():
            parent_id = self._hierarchy.parent_map.get(goal_id)
            if parent_id:
                parent_level = self._hierarchy.level_map.get(parent_id, '')
                expected_child = _VALID_TRANSITIONS.get(parent_level)
                if expected_child is not None and expected_child != level:
                    errors.append(
                        f'Invalid level transition: {parent_level} → {level} '
                        f'for goal {goal_id} (expected {expected_child})'
                    )

        # Check root goals have no parent
        for root_id in self._hierarchy.root_goals:
            if root_id in self._hierarchy.parent_map:
                errors.append(
                    f'Root goal {root_id} has a parent: '
                    f'{self._hierarchy.parent_map[root_id]}'
                )

        if errors:
            logger.warning('dec.goal_hierarchy.validation_failed', error_count=len(errors))
        else:
            logger.debug('dec.goal_hierarchy.validation_passed')

        return tuple(errors)

    def get_ancestors(self, goal_id: str) -> tuple[str, ...]:
        """Get all ancestors from goal_id up to root."""
        ancestors: list[str] = []
        current = goal_id
        visited: set[str] = set()

        while current in self._hierarchy.parent_map:
            if current in visited:
                break
            visited.add(current)
            parent = self._hierarchy.parent_map[current]
            ancestors.append(parent)
            current = parent

        return tuple(ancestors)

    def get_descendants(self, goal_id: str) -> tuple[str, ...]:
        """Get all descendants from goal_id down to leaves."""
        descendants: list[str] = []
        queue = list(self._hierarchy.children_map.get(goal_id, ()))
        visited: set[str] = set()

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            descendants.append(current)
            queue.extend(self._hierarchy.children_map.get(current, ()))

        return tuple(descendants)

    def get_depth(self, goal_id: str) -> int:
        """Get depth from root to goal_id."""
        ancestors = self.get_ancestors(goal_id)
        return len(ancestors)

    def get_path(self, from_id: str, to_id: str) -> tuple[str, ...]:
        """Get path from one goal to another via common ancestors."""
        from_ancestors = set(self.get_ancestors(from_id))
        to_ancestors = self.get_ancestors(to_id)

        # Find lowest common ancestor
        lca = None

        # to_id itself might be an ancestor of from_id
        if to_id in from_ancestors:
            lca = to_id
        elif from_id in set(to_ancestors):
            lca = from_id
        else:
            for a in to_ancestors:
                if a in from_ancestors:
                    lca = a
                    break

        if lca is None:
            return ()

        # Build path: from_id → ... → LCA → ... → to_id
        up_path: list[str] = []
        current = from_id
        while current != lca:
            up_path.append(current)
            current = self._hierarchy.parent_map.get(current, '')
            if not current:
                return ()

        down_path: list[str] = []
        stack = [to_id]
        while stack:
            node = stack.pop()
            if node == lca:
                break
            down_path.append(node)
            parent = self._hierarchy.parent_map.get(node, '')
            if parent:
                stack.append(parent)

        down_path.reverse()
        return tuple(up_path + [lca] + down_path)

    def get_goals_at_level(self, level: str) -> tuple[str, ...]:
        """Get all goal IDs at a specific hierarchy level."""
        return tuple(
            gid for gid, lv in self._hierarchy.level_map.items()
            if lv == level
        )

    def get_level_counts(self) -> dict[str, int]:
        """Count goals at each hierarchy level."""
        counts: dict[str, int] = {}
        for level in GOAL_HIERARCHY_LEVELS:
            counts[level] = sum(
                1 for lv in self._hierarchy.level_map.values() if lv == level
            )
        return counts

    def get_max_depth(self) -> int:
        """Get the maximum depth of the hierarchy."""
        if not self._hierarchy.level_map:
            return 0
        return max(self.get_depth(gid) for gid in self._hierarchy.level_map)
