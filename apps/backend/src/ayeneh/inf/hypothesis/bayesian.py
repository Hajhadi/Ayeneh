"""INF-05 Bayesian Updater.

Provides incremental Bayesian confidence updates for hypotheses as new
evidence arrives.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


class BayesianUpdater:
    """Incremental Bayesian confidence updater for hypotheses."""

    def update(
        self,
        prior: float,
        evidence_quality: float,
        likelihood_ratio: float,
    ) -> float:
        """Bayesian update of hypothesis confidence.

        P(H|E) = P(E|H) * P(H) / P(E)

        Where P(E) is marginalised out via:
            posterior = LR * prior / (LR * prior + (1 - prior))

        Args:
            prior: Current confidence in the hypothesis (0–1).
            evidence_quality: Quality of the new evidence (0–1).
            likelihood_ratio: P(E|H) / P(E|¬H), typically derived from
                evidence quality.

        Returns:
            Updated posterior probability clamped to [0, 1].
        """
        if prior <= 0 or prior >= 1:
            return prior

        effective_lr = likelihood_ratio * evidence_quality
        if effective_lr <= 0:
            return prior

        posterior = (effective_lr * prior) / (
            effective_lr * prior + (1 - prior)
        )
        result = max(0.0, min(1.0, posterior))
        logger.debug(
            'bayesian_update',
            prior=round(prior, 4),
            evidence_quality=round(evidence_quality, 4),
            likelihood_ratio=round(likelihood_ratio, 4),
            posterior=round(result, 4),
        )
        return result

    def batch_update(
        self,
        prior: float,
        evidence_items: list[tuple[float, float]],
    ) -> float:
        """Apply multiple sequential Bayesian updates.

        Args:
            prior: Starting confidence (0–1).
            evidence_items: List of (evidence_quality, likelihood_ratio) tuples.

        Returns:
            Final posterior after all updates.
        """
        current = prior
        for quality, lr in evidence_items:
            current = self.update(current, quality, lr)
        return current

    def odds_update(self, prior_odds: float, likelihood_ratio: float) -> float:
        """Update via odds form: posterior_odds = likelihood_ratio * prior_odds.

        Args:
            prior_odds: Prior odds in favour of H (can be any non-negative).
            likelihood_ratio: P(E|H) / P(E|¬H).

        Returns:
            Posterior odds.
        """
        return prior_odds * likelihood_ratio

    @staticmethod
    def probability_to_odds(probability: float) -> float:
        """Convert probability to odds. Returns inf if p == 1."""
        if probability >= 1.0:
            return float('inf')
        if probability <= 0.0:
            return 0.0
        return probability / (1.0 - probability)

    @staticmethod
    def odds_to_probability(odds: float) -> float:
        """Convert odds to probability. Returns 1.0 if odds is inf."""
        if odds <= 0.0:
            return 0.0
        if odds == float('inf'):
            return 1.0
        return odds / (1.0 + odds)
