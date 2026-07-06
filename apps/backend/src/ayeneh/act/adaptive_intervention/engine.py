"""ACT-03 Adaptive Intervention Engine.

7-phase pipeline:
    1. CurrentContext — gather current context
    2. ExecutionMonitoring — assess execution state
    3. GoalAnalysis — analyze goal alignment
    4. OpportunityDetection — detect intervention opportunities
    5. RiskAssessment — assess risks
    6. InterventionEvaluation — evaluate intervention value
    7. DialogueStrategy — design dialogue strategy
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.act.adaptive_intervention.timing import TimingIntelligence
from ayeneh.act.adaptive_intervention.types import (
    INTERVENTION_CATEGORIES,
    TIMING_ASSESSMENTS,
    DialoguePlan,
    InterventionEvaluation,
    InterventionObject,
    InterventionResult,
    OpportunitySignal,
    RiskSignal,
)

logger = structlog.get_logger(__name__)


class AdaptiveInterventionEngine:
    """Adaptive intervention engine (ACT-03).

    Pipeline:
        1. CurrentContext — gather current context
        2. ExecutionMonitoring — assess execution state
        3. GoalAnalysis — analyze goal alignment
        4. OpportunityDetection — detect intervention opportunities
        5. RiskAssessment — assess risks
        6. InterventionEvaluation — evaluate intervention value
        7. DialogueStrategy — design dialogue strategy
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._interventions: dict[str, InterventionObject] = {}
        self._timing_intelligence = TimingIntelligence()

    def process(
        self,
        intervention_request: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> InterventionResult:
        """Run the full ACT-03 pipeline.

        Parameters
        ----------
        intervention_request:
            Dict with ``'intervention_id'``, ``'trigger_event'``,
            ``'associated_goal'``, and optional fields.
        context:
            Optional context dict with execution state, goal data,
            opportunities, and risks.
        """
        ctx = context or {}

        logger.info(
            'act.adaptive_intervention.pipeline_started',
            intervention_id=intervention_request.get(
                'intervention_id', '',
            ),
        )

        # Phase 1: CurrentContext
        current_ctx = self._phase_current_context(intervention_request, ctx)

        # Phase 2: ExecutionMonitoring
        exec_assessment = self._phase_execution_monitoring(current_ctx, ctx)

        # Phase 3: GoalAnalysis
        goal_analysis = self._phase_goal_analysis(current_ctx, ctx)

        # Phase 4: OpportunityDetection
        opportunities = self._phase_opportunity_detection(
            current_ctx, exec_assessment, goal_analysis, ctx,
        )

        # Phase 5: RiskAssessment
        risks = self._phase_risk_assessment(
            current_ctx, exec_assessment, goal_analysis, ctx,
        )

        # Phase 6: InterventionEvaluation
        evaluation = self._phase_intervention_evaluation(
            opportunities, risks, ctx,
        )

        # Phase 7: DialogueStrategy
        dialogue_plan = self._phase_dialogue_strategy(
            evaluation, ctx,
        )

        # Build intervention object
        intervention = self._build_intervention_object(
            intervention_request,
            evaluation,
            dialogue_plan,
            ctx,
        )

        # Timing assessment
        timing = self._timing_intelligence.evaluate(ctx)

        phases = (
            'CurrentContext',
            'ExecutionMonitoring',
            'GoalAnalysis',
            'OpportunityDetection',
            'RiskAssessment',
            'InterventionEvaluation',
            'DialogueStrategy',
        )

        result = InterventionResult(
            intervention=intervention,
            timing=timing,
            opportunities=opportunities,
            risks=risks,
            evaluation=evaluation,
            dialogue_plan=dialogue_plan,
            pipeline_phases_completed=phases,
        )

        logger.info(
            'act.adaptive_intervention.pipeline_completed',
            intervention_id=intervention.intervention_id,
            type=intervention.intervention_type,
            timing=timing.overall_timing,
        )

        return result

    # -------------------------------------------------------------------
    # Phase 1: CurrentContext
    # -------------------------------------------------------------------

    def _phase_current_context(
        self,
        request: dict[str, Any],
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        """Gather and normalize current context."""
        current = {
            'intervention_id': request.get('intervention_id', ''),
            'trigger_event': request.get('trigger_event', ''),
            'associated_goal': request.get('associated_goal', ''),
            'associated_plan': request.get('associated_plan', ''),
            'associated_habit': request.get('associated_habit', ''),
            'execution_state': ctx.get('execution_state', ''),
            'execution_progress': ctx.get('execution_progress', 0.0),
            'goal_priority': ctx.get('goal_priority', 0.5),
            'habit_strength': ctx.get('habit_strength', 0.0),
            'cognitive_load': ctx.get('cognitive_load', 0.5),
            'emotional_state': ctx.get('emotional_state', 'neutral'),
            'recent_events': ctx.get('recent_events', []),
        }

        logger.debug(
            'act.adaptive_intervention.phase_current_context',
            trigger=current['trigger_event'],
        )
        return current

    # -------------------------------------------------------------------
    # Phase 2: ExecutionMonitoring
    # -------------------------------------------------------------------

    def _phase_execution_monitoring(
        self,
        current_ctx: dict[str, Any],
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        """Assess execution state for intervention relevance."""
        exec_state = current_ctx.get('execution_state', '')
        progress = current_ctx.get('execution_progress', 0.0)

        assessment = {
            'state': exec_state,
            'progress': progress,
            'deviations': ctx.get('execution_deviations', []),
            'blocked': exec_state == 'blocked',
            'stalled': progress < 0.1 and exec_state == 'running',
            'near_completion': progress > 0.9,
            'resource_pressure': ctx.get('resource_pressure', False),
        }

        logger.debug(
            'act.adaptive_intervention.phase_execution_monitoring',
            state=exec_state,
            blocked=assessment['blocked'],
        )
        return assessment

    # -------------------------------------------------------------------
    # Phase 3: GoalAnalysis
    # -------------------------------------------------------------------

    def _phase_goal_analysis(
        self,
        current_ctx: dict[str, Any],
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze goal alignment and progress."""
        goal_priority = current_ctx.get('goal_priority', 0.5)
        progress = current_ctx.get('execution_progress', 0.0)

        analysis = {
            'priority': goal_priority,
            'progress': progress,
            'goal_frustration': ctx.get('goal_frustration', 0.0),
            'goal_abandonment_risk': ctx.get(
                'goal_abandonment_risk', 0.0,
            ),
            'alignment_score': ctx.get('goal_alignment', 0.5),
            'recent_progress_trend': ctx.get(
                'progress_trend', 'stable',
            ),
        }

        logger.debug(
            'act.adaptive_intervention.phase_goal_analysis',
            priority=goal_priority,
            frustration=analysis['goal_frustration'],
        )
        return analysis

    # -------------------------------------------------------------------
    # Phase 4: OpportunityDetection
    # -------------------------------------------------------------------

    def _phase_opportunity_detection(
        self,
        current_ctx: dict[str, Any],
        exec_assessment: dict[str, Any],
        goal_analysis: dict[str, Any],
        ctx: dict[str, Any],
    ) -> tuple[OpportunitySignal, ...]:
        """Detect opportunities for intervention."""
        opportunities: list[OpportunitySignal] = []

        if exec_assessment['near_completion']:
            opportunities.append(
                OpportunitySignal(
                    signal_id=str(uuid.uuid4()),
                    signal_type='completion_celebration',
                    description='Execution is near completion. Celebrate progress.',
                    strength=0.9,
                    urgency=0.7,
                ),
            )

        if exec_assessment['stalled']:
            opportunities.append(
                OpportunitySignal(
                    signal_id=str(uuid.uuid4()),
                    signal_type='stall_recovery',
                    description='Execution appears stalled. Suggest recovery.',
                    strength=0.8,
                    urgency=0.8,
                ),
            )

        if goal_analysis['goal_frustration'] > 0.6:
            opportunities.append(
                OpportunitySignal(
                    signal_id=str(uuid.uuid4()),
                    signal_type='frustration_support',
                    description='High frustration detected. Offer support.',
                    strength=0.85,
                    urgency=0.9,
                ),
            )

        if goal_analysis['recent_progress_trend'] == 'improving':
            opportunities.append(
                OpportunitySignal(
                    signal_id=str(uuid.uuid4()),
                    signal_type='momentum_reinforcement',
                    description='Progress is improving. Reinforce momentum.',
                    strength=0.7,
                    urgency=0.5,
                ),
            )

        raw_opportunities = ctx.get('opportunities', [])
        for raw in raw_opportunities:
            opportunities.append(
                OpportunitySignal(
                    signal_id=raw.get(
                        'signal_id', str(uuid.uuid4()),
                    ),
                    signal_type=raw.get('signal_type', ''),
                    description=raw.get('description', ''),
                    strength=raw.get('strength', 0.5),
                    urgency=raw.get('urgency', 0.5),
                ),
            )

        result = tuple(opportunities)

        logger.debug(
            'act.adaptive_intervention.phase_opportunity_detection',
            opportunities_found=len(result),
        )
        return result

    # -------------------------------------------------------------------
    # Phase 5: RiskAssessment
    # -------------------------------------------------------------------

    def _phase_risk_assessment(
        self,
        current_ctx: dict[str, Any],
        exec_assessment: dict[str, Any],
        goal_analysis: dict[str, Any],
        ctx: dict[str, Any],
    ) -> tuple[RiskSignal, ...]:
        """Assess risks that may warrant intervention."""
        risks: list[RiskSignal] = []

        if exec_assessment['blocked']:
            risks.append(
                RiskSignal(
                    signal_id=str(uuid.uuid4()),
                    risk_type='execution_blocked',
                    description='Execution is blocked. Risk of abandonment.',
                    severity=0.8,
                    probability=0.7,
                ),
            )

        if goal_analysis['goal_abandonment_risk'] > 0.5:
            risks.append(
                RiskSignal(
                    signal_id=str(uuid.uuid4()),
                    risk_type='goal_abandonment',
                    description='Risk of goal abandonment detected.',
                    severity=goal_analysis['goal_abandonment_risk'],
                    probability=goal_analysis['goal_abandonment_risk'],
                ),
            )

        if exec_assessment['resource_pressure']:
            risks.append(
                RiskSignal(
                    signal_id=str(uuid.uuid4()),
                    risk_type='resource_depletion',
                    description='Resource pressure may impact execution.',
                    severity=0.6,
                    probability=0.6,
                ),
            )

        if goal_analysis['goal_frustration'] > 0.7:
            risks.append(
                RiskSignal(
                    signal_id=str(uuid.uuid4()),
                    risk_type='emotional_overload',
                    description='High frustration may impair decision-making.',
                    severity=0.7,
                    probability=0.65,
                ),
            )

        raw_risks = ctx.get('risks', [])
        for raw in raw_risks:
            risks.append(
                RiskSignal(
                    signal_id=raw.get(
                        'signal_id', str(uuid.uuid4()),
                    ),
                    risk_type=raw.get('risk_type', ''),
                    description=raw.get('description', ''),
                    severity=raw.get('severity', 0.5),
                    probability=raw.get('probability', 0.5),
                ),
            )

        result = tuple(risks)

        logger.debug(
            'act.adaptive_intervention.phase_risk_assessment',
            risks_found=len(result),
        )
        return result

    # -------------------------------------------------------------------
    # Phase 6: InterventionEvaluation
    # -------------------------------------------------------------------

    def _phase_intervention_evaluation(
        self,
        opportunities: tuple[OpportunitySignal, ...],
        risks: tuple[RiskSignal, ...],
        ctx: dict[str, Any],
    ) -> InterventionEvaluation:
        """Evaluate the cost-benefit of intervention."""
        if opportunities:
            max_opportunity = max(opportunities, key=lambda o: o.strength)
            expected_benefit = max_opportunity.strength * 0.8
        else:
            expected_benefit = 0.0

        if risks:
            max_risk = max(risks, key=lambda r: r.severity)
            potential_cost = max_risk.severity * 0.3
        else:
            potential_cost = 0.1

        net_value = expected_benefit - potential_cost

        reasoning_parts: list[str] = []
        if opportunities:
            reasoning_parts.append(
                f'{len(opportunities)} opportunity signal(s) detected.'
            )
        if risks:
            reasoning_parts.append(
                f'{len(risks)} risk signal(s) detected.'
            )
        reasoning = ' '.join(reasoning_parts) if reasoning_parts else (
            'No significant signals detected.'
        )

        evaluation = InterventionEvaluation(
            evaluation_id=str(uuid.uuid4()),
            expected_benefit=expected_benefit,
            potential_cost=potential_cost,
            net_value=net_value,
            confidence=ctx.get('evaluation_confidence', 0.5),
            reasoning=reasoning,
        )

        logger.debug(
            'act.adaptive_intervention.phase_intervention_evaluation',
            net_value=net_value,
            confidence=evaluation.confidence,
        )
        return evaluation

    # -------------------------------------------------------------------
    # Phase 7: DialogueStrategy
    # -------------------------------------------------------------------

    def _phase_dialogue_strategy(
        self,
        evaluation: InterventionEvaluation,
        ctx: dict[str, Any],
    ) -> DialoguePlan:
        """Design the dialogue strategy for intervention delivery."""
        net_value = evaluation.net_value

        if net_value > 0.5:
            strategy = 'collaborative_planning'
            intensity = 'StructuredRecommendation'
        elif net_value > 0.2:
            strategy = 'reflective_guidance'
            intensity = 'ReflectiveQuestion'
        elif net_value > 0.0:
            strategy = 'gentle_nudge'
            intensity = 'GentleReminder'
        else:
            strategy = 'direct_suggestion'
            intensity = 'PassiveLogging'

        if ctx.get('celebration_warranted', False):
            strategy = 'celebratory_acknowledgment'
            intensity = 'StructuredRecommendation'

        plan = DialoguePlan(
            plan_id=str(uuid.uuid4()),
            strategy=strategy,
            intensity=intensity,
            content_outline=ctx.get('content_outline', ''),
            follow_up_needed=net_value > 0.3,
            follow_up_delay_hours=ctx.get('follow_up_delay_hours', 24.0),
        )

        logger.debug(
            'act.adaptive_intervention.phase_dialogue_strategy',
            strategy=strategy,
            intensity=intensity,
        )
        return plan

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def _build_intervention_object(
        self,
        request: dict[str, Any],
        evaluation: InterventionEvaluation,
        dialogue_plan: DialoguePlan,
        ctx: dict[str, Any],
    ) -> InterventionObject:
        """Build or update the intervention object."""
        intervention_id = request.get(
            'intervention_id', str(uuid.uuid4()),
        )
        existing = self._interventions.get(intervention_id)

        intervention_type = request.get('intervention_type', '')
        if intervention_type not in INTERVENTION_CATEGORIES:
            intervention_type = ctx.get(
                'suggested_type', 'Reminder',
            )
            if intervention_type not in INTERVENTION_CATEGORIES:
                intervention_type = 'Reminder'

        timing_str = ctx.get('timing_assessment', 'acceptable')
        if timing_str not in TIMING_ASSESSMENTS:
            timing_str = 'acceptable'

        outcome_str = 'pending_evaluation'

        if existing:
            new_history = list(existing.version_history)
            new_history.append({
                'type': existing.intervention_type,
                'outcome': existing.outcome_evaluation,
                'timestamp': ctx.get('update_timestamp', ''),
            })

            intervention = InterventionObject(
                intervention_id=intervention_id,
                trigger_event=ctx.get(
                    'trigger_event', existing.trigger_event,
                ),
                associated_goal=ctx.get(
                    'associated_goal', existing.associated_goal,
                ),
                associated_plan=ctx.get(
                    'associated_plan', existing.associated_plan,
                ),
                associated_habit=ctx.get(
                    'associated_habit', existing.associated_habit,
                ),
                intervention_type=intervention_type,
                expected_benefit=evaluation.expected_benefit,
                potential_cost=evaluation.potential_cost,
                confidence=evaluation.confidence,
                timing_assessment=timing_str,
                outcome_evaluation=outcome_str,
                version_history=tuple(new_history),
                creation_timestamp=existing.creation_timestamp,
                explainability_metadata=dict(
                    ctx.get('explainability_metadata',
                            existing.explainability_metadata),
                ),
            )
        else:
            intervention = InterventionObject(
                intervention_id=intervention_id,
                trigger_event=request.get('trigger_event', ''),
                associated_goal=request.get('associated_goal', ''),
                associated_plan=request.get('associated_plan', ''),
                associated_habit=request.get('associated_habit', ''),
                intervention_type=intervention_type,
                expected_benefit=evaluation.expected_benefit,
                potential_cost=evaluation.potential_cost,
                confidence=evaluation.confidence,
                timing_assessment=timing_str,
                outcome_evaluation=outcome_str,
                explainability_metadata=dict(
                    ctx.get('explainability_metadata', {}),
                ),
            )

        self._interventions[intervention_id] = intervention
        return intervention

    # -------------------------------------------------------------------
    # Public helpers
    # -------------------------------------------------------------------

    def get_intervention(
        self, intervention_id: str,
    ) -> InterventionObject | None:
        """Retrieve a tracked intervention by ID."""
        return self._interventions.get(intervention_id)

    def list_interventions(self) -> list[InterventionObject]:
        """Return all tracked interventions."""
        return list(self._interventions.values())

    def get_timing_intelligence(self) -> TimingIntelligence:
        """Return the timing intelligence module."""
        return self._timing_intelligence
