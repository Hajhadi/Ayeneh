"""Simulation modules — COG-14 support.

Counterfactual and intervention simulation for exploring alternative
cognitive futures, plus sensitivity analysis to identify leverage points.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Counterfactual Simulator
# ---------------------------------------------------------------------------


class CounterfactualSimulator:
    """Simulates alternative outcomes by changing a single variable.

    Answers "what would happen if X were different?" by modifying one
    aspect of the current state and projecting consequences.
    """

    def simulate(
        self,
        current_state: dict[str, Any],
        change: str,
    ) -> dict[str, Any]:
        """Simulate the effect of a counterfactual change.

        Parameters
        ----------
        current_state:
            The current cognitive state dict.
        change:
            Description of the change to simulate (e.g., "belief X was not adopted").
        """
        logger.info('cog.prediction.counterfactual_simulated', change=change)

        change_lower = change.lower()

        # Extract relevant components from current state
        beliefs = current_state.get('beliefs', [])
        values = current_state.get('values', [])
        goals = current_state.get('goals', [])
        identity = current_state.get('identity', [])

        # Analyze impact areas
        impact_areas: list[str] = []
        affected_components: list[str] = []
        projected_changes: list[str] = []

        # Check belief-related changes
        if 'belief' in change_lower:
            impact_areas.append('belief_network')
            affected_components.extend(
                b.get('id', '') for b in beliefs
                if _text_match(change_lower, b.get('statement', ''))
            )
            if affected_components:
                projected_changes.append(
                    'belief network would need restructuring'
                )

        # Check value-related changes
        if 'value' in change_lower:
            impact_areas.append('value_system')
            affected_components.extend(
                v.get('id', '') for v in values
                if _text_match(change_lower, v.get('statement', ''))
            )
            if affected_components:
                projected_changes.append(
                    'value hierarchy would shift'
                )

        # Check goal-related changes
        if 'goal' in change_lower:
            impact_areas.append('goal_structure')
            affected_components.extend(
                g.get('id', '') for g in goals
                if _text_match(change_lower, g.get('description', ''))
            )
            if affected_components:
                projected_changes.append(
                    'goal priorities would need realignment'
                )

        # Check identity-related changes
        if 'identity' in change_lower or 'who i am' in change_lower:
            impact_areas.append('identity_structure')
            affected_components.extend(
                i.get('id', '') for i in identity
                if _text_match(change_lower, i.get('statement', ''))
            )
            if affected_components:
                projected_changes.append(
                    'self-concept would require revision'
                )

        # Default impact if no specific match
        if not impact_areas:
            impact_areas = ['general']
            projected_changes = [
                'effects would propagate through connected cognitive structures'
            ]

        # Estimate cascade magnitude
        cascade_magnitude = min(1.0, len(affected_components) * 0.2 + 0.1)

        return {
            'change': change,
            'impact_areas': impact_areas,
            'affected_components': affected_components,
            'projected_changes': projected_changes,
            'cascade_magnitude': cascade_magnitude,
            'confidence': max(0.2, 1.0 - cascade_magnitude * 0.5),
        }


# ---------------------------------------------------------------------------
# Intervention Simulator
# ---------------------------------------------------------------------------


class InterventionSimulator:
    """Simulates the effect of deliberate cognitive interventions.

    Answers "what would happen if the user actively worked on X?" by
    modeling the expected trajectory under intentional effort.
    """

    def simulate(
        self,
        current_state: dict[str, Any],
        intervention: str,
    ) -> dict[str, Any]:
        """Simulate the effect of a cognitive intervention.

        Parameters
        ----------
        current_state:
            The current cognitive state dict.
        intervention:
            Description of the intervention (e.g., "challenge belief X daily").
        """
        logger.info('cog.prediction.intervention_simulated', intervention=intervention)

        intervention_lower = intervention.lower()

        # Determine intervention target
        target_area = 'general'
        if 'belief' in intervention_lower:
            target_area = 'belief_network'
        elif 'value' in intervention_lower:
            target_area = 'value_system'
        elif 'goal' in intervention_lower:
            target_area = 'goal_structure'
        elif 'identity' in intervention_lower:
            target_area = 'identity_structure'
        elif 'narrative' in intervention_lower:
            target_area = 'narrative_framework'
        elif 'pattern' in intervention_lower:
            target_area = 'behavioral_patterns'

        # Estimate intervention effectiveness based on keywords
        effectiveness = _estimate_intervention_effectiveness(intervention_lower)

        # Project timeline
        if effectiveness >= 0.7:
            timeline = 'weeks'
        elif effectiveness >= 0.4:
            timeline = 'months'
        else:
            timeline = 'months_to_years'

        # Identify required conditions
        conditions = _infer_conditions(intervention_lower)

        # Identify risks
        risks = _infer_risks(intervention_lower, target_area)

        return {
            'intervention': intervention,
            'target_area': target_area,
            'effectiveness_estimate': effectiveness,
            'projected_timeline': timeline,
            'required_conditions': conditions,
            'risks': risks,
            'confidence': effectiveness * 0.8,
        }


# ---------------------------------------------------------------------------
# Sensitivity Analyzer
# ---------------------------------------------------------------------------


class SensitivityAnalyzer:
    """Identifies leverage points — cognitive structures where small changes
    produce large effects across the system.
    """

    def analyze(
        self,
        cognitive_objects: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Analyze sensitivity to identify leverage points.

        Parameters
        ----------
        cognitive_objects:
            List of cognitive object dicts with ``'id'``, ``'type'``,
            ``'connections'``, and ``'stability'`` keys.
        """
        logger.info('cog.prediction.sensitivity_analysis_started')

        leverage_points: list[dict[str, Any]] = []

        for obj in cognitive_objects:
            obj_id = obj.get('id', '')
            obj_type = obj.get('type', '')
            connections = obj.get('connections', [])
            stability = obj.get('stability', 0.5)

            # Leverage = many connections + low stability
            connection_count = len(connections) if isinstance(connections, list) else 0
            leverage = connection_count * 0.2 * (1.0 - stability)

            if leverage > 0.3:
                leverage_points.append({
                    'object_id': obj_id,
                    'object_type': obj_type,
                    'leverage_score': min(1.0, leverage),
                    'connection_count': connection_count,
                    'stability': stability,
                    'recommendation': _leverage_recommendation(obj_type, stability),
                })

        # Sort by leverage score descending
        leverage_points.sort(key=lambda x: x['leverage_score'], reverse=True)

        logger.info(
            'cog.prediction.sensitivity_analysis_completed',
            leverage_points_found=len(leverage_points),
        )
        return leverage_points


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _text_match(query: str, text: str) -> bool:
    """Check if query words appear in text."""
    query_words = set(query.split())
    text_words = set(text.lower().split())
    stop_words = {
        'i', 'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be',
        'have', 'has', 'had', 'do', 'does', 'did', 'to', 'of', 'in',
        'for', 'on', 'with', 'at', 'by', 'it', 'this', 'that', 'and',
        'or', 'but', 'not', 'my', 'me',
    }
    meaningful_q = query_words - stop_words
    meaningful_t = text_words - stop_words
    if not meaningful_q or not meaningful_t:
        return False
    return len(meaningful_q & meaningful_t) >= 1


