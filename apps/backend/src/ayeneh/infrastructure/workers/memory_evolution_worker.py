"""Scheduled memory evolution worker — Phase 1 stub.

The worker infrastructure is in place. Algorithm scheduling will be
implemented in Phase 2. This stub provides the interface contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class EvolutionJobResult:
    job_type: str
    user_id: str
    metrics: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    error: str | None = None


class MemoryEvolutionWorker:
    """Stub worker for scheduled memory evolution jobs.

    Phase 2 will implement:
    - daily_consolidation (aging, weakening, contradiction detection)
    - weekly_strengthening (merge, supersession)
    - monthly_archival
    """

    def __init__(self, evolution_service: Any, event_publisher: Any | None = None) -> None:
        self._evolution = evolution_service
        self._events = event_publisher
        self.results: list[EvolutionJobResult] = []

    async def run_daily_for_user(self, user_id: str) -> EvolutionJobResult:
        return EvolutionJobResult(job_type="daily_consolidation", user_id=user_id)

    async def run_weekly_for_user(self, user_id: str) -> EvolutionJobResult:
        return EvolutionJobResult(job_type="weekly_strengthening", user_id=user_id)

    async def run_monthly_for_user(self, user_id: str) -> EvolutionJobResult:
        return EvolutionJobResult(job_type="monthly_archival", user_id=user_id)
