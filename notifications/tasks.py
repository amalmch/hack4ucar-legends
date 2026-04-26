"""
notifications/tasks.py
───────────────────────
Celery async tasks for notification dispatch.
Falls back to synchronous execution if Celery/Redis is unavailable.

Tasks:
    send_inapp_notification    — push to in-memory store
    send_email_notification    — SMTP via Flask-Mail
    route_alert_to_roles       — distribute AI alert to role inboxes
    bulk_notify_institution    — notify all users of an institution
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from loguru import logger


# ── Celery app (lazy init) ────────────────────────────────────────────────

_celery_app = None


def get_celery_app():
    """Return or create the Celery app singleton."""
    global _celery_app
    if _celery_app is not None:
        return _celery_app
    try:
        from celery import Celery
        import os
        broker = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        backend = os.getenv("CELERY_RESULT_BACKEND", broker)
        _celery_app = Celery("binome_b", broker=broker, backend=backend)
        _celery_app.conf.update(
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            timezone="Africa/Algiers",
            enable_utc=True,
            task_track_started=True,
        )
        logger.info("✅ Celery connected to broker")
        return _celery_app
    except Exception as e:
        logger.warning(f"⚠️  Celery unavailable ({e}), using sync fallback")
        return None


# ── Helper: run task sync or async ───────────────────────────────────────

def _dispatch(fn, *args, **kwargs):
    """Send task to Celery if available, else run synchronously."""
    celery = get_celery_app()
    if celery:
        try:
            return fn.delay(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Celery dispatch failed ({e}), running sync")
    return fn(*args, **kwargs)


# ── Task: in-app notification ─────────────────────────────────────────────

def send_inapp_notification(
    user_id: str,
    title: str,
    message: str,
    severity: str = "info",
    category: str = "system",
    institution_id: str | None = None,
    meta: dict | None = None,
) -> dict:
    """Push an in-app notification to a user's inbox."""
    from notifications.store import push_notification
    notif = push_notification(
        user_id=user_id,
        title=title,
        message=message,
        severity=severity,
        category=category,
        institution_id=institution_id,
        meta=meta,
    )
    logger.info(f"📬 In-app notif → {user_id} | {severity} | {title}")
    return notif


# Make it a Celery task if Celery is available
try:
    celery = get_celery_app()
    if celery:
        send_inapp_notification = celery.task(name="notif.inapp")(send_inapp_notification)
except Exception:
    pass


# ── Task: email notification ──────────────────────────────────────────────

def send_email_notification(
    recipient_email: str,
    subject: str,
    body_html: str,
    body_text: str | None = None,
) -> bool:
    """
    Send an email notification via SMTP.
    Reads MAIL_* config from environment.
    Returns True on success.
    """
    import os
    mail_server = os.getenv("MAIL_SERVER", "localhost")
    mail_port = int(os.getenv("MAIL_PORT", 587))
    mail_user = os.getenv("MAIL_USERNAME", "")
    mail_pass = os.getenv("MAIL_PASSWORD", "")
    mail_from = os.getenv("MAIL_DEFAULT_SENDER", "noreply@ucar.dz")

    if not mail_user:
        logger.warning(f"📧 Email skipped (MAIL_USERNAME not set) → {recipient_email}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = mail_from
        msg["To"] = recipient_email

        if body_text:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(mail_server, mail_port) as server:
            server.ehlo()
            if mail_port in (587, 465):
                server.starttls()
            if mail_user and mail_pass:
                server.login(mail_user, mail_pass)
            server.sendmail(mail_from, [recipient_email], msg.as_string())

        logger.info(f"📧 Email sent → {recipient_email} | {subject}")
        return True

    except Exception as e:
        logger.error(f"📧 Email failed → {recipient_email}: {e}")
        return False


try:
    celery = get_celery_app()
    if celery:
        send_email_notification = celery.task(name="notif.email")(send_email_notification)
except Exception:
    pass


# ── Task: route AI alert to roles ─────────────────────────────────────────

def route_alert_to_roles(alert: dict) -> dict:
    """
    Distribute an AI-generated alert to role inboxes via the notification store.
    Called by alert_routes after /api/alerts/generate.
    """
    from notifications.store import route_alert_notification
    notifications = route_alert_notification(alert)
    logger.info(
        f"🔔 Alert routed | severity={alert.get('severity')} | "
        f"institution={alert.get('institution', alert.get('institution_id'))} | "
        f"dispatched={len(notifications)} broadcasts"
    )
    return {"dispatched": len(notifications), "alert_id": alert.get("id")}


try:
    celery = get_celery_app()
    if celery:
        route_alert_to_roles = celery.task(name="notif.route_alert")(route_alert_to_roles)
except Exception:
    pass


# ── Task: bulk notify institution ─────────────────────────────────────────

def bulk_notify_institution(
    institution_id: str,
    user_ids: list[str],
    title: str,
    message: str,
    severity: str = "info",
    category: str = "system",
) -> dict:
    """Notify all users belonging to an institution."""
    from notifications.store import push_notification
    sent = 0
    for uid in user_ids:
        push_notification(
            user_id=uid,
            title=title,
            message=message,
            severity=severity,
            category=category,
            institution_id=institution_id,
        )
        sent += 1
    logger.info(f"📢 Bulk notify | institution={institution_id} | sent={sent}")
    return {"institution_id": institution_id, "sent": sent}


try:
    celery = get_celery_app()
    if celery:
        bulk_notify_institution = celery.task(name="notif.bulk")(bulk_notify_institution)
except Exception:
    pass
