from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderHealth:
    is_healthy: bool = True
    success_rate: float = 1.0


class ProviderRegistry:
    def __init__(self):
        self._providers = {}
        self._health = {}
        self._fallback_chain = []

    def register(self, name, provider):
        self._providers[name] = provider
        self._health.setdefault(name, ProviderHealth())

    def get(self, name):
        return self._providers.get(name)

    def get_healthy(self):
        return {n: p for n, p in self._providers.items() if self._health[n].is_healthy}

    def get_health(self, name):
        return self._health.get(name, ProviderHealth(False, 0.0))

    async def check_health(self, name):
        ok = bool(await self._providers[name].health_check())
        self._health[name].is_healthy = ok
        return ok

    def set_fallback_chain(self, names):
        self._fallback_chain = list(names)

    def get_by_capability(self, cap):
        return {n: p for n, p in self._providers.items() if p.get_capabilities().supports(cap)}

    def get_supporting_all(self, caps):
        return {n: p for n, p in self._providers.items() if p.get_capabilities().supports_all(caps)}

    def list_capabilities(self):
        return {
            n: [c.value for c in p.get_capabilities().capabilities]
            for n, p in self._providers.items()
        }

    def list_providers(self):
        return {
            n: {
                "provider_type": p.provider_type.value,
                "capabilities": self.list_capabilities()[n],
                "healthy": self._health[n].is_healthy,
            }
            for n, p in self._providers.items()
        }
