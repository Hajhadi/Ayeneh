"""Goal system observability — metrics, events, and tracking for goal integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ayeneh.observability.base import MetricsPublisher


@dataclass
class GoalMetrics(MetricsPublisher):
    """Tracks goal-related metrics for observability and Prometheus export."""

    def __post_init__(self) -> None:
        MetricsPublisher.__init__(self, "goal")

    goal_retrieval_total: int = 0
    goal_prompt_tokens: int = 0
    goal_context_size: int = 0
    goal_scheduler_runs: int = 0
    goal_overdue_total: int = 0
    goal_completion_rate: float = 0.0
    goal_abandonment_rate: float = 0.0
    goal_blocked_total: int = 0
    goal_conflicts_total: int = 0
    goal_evolution_total: int = 0

    retrieval_latencies_ms: list[float] = field(default_factory=list)
    scheduler_latencies_ms: list[float] = field(default_factory=list)
    failures: int = 0

    def record_retrieval(self, count: int, latency_ms: float) -> None:
        self.goal_retrieval_total += count
        self.retrieval_latencies_ms.append(latency_ms)
        if len(self.retrieval_latencies_ms) > 1000:
            self.retrieval_latencies_ms = self.retrieval_latencies_ms[-500:]

    def record_prompt_injection(self, tokens: int, context_size: int) -> None:
        self.goal_prompt_tokens += tokens
        self.goal_context_size = context_size

    def record_scheduler_run(self, latency_ms: float) -> None:
        self.goal_scheduler_runs += 1
        self.scheduler_latencies_ms.append(latency_ms)

    def record_completion_rate(self, rate: float) -> None:
        self.goal_completion_rate = rate

    def record_abandonment_rate(self, rate: float) -> None:
        self.goal_abandonment_rate = rate

    def record_overdue(self, count: int) -> None:
        self.goal_overdue_total += count

    def record_blocked(self, count: int) -> None:
        self.goal_blocked_total = count

    def record_conflict(self) -> None:
        self.goal_conflicts_total += 1

    def record_evolution(self) -> None:
        self.goal_evolution_total += 1

    def record_failure(self) -> None:
        self.failures += 1

    def export_prometheus_text(self) -> str:
        lines = [
            f"ayeneh_goal_retrieval_total {self.goal_retrieval_total}",
            f"ayeneh_goal_prompt_tokens_total {self.goal_prompt_tokens}",
            f"ayeneh_goal_context_size {self.goal_context_size}",
            f"ayeneh_goal_scheduler_runs_total {self.goal_scheduler_runs}",
            f"ayeneh_goal_overdue_total {self.goal_overdue_total}",
            f"ayeneh_goal_completion_rate {self.goal_completion_rate:.4f}",
            f"ayeneh_goal_abandonment_rate {self.goal_abandonment_rate:.4f}",
            f"ayeneh_goal_blocked_total {self.goal_blocked_total}",
            f"ayeneh_goal_conflicts_total {self.goal_conflicts_total}",
            f"ayeneh_goal_evolution_total {self.goal_evolution_total}",
            f"ayeneh_goal_failures_total {self.failures}",
        ]
        if self.retrieval_latencies_ms:
            avg = sum(self.retrieval_latencies_ms[-100:]) / len(self.retrieval_latencies_ms[-100:])
            lines.append(f"ayeneh_goal_retrieval_latency_ms_avg {avg:.2f}")
        return "\n".join(lines) + "\n"


class GoalEventPublisher:
    """Publishes goal-specific events through the EventBus."""

    EVENT_TYPES = {
        "GoalRetrieved": "goal_retrieval",
        "GoalInjectedIntoPrompt": "goal_injection",
        "GoalReviewStarted": "goal_review",
        "GoalReviewCompleted": "goal_review",
        "GoalEvolutionCompleted": "goal_evolution",
        "GoalConflictDetected": "goal_conflict",
        "GoalOverdueDetected": "goal_overdue",
        "GoalSchedulerStarted": "goal_scheduler",
        "GoalSchedulerCompleted": "goal_scheduler",
        "GoalSchedulerFailed": "goal_scheduler",
    }

    def __init__(self, event_bus: Any | None = None) -> None:
        self._event_bus = event_bus

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._event_bus:
            try:
                await self._event_bus.publish(event_type, payload)
            except Exception:
                pass

    async def goal_retrieved(self, user_id: str, goal_count: int) -> None:
        await self.publish("GoalRetrieved", {"user_id": user_id, "goal_count": goal_count})

    async def goal_injected(self, user_id: str, tokens: int) -> None:
        await self.publish("GoalInjectedIntoPrompt", {"user_id": user_id, "tokens": tokens})

    async def goal_review(self, user_id: str, goal_id: str) -> None:
        await self.publish("GoalReviewStarted", {"user_id": user_id, "goal_id": goal_id})

    async def goal_evolution(self, user_id: str, results: dict[str, Any]) -> None:
        await self.publish("GoalEvolutionCompleted", {"user_id": user_id, **results})

    async def goal_conflict(self, user_id: str, goal_ids: list[str]) -> None:
        await self.publish("GoalConflictDetected", {"user_id": user_id, "goal_ids": goal_ids})

    async def goal_overdue(self, user_id: str, count: int) -> None:
        await self.publish("GoalOverdueDetected", {"user_id": user_id, "count": count})

    async def scheduler_started(self, job_type: str) -> None:
        await self.publish("GoalSchedulerStarted", {"job_type": job_type})

    async def scheduler_completed(self, job_type: str, duration_ms: float) -> None:
        await self.publish("GoalSchedulerCompleted", {"job_type": job_type, "duration_ms": duration_ms})

    async def scheduler_failed(self, job_type: str, error: str) -> None:
        await self.publish("GoalSchedulerFailed", {"job_type": job_type, "error": error})
