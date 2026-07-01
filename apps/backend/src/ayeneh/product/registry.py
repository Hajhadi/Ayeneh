"""Product Registry — manages product profiles with dynamic loading."""

from __future__ import annotations

import structlog
from typing import Any

from ayeneh.product.types import ProductProfile

logger = structlog.get_logger(__name__)


class ProductRegistry:
    """Singleton registry for product profiles."""

    _instance: ProductRegistry | None = None

    def __init__(self) -> None:
        self._profiles: dict[str, ProductProfile] = {}
        self._default_id: str = ""

    @classmethod
    def get_instance(cls) -> ProductRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def register(self, profile: ProductProfile) -> None:
        self._profiles[profile.id] = profile
        logger.info("product_registered", product_id=profile.id, name=profile.name)

    def unregister(self, product_id: str) -> bool:
        if product_id in self._profiles:
            del self._profiles[product_id]
            return True
        return False

    def get(self, product_id: str) -> ProductProfile | None:
        return self._profiles.get(product_id)

    def get_or_default(self, product_id: str | None = None) -> ProductProfile:
        pid = product_id or self._default_id
        if pid and pid in self._profiles:
            return self._profiles[pid]
        if self._default_id and self._default_id in self._profiles:
            return self._profiles[self._default_id]
        if self._profiles:
            return next(iter(self._profiles.values()))
        raise RuntimeError("No product profiles registered")

    def set_default(self, product_id: str) -> None:
        self._default_id = product_id

    def list_profiles(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._profiles.values()]

    def list_ids(self) -> list[str]:
        return list(self._profiles.keys())

    def __len__(self) -> int:
        return len(self._profiles)


def load_default_profiles() -> ProductRegistry:
    """Load all built-in product profiles."""
    from ayeneh.product.profiles import AYENEH_PROFILE, CAREER_PROFILE, BUSINESS_PROFILE
    registry = ProductRegistry.get_instance()
    registry.register(AYENEH_PROFILE)
    registry.register(CAREER_PROFILE)
    registry.register(BUSINESS_PROFILE)
    registry.set_default("ayeneh")
    return registry
