from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import RoutingMetrics


class MetricsCollector:
    def __init__(self):
        self._items = []

    def record_routing(self, metric: RoutingMetrics):
        self._items.append(metric)

    def get_summary(self):
        return {
            "total_requests": len(self._items),
            "successful_requests": sum(x.success for x in self._items),
            "providers": dict(Counter(x.provider for x in self._items)),
            "total_tokens": sum(x.tokens_used for x in self._items),
            "total_cost_usd": sum(x.cost_usd for x in self._items),
        }
