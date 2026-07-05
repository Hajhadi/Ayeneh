"""Cognitive pipeline orchestrator for the Ayeneh COG architecture.

Chains all COG modules in their dependency order, passing typed data between
pipeline stages.  Individual modules are registered by name; the orchestrator
calls each module's ``process`` method sequentially, threading the accumulator
dict through every stage.
"""

from __future__ import annotations

import structlog
from typing import Any

logger = structlog.get_logger(__name__)

# Ordered pipeline phases — COG-01 through COG-16 dependency order
PIPELINE_PHASES: list[str] = [
    'conversation_understanding',   # COG-01
    'evidence_extraction',          # COG-02
    'personal_knowledge',           # COG-04
    'narrative_extraction',         # COG-05
    'belief_modeling',              # COG-06
    'value_modeling',               # COG-07
    'goal_modeling',                # COG-08
    'identity_graph',               # COG-09
    'decision_architecture',        # COG-10
    'behavioral_pattern',           # COG-11
    'reflection',                   # COG-12
    'cognitive_trajectory',         # COG-13
    'prediction',                   # COG-14
    'reality_calibration',          # COG-15
    'meta_cognition',               # COG-16
]


class CognitivePipelineOrchestrator:
    """Chains COG modules in dependency order.

    Usage::

        orch = CognitivePipelineOrchestrator()
        orch.register('conversation_understanding', cog_module)
        result = await orch.process({'segments': [...]})
    """

    def __init__(self) -> None:
        self._modules: dict[str, Any] = {}

    # -- registration --------------------------------------------------------

    def register(self, name: str, module: Any) -> None:
        """Register a module under *name* (must appear in PIPELINE_PHASES)."""
        self._modules[name] = module
        logger.info('cog.module_registered', module_name=name)

    def has_module(self, name: str) -> bool:
        """Return True if a module is registered for *name*."""
        return name in self._modules

    # -- execution -----------------------------------------------------------

    async def process(self, conversation_data: dict[str, Any]) -> dict[str, Any]:
        """Run the full cognitive pipeline.

        *conversation_data* is seeded into the accumulator; each module
        receives and may mutate it.  Unregistered phases are skipped with
        a warning so that partial pipelines can still execute during
        development.
        """
        accumulator: dict[str, Any] = dict(conversation_data)
        logger.info('cog.pipeline_started')

        for phase_name in PIPELINE_PHASES:
            module = self._modules.get(phase_name)
            if module is None:
                logger.warning('cog.phase_skipped', phase=phase_name)
                continue

            logger.info('cog.phase_started', phase=phase_name)
            try:
                accumulator = await module.process(accumulator)  # type: ignore[union-attr]
            except Exception as exc:
                logger.error(
                    'cog.phase_failed',
                    phase=phase_name,
                    error=str(exc),
                )
                raise

            logger.info('cog.phase_completed', phase=phase_name)

        logger.info('cog.pipeline_completed')
        return accumulator
