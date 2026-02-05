"""Credential encryption helper for finance integrations.

Provides basic credential encoding/decoding for storage.
Uses base64 with environment-based secret for obfuscation.
For production, should be upgraded to use proper encryption (Fernet/AES).
"""

import base64
import json
import hashlib
import os
from typing import Optional


def _get_secret_key() -> bytes:
    """Get the secret key from environment or use default.
    
    In production, FINANCE_ENCRYPTION_KEY should be set.
    """
    key = os.environ.get("FINANCE_ENCRYPTION_KEY", "default-dev-key-change-in-prod")
    return hashlib.sha256(key.encode()).digest()


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    """XOR data with key (repeating key as needed)."""
    key_len = len(key)
    return bytes(data[i] ^ key[i % key_len] for i in range(len(data)))


def encrypt_credentials(credentials: dict) -> bytes:
    """Encrypt credentials dictionary for storage.
    
    Args:
        credentials: Dictionary of credentials to encrypt.
        
    Returns:
        Encrypted bytes for database storage.
    """
    json_str = json.dumps(credentials)
    data_bytes = json_str.encode("utf-8")
    key = _get_secret_key()
    encrypted = _xor_bytes(data_bytes, key)
    return base64.b64encode(encrypted)


def decrypt_credentials(encrypted_data: bytes) -> Optional[dict]:
    """Decrypt credentials from storage.
    
    Args:
        encrypted_data: Encrypted bytes from database.
        
    Returns:
        Decrypted credentials dictionary, or None if decryption fails.
    """
    if not encrypted_data:
        return None
        
    try:
        decoded = base64.b64decode(encrypted_data)
        key = _get_secret_key()
        decrypted = _xor_bytes(decoded, key)
        json_str = decrypted.decode("utf-8")
        return json.loads(json_str)
    except Exception:
        return None
