"""Application-level AES-256-GCM encryption for sensitive audit log content.

The encryption key is derived from AUDITHIVE_ENCRYPTION_KEY in the environment.
In self-hosted deployments, the customer controls their own key.
"""

from __future__ import annotations

import base64
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENC_PREFIX = "ENC:"


def get_encryption_key() -> bytes | None:
    """Get the 256-bit encryption key from the environment. Returns None if not set."""
    key_b64 = os.environ.get("AUDITHIVE_ENCRYPTION_KEY")
    if not key_b64:
        return None
    return base64.b64decode(key_b64)


def generate_encryption_key() -> str:
    """Generate a new 256-bit AES key. Returns base64-encoded string for .env."""
    key = AESGCM.generate_key(bit_length=256)
    return base64.b64encode(key).decode()


def encrypt_content(plaintext: str, key: bytes | None = None) -> str:
    """Encrypt a string with AES-256-GCM. Returns ENC:-prefixed base64 ciphertext.

    If no key is available, returns plaintext unchanged (encryption disabled).
    """
    if key is None:
        key = get_encryption_key()
    if key is None:
        return plaintext

    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return ENC_PREFIX + base64.b64encode(nonce + ciphertext).decode()


def decrypt_content(stored: str, key: bytes | None = None) -> str:
    """Decrypt an ENC:-prefixed string. Unencrypted strings pass through unchanged."""
    if not stored.startswith(ENC_PREFIX):
        return stored

    if key is None:
        key = get_encryption_key()
    if key is None:
        raise ValueError("Encrypted content found but AUDITHIVE_ENCRYPTION_KEY not set")

    raw = base64.b64decode(stored[len(ENC_PREFIX):])
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


def encrypt_json(data: dict | list | None, key: bytes | None = None) -> dict | list | str | None:
    """Encrypt a JSON-serializable value. Returns encrypted string or original data if no key."""
    if data is None:
        return None
    if key is None:
        key = get_encryption_key()
    if key is None:
        return data  # No encryption configured, return original object
    return encrypt_content(json.dumps(data), key)


def decrypt_json(stored, key: bytes | None = None):
    """Decrypt a value back to a Python object. Handles both encrypted and plain JSON."""
    if stored is None:
        return None
    if isinstance(stored, (dict, list)):
        return stored  # Already a Python object (unencrypted or SQLite)
    if isinstance(stored, str):
        decrypted = decrypt_content(stored, key)
        return json.loads(decrypted)
    return stored
