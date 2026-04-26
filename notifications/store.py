"""
notifications/store.py
──────────────────────
In-memory notification store with per-user inbox, read/unread tracking,
and archive. Designed to be easily swapped for a PostgreSQL backend.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional


# ── In-memory store ───────────────────────────────────────────────────────

# { user_id: [notification_dict, ...] }
_inbox: dict[str, list[dict]] = defaultdict(list)

# Broadcast notifications (sent to all users of a role)
# { role: [notification_dict, ...] }
_broadcast: dict[str, list[dict]] = defaultdict(list)


# ── Notification schema ───────────────────────────────────────────────────

def _make_notification(
    user_id: str | None,
    title: str,
    message: str,
    severity: str = "info",          # info | warning | critical
    category: str = "system",        # system | ai_alert | kpi | report | approval
    institution_id: str | None = None,
    role_target: str | None = None,  # if set → broadcast to role
    meta: dict | None = None,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "role_target": role_target,
        "title": title,
        "message": message,
        "severity": severity,
        "category": category,
        "institution_id": institution_id,
        "read": False,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "meta": meta or {},
    }


# ── Write operations ──────────────────────────────────────────────────────

def push_notification(
    user_id: str,
    title: str,
    message: str,
    severity: str = "info",
    category: str = "system",
    institution_id: str | None = None,
    meta: dict | None = None,
) -> dict:
    """Push a notification to a specific user's inbox."""
    notif = _make_notification(
        user_id=user_id,
        title=title,
        message=message,
        severity=severity,
        category=category,
        institution_id=institution_id,
        meta=meta,
    )
    _inbox[user_id].append(notif)
    return notif


def broadcast_to_role(
    role: str,
    title: str,
    message: str,
    severity: str = "info",
    category: str = "ai_alert",
    institution_id: str | None = None,
    meta: dict | None = None,
) -> dict:
    """Broadcast a notification to all users of a given role."""
    notif = _make_notification(
        user_id=None,
        title=title,
        message=message,
        severity=severity,
        category=category,
        institution_id=institution_id,
        role_target=role,
        meta=meta,
    )
    _broadcast[role].append(notif)
    return notif


def route_alert_notification(alert: dict) -> list[dict]:
    """
    Route an AI alert to the appropriate role inboxes based on severity.

    Routing rules:
        critical → superadmin + institution_admin (broadcast)
        warning  → institution_admin + teacher (broadcast)
        info     → teacher (broadcast)
    """
    severity = alert.get("severity", "info")
    institution_id = alert.get("institution", alert.get("institution_id"))
    title = f"🚨 Alerte IA — {severity.upper()}"
    message = alert.get("message", alert.get("alert_text", "Nouvelle alerte détectée."))
    meta = {"alert_id": alert.get("id"), "source": "ai_anomaly"}

    sent = []
    if severity == "critical":
        sent.append(broadcast_to_role("superadmin", title, message, severity, "ai_alert", institution_id, meta))
        sent.append(broadcast_to_role("institution_admin", title, message, severity, "ai_alert", institution_id, meta))
    elif severity == "warning":
        sent.append(broadcast_to_role("institution_admin", title, message, severity, "ai_alert", institution_id, meta))
        sent.append(broadcast_to_role("teacher", title, message, "warning", "ai_alert", institution_id, meta))
    else:
        sent.append(broadcast_to_role("teacher", title, message, "info", "ai_alert", institution_id, meta))

    return sent


# ── Read operations ───────────────────────────────────────────────────────

def get_notifications(
    user_id: str,
    role: str,
    institution_id: str | None = None,
    unread_only: bool = False,
    limit: int = 50,
) -> list[dict]:
    """
    Fetch notifications for a user — combines personal inbox + role broadcasts.
    Filters broadcasts to matching institution if institution_id is set.
    """
    personal = list(_inbox.get(user_id, []))

    broadcasts = list(_broadcast.get(role, []))
    if institution_id:
        broadcasts = [
            b for b in broadcasts
            if b.get("institution_id") is None or b.get("institution_id") == institution_id
        ]

    all_notifs = personal + broadcasts
    all_notifs.sort(key=lambda n: n["created_at"], reverse=True)

    if unread_only:
        all_notifs = [n for n in all_notifs if not n["read"]]

    return all_notifs[:limit]


def mark_as_read(notification_id: str, user_id: str) -> bool:
    """Mark a personal notification as read. Returns True if found."""
    for notif in _inbox.get(user_id, []):
        if notif["id"] == notification_id:
            notif["read"] = True
            return True
    return False


def mark_all_read(user_id: str, role: str) -> int:
    """Mark all notifications (personal + broadcasts) as read. Returns count."""
    count = 0
    for notif in _inbox.get(user_id, []):
        if not notif["read"]:
            notif["read"] = True
            count += 1
    for notif in _broadcast.get(role, []):
        if not notif["read"]:
            notif["read"] = True
            count += 1
    return count


def get_unread_count(user_id: str, role: str) -> int:
    """Return total unread count for a user."""
    personal_unread = sum(1 for n in _inbox.get(user_id, []) if not n["read"])
    broadcast_unread = sum(1 for n in _broadcast.get(role, []) if not n["read"])
    return personal_unread + broadcast_unread


def get_notification_stats() -> dict:
    """Admin stats: total notifications, broadcast counts per role."""
    total_personal = sum(len(v) for v in _inbox.values())
    total_broadcasts = {role: len(notifs) for role, notifs in _broadcast.items()}
    return {
        "total_personal": total_personal,
        "total_users_with_inbox": len(_inbox),
        "broadcasts_by_role": total_broadcasts,
    }
