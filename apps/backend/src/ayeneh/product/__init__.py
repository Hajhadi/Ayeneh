"""Product Profile Layer — separates reusable cognitive platform from product-specific behavior."""

from ayeneh.product.types import ProductProfile, BehaviorPolicy, ResourcePolicy, KnowledgePolicy
from ayeneh.product.registry import ProductRegistry, load_default_profiles

__all__ = [
    "ProductProfile", "BehaviorPolicy", "ResourcePolicy", "KnowledgePolicy",
    "ProductRegistry", "load_default_profiles",
]