def _estimate_intervention_effectiveness(intervention: str) -> float:
    """Estimate effectiveness of an intervention based on its description."""
    score = 0.3  # baseline

    # Active engagement keywords increase effectiveness
    if any(kw in intervention for kw in ('daily', 'regularly', 'consistently')):
        score += 0.3
    if any(kw in intervention for kw in ('challenge', 'question', 'examine')):
        score += 0.2
    if any(kw in intervention for kw in ('track', 'monitor', 'measure')):
        score += 0.1
    if any(kw in intervention for kw in ('therapy', 'counseling', 'professional')):
        score += 0.2

    return min(1.0, score)


def _infer_conditions(intervention: str) -> tuple[str, ...]:
    """Infer required conditions for intervention success."""
    conditions: list[str] = ['consistent effort']

    if 'daily' in intervention or 'regularly' in intervention:
        conditions.append('regular schedule')
    if 'therapy' in intervention or 'counsel' in intervention:
        conditions.append('professional support')
    if 'challenge' in intervention or 'question' in intervention:
        conditions.append('willingness to confront discomfort')
    if 'track' in intervention or 'journal' in intervention:
        conditions.append('systematic documentation')

    return tuple(conditions)


def _infer_risks(intervention: str, target_area: str) -> tuple[str, ...]:
    """Infer potential risks of an intervention."""
    risks: list[str] = []

    if target_area == 'identity_structure':
        risks.append('temporary identity confusion')
    if target_area == 'belief_network':
        risks.append('belief instability during transition')
    if target_area == 'value_system':
        risks.append('value conflict with existing commitments')
    if 'rapid' in intervention or 'intensive' in intervention:
        risks.append('overwhelm from rapid change')

    if not risks:
        risks.append('minimal risk expected')

    return tuple(risks)


def _leverage_recommendation(obj_type: str, stability: float) -> str:
    """Generate recommendation for a leverage point."""
    if stability < 0.3:
        return f"High-leverage {obj_type}: small changes here propagate widely"
    elif stability < 0.6:
        return f"Moderate-leverage {obj_type}: changes require sustained effort"
    else:
        return f"Stable {obj_type}: changes slow but durable"
