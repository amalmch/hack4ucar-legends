"""
api/routes/student_routes.py
─────────────────────────────
Student portal backend: grades, absences, requests, notifications.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime, timezone
import uuid

from db.mongo import get_db, audit

student_bp = Blueprint("student", __name__)


def _get_student_id():
    """Extract student_id from the user's JWT identity."""
    user_id = get_jwt_identity()
    # student user IDs follow the pattern "student-{student_id}"
    if user_id and user_id.startswith("student-"):
        return user_id.replace("student-", "", 1)
    return user_id


# ── Grades ────────────────────────────────────────────────────────────────────

@student_bp.get("/grades")
@jwt_required()
def get_grades():
    """Get all grades for the logged-in student."""
    claims = get_jwt()
    if claims.get("role") not in ("student", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    student_id = _get_student_id()
    db = get_db()
    grades = []

    if db is not None:
        grades = list(db.grades.find(
            {"student_id": student_id},
            {"_id": 0}
        ).sort("subject", 1))

    # Compute overall average
    valid_grades = [g for g in grades if not g.get("eliminated", False) and g.get("moyenne", 0) > 0]
    overall_avg = round(sum(g["moyenne"] for g in valid_grades) / len(valid_grades), 2) if valid_grades else 0

    return jsonify({
        "grades": grades,
        "count": len(grades),
        "overall_average": overall_avg,
        "total_subjects": len(grades),
        "eliminated_count": sum(1 for g in grades if g.get("eliminated", False)),
    })


# ── Absences ──────────────────────────────────────────────────────────────────

@student_bp.get("/absences")
@jwt_required()
def get_absences():
    """Get absence summary per subject."""
    claims = get_jwt()
    if claims.get("role") not in ("student", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    student_id = _get_student_id()
    db = get_db()
    absences = []

    if db is not None:
        grades = list(db.grades.find(
            {"student_id": student_id},
            {"_id": 0, "subject": 1, "absences": 1, "eliminated": 1}
        ))
        for g in grades:
            absences.append({
                "subject": g.get("subject", ""),
                "absences": g.get("absences", 0),
                "eliminated": g.get("eliminated", False),
                "limit": 3,
            })

    total = sum(a["absences"] for a in absences)
    eliminated_count = sum(1 for a in absences if a["eliminated"])

    return jsonify({
        "absences": absences,
        "total_absences": total,
        "eliminated_count": eliminated_count,
    })


# ── Student Info ──────────────────────────────────────────────────────────────

@student_bp.get("/profile")
@jwt_required()
def get_profile():
    """Get the student's profile info from the students collection."""
    claims = get_jwt()
    if claims.get("role") not in ("student", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    student_id = _get_student_id()
    db = get_db()
    profile = {}

    if db is not None:
        profile = db.students.find_one({"student_id": student_id}, {"_id": 0}) or {}

    return jsonify(profile)


# ── Requests (Demandes) ──────────────────────────────────────────────────────

@student_bp.get("/requests")
@jwt_required()
def get_requests():
    """Get student's admin requests."""
    claims = get_jwt()
    if claims.get("role") not in ("student", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    student_id = _get_student_id()
    db = get_db()
    requests_list = []

    if db is not None:
        requests_list = list(db.student_requests.find(
            {"student_id": student_id},
            {"_id": 0}
        ).sort("created_at", -1))

    return jsonify({"requests": requests_list, "count": len(requests_list)})


@student_bp.post("/requests")
@jwt_required()
def submit_request():
    """Submit a new request to the institution admin."""
    claims = get_jwt()
    if claims.get("role") not in ("student", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    student_id = _get_student_id()
    institution_id = claims.get("institution_id")
    data = request.get_json() or {}
    db = get_db()

    req_type = data.get("type", "Autre")
    message = data.get("message", "")
    now = datetime.now(timezone.utc)

    # Check eligibility based on absences for "Attestation de présence"
    eligible = True
    rejection_reason = None
    if req_type == "Attestation de présence" and db is not None:
        absences = list(db.grades.find({"student_id": student_id}, {"absences": 1}))
        total_abs = sum(g.get("absences", 0) for g in absences)
        if total_abs > 15:
            eligible = False
            rejection_reason = f"Trop d'absences ({total_abs}). L'attestation ne peut pas être délivrée."

    req_doc = {
        "id": str(uuid.uuid4()),
        "student_id": student_id,
        "institution_id": institution_id,
        "type": req_type,
        "message": message,
        "status": "rejected" if not eligible else "pending",
        "admin_response": rejection_reason,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat() if not eligible else None,
    }

    if db is not None:
        db.student_requests.insert_one(req_doc)

        # Create notification for student
        user_id = get_jwt_identity()
        if not eligible:
            db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "type": "request_status",
                "title": f"Demande refusée : {req_type}",
                "message": rejection_reason,
                "read": False,
                "created_at": now.isoformat(),
            })
        else:
            db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "type": "request_status",
                "title": f"Demande envoyée : {req_type}",
                "message": f"Votre demande de {req_type.lower()} a été envoyée. Vous serez notifié du résultat.",
                "read": False,
                "created_at": now.isoformat(),
            })

        # Notify institution admin
        admins = list(db.users.find({"institution_id": institution_id, "role": "institution_admin"}, {"id": 1}))
        for admin in admins:
            db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": admin["id"],
                "type": "request",
                "title": f"Nouvelle demande : {req_type}",
                "message": f"L'étudiant {student_id} a demandé une {req_type.lower()}.",
                "read": False,
                "created_at": now.isoformat(),
            })

    audit("STUDENT_REQUEST", user_id=get_jwt_identity(), details={"type": req_type, "status": req_doc["status"]})

    return jsonify({
        "message": "Demande soumise" if eligible else "Demande refusée automatiquement",
        "request": {k: v for k, v in req_doc.items() if k != "_id"},
        "eligible": eligible,
    }), 201


