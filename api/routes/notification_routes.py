"""
api/routes/notification_routes.py
──────────────────────────────────
Notifications CRUD for all user roles.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime, timezone

from db.mongo import get_db

notif_bp = Blueprint("notifications", __name__)


@notif_bp.get("")
@jwt_required()
def get_notifications():
    """Get all notifications for the current user."""
    user_id = get_jwt_identity()
    db = get_db()
    notifs = []

    if db is not None:
        notifs = list(db.notifications.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("created_at", -1).limit(100))

    unread = sum(1 for n in notifs if not n.get("read", False))
    return jsonify({"notifications": notifs, "count": len(notifs), "unread": unread})


@notif_bp.patch("/<notif_id>/read")
@jwt_required()
def mark_read(notif_id):
    """Mark a notification as read."""
    user_id = get_jwt_identity()
    db = get_db()

    if db is not None:
        result = db.notifications.update_one(
            {"id": notif_id, "user_id": user_id},
            {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
        )
        if result.modified_count == 0:
            return jsonify({"error": "Notification non trouvée"}), 404

    return jsonify({"message": "Notification marquée comme lue"})


@notif_bp.patch("/read-all")
@jwt_required()
def mark_all_read():
    """Mark all notifications as read."""
    user_id = get_jwt_identity()
    db = get_db()

    if db is not None:
        db.notifications.update_many(
            {"user_id": user_id, "read": False},
            {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
        )

    return jsonify({"message": "Toutes les notifications marquées comme lues"})


@notif_bp.get("/unread-count")
@jwt_required()
def unread_count():
    """Get unread notification count (for badge)."""
    user_id = get_jwt_identity()
    db = get_db()
    count = 0
    if db is not None:
        count = db.notifications.count_documents({"user_id": user_id, "read": False})
    return jsonify({"unread": count})
