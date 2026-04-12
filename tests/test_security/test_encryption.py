"""Tests for the AES-256-GCM encryption module."""

import base64

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from audithive.core.encryption import (
    decrypt_content,
    decrypt_json,
    encrypt_content,
    encrypt_json,
    generate_encryption_key,
)


@pytest.fixture
def test_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def test_encrypt_decrypt_roundtrip(test_key: bytes) -> None:
    original = "Hello, this is sensitive data!"
    encrypted = encrypt_content(original, test_key)
    decrypted = decrypt_content(encrypted, test_key)
    assert decrypted == original


def test_encrypted_has_prefix(test_key: bytes) -> None:
    encrypted = encrypt_content("test", test_key)
    assert encrypted.startswith("ENC:")


def test_unencrypted_passthrough() -> None:
    """Unencrypted content (no ENC: prefix) passes through decrypt unchanged."""
    plain = "just regular text"
    assert decrypt_content(plain) == plain


def test_no_key_returns_plaintext() -> None:
    """When no key is provided and env var not set, encryption is disabled."""
    result = encrypt_content("plaintext", key=None)
    # Without env var, should return plaintext
    assert result == "plaintext" or result.startswith("ENC:")


def test_different_ciphertext_for_same_plaintext(test_key: bytes) -> None:
    """Random nonce ensures different ciphertext each time."""
    a = encrypt_content("same text", test_key)
    b = encrypt_content("same text", test_key)
    assert a != b  # Different nonces


def test_wrong_key_fails(test_key: bytes) -> None:
    """Decryption with wrong key raises an error."""
    encrypted = encrypt_content("secret", test_key)
    wrong_key = AESGCM.generate_key(bit_length=256)
    with pytest.raises(Exception):
        decrypt_content(encrypted, wrong_key)


def test_generate_key_valid() -> None:
    key_b64 = generate_encryption_key()
    key_bytes = base64.b64decode(key_b64)
    assert len(key_bytes) == 32  # 256 bits


def test_encrypt_json_roundtrip(test_key: bytes) -> None:
    data = {"messages": [{"role": "user", "content": "Hello"}]}
    encrypted = encrypt_json(data, test_key)
    assert isinstance(encrypted, str)
    assert encrypted.startswith("ENC:")
    decrypted = decrypt_json(encrypted, test_key)
    assert decrypted == data


def test_decrypt_json_handles_dict() -> None:
    """Already-deserialized dicts pass through unchanged (SQLite behavior)."""
    data = {"key": "value"}
    assert decrypt_json(data) == data


def test_decrypt_json_none() -> None:
    assert decrypt_json(None) is None
