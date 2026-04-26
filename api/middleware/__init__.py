"""
api/middleware/__init__.py
──────────────────────────
JWT + RBAC middleware for all portal routes.

Decorators:
    @require_role(*roles)              — allow only listed JWT roles
    @require_institution_match         — student/teacher can only see their own institution
    @portal_guard(role, permission)    — combined role + permission check

Hooks:
    register_after_request(app)        — attaches audit log to every response
"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import jsonify, request, g
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from loguru import logger

from security.encryption import audit_log, has_permission, ROLES


# ── Role guard ────────────────────────────────────────────────────────────

def require_role(*allowed_roles: str) -> Callable:
    """
    Decorator: only allow JWT holders whose 'role' claim is in *allowed_roles*.

    Usage:
        @admin_bp.get("/budget")
        @jwt_required()
        @require_role("superadmin", "institution_admin")
        def get_budget(): ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role", "student")
            if role not in allowed_roles:
                user_id = get_jwt_identity() or "unknown"
                audit_log(
                    action="ACCESS_DENIED",
                    resource=request.path,
                    user_id=user_id,
                    role=role,
                    institution_id=claims.get("institution_id"),
                    success=False,
                    ip_address=request.remote_addr,
                )
                return jsonify({
                    "error": "Accès refusé",
                    "required_roles": list(allowed_roles),
                    "your_role": role,
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ── Permission guard ──────────────────────────────────────────────────────

def require_permission(permission: str) -> Callable:
    """
    Decorator: check JWT role has a specific permission from ROLES map.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role", "student")
            if not has_permission(role, permission):
                return jsonify({
                    "error": "Permission insuffisante",
                    "required": permission,
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ── Institution isolation guard ───────────────────────────────────────────

def require_institution_match(fn: Callable) -> Callable:
    """
    Decorator: non-superadmin users can only query their own institution.

    Reads `institution_id` from query params or JSON body.
    Compares against JWT claim `institution_id`.
    Superadmin bypasses this check.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        role = claims.get("role", "student")

        if role == "superadmin":
            return fn(*args, **kwargs)

        jwt_institution = claims.get("institution_id")
        requested_institution = (
            request.args.get("institution_id")
            or (request.get_json(silent=True) or {}).get("institution_id")
            or kwargs.get("institution_id")
        )

        if requested_institution and requested_institution != jwt_institution:
            audit_log(
                action="INSTITUTION_MISMATCH",
                resource=request.path,
                user_id=get_jwt_identity() or "unknown",
                role=role,
                institution_id=requested_institution,
                success=False,
                ip_address=request.remote_addr,
            )
            return jsonify({
                "error": "Accès interdit à cette institution",
                "your_institution": jwt_institution,
            }), 403

        return fn(*args, **kwargs)
    return wrapper


# ── Combined portal guard ─────────────────────────────────────────────────

def portal_guard(*allowed_roles: str, permission: str | None = None) -> Callable:
    """
    Combined decorator: role check + optional permission check.

    Usage:
        @portal_guard("superadmin", "institution_admin", permission="write")
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role", "student")

            if allowed_roles and role not in allowed_roles:
                return jsonify({"error": "Accès refusé", "required_roles": list(allowed_roles)}), 403

            if permission and not has_permission(role, permission):
                return jsonify({"error": "Permission insuffisante", "required": permission}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ── After-request audit hook ──────────────────────────────────────────────

def register_after_request(app) -> None:
    """
    Attach a lightweight audit log to every API response.
    Skips health check and internal endpoints.
    """
    @app.after_request
    def _audit_response(response):
        path = request.path
        # Skip noisy endpoints
        if path in ("/health", "/dev/token") or path.startswith("/internal"):
            return response

        # Try to extract JWT identity (may not be present on all routes)
        user_id = "anonymous"
        role = "anonymous"
        institution_id = None
        try:
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
            claims = get_jwt()
            if identity:
                user_id = identity
                role = claims.get("role", "unknown")
                institution_id = claims.get("institution_id")
        except Exception:
            pass

        if response.status_code >= 400:
            audit_log(
                action=f"HTTP_{request.method}",
                resource=path,
                user_id=user_id,
                role=role,
                institution_id=institution_id,
                success=False,
                ip_address=request.remote_addr,
            )

        return response
