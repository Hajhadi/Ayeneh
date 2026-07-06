"""DEC-01 Decision Support Engine.

Decision support engine implementing a 9-phase pipeline:
1. DecisionContext — gather contextual information
2. GoalRetrieval — identify relevant goals
3. ConstraintAnalysis — analyze constraints
4. OptionGeneration — generate decision options
5. EvidenceEvaluation — evaluate supporting evidence
6. ScenarioSimulation — simulate predicted outcomes
7. RiskOpportunityAnalysis — assess risks and opportunities
8. DecisionSupportObject — construct the decision object
9. DialoguePresentation — prepare for dialogue presentation
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.dec.decision_support.types import (
    DECISION_CATEGORIES,
    REVERSIBILITY_LEVELS,
    DecisionContext,
    DecisionObject,
    DecisionResult,
    MultiCriteriaScore,
    OpportunityAssessment,
    RiskAssessment,
    ScenarioOutcome,
    TradeOff,
)

logger = structlog.get_logger(__name__)


class DecisionSupportEngine:
    """Decision support engine (DEC-01).

    Pipeline:
        1. DecisionContext — gather contextual information
        2. GoalRetrieval — identify relevant goals
        3. ConstraintAnalysis — analyze constraints
        4. OptionGeneration — generate decision options
        5. EvidenceEvaluation — evaluate supporting evidence
        6. ScenarioSimulation — simulate predicted outcomes
        7. RiskOpportunityAnalysis — assess risks and opportunities
        8. DecisionSupportObject — construct the decision object
        9. DialoguePresentation — prepare for dialogue presentation
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._decisions: dict[str, DecisionObject] = {}

    def process(
        self,
        question: str,
        context: dict[str, Any] | None = None,
        existing_goals: list[dict[str, Any]] | None = None,
        memories: list[dict[str, Any]] | None = None,
    ) -> DecisionResult:
        """Run the full DEC-01 pipeline.

        Parameters
        ----------
        question:
            The decision question to analyze.
        context:
            Optional context dict with goals, constraints, resources.
        existing_goals:
            Optional list of goal dicts from the goal management module.
        memories:
            Optional list of memory dicts for evidence.
        """
        ctx = context or {}
        goals = existing_goals or []
        mems = memories or []

        logger.info(
            'dec.decision_support.pipeline_started',
            question=question[:80],
            goal_count=len(goals),
            memory_count=len(mems),
        )

        # Phase 1: DecisionContext
        decision_context = self._phase_decision_context(ctx, goals, mems)

        # Phase 2: GoalRetrieval
        relevant_goals = self._phase_goal_retrieval(goals, question)

        # Phase 3: ConstraintAnalysis
        constraints = self._phase_constraint_analysis(ctx, decision_context)

        # Phase 4: OptionGeneration
        options = self._phase_option_generation(question, decision_context, relevant_goals)

        # Phase 5: EvidenceEvaluation
        evidence, competing = self._phase_evidence_evaluation(mems, options)

        # Phase 6: ScenarioSimulation
        scenarios = self._phase_scenario_simulation(options, relevant_goals)

        # Phase 7: RiskOpportunityAnalysis
        risks, opportunities = self._phase_risk_opportunity_analysis(options, scenarios)

        # Phase 8: DecisionSupportObject
        decision = self._phase_decision_support_object(
            question, decision_context, options, relevant_goals,
            constraints, evidence, competing, scenarios, risks, opportunities,
        )

        # Phase 9: DialoguePresentation
        result = self._phase_dialogue_presentation(
            decision, decision_context, scenarios, risks, opportunities,
        )

        logger.info(
            'dec.decision_support.pipeline_completed',
            decision_id=decision.decision_id,
            option_count=len(options),
            overall_confidence=result.overall_confidence,
        )

        return result

    # ------------------------------------------------------------------
    # Phase 1: DecisionContext
    # ------------------------------------------------------------------

    def _phase_decision_context(
        self,
        context: dict[str, Any],
        goals: list[dict[str, Any]],
        memories: list[dict[str, Any]],
    ) -> DecisionContext:
        """Gather and structure the decision context."""
        logger.debug('dec.decision_support.phase1_decision_context')

        current_goals = tuple(g.get('description', '') for g in goals if g.get('description'))
        relevant_projects = tuple(context.get('relevant_projects', ()))
        identity_considerations = tuple(context.get('identity_considerations', ()))
        behavioral_history = tuple(
            m.get('content', '') for m in memories
            if m.get('category') == 'behavior'
        )
        available_resources = tuple(context.get('available_resources', ()))
        environmental_constraints = tuple(context.get('environmental_constraints', ()))
        time_constraints = tuple(context.get('time_constraints', ()))

        return DecisionContext(
            current_goals=current_goals,
            relevant_projects=relevant_projects,
            identity_considerations=identity_considerations,
            behavioral_history=behavioral_history,
            available_resources=available_resources,
            environmental_constraints=environmental_constraints,
            time_constraints=time_constraints,
        )

    # ------------------------------------------------------------------
    # Phase 2: GoalRetrieval
    # ------------------------------------------------------------------

    def _phase_goal_retrieval(
        self,
        goals: list[dict[str, Any]],
        question: str,
    ) -> tuple[str, ...]:
        """Identify goals relevant to the decision question."""
        logger.debug('dec.decision_support.phase2_goal_retrieval')

        if not goals:
            return ()

        relevant: list[str] = []
        question_lower = question.lower()
        for goal in goals:
            desc = goal.get('description', '').lower()
            category = goal.get('category', '').lower()
            keywords = desc.split() + category.split()
            overlap = sum(1 for kw in keywords if kw in question_lower)
            if overlap > 0 or goal.get('priority', 0.0) > 0.7:
                relevant.append(goal.get('description', ''))

        return tuple(relevant)

    # ------------------------------------------------------------------
    # Phase 3: ConstraintAnalysis
    # ------------------------------------------------------------------

    def _phase_constraint_analysis(
        self,
        context: dict[str, Any],
        decision_context: DecisionContext,
    ) -> tuple[dict[str, Any], ...]:
        """Analyze constraints that affect the decision."""
        logger.debug('dec.decision_support.phase3_constraint_analysis')

        constraints: list[dict[str, Any]] = []

        for rc in decision_context.environmental_constraints:
            constraints.append({
                'type': 'environmental',
                'description': rc,
                'severity': 0.5,
            })

        for tc in decision_context.time_constraints:
            constraints.append({
                'type': 'temporal',
                'description': tc,
                'severity': 0.6,
            })

        for res in decision_context.available_resources:
            constraints.append({
                'type': 'resource',
                'description': res,
                'severity': 0.3,
            })

        explicit = context.get('constraints', [])
        for c in explicit:
            constraints.append({
                'type': c.get('type', 'explicit'),
                'description': c.get('description', ''),
                'severity': c.get('severity', 0.5),
            })

        return tuple(constraints)

    # ------------------------------------------------------------------
    # Phase 4: OptionGeneration
    # ------------------------------------------------------------------

    def _phase_option_generation(
        self,
        question: str,
        decision_context: DecisionContext,
        goals: tuple[str, ...],
    ) -> tuple[dict[str, Any], ...]:
        """Generate decision options."""
        logger.debug('dec.decision_support.phase4_option_generation')

        options: list[dict[str, Any]] = [
            {
                'option_id': str(uuid.uuid4()),
                'name': 'Option A — Default approach',
                'description': f"Standard approach to: {question}",
                'pros': ('Well-understood', 'Low risk'),
                'cons': ('May not be optimal',),
                'resource_needs': (),
            },
            {
                'option_id': str(uuid.uuid4()),
                'name': 'Option B — Alternative approach',
                'description': f"Creative approach to: {question}",
                'pros': ('Novel perspective', 'Higher potential upside'),
                'cons': ('Higher uncertainty', 'More resources needed'),
                'resource_needs': (),
            },
            {
                'option_id': str(uuid.uuid4()),
                'name': 'Option C — Do nothing / Defer',
                'description': 'Delay the decision to gather more information',
                'pros': ('No immediate resource commitment', 'More time to evaluate'),
                'cons': ('Misses potential gains', 'May worsen over time'),
                'resource_needs': (),
            },
        ]

        return tuple(options)

    # ------------------------------------------------------------------
    # Phase 5: EvidenceEvaluation
    # ------------------------------------------------------------------

    def _phase_evidence_evaluation(
        self,
        memories: list[dict[str, Any]],
        options: tuple[dict[str, Any], ...],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Evaluate evidence for and against options."""
        logger.debug('dec.decision_support.phase5_evidence_evaluation')

        evidence = tuple(
            m.get('content', '') for m in memories
            if m.get('content') and m.get('confidence', 0.0) > 0.3
        )

        competing = ()
        if len(options) > 1:
            competing = (
                f"Alternative option exists: {options[1].get('name', '')}",
            )

        return evidence, competing

    # ------------------------------------------------------------------
    # Phase 6: ScenarioSimulation
    # ------------------------------------------------------------------

    def _phase_scenario_simulation(
        self,
        options: tuple[dict[str, Any], ...],
        goals: tuple[str, ...],
    ) -> tuple[ScenarioOutcome, ...]:
        """Simulate predicted outcomes for each option."""
        logger.debug('dec.decision_support.phase6_scenario_simulation')

        scenarios: list[ScenarioOutcome] = []
        for i, option in enumerate(options):
            scenarios.append(ScenarioOutcome(
                scenario_id=str(uuid.uuid4()),
                description=f"Outcome if {option.get('name', f'option_{i}')} is chosen",
                probability=0.5 + 0.1 * (len(options) - i),
                impact=0.5 + 0.1 * i,
                affected_goals=goals[:2] if goals else (),
            ))

        return tuple(scenarios)

    # ------------------------------------------------------------------
    # Phase 7: RiskOpportunityAnalysis
    # ------------------------------------------------------------------

    def _phase_risk_opportunity_analysis(
        self,
        options: tuple[dict[str, Any], ...],
        scenarios: tuple[ScenarioOutcome, ...],
    ) -> tuple[tuple[RiskAssessment, ...], tuple[OpportunityAssessment, ...]]:
        """Assess risks and opportunities."""
        logger.debug('dec.decision_support.phase7_risk_opportunity_analysis')

        risks: list[RiskAssessment] = []
        for option in options:
            risks.append(RiskAssessment(
                risk_id=str(uuid.uuid4()),
                description=f"Risk associated with {option.get('name', '')}",
                probability=0.3,
                severity=0.4,
                mitigations=('Gather more evidence', 'Set checkpoints'),
            ))

        opportunities: list[OpportunityAssessment] = []
        for option in options:
            opportunities.append(OpportunityAssessment(
                opportunity_id=str(uuid.uuid4()),
                description=f"Opportunity from {option.get('name', '')}",
                probability=0.4,
                potential_value=0.6,
                requirements=('Commitment of resources',),
            ))

        return tuple(risks), tuple(opportunities)

    # ------------------------------------------------------------------
    # Phase 8: DecisionSupportObject
    # ------------------------------------------------------------------

    def _phase_decision_support_object(
        self,
        question: str,
        decision_context: DecisionContext,
        options: tuple[dict[str, Any], ...],
        goals: tuple[str, ...],
        constraints: tuple[dict[str, Any], ...],
        evidence: tuple[str, ...],
        competing: tuple[str, ...],
        scenarios: tuple[ScenarioOutcome, ...],
        risks: tuple[RiskAssessment, ...],
        opportunities: tuple[OpportunityAssessment, ...],
    ) -> DecisionObject:
        """Construct the decision support object."""
        logger.debug('dec.decision_support.phase8_decision_support_object')

        risk_dicts = tuple({
            'risk_id': r.risk_id,
            'description': r.description,
            'probability': r.probability,
            'severity': r.severity,
        } for r in risks)

        opp_dicts = tuple({
            'opportunity_id': o.opportunity_id,
            'description': o.description,
            'probability': o.probability,
            'potential_value': o.potential_value,
        } for o in opportunities)

        outcome_dicts = tuple({
            'scenario_id': s.scenario_id,
            'description': s.description,
            'probability': s.probability,
            'impact': s.impact,
        } for s in scenarios)

        confidence = 0.5
        if evidence:
            confidence = min(0.5 + len(evidence) * 0.05, 0.9)
        remaining = round(1.0 - confidence, 4)

        decision = DecisionObject(
            decision_id=str(uuid.uuid4()),
            context=str(decision_context),
            question=question,
            options=options,
            goals=goals,
            constraints=constraints,
            supporting_evidence=evidence,
            competing_hypotheses=competing,
            predicted_outcomes=outcome_dicts,
            risks=risk_dicts,
            opportunities=opp_dicts,
            confidence=round(confidence, 4),
            remaining_uncertainty=remaining,
            explainability_metadata={
                'phase': 'decision_support',
                'option_count': len(options),
                'evidence_count': len(evidence),
                'scenario_count': len(scenarios),
                'risk_count': len(risks),
                'opportunity_count': len(opportunities),
            },
        )

        self._decisions[decision.decision_id] = decision
        return decision

    # ------------------------------------------------------------------
    # Phase 9: DialoguePresentation
    # ------------------------------------------------------------------

    def _phase_dialogue_presentation(
        self,
        decision: DecisionObject,
        decision_context: DecisionContext,
        scenarios: tuple[ScenarioOutcome, ...],
        risks: tuple[RiskAssessment, ...],
        opportunities: tuple[OpportunityAssessment, ...],
    ) -> DecisionResult:
        """Prepare the decision for dialogue presentation."""
        logger.debug('dec.decision_support.phase9_dialogue_presentation')

        trade_offs: list[TradeOff] = []
        if len(decision.options) >= 2:
            trade_offs.append(TradeOff(
                trade_off_id=str(uuid.uuid4()),
                option_a=decision.options[0].get('name', ''),
                option_b=decision.options[1].get('name', ''),
                dimension='risk_vs_reward',
                weight_a=0.5,
                weight_b=0.5,
            ))

        multi_scores = tuple(
            MultiCriteriaScore(
                option=opt.get('name', ''),
                goal_alignment=0.6,
                evidence_quality=0.5,
                risk=0.4,
                opportunity=0.5,
                ethical=0.7,
                sustainability=0.5,
                resource_requirement=0.4,
                reversibility=0.6,
                learning_potential=0.5,
                overall=0.5,
            )
            for opt in decision.options
        )

        dialogue_lines = [
            f"Decision: {decision.question}",
            f"Options available: {len(decision.options)}",
            f"Confidence: {decision.confidence}",
            f"Remaining uncertainty: {decision.remaining_uncertainty}",
            f"Risks identified: {len(risks)}",
            f"Opportunities identified: {len(opportunities)}",
        ]
        dialogue_prompt = '\n'.join(dialogue_lines)

        return DecisionResult(
            decision=decision,
            context=decision_context,
            trade_offs=tuple(trade_offs),
            multi_criteria_scores=multi_scores,
            scenarios=scenarios,
            risks=risks,
            opportunities=opportunities,
            dialogue_prompt=dialogue_prompt,
            overall_confidence=decision.confidence,
            processing_metadata={
                'option_count': len(decision.options),
                'scenario_count': len(scenarios),
                'risk_count': len(risks),
                'opportunity_count': len(opportunities),
                'trade_off_count': len(trade_offs),
            },
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_decision(self, decision_id: str) -> DecisionObject | None:
        """Retrieve a decision by ID."""
        return self._decisions.get(decision_id)

    def get_all_decisions(self) -> list[DecisionObject]:
        """Retrieve all stored decisions."""
        return list(self._decisions.values())
