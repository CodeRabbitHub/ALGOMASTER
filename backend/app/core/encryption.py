"""
Symmetric encryption helpers for storing secrets (e.g. API keys) in the database.

Uses Fernet (AES-128-CBC + HMAC-SHA256), keyed from the app's SECRET_KEY via SHA-256.
The encrypted token is URL-safe base64 and safe to store as TEXT in Postgres.
"""

import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken


def _fernet(secret_key: str) -> Fernet:
    """Derive a Fernet key from the app SECRET_KEY."""
    key_bytes = hashlib.sha256(secret_key.encode()).digest()   # 32 bytes
    fernet_key = base64.urlsafe_b64encode(key_bytes)           # Fernet needs urlsafe-b64
    return Fernet(fernet_key)


def encrypt(value: str, secret_key: str) -> str:
    """Encrypt a plaintext string. Returns a URL-safe base64 token."""
    return _fernet(secret_key).encrypt(value.encode()).decode()


def decrypt(token: str, secret_key: str) -> str:
    """
    Decrypt a token produced by encrypt().
    Raises InvalidToken if the token is corrupt or was encrypted with a different key.
    """
    return _fernet(secret_key).decrypt(token.encode()).decode()
