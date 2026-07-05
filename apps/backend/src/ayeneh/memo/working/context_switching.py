"""Context switching for working memory (MEM-04).

Handles transitions between context windows, preserving state and
managing residual dependencies during switches.
"""

from __future__ import annotations

import uuid

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.working.types import (
    ContextSwitch,
    ContextWindow,
    WorkingMemoryObject,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Context switching manager
# ---------------------------------------------------------------------------


class ContextSwitchingManager:
    """Manages transitions between working memory context windows.

    Preserves previous state, tracks reasons for switching, manages
    residual dependencies, and maintains open hypotheses across switches.
    """

    def __init__(self) -> None:
        self._switch_history: list[ContextSwitch] = []
        self._active_window: ContextWindow | None = None
        self._window_stack: list[ContextWindow] = []
        self._residual_dependencies: dict[str, tuple[str, ...]] = {}
        self._open_hypotheses: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def switch_context(
        self,
        new_window: ContextWindow,
        *,
        reason: str = '',
        current_objects: tuple[WorkingMemoryObject, ...] = (),
        residual_ids: tuple[str, ...] = (),
        hypotheses: tuple[str, ...] = (),
    ) -> ContextSwitch:
        """Execute a context switch to a new window.

        Preserves the previous state and records the switch.
        """
        previous_state = current_objects
        if self._active_window is not None:
            previous_state = self._active_window.activated_objects

        # Push current window onto stack
        if self._active_window is not None:
            self._window_stack.append(self._active_window)

        # Create the switch record
        switch = ContextSwitch(
            previous_state=previous_state,
            reason=reason,
            new_activation_set=new_window.activated_objects,
            residual_dependencies=residual_ids,
            open_hypotheses=hypotheses,
        )

        # Store residual dependencies
        if residual_ids:
            self._residual_dependencies[new_window.window_id] = residual_ids

        # Store open hypotheses
        if hypotheses:
            self._open_hypotheses[new_window.window_id] = list(hypotheses)

        # Update active window
        self._active_window = new_window
        self._switch_history.append(switch)

        logger.debug(
            'context_switched',
            from_window=self._active_window.window_id if self._active_window else None,
            to_window=new_window.window_id,
            reason=reason,
            residual_count=len(residual_ids),
        )

        return switch

    def pop_context(self) -> ContextSwitch | None:
        """Return to the previous context window (pop from stack).

        Returns None if there is no previous context to return to.
        """
        if not self._window_stack:
            return None

        previous_window = self._window_stack.pop()
        current_objects = (
            self._active_window.activated_objects
            if self._active_window is not None
            else ()
        )

        # Gather residual dependencies from the departing window
        departing_id = self._active_window.window_id if self._active_window else ''
        residual_ids = self._residual_dependencies.get(departing_id, ())
        hypotheses = tuple(self._open_hypotheses.get(departing_id, []))

        switch = ContextSwitch(
            previous_state=current_objects,
            reason='pop_context',
            new_activation_set=previous_window.activated_objects,
            residual_dependencies=residual_ids,
            open_hypotheses=hypotheses,
        )

        self._active_window = previous_window
        self._switch_history.append(switch)

        logger.debug(
            'context_popped',
            to_window=previous_window.window_id,
            residual_count=len(residual_ids),
        )

        return switch

    def get_residual_dependencies(self, window_id: str) -> tuple[str, ...]:
        """Return residual dependencies for a given window."""
        return tuple(self._residual_dependencies.get(window_id, ()))

    def get_open_hypotheses(self, window_id: str) -> tuple[str, ...]:
        """Return open hypotheses for a given window."""
        return tuple(self._open_hypotheses.get(window_id, []))

    def clear_hypotheses(self, window_id: str) -> None:
        """Clear open hypotheses for a given window."""
        self._open_hypotheses.pop(window_id, None)

    def get_switch_history(self) -> list[ContextSwitch]:
        """Return the full switch history."""
        return list(self._switch_history)

    def get_active_window(self) -> ContextWindow | None:
        """Return the currently active context window."""
        return self._active_window

    def get_window_stack_depth(self) -> int:
        """Return the depth of the window stack."""
        return len(self._window_stack)

    def has_previous_context(self) -> bool:
        """Return True if there is a previous context to return to."""
        return len(self._window_stack) > 0
