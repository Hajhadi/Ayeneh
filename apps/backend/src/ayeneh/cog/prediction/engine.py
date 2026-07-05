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
