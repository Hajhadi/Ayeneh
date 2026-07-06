"""Predictive Cognitive Engine — COG-14.

Probabilistic simulation of future cognitive states.
Pipeline: History → Patterns → Trajectory Analysis → Current State →
Simulation → Predictions.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.cog.prediction.simulation import (
    CounterfactualSimulator,
    InterventionSimulator,
    SensitivityAnalyzer,
)
from ayeneh.cog.prediction.types import (
    PREDICTION_HORIZONS,
    PredictionDomain,
    PredictionHorizon,
    EarlyWarning,
    PredictionObject,
    PredictionResult,
    ScenarioObject,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Predictive Cognitive Engine
# ---------------------------------------------------------------------------


class PredictiveCognitiveEngine:
    """Probabilistic simulation of future cognitive states (COG-14).

    Pipeline:
        1. Trajectory Analysis — summarize trajectory trends
        2. Scenario Generation — generate plausible future scenarios
        3. Simulation — run probabilistic simulation
        4. Validation — filter and validate predictions
        5. Early Warning Detection — identify impending changes
    """

    def __init__(self) -> None:
        self._predictions: dict[str, PredictionObject] = {}
        self._counterfactual_simulator = CounterfactualSimulator()
        self._intervention_simulator = InterventionSimulator()
        self._sensitivity_analyzer = SensitivityAnalyzer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        trajectories: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        current_state: dict[str, Any],
    ) -> PredictionResult:
        """Run the full COG-14 pipeline.

        Parameters
        ----------
        trajectories:
            List of trajectory dicts with ``'id'``, ``'target_type'``,
            ``'direction'``, and ``'rate_of_change'`` keys.
        patterns:
            List of pattern dicts with ``'id'``, ``'description'``, and
            ``'confidence'`` keys.
        current_state:
            Dict representing the current cognitive state with optional
            ``'beliefs'``, ``'values'``, ``'goals'``, ``'identity'`` keys.
        """
        logger.info(
            'cog.prediction.pipeline_started',
            trajectory_count=len(trajectories),
            pattern_count=len(patterns),
        )

        # Phase 1 — Trajectory Analysis
        trajectories_analysis = self._analyze_trajectories(trajectories)

        # Phase 2 — Scenario Generation
        scenarios = self._generate_scenarios(trajectories_analysis, patterns, current_state)

        # Phase 3 — Simulation
        predictions = self._simulate(scenarios, trajectories_analysis)

        # Phase 4 — Validation
        validated = self._validate(predictions)

        # Phase 5 — Early Warning Detection
        warnings = self._detect_early_warnings(patterns, trajectories)

        # Store predictions
        for pred in validated.values():
            self._predictions[pred.identifier] = pred

        result = PredictionResult(
            predictions=validated,
            scenarios=scenarios,
            early_warnings=warnings,
            total_extracted=len(validated),
        )

        logger.info(
            'cog.prediction.pipeline_completed',
            total_extracted=result.total_extracted,
            scenarios_generated=len(scenarios),
            warnings_detected=len(warnings),
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Trajectory Analysis
    # ------------------------------------------------------------------

    @staticmethod
    def _analyze_trajectories(
        trajectories: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Summarize trajectory trends for prediction."""
        if not trajectories:
            return {
                'dominant_direction': 'stabilizing',
                'avg_rate': 0.0,
                'type_directions': {},
                'total': 0,
            }

        # Compute direction distribution
        direction_counts: dict[str, int] = {}
        type_directions: dict[str, dict[str, int]] = {}
        rates: list[float] = []

        for traj in trajectories:
            direction = traj.get('direction', 'stabilizing')
            target_type = traj.get('target_type', 'belief')
            rate = traj.get('rate_of_change', 0.0)

            direction_counts[direction] = direction_counts.get(direction, 0) + 1
            rates.append(rate)

            if target_type not in type_directions:
                type_directions[target_type] = {}
            type_directions[target_type][direction] = (
                type_directions[target_type].get(direction, 0) + 1
            )

        # Dominant direction
        dominant = max(direction_counts, key=direction_counts.get)  # type: ignore[arg-type]
        avg_rate = sum(rates) / len(rates) if rates else 0.0

        return {
            'dominant_direction': dominant,
            'avg_rate': avg_rate,
            'type_directions': type_directions,
            'total': len(trajectories),
            'direction_counts': direction_counts,
        }

    # ------------------------------------------------------------------
    # Phase 2: Scenario Generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_scenarios(
        trajectories_analysis: dict[str, Any],
        patterns: list[dict[str, Any]],
        current_state: dict[str, Any],
    ) -> list[ScenarioObject]:
        """Generate plausible future scenarios."""
        scenarios: list[ScenarioObject] = []
        dominant = trajectories_analysis.get('dominant_direction', 'stabilizing')
        avg_rate = trajectories_analysis.get('avg_rate', 0.0)

        # Scenario 1: Continuation — current trends continue
        continuation_prob = max(0.3, 1.0 - avg_rate * 0.5)
        scenarios.append(ScenarioObject(
            scenario_id=str(uuid.uuid4()),
            description=(
                f"Continuation: current {dominant} trend persists "
                f"at similar rate ({avg_rate:.2f})"
            ),
            probability=continuation_prob,
            supporting_evidence=tuple(
                t.get('id', '') for t in patterns[:3]
            ),
            assumptions=('current conditions persist', 'no major disruptions'),
        ))

        # Scenario 2: Acceleration — trends intensify
        if avg_rate > 0.3:
            scenarios.append(ScenarioObject(
                scenario_id=str(uuid.uuid4()),
                description=(
                    f"Acceleration: {dominant} trend intensifies, "
                    f"rate increases to {min(1.0, avg_rate * 1.5):.2f}"
                ),
                probability=min(0.4, avg_rate * 0.6),
                assumptions=('reinforcing feedback loops activate',),
                uncertainties=('may be destabilizing',),
            ))

        # Scenario 3: Reversal — trends reverse
        reversal_prob = max(0.1, 0.5 - avg_rate * 0.3)
        scenarios.append(ScenarioObject(
            scenario_id=str(uuid.uuid4()),
            description=(
                f"Reversal: {dominant} trend reverses direction"
            ),
            probability=reversal_prob,
            assumptions=('contradictory evidence accumulates',),
            uncertainties=('uncertain trigger', 'may cause instability'),
        ))

        # Scenario 4: Stabilization — change slows
        if avg_rate > 0.2:
            scenarios.append(ScenarioObject(
                scenario_id=str(uuid.uuid4()),
                description=(
                    f"Stabilization: change rate decreases, "
                    f"structures consolidate"
                ),
                probability=min(0.5, 0.3 + avg_rate * 0.2),
                assumptions=('sufficient integration occurs',),
            ))

        # Scenario 5: Transformation — qualitative shift
        if dominant in ('transforming', 'fragmenting', 'integrating'):
            scenarios.append(ScenarioObject(
                scenario_id=str(uuid.uuid4()),
                description=(
                    f"Transformation: qualitative reorganization of "
                    f"cognitive structures"
                ),
                probability=min(0.3, avg_rate * 0.4),
                assumptions=('critical mass of change reached',),
                uncertainties=('outcome uncertain', 'may involve temporary destabilization'),
            ))

        logger.info('cog.prediction.scenarios_generated', count=len(scenarios))
        return scenarios

    # ------------------------------------------------------------------
    # Phase 3: Simulation
    # ------------------------------------------------------------------

    @staticmethod
    def _simulate(
        scenarios: list[ScenarioObject],
        trajectories_analysis: dict[str, Any],
    ) -> dict[str, PredictionObject]:
        """Run probabilistic simulation to generate predictions."""
        predictions: dict[str, PredictionObject] = {}

        for scenario in scenarios:
            # Generate prediction for each scenario
            pred = PredictionObject(
                identifier=str(uuid.uuid4()),
                prediction_statement=scenario.description,
                target_cognitive_object='general',
                probability=scenario.probability,
                confidence=min(1.0, scenario.probability * 0.8),
                assumptions=scenario.assumptions,
                supporting_evidence=scenario.supporting_evidence,
                contradictory_evidence=scenario.uncertainties,
                prediction_horizon=_infer_horizon(trajectories_analysis),
            )
            predictions[pred.identifier] = pred

        logger.info('cog.prediction.simulation_completed', count=len(predictions))
        return predictions

    # ------------------------------------------------------------------
    # Phase 4: Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(
        predictions: dict[str, PredictionObject],
    ) -> dict[str, PredictionObject]:
        """Validate and filter predictions."""
        validated: dict[str, PredictionObject] = {}

        for pred in predictions.values():
            # Must have non-zero probability
            if pred.probability <= 0:
                continue

            # Must have some supporting evidence or assumptions
            has_basis = (
                len(pred.supporting_evidence) > 0
                or len(pred.assumptions) > 0
            )
            if not has_basis:
                continue

            validated[pred.identifier] = pred

        logger.info('cog.prediction.validated', count=len(validated))
        return validated

    # ------------------------------------------------------------------
    # Phase 5: Early Warning Detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_early_warnings(
        patterns: list[dict[str, Any]],
        trajectories: list[dict[str, Any]],
    ) -> list[EarlyWarning]:
        """Detect early warning signals of impending change."""
        warnings: list[EarlyWarning] = []

        # Check for high-rate trajectories
        for traj in trajectories:
            rate = traj.get('rate_of_change', 0.0)
            direction = traj.get('direction', 'stabilizing')

            if rate > 0.7 and direction in ('transforming', 'fragmenting'):
                warnings.append(EarlyWarning(
                    warning_id=str(uuid.uuid4()),
                    description=(
                        f"High rate of change ({rate:.2f}) in "
                        f"{traj.get('target_type', 'unknown')} "
                        f"trajectory ({direction})"
                    ),
                    severity=min(1.0, rate),
                    evidence=(traj.get('id', ''),),
                    recommended_attention='monitor closely',
                ))

        # Check for low-confidence patterns (instability signal)
        low_conf_patterns = [
            p for p in patterns
            if p.get('confidence', 1.0) < 0.3
        ]
        if len(low_conf_patterns) >= 2:
            warnings.append(EarlyWarning(
                warning_id=str(uuid.uuid4()),
                description=(
                    f"{len(low_conf_patterns)} patterns with low confidence, "
                    f"suggesting cognitive instability"
                ),
                severity=min(1.0, len(low_conf_patterns) * 0.15),
                evidence=tuple(p.get('id', '') for p in low_conf_patterns[:5]),
                recommended_attention='review underlying evidence',
            ))

        # Check for conflicting directions
        directions = {t.get('direction', '') for t in trajectories}
        conflicting = directions & {'strengthening', 'weakening'}
        if len(conflicting) >= 2:
            warnings.append(EarlyWarning(
                warning_id=str(uuid.uuid4()),
                description="Conflicting trajectory directions detected",
                severity=0.5,
                evidence=tuple(t.get('id', '') for t in trajectories[:5]),
                recommended_attention='assess competing influences',
            ))

        logger.info('cog.prediction.warnings_detected', count=len(warnings))
        return warnings

    # ------------------------------------------------------------------
    # Phase 6: Hypothesis Generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_hypotheses(
        trajectories: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        current_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate hypotheses before scenario construction.

        Each hypothesis is a testable proposition derived from trajectory
        trends and pattern signals.
        """
        hypotheses: list[dict[str, Any]] = []

        for traj in trajectories:
            direction = traj.get('direction', 'stabilizing')
            target_type = traj.get('target_type', 'belief')
            rate = traj.get('rate_of_change', 0.0)
            hypothesis_text = (
                f"{target_type} will continue {direction} "
                f"at approximately {rate:.2f} rate"
            )
            hypotheses.append({
                'hypothesis_id': str(uuid.uuid4()),
                'statement': hypothesis_text,
                'supporting_trajectory': traj.get('id', ''),
                'strength': min(1.0, rate + 0.2),
            })

        for pat in patterns:
            conf = pat.get('confidence', 0.0)
            hypothesis_text = (
                f"Pattern '{pat.get('description', '')}' "
                f"will persist with {conf:.2f} confidence"
            )
            hypotheses.append({
                'hypothesis_id': str(uuid.uuid4()),
                'statement': hypothesis_text,
                'supporting_pattern': pat.get('id', ''),
                'strength': conf,
            })

        logger.info('cog.prediction.hypotheses_generated', count=len(hypotheses))
        return hypotheses

    # ------------------------------------------------------------------
    # Phase 7: Uncertainty Analysis
    # ------------------------------------------------------------------

    @staticmethod
    def _analyze_uncertainty(
        prediction: PredictionObject,
        trajectories: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Perform independent uncertainty estimation for a prediction.

        Returns a breakdown of epistemic, aleatory, and model-form
        uncertainty components.
        """
        epistemic_sources: list[str] = []
        aleatory_sources: list[str] = []

        if not trajectories:
            epistemic_sources.append('no trajectory data available')

        high_rate_count = sum(
            1 for t in trajectories if t.get('rate_of_change', 0.0) > 0.7
        )
        if high_rate_count > 0:
            aleatory_sources.append(
                f"{high_rate_count} trajectory(s) with high rate of change"
            )

        conflicting = set()
        for t in trajectories:
            conflicting.add(t.get('direction', ''))
        if len(conflicting) > 2:
            aleatory_sources.append('multiple conflicting trajectory directions')

        if not prediction.supporting_evidence:
            epistemic_sources.append('no supporting evidence cited')

        total_uncertainty = min(1.0, (
            len(epistemic_sources) * 0.15
            + len(aleatory_sources) * 0.2
            + (1.0 - prediction.confidence)
        ))

        return {
            'prediction_id': prediction.identifier,
            'epistemic_uncertainty': epistemic_sources,
            'aleatory_uncertainty': aleatory_sources,
            'total_uncertainty': round(total_uncertainty, 4),
        }

    # ------------------------------------------------------------------
    # Phase 8: Scenario Tree Construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_scenario_trees(
        scenarios: list[ScenarioObject],
        trajectories_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Build tree-structured scenario branching from flat scenarios.

        Returns a tree where each node is a scenario with child branches
        representing further developments.
        """
        root: dict[str, Any] = {
            'node_id': 'root',
            'description': 'Current state',
            'probability': 1.0,
            'children': [],
        }

        dominant = trajectories_analysis.get('dominant_direction', 'stabilizing')

        for scenario in scenarios:
            branch: dict[str, Any] = {
                'node_id': scenario.scenario_id,
                'description': scenario.description,
                'probability': scenario.probability,
                'assumptions': scenario.assumptions,
                'children': [],
            }

            if scenario.probability > 0.3:
                sub_branch: dict[str, Any] = {
                    'node_id': f"{scenario.scenario_id}-follow-on",
                    'description': f"Follow-on from {dominant} continuation",
                    'probability': scenario.probability * 0.5,
                    'children': [],
                }
                branch['children'].append(sub_branch)

            root['children'].append(branch)

        return {
            'tree': root,
            'total_branches': len(root['children']),
            'depth': 2,
        }

    # ------------------------------------------------------------------
    # Phase 9: Prediction Validation (feedback loop)
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_prediction(
        prediction: PredictionObject,
        observed_outcome: str = '',
    ) -> dict[str, Any]:
        """Compare predicted vs observed outcome for a prediction.

        Returns a validation record with accuracy assessment and
        corrective feedback.
        """
        is_confirmed = bool(observed_outcome)
        accuracy: float = 0.0

        if observed_outcome:
            predicted_words = set(prediction.prediction_statement.lower().split())
            observed_words = set(observed_outcome.lower().split())
            overlap = predicted_words & observed_words
            accuracy = min(1.0, len(overlap) / max(1, len(predicted_words))) if predicted_words else 0.0

        return {
            'prediction_id': prediction.identifier,
            'predicted_statement': prediction.prediction_statement,
            'observed_outcome': observed_outcome,
            'accuracy': round(accuracy, 4),
            'is_confirmed': is_confirmed,
            'assumptions_evaluated': prediction.assumptions,
        }

    # ------------------------------------------------------------------
    # Phase 10: Risk Modeling
    # ------------------------------------------------------------------

    @staticmethod
    def _model_risks(
        trajectories: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        current_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Model behavioral and cognitive risks.

        Risks include: behavioral stagnation, identity rigidity,
        narrative reinforcement, and goal abandonment.
        """
        risks: list[dict[str, Any]] = []

        stabilizing = sum(
            1 for t in trajectories
            if t.get('direction') == 'stabilizing'
        )
        if stabilizing >= 2:
            risks.append({
                'risk_id': str(uuid.uuid4()),
                'type': 'behavioral_stagnation',
                'description': (
                    f"{stabilizing} trajectories are stabilizing, "
                    f"indicating reduced cognitive flexibility"
                ),
                'severity': min(1.0, stabilizing * 0.25),
            })

        identity_trajs = [
            t for t in trajectories if t.get('target_type') == 'identity'
        ]
        rigid = [t for t in identity_trajs if t.get('direction') == 'strengthening']
        if rigid:
            risks.append({
                'risk_id': str(uuid.uuid4()),
                'type': 'identity_rigidity',
                'description': (
                    f"{len(rigid)} identity trajectory(ies) strengthening "
                    f"without corresponding change"
                ),
                'severity': min(1.0, len(rigid) * 0.3),
            })

        high_conf_patterns = [
            p for p in patterns if p.get('confidence', 0.0) > 0.8
        ]
        if len(high_conf_patterns) >= 2:
            risks.append({
                'risk_id': str(uuid.uuid4()),
                'type': 'narrative_reinforcement',
                'description': (
                    f"{len(high_conf_patterns)} high-confidence patterns "
                    f"may reinforce existing narratives"
                ),
                'severity': min(1.0, len(high_conf_patterns) * 0.2),
            })

        goals = current_state.get('goals', [])
        if goals:
            inactive = [
                g for g in goals
                if g.get('status') in ('abandoned', 'stalled', 'inactive')
            ]
            if inactive:
                risks.append({
                    'risk_id': str(uuid.uuid4()),
                    'type': 'goal_abandonment',
                    'description': (
                        f"{len(inactive)} goal(s) appear abandoned or stalled"
                    ),
                    'severity': min(1.0, len(inactive) * 0.3),
                })

        logger.info('cog.prediction.risks_modeled', count=len(risks))
        return risks

    # ------------------------------------------------------------------
    # Phase 11: Opportunity Modeling
    # ------------------------------------------------------------------

    @staticmethod
    def _model_opportunities(
        trajectories: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        current_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Model positive developmental opportunities.

        Opportunities include: emerging capacity, reflective ability,
        habit strengthening, and identity integration.
        """
        opportunities: list[dict[str, Any]] = []

        growing = [
            t for t in trajectories
            if t.get('direction') in ('strengthening', 'transforming')
            and t.get('rate_of_change', 0.0) > 0.3
        ]
        if growing:
            opportunities.append({
                'opportunity_id': str(uuid.uuid4()),
                'type': 'emerging_capacity',
                'description': (
                    f"{len(growing)} trajectory(ies) showing accelerating growth"
                ),
                'potential': min(1.0, sum(
                    t.get('rate_of_change', 0.0) for t in growing
                ) / len(growing)),
            })

        meta_patterns = [
            p for p in patterns
            if any(kw in p.get('description', '').lower()
                   for kw in ('reflect', 'meta', 'awareness', 'insight'))
        ]
        if meta_patterns:
            opportunities.append({
                'opportunity_id': str(uuid.uuid4()),
                'type': 'reflective_ability',
                'description': (
                    f"{len(meta_patterns)} meta-cognitive pattern(s) detected"
                ),
                'potential': min(1.0, sum(
                    p.get('confidence', 0.0) for p in meta_patterns
                ) / len(meta_patterns)),
            })

        habit_trajs = [
            t for t in trajectories
            if t.get('target_type') == 'habit'
            and t.get('direction') == 'strengthening'
        ]
        if habit_trajs:
            opportunities.append({
                'opportunity_id': str(uuid.uuid4()),
                'type': 'habit_strengthening',
                'description': (
                    f"{len(habit_trajs)} habit trajectory(ies) strengthening"
                ),
                'potential': min(1.0, sum(
                    t.get('rate_of_change', 0.0) for t in habit_trajs
                ) / len(habit_trajs)),
            })

        identity_trajs = [
            t for t in trajectories
            if t.get('target_type') == 'identity'
            and t.get('direction') == 'integrating'
        ]
        if identity_trajs:
            opportunities.append({
                'opportunity_id': str(uuid.uuid4()),
                'type': 'identity_integration',
                'description': (
                    f"{len(identity_trajs)} identity trajectory(ies) integrating"
                ),
                'potential': min(1.0, sum(
                    t.get('rate_of_change', 0.0) for t in identity_trajs
                ) / len(identity_trajs)),
            })

        logger.info('cog.prediction.opportunities_modeled', count=len(opportunities))
        return opportunities

    # ------------------------------------------------------------------
    # Phase 12: Decision Support Generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_decision_support(
        predictions: dict[str, PredictionObject],
        risks: list[dict[str, Any]],
        opportunities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate decision support output from predictions, risks, and opportunities.

        Returns consequences, opportunities, risks, alternatives, and
        critical uncertainties to support informed decision making.
        """
        consequences: list[str] = []
        for pred in predictions.values():
            if pred.probability > 0.5:
                consequences.append(pred.prediction_statement)

        opp_summaries = [
            f"{o['type']}: {o['description']}" for o in opportunities
        ]

        risk_summaries = [
            f"{r['type']}: {r['description']}" for r in risks
        ]

        alternatives: list[str] = []
        for pred in predictions.values():
            if pred.probability < 0.5:
                alternatives.append(pred.prediction_statement)

        critical_uncertainties: list[str] = []
        for pred in predictions.values():
            if pred.confidence < 0.4:
                critical_uncertainties.append(
                    f"Low confidence ({pred.confidence:.2f}) "
                    f"on: {pred.prediction_statement}"
                )

        return {
            'consequences': consequences,
            'opportunities': opp_summaries,
            'risks': risk_summaries,
            'alternatives': alternatives,
            'critical_uncertainties': critical_uncertainties,
        }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _infer_horizon(trajectories_analysis: dict[str, Any]) -> str:
    """Infer prediction horizon from trajectory analysis."""
    avg_rate = trajectories_analysis.get('avg_rate', 0.0)
    total = trajectories_analysis.get('total', 0)

    if total == 0:
        return 'next_conversation'
    elif avg_rate > 0.7:
        return 'weeks'
    elif avg_rate > 0.3:
        return 'months'
    elif total >= 5:
        return 'months'
    else:
        return 'next_conversation'
