"""Encryption utilities for sensitive data at rest.

Uses Fernet symmetric encryption with a master key derived from
environment variable API_KEY_MASTER_KEY.
"""

import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


def derive_fernet_key(master_key: str) -> bytes:
    """Derive a valid Fernet key from an arbitrary string."""
    return base64.urlsafe_b64encode(hashlib.sha256(master_key.encode()).digest())


def _get_cipher() -> Fernet:
    """Initialize Fernet cipher from API_KEY_MASTER_KEY env var."""
    key_str = os.getenv("API_KEY_MASTER_KEY")
    if not key_str:
        logger.error("API_KEY_MASTER_KEY environment variable is not set!")
        raise RuntimeError(
            "API_KEY_MASTER_KEY is required for secure operation. "
            "Set it in your .env file or environment."
        )
    try:
        key = derive_fernet_key(key_str)
        return Fernet(key)
    except Exception as exc:
        logger.error(f"Invalid API_KEY_MASTER_KEY: {exc}")
        raise RuntimeError(f"Invalid API_KEY_MASTER_KEY: {exc}") from exc


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns base64-encoded ciphertext."""
    cipher = _get_cipher()
    return cipher.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str | None) -> str | None:
    """Decrypt a ciphertext string. Returns plaintext or None on failure."""
    if not ciphertext:
        return None
    cipher = _get_cipher()
    try:
        return cipher.decrypt(ciphertext.encode()).decode()
    except Exception as exc:
        logger.error(f"Failed to decrypt value: {exc}")
        return None


def mask_api_key(api_key: str | None) -> str:
    """Return a masked representation of an API key (e.g. sk-****xxxx)."""
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "****"
    return api_key[:4] + "****" + api_key[-4:]
