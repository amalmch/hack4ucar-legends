"""
security/encryption.py
────────────────────────
AES-256 encryption/decryption for sensitive KPI fields.
Audit log for all API actions (who, what, when).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from loguru import logger


# ── AES-256-GCM Encryption ────────────────────────────────────────────────

class AESEncryptor:
    """
    AES-256-GCM symmetric encryption.
    Key is derived from AES_KEY env var (hex string) or auto-generated.

    Usage:
        enc = AESEncryptor()
        ciphertext = enc.encrypt("sensitive value")
        plaintext  = enc.decrypt(ciphertext)
    """

    def __init__(self, key_hex: Optional[str] = None):
        raw = key_hex or os.getenv("AES_KEY", "")
        if raw and len(raw) >= 64:
            self._key = bytes.fromhex(raw[:64])
        else:
            self._key = AESGCM.generate_key(bit_length=256)
            logger.warning(
                "AES_KEY not set — generated ephemeral key. "
                "Data encrypted in this session cannot be decrypted after restart."
            )

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string, return base64-encoded ciphertext."""
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        payload = nonce + ct
        return base64.urlsafe_b64encode(payload).decode("ascii")

    def decrypt(self, ciphertext_b64: str) -> str:
        """Decrypt a base64-encoded ciphertext string."""
        payload = base64.urlsafe_b64decode(ciphertext_b64.encode("ascii"))
        nonce = payload[:12]
        ct = payload[12:]
        aesgcm = AESGCM(self._key)
        plaintext = aesgcm.decrypt(nonce, ct, None)
        return plaintext.decode("utf-8")

    def encrypt_dict(self, data: dict, fields: list[str]) -> dict:
        """Encrypt specific fields in a dict in-place (returns copy)."""
        out = data.copy()
        for field in fields:
            if field in out and out[field] is not None:
                out[field] = self.encrypt(str(out[field]))
        return out

    def decrypt_dict(self, data: dict, fields: list[str]) -> dict:
        """Decrypt specific fields in a dict."""
        out = data.copy()
        for field in fields:
            if field in out and out[field] is not None:
                try:
                    out[field] = self.decrypt(out[field])
                except Exception:
                    pass  # Field may not be encrypted
        return out


# ── RBAC (Role-Based Access Control) ─────────────────────────────────────

ROLES = {
    "superadmin":        {"read", "write", "delete", "admin", "export", "ai"},
    "institution_admin": {"read", "write", "export", "ai"},
    "teacher":           {"read", "export"},
    "student":           {"read"},
    "binome_a":          {"internal_write"},   # Binôme A service account
}


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLES.get(role, set())


def require_permission(permission: str):
    """Flask decorator — check JWT role has the required permission."""
    from functools import wraps
    from flask import jsonify
    from flask_jwt_extended import get_jwt, verify_jwt_in_request

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role", "student")
            if not has_permission(role, permission):
                audit_log(
                    action="PERMISSION_DENIED",
                    resource=permission,
                    user_id=claims.get("sub", "unknown"),
                    role=role,
                    success=False,
                )
                return jsonify({"error": "Permission insuffisante"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ── Audit Log ─────────────────────────────────────────────────────────────

_AUDIT_LOG_DIR = Path("./logs/audit")
_AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)


def audit_log(
    action: str,
    resource: str,
    user_id: str = "system",
    role: str = "system",
    institution_id: Optional[str] = None,
    payload: Optional[dict] = None,
    success: bool = True,
    ip_address: Optional[str] = None,
) -> dict:
    """
    Write an immutable audit log entry.

    Fields: id, timestamp, user_id, role, action, resource,
            institution_id, success, ip_address, payload_hash
    """
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "user_id": user_id,
        "role": role,
        "action": action,
        "resource": resource,
        "institution_id": institution_id,
        "success": success,
        "ip_address": ip_address,
        "payload_hash": (
            hashlib.sha256(json.dumps(payload, default=str, sort_keys=True).encode()).hexdigest()
            if payload else None
        ),
    }

    # Append to daily log file (NDJSON)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    log_file = _AUDIT_LOG_DIR / f"audit_{date_str}.ndjson"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Also log to loguru for monitoring
    level = "INFO" if success else "WARNING"
    logger.log(level, f"AUDIT | {user_id} ({role}) | {action} | {resource} | success={success}")

    return entry


def get_audit_logs(
    date: Optional[str] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Read and filter audit logs."""
    date_str = date or datetime.utcnow().strftime("%Y-%m-%d")
    log_file = _AUDIT_LOG_DIR / f"audit_{date_str}.ndjson"

    if not log_file.exists():
        return []

    entries = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if user_id and entry.get("user_id") != user_id:
                    continue
                if action and entry.get("action") != action:
                    continue
                entries.append(entry)
            except json.JSONDecodeError:
                continue

    return entries[-limit:]


# ── Data Masking ──────────────────────────────────────────────────────────

SENSITIVE_FIELDS = {"password", "token", "aes_key", "national_id", "phone", "email"}


def mask_sensitive(data: dict, show_last: int = 4) -> dict:
    """Replace sensitive field values with masked versions for logging."""
    out = {}
    for k, v in data.items():
        if k.lower() in SENSITIVE_FIELDS or any(s in k.lower() for s in ("secret", "key", "pass")):
            out[k] = "****" + str(v)[-show_last:] if isinstance(v, str) and len(str(v)) > show_last else "****"
        else:
            out[k] = v
    return out
