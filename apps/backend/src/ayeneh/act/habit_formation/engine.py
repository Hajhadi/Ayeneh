"""ACT-02 Habit Formation Engine.

7-phase pipeline:
    1. BehaviorObservation — observe target behavior
    2. CueDetection — detect cues associated with behavior
    3. ReinforcementTracking — track reinforcement events
    4. StrengthEstimation — estimate habit strength
    5. StabilityAssessment — assess context stability
    6. CompetitionAnalysis — analyze habit competition
    7. HabitPublication — publish habit for downstream use
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.act.habit_formation.types import (
    CUE_CATEGORIES,
    HABIT_LIFECYCLE,
    HABIT_LIFECYCLE_TRANSITIONS,
    REINFORCEMENT_TYPES,
    CueInstance,
    HabitCompetition,
    HabitObject,
    HabitPublication,
    HabitResult,
    HabitStrengthSnapshot,
    ReinforcementRecord,
)

logger = structlog.get_logger(__name__)


class HabitFormationEngine:
    """Habit formation engine (ACT-02).

    Pipeline:
        1. BehaviorObservation — observe target behavior
        2. CueDetection — detect cues associated with behavior
        3. ReinforcementTracking — track reinforcement events
        4. StrengthEstimation — estimate habit strength
        5. StabilityAssessment — assess context stability
        6. CompetitionAnalysis — analyze habit competition
        7. HabitPublication — publish habit for downstream use
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._habits: dict[str, HabitObject] = {}

    def process(
        self,
        habit_request: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> HabitResult:
        """Run the full ACT-02 pipeline.

        Parameters
        ----------
        habit_request:
            Dict with ``'habit_id'``, ``'associated_behavior'``,
            ``'primary_cue'``, and optional fields.
        context:
            Optional context dict with observations, reinforcements,
            cues, and competition data.
        """
        ctx = context or {}

        logger.info(
            'act.habit_formation.pipeline_started',
            habit_id=habit_request.get('habit_id', ''),
        )

        # Phase 1: BehaviorObservation
        behavior_obs = self._phase_behavior_observation(habit_request, ctx)

        # Phase 2: CueDetection
        cues = self._phase_cue_detection(habit_request, ctx)

        # Phase 3: ReinforcementTracking
        reinforcements = self._phase_reinforcement_tracking(
            habit_request, ctx,
        )

        # Phase 4: StrengthEstimation
        strength_snapshot = self._phase_strength_estimation(
            behavior_obs, reinforcements, ctx,
        )

        # Phase 5: StabilityAssessment
        stability = self._phase_stability_assessment(habit_request, ctx)

        # Phase 6: CompetitionAnalysis
        competitions = self._phase_competition_analysis(
            habit_request, ctx,
        )

        # Build or update habit object
        habit = self._build_habit_object(
            habit_request, behavior_obs, strength_snapshot, stability, ctx,
        )

        # Phase 7: HabitPublication
        publications = self._phase_habit_publication(habit, ctx)

        lifecycle_transition = f'{behavior_obs.get("previous_status", "proposed")}->{habit.current_status}'

        phases = (
            'BehaviorObservation',
            'CueDetection',
            'ReinforcementTracking',
            'StrengthEstimation',
            'StabilityAssessment',
            'CompetitionAnalysis',
            'HabitPublication',
        )

        result = HabitResult(
            habit=habit,
            lifecycle_transition=lifecycle_transition,
            cue_instances=cues,
            reinforcement_records=reinforcements,
            competitions=competitions,
            strength_snapshots=(strength_snapshot,),
            publications=publications,
            pipeline_phases_completed=phases,
        )

        logger.info(
            'act.habit_formation.pipeline_completed',
            habit_id=habit.habit_id,
            status=habit.current_status,
            strength=habit.habit_strength,
        )

        return result

    # -------------------------------------------------------------------
    # Phase 1: BehaviorObservation
    # -------------------------------------------------------------------

    def _phase_behavior_observation(
        self,
        request: dict[str, Any],
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        """Observe and record the target behavior."""
        behavior = request.get('associated_behavior', '')
        frequency = ctx.get('observation_frequency', 0.0)
        consistency = ctx.get('behavioral_consistency', 0.0)
        previous_status = request.get('current_status', 'proposed')

        observation = {
            'behavior': behavior,
            'frequency': frequency,
            'consistency': consistency,
            'previous_status': previous_status,
            'observation_count': ctx.get('observation_count', 0),
            'observation_period_days': ctx.get('observation_period_days', 0),
        }

        logger.debug(
            'act.habit_formation.phase_behavior_observation',
            habit_id=request.get('habit_id', ''),
            behavior=behavior,
            frequency=frequency,
        )
        return observation

    # -------------------------------------------------------------------
    # Phase 2: CueDetection
    # -------------------------------------------------------------------

    def _phase_cue_detection(
        self,
        request: dict[str, Any],
        ctx: dict[str, Any],
    ) -> tuple[CueInstance, ...]:
        """Detect cues associated with the behavior."""
        cues: list[CueInstance] = []

        primary = request.get('primary_cue', '')
        if primary:
            category = ctx.get(
                'primary_cue_category', 'Time',
            )
            if category not in CUE_CATEGORIES:
                category = 'Time'
            cues.append(
                CueInstance(
                    cue_id=str(uuid.uuid4()),
                    cue_category=category,
                    cue_description=primary,
                    cue_strength=ctx.get('primary_cue_strength', 0.5),
                    frequency=ctx.get('primary_cue_frequency', 0.0),
                ),
            )

        secondary = request.get('secondary_cues', ())
        for cue_desc in secondary:
            cues.append(
                CueInstance(
                    cue_id=str(uuid.uuid4()),
                    cue_description=cue_desc,
                    cue_strength=ctx.get('secondary_cue_strength', 0.3),
                ),
            )

        raw_cues = ctx.get('additional_cues', [])
        for raw in raw_cues:
            category = raw.get('cue_category', 'Time')
            if category not in CUE_CATEGORIES:
                category = 'Time'
            cues.append(
                CueInstance(
                    cue_id=raw.get('cue_id', str(uuid.uuid4())),
                    cue_category=category,
                    cue_description=raw.get('cue_description', ''),
                    cue_strength=raw.get('cue_strength', 0.0),
                    frequency=raw.get('frequency', 0.0),
                ),
            )

        result = tuple(cues)

        logger.debug(
            'act.habit_formation.phase_cue_detection',
            habit_id=request.get('habit_id', ''),
            cues_found=len(result),
        )
        return result

    # -------------------------------------------------------------------
    # Phase 3: ReinforcementTracking
    # -------------------------------------------------------------------

    def _phase_reinforcement_tracking(
        self,
        request: dict[str, Any],
        ctx: dict[str, Any],
    ) -> tuple[ReinforcementRecord, ...]:
        """Track reinforcement events for the habit."""
        records: list[ReinforcementRecord] = []

        raw_reinforcements = ctx.get('reinforcements', [])
        for raw in raw_reinforcements:
            r_type = raw.get('reinforcement_type', 'positive_outcome')
            if r_type not in REINFORCEMENT_TYPES:
                r_type = 'positive_outcome'

            records.append(
                ReinforcementRecord(
                    reinforcement_id=raw.get(
                        'reinforcement_id', str(uuid.uuid4()),
                    ),
                    reinforcement_type=r_type,
                    intensity=raw.get('intensity', 0.0),
                    description=raw.get('description', ''),
                ),
            )

        if not records:
            expected = request.get('expected_reward', '')
            if expected:
                records.append(
                    ReinforcementRecord(
                        reinforcement_id=str(uuid.uuid4()),
                        reinforcement_type='anticipated_reward',
                        intensity=ctx.get('expected_reward_intensity', 0.5),
                        description=expected,
                    ),
                )

        result = tuple(records)

        logger.debug(
            'act.habit_formation.phase_reinforcement_tracking',
            habit_id=request.get('habit_id', ''),
            reinforcements=len(result),
        )
        return result

    # -------------------------------------------------------------------
    # Phase 4: StrengthEstimation
    # -------------------------------------------------------------------

    def _phase_strength_estimation(
        self,
        behavior_obs: dict[str, Any],
        reinforcements: tuple[ReinforcementRecord, ...],
        ctx: dict[str, Any],
    ) -> HabitStrengthSnapshot:
        """Estimate the current strength of the habit."""
        frequency = behavior_obs.get('frequency', 0.0)
        consistency = behavior_obs.get('consistency', 0.0)

        positive_count = sum(
            1 for r in reinforcements
            if r.reinforcement_type in ('positive_outcome', 'intrinsic_satisfaction')
        )
        total_reinforcements = max(len(reinforcements), 1)
        reinforcement_ratio = positive_count / total_reinforcements

        strength = (
            0.3 * min(frequency, 1.0)
            + 0.3 * consistency
            + 0.2 * reinforcement_ratio
            + 0.2 * ctx.get('context_stability', 0.0)
        )
        strength = max(0.0, min(1.0, strength))

        snapshot = HabitStrengthSnapshot(
            snapshot_id=str(uuid.uuid4()),
            strength_value=strength,
            consistency_score=consistency,
            context_stability=ctx.get('context_stability', 0.0),
        )

        logger.debug(
            'act.habit_formation.phase_strength_estimation',
            strength=strength,
        )
        return snapshot

    # -------------------------------------------------------------------
    # Phase 5: StabilityAssessment
    # -------------------------------------------------------------------

    def _phase_stability_assessment(
        self,
        request: dict[str, Any],
        ctx: dict[str, Any],
    ) -> float:
        """Assess the stability of the habit's context."""
        context_stability = ctx.get('context_stability', 0.0)
        cue_diversity = len(
            request.get('secondary_cues', ()),
        )
        cue_stability = min(1.0, 0.5 + cue_diversity * 0.1)

        stability = (context_stability * 0.6 + cue_stability * 0.4)
        stability = max(0.0, min(1.0, stability))

        logger.debug(
            'act.habit_formation.phase_stability_assessment',
            habit_id=request.get('habit_id', ''),
            stability=stability,
        )
        return stability

    # -------------------------------------------------------------------
    # Phase 6: CompetitionAnalysis
    # -------------------------------------------------------------------

    def _phase_competition_analysis(
        self,
        request: dict[str, Any],
        ctx: dict[str, Any],
    ) -> tuple[HabitCompetition, ...]:
        """Analyze competition with other habits."""
        competitions: list[HabitCompetition] = []

        raw_competitions = ctx.get('competitions', [])
        for raw in raw_competitions:
            competitions.append(
                HabitCompetition(
                    competition_id=raw.get(
                        'competition_id', str(uuid.uuid4()),
                    ),
                    habit_a=raw.get(
                        'habit_a', request.get('habit_id', ''),
                    ),
                    habit_b=raw.get('habit_b', ''),
                    competition_type=raw.get(
                        'competition_type', 'competing',
                    ),
                    resolution_strategy=raw.get(
                        'resolution_strategy', 'prioritize_stronger',
                    ),
                    resolution_outcome=raw.get('resolution_outcome', ''),
                ),
            )

        result = tuple(competitions)

        logger.debug(
            'act.habit_formation.phase_competition_analysis',
            habit_id=request.get('habit_id', ''),
            competitions_found=len(result),
        )
        return result

    # -------------------------------------------------------------------
    # Phase 7: HabitPublication
    # -------------------------------------------------------------------

    def _phase_habit_publication(
        self,
        habit: HabitObject,
        ctx: dict[str, Any],
    ) -> tuple[HabitPublication, ...]:
        """Publish habit for downstream consumption."""
        publications: list[HabitPublication] = []

        recommendation = self._generate_recommendation(habit)

        publications.append(
            HabitPublication(
                publication_id=str(uuid.uuid4()),
                habit_id=habit.habit_id,
                habit_status=habit.current_status,
                strength=habit.habit_strength,
                recommendation=recommendation,
            ),
        )

        result = tuple(publications)

        logger.debug(
            'act.habit_formation.phase_habit_publication',
            habit_id=habit.habit_id,
            publications=len(result),
        )
        return result

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def _build_habit_object(
        self,
        request: dict[str, Any],
        behavior_obs: dict[str, Any],
        strength_snapshot: HabitStrengthSnapshot,
        stability: float,
        ctx: dict[str, Any],
    ) -> HabitObject:
        """Build or update the habit object."""
        habit_id = request.get('habit_id', str(uuid.uuid4()))
        existing = self._habits.get(habit_id)

        status = request.get('current_status', 'proposed')
        if status not in HABIT_LIFECYCLE:
            status = 'proposed'

        if existing:
            new_history = list(existing.version_history)
            new_history.append({
                'status': existing.current_status,
                'strength': existing.habit_strength,
                'timestamp': datetime.now(UTC).isoformat(),
            })

            habit = HabitObject(
                habit_id=habit_id,
                associated_goal=ctx.get(
                    'associated_goal', existing.associated_goal,
                ),
                associated_behavior=ctx.get(
                    'associated_behavior',
                    existing.associated_behavior,
                ),
                primary_cue=ctx.get(
                    'primary_cue', existing.primary_cue,
                ),
                secondary_cues=ctx.get(
                    'secondary_cues', existing.secondary_cues,
                ),
                expected_reward=ctx.get(
                    'expected_reward', existing.expected_reward,
                ),
                observed_reinforcement=ctx.get(
                    'observed_reinforcement',
                    existing.observed_reinforcement,
                ),
                habit_strength=strength_snapshot.strength_value,
                context_stability=stability,
                behavioral_consistency=behavior_obs.get(
                    'consistency', existing.behavioral_consistency,
                ),
                current_status=status,
                version_history=tuple(new_history),
                creation_timestamp=existing.creation_timestamp,
                explainability_metadata=dict(
                    ctx.get('explainability_metadata',
                            existing.explainability_metadata),
                ),
            )
        else:
            habit = HabitObject(
                habit_id=habit_id,
                associated_goal=ctx.get('associated_goal', ''),
                associated_behavior=ctx.get(
                    'associated_behavior',
                    request.get('associated_behavior', ''),
                ),
                primary_cue=ctx.get(
                    'primary_cue',
                    request.get('primary_cue', ''),
                ),
                secondary_cues=tuple(ctx.get(
                    'secondary_cues',
                    request.get('secondary_cues', ()),
                )),
                expected_reward=ctx.get(
                    'expected_reward',
                    request.get('expected_reward', ''),
                ),
                observed_reinforcement=ctx.get(
                    'observed_reinforcement', 0.0,
                ),
                habit_strength=strength_snapshot.strength_value,
                context_stability=stability,
                behavioral_consistency=behavior_obs.get(
                    'consistency', 0.0,
                ),
                current_status=status,
                explainability_metadata=dict(
                    ctx.get('explainability_metadata', {}),
                ),
            )

        self._habits[habit_id] = habit
        return habit

    def _generate_recommendation(self, habit: HabitObject) -> str:
        """Generate a recommendation based on habit state."""
        if habit.current_status in ('proposed', 'initiated'):
            return (
                'Continue observing to build strength. '
                'Focus on cue consistency.'
            )
        if habit.current_status == 'developing':
            return (
                'Habit is forming. Reinforce with positive outcomes.'
            )
        if habit.current_status == 'strengthening':
            return (
                'Good progress. Maintain consistency to reach stability.'
            )
        if habit.current_status == 'stable':
            return (
                'Habit is stable. Monitor for weakening signals.'
            )
        if habit.current_status == 'weakening':
            return (
                'Habit is weakening. Re-examine cues and reinforcement.'
            )
        if habit.current_status == 'dormant':
            return (
                'Habit is dormant. Consider re-initiating with '
                'stronger cues.'
            )
        return 'No recommendation available.'

    # -------------------------------------------------------------------
    # Public helpers
    # -------------------------------------------------------------------

    def get_habit(self, habit_id: str) -> HabitObject | None:
        """Retrieve a tracked habit by ID."""
        return self._habits.get(habit_id)

    def list_habits(self) -> list[HabitObject]:
        """Return all tracked habits."""
        return list(self._habits.values())

    def validate_lifecycle_transition(
        self, from_status: str, to_status: str,
    ) -> bool:
        """Check whether a lifecycle transition is valid."""
        allowed = HABIT_LIFECYCLE_TRANSITIONS.get(from_status, [])
        return to_status in allowed
