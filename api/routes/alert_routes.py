"""
api/routes/alert_routes.py
───────────────────────────
System alerts and KPI threshold alerts.
Re-exports the alert blueprint from the notification system.
"""
from flask import Blueprint

alert_bp = Blueprint("alerts", __name__)


@alert_bp.get("/")
def get_alerts():
    """Placeholder — alerts are served via /api/notifications and /api/ai/insights."""
    from flask_jwt_extended import jwt_required, get_jwt_identity
    from db.mongo import get_db

    @jwt_required()
    def _inner():
        db = get_db()
        alerts = []
        if db is not None:
            alerts = list(db.notifications.find(
                {"type": {"$in": ["warning", "system", "request"]}},
                {"_id": 0}
            ).sort("created_at", -1).limit(50))
        return {"alerts": alerts, "count": len(alerts)}
    return _inner()
