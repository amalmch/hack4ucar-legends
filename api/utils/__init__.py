"""
api/utils/__init__.py
──────────────────────
Shared response helpers, pagination, and validators.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from flask import jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity


# ── Standard response envelope ────────────────────────────────────────────

def success_response(data: Any = None, message: str = "OK", status: int = 200):
    """Return a standardised success JSON response."""
    payload = {
        "success": True,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def error_response(message: str, code: int = 400, details: Any = None):
    """Return a standardised error JSON response."""
    payload = {
        "success": False,
        "error": message,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if details is not None:
        payload["details"] = details
    return jsonify(payload), code


# ── Pagination ────────────────────────────────────────────────────────────

def paginate(data: list, page: int = 1, per_page: int = 20) -> dict:
    """
    Slice a list into a paginated envelope.

    Returns:
        {items, page, per_page, total, total_pages}
    """
    total = len(data)
    total_pages = max(1, math.ceil(total / per_page))
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page

    return {
        "items": data[start:end],
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
    }


def get_pagination_params() -> tuple[int, int]:
    """Extract page + per_page from query string."""
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    return page, per_page


# ── Institution access control ────────────────────────────────────────────

def validate_institution_access(institution_id: str | None = None) -> tuple[bool, str | None]:
    """
    Check if current JWT holder can access the requested institution.

    Returns:
        (allowed: bool, resolved_institution_id: str | None)
    """
    try:
        claims = get_jwt()
        role = claims.get("role", "student")
        jwt_institution = claims.get("institution_id")

        if role == "superadmin":
            # Superadmin can query any institution or all
            return True, institution_id

        if institution_id and institution_id != jwt_institution:
            return False, jwt_institution

        return True, jwt_institution or institution_id
    except Exception:
        return False, None


def get_current_user() -> dict:
    """Extract current user info from JWT claims."""
    try:
        identity = get_jwt_identity() or "anonymous"
        claims = get_jwt()
        return {
            "user_id": identity,
            "role": claims.get("role", "student"),
            "institution_id": claims.get("institution_id"),
        }
    except Exception:
        return {"user_id": "anonymous", "role": "student", "institution_id": None}


# ── Field validators ──────────────────────────────────────────────────────

def require_fields(body: dict, *fields: str) -> str | None:
    """
    Check that all required fields are present in body.
    Returns error message string if missing, else None.
    """
    missing = [f for f in fields if f not in body or body[f] is None]
    if missing:
        return f"Champs manquants: {', '.join(missing)}"
    return None


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a numeric value between min and max."""
    return max(min_val, min(max_val, value))
