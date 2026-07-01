"""Goal Engine — first-class cognitive subsystem for goal management and evolution.

Goals are independent cognitive entities with their own lifecycle, persistence,
retrieval, evolution, scheduling, and runtime behavior. They are NOT stored as
memories and never evolve through MemoryEvolutionService.
"""

from ayeneh.goal.domain import (
    Goal,
    GoalStatus,
    GoalPriority,
    GoalCategory,
    GoalType,
    GoalMilestone,
    GoalDependency,
    GoalHistory,
    GoalObservation,
    GoalReview,
)
from ayeneh.goal.service import GoalService, GoalStats
from ayeneh.goal.retrieval import GoalRetrievalService
from ayeneh.goal.evolution import GoalEvolutionService
from ayeneh.goal.context import GoalContextBuilder, GoalContext
from ayeneh.goal.observability import GoalMetrics, GoalEventPublisher

__all__ = [
    "Goal", "GoalStatus", "GoalPriority", "GoalCategory", "GoalType",
    "GoalMilestone", "GoalDependency", "GoalHistory",
    "GoalObservation", "GoalReview",
    "GoalService", "GoalStats", "GoalRetrievalService",
    "GoalEvolutionService", "GoalContextBuilder", "GoalContext",
    "GoalMetrics", "GoalEventPublisher",
]
