"""API key generation and verification using bcrypt."""

import secrets

import bcrypt

from audithive.core.config import settings

API_KEY_RANDOM_LENGTH = 48


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns:
        Tuple of (full_key, key_hash, key_prefix).
        full_key: shown to customer once at creation.
        key_hash: bcrypt hash stored in the database.
        key_prefix: first 8 chars after prefix, for display.
    """
    random_part = secrets.token_urlsafe(API_KEY_RANDOM_LENGTH)[:API_KEY_RANDOM_LENGTH]
    full_key = f"{settings.API_KEY_PREFIX}{random_part}"
    key_hash = hash_api_key(full_key)
    key_prefix = random_part[:8]
    return full_key, key_hash, key_prefix


def hash_api_key(plain_key: str) -> str:
    """Hash an API key with bcrypt."""
    return bcrypt.hashpw(plain_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify a plaintext API key against its bcrypt hash."""
    return bcrypt.checkpw(plain_key.encode("utf-8"), hashed_key.encode("utf-8"))