# ── Vie Associative (Événements) ──────────────────────────────────────────────

@student_bp.get("/events")
@jwt_required()
def get_events():
    """Get student's submitted events."""
    claims = get_jwt()
    if claims.get("role") not in ("student", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    student_id = _get_student_id()
    db = get_db()
    events = []

    if db is not None:
        events = list(db.events.find(
            {"student_id": student_id},
            {"_id": 0}
        ).sort("created_at", -1))

    return jsonify({"events": events, "count": len(events)})


@student_bp.post("/events")
@jwt_required()
def submit_event():
    """Submit a new event proposal to the institution admin."""
    claims = get_jwt()
    if claims.get("role") not in ("student", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    student_id = _get_student_id()
    institution_id = claims.get("institution_id")
    data = request.get_json() or {}
    db = get_db()

    title = data.get("title", "")
    club = data.get("club", "")
    date = data.get("date", "")
    description = data.get("description", "")
    now = datetime.now(timezone.utc)

    event_doc = {
        "id": str(uuid.uuid4()),
        "student_id": student_id,
        "institution_id": institution_id,
        "title": title,
        "club": club,
        "date": date,
        "description": description,
        "status": "pending",
        "admin_response": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    if db is not None:
        db.events.insert_one(event_doc)

        # Notify institution admin
        admins = list(db.users.find({"institution_id": institution_id, "role": "institution_admin"}, {"id": 1}))
        for admin in admins:
            db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": admin["id"],
                "type": "event_request",
                "title": f"Nouvel événement proposé : {title}",
                "message": f"Le club {club} propose un événement pour le {date}.",
                "read": False,
                "created_at": now.isoformat(),
            })

    audit("STUDENT_EVENT_PROPOSED", user_id=get_jwt_identity(), details={"title": title, "club": club})

    return jsonify({
        "message": "Événement soumis pour approbation",
        "event": {k: v for k, v in event_doc.items() if k != "_id"}
    }), 201


# ── Notifications shortcut ───────────────────────────────────────────────────

@student_bp.get("/notifications")
@jwt_required()
def get_student_notifications():
    """Shortcut to get student's notifications."""
    user_id = get_jwt_identity()
    db = get_db()
    notifs = []

    if db is not None:
        notifs = list(db.notifications.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).limit(50))

    unread = sum(1 for n in notifs if not n.get("read", False))
    return jsonify({"notifications": notifs, "count": len(notifs), "unread": unread})
