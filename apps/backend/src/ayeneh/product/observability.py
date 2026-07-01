"""Product observability — tracks per-product metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProductMetrics:
    """Tracks per-product execution metrics."""

    executions_per_product: dict[str, int] = field(default_factory=dict)
    token_usage_per_product: dict[str, int] = field(default_factory=dict)
    latency_per_product: dict[str, float] = field(default_factory=dict)
    active_users_per_product: dict[str, int] = field(default_factory=dict)
    profile_switches: int = 0
    profile_errors: int = 0

    def record_execution(self, product_id: str, tokens: int, latency_ms: float) -> None:
        self.executions_per_product[product_id] = self.executions_per_product.get(product_id, 0) + 1
        self.token_usage_per_product[product_id] = self.token_usage_per_product.get(product_id, 0) + tokens
        self.latency_per_product[product_id] = latency_ms

    def record_active_user(self, product_id: str) -> None:
        self.active_users_per_product[product_id] = self.active_users_per_product.get(product_id, 0) + 1

    def record_switch(self) -> None:
        self.profile_switches += 1

    def record_error(self) -> None:
        self.profile_errors += 1

    def get_summary(self) -> dict[str, Any]:
        return {
            "executions_per_product": dict(self.executions_per_product),
            "token_usage_per_product": dict(self.token_usage_per_product),
            "profile_switches": self.profile_switches,
            "profile_errors": self.profile_errors,
        }

    def export_prometheus_text(self) -> str:
        lines = []
        for pid, count in self.executions_per_product.items():
            lines.append(f'ayeneh_product_executions_total{{product="{pid}"}} {count}')
        for pid, tokens in self.token_usage_per_product.items():
            lines.append(f'ayeneh_product_tokens_total{{product="{pid}"}} {tokens}')
        lines.append(f"ayeneh_profile_switches_total {self.profile_switches}")
        lines.append(f"ayeneh_profile_errors_total {self.profile_errors}")
        return "\n".join(lines) + "\n"
