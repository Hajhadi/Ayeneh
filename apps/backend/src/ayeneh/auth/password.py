"""Password hashing using Argon2id — OWASP recommended."""

from __future__ import annotations

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash. Returns False on mismatch."""
    try:
        hasher.verify(hashed, password)
        return True
    except VerifyMismatchError:
        return False


def needs_rehash(hashed: str) -> bool:
    """Check if a hash needs rehashing (e.g., after parameter change)."""
    return hasher.check_needs_rehash(hashed)


def generate_api_key() -> str:
    """Generate a cryptographically secure API key."""
    return secrets.token_urlsafe(32)
