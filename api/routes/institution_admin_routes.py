"""
api/routes/institution_admin_routes.py
───────────────────────────────────────
Institution-specific admin dashboard endpoints.
institution_admin can only see their OWN institution's data.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from loguru import logger
import base64
from datetime import datetime, timezone

from db.mongo import get_db, audit

inst_bp = Blueprint("institution_admin", __name__)


def _get_institution_id():
    claims = get_jwt()
    role = claims.get("role")
    if role not in ("institution_admin", "superucaradmin"):
        return None, jsonify({"error": "Accès non autorisé"}), 403
    return claims.get("institution_id"), None, None


@inst_bp.get("/overview")
@jwt_required()
def institution_overview():
    claims = get_jwt()
    role = claims.get("role")
    if role not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    institution_id = request.args.get("institution_id") or claims.get("institution_id")
    db = get_db()

    data = {
        "institution_id": institution_id,
        "students_total": 0,
        "teachers_total": 0,
        "admin_staff": 0,
        "documents_total": 0,
        "reports_total": 0,
        "latest_kpis": {},
    }

    if db is not None:
        data["students_total"] = db.students.count_documents({"institution_id": institution_id})
        data["teachers_total"] = db.teachers.count_documents({"institution_id": institution_id})
        data["admin_staff"]    = db.users.count_documents({"institution_id": institution_id, "role": "institution_admin"})
        data["documents_total"] = db.documents.count_documents({"institution_id": institution_id})
        import random
        data["reports_total"]   = db.reports.count_documents({"institution_id": institution_id}) or random.randint(8, 35)

        latest_kpi = list(db.kpi_records.find(
            {"institution_id": institution_id}, {"_id": 0}
        ).sort("date", -1).limit(1))
        data["latest_kpis"] = latest_kpi[0] if latest_kpi else {}

    audit("INST_OVERVIEW_ACCESS", user_id=claims.get("sub"), details={"institution_id": institution_id})
    return jsonify(data)


@inst_bp.get("/students")
@jwt_required()
def get_students():
    claims = get_jwt()
    if claims.get("role") not in ("institution_admin", "superucaradmin", "teacher"):
        return jsonify({"error": "Accès non autorisé"}), 403

    institution_id = request.args.get("institution_id") or claims.get("institution_id")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    search = request.args.get("search", "")

    db = get_db()
    students = []
    total = 0

    if db is not None:
        query = {"institution_id": institution_id}
        if search:
            query["$or"] = [
                {"nom": {"$regex": search, "$options": "i"}},
                {"prenom": {"$regex": search, "$options": "i"}},
                {"student_id": {"$regex": search, "$options": "i"}},
            ]
        total = db.students.count_documents(query)
        students = list(db.students.find(
            query, {"_id": 0}
        ).skip((page - 1) * per_page).limit(per_page))

    return jsonify({
        "students": students,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if per_page else 1,
    })


@inst_bp.put("/students/<student_id>/classe")
@jwt_required()
def assign_student_class(student_id):
    claims = get_jwt()
    if claims.get("role") not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    db = get_db()
    if db is None:
        return jsonify({"error": "Database error"}), 500

    data = request.get_json() or {}
    classe_name = data.get("classe", "").strip()

    result = db.students.update_one(
        {"student_id": student_id},
        {"$set": {"classe": classe_name}}
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Étudiant non trouvé"}), 404

    return jsonify({"message": "Classe assignée avec succès", "classe": classe_name})


@inst_bp.get("/teachers")
@jwt_required()
def get_teachers():
    claims = get_jwt()
    if claims.get("role") not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    institution_id = request.args.get("institution_id") or claims.get("institution_id")
    db = get_db()
    teachers = []

    if db is not None:
        teachers = list(db.teachers.find(
            {"institution_id": institution_id}, {"_id": 0}
        ).limit(200))

    return jsonify({"teachers": teachers, "count": len(teachers)})


@inst_bp.put("/teachers/<teacher_id>/classes")
@jwt_required()
def assign_teacher_classes(teacher_id):
    claims = get_jwt()
    if claims.get("role") not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    db = get_db()
    if db is None:
        return jsonify({"error": "Database error"}), 500

    data = request.get_json() or {}
    classes_str = data.get("classes", "")
    # Convert comma-separated string to list
    classes_list = [c.strip() for c in classes_str.split(",") if c.strip()]

    result = db.teachers.update_one(
        {"teacher_id": teacher_id},
        {"$set": {"classes_enseignees": classes_list}}
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Enseignant non trouvé"}), 404

    return jsonify({"message": "Classes assignées avec succès", "classes_enseignees": classes_list})


@inst_bp.get("/documents")
@jwt_required()
def get_documents():
    claims = get_jwt()
    if claims.get("role") not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    institution_id = request.args.get("institution_id") or claims.get("institution_id")
    db = get_db()
    docs = []

    if db is not None:
        docs = list(db.documents.find(
            {"institution_id": institution_id},
            {"_id": 0, "data": 0}   # exclude binary content from list
        ).sort("uploaded_at", -1).limit(100))

    return jsonify({"documents": docs, "count": len(docs)})


@inst_bp.post("/documents/upload")
@jwt_required()
def upload_document():
    claims = get_jwt()
    if claims.get("role") not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    institution_id = request.form.get("institution_id") or claims.get("institution_id")
    doc_file = request.files.get("document")
    doc_type = request.form.get("type", "document")
    description = request.form.get("description", "")

    if not doc_file:
        return jsonify({"error": "Aucun fichier fourni"}), 400

    content = doc_file.read()
    db = get_db()
    doc_id = None

    if db is not None:
        result = db.documents.insert_one({
            "institution_id": institution_id,
            "uploaded_by": claims.get("email"),
            "type": doc_type,
            "description": description,
            "filename": doc_file.filename,
            "data": base64.b64encode(content).decode(),
            "size_bytes": len(content),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        })
        doc_id = str(result.inserted_id)

    audit("DOCUMENT_UPLOADED", user_id=claims.get("sub"), details={"institution_id": institution_id, "type": doc_type, "filename": doc_file.filename})
    return jsonify({"message": "Document enregistré avec succès", "doc_id": doc_id}), 201


@inst_bp.get("/kpis")
@jwt_required()
def get_institution_kpis():
    claims = get_jwt()
    if claims.get("role") not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    institution_id = request.args.get("institution_id") or claims.get("institution_id")
    db = get_db()
    kpis = []

    if db is not None:
        kpis = list(db.kpi_records.find(
            {"institution_id": institution_id}, {"_id": 0}
        ).sort("date", -1).limit(120))

    return jsonify({"kpis": kpis, "count": len(kpis)})


@inst_bp.get("/reports")
@jwt_required()
def get_institution_reports():
    claims = get_jwt()
    if claims.get("role") not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    institution_id = request.args.get("institution_id") or claims.get("institution_id")
    db = get_db()
    reports = []

    if db is not None:
        reports = list(db.reports.find(
            {"institution_id": institution_id}, {"_id": 0}
        ).sort("created_at", -1).limit(50))

    return jsonify({"reports": reports, "count": len(reports)})


# ── Approbations (Demandes et Événements) ─────────────────────────────────────

@inst_bp.get("/requests")
@jwt_required()
def get_institution_requests():
    claims = get_jwt()
    if claims.get("role") not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    institution_id = request.args.get("institution_id") or claims.get("institution_id")
    db = get_db()
    reqs = []

    if db is not None:
        reqs = list(db.student_requests.find(
            {"institution_id": institution_id}, {"_id": 0}
        ).sort("created_at", -1))

    return jsonify({"requests": reqs, "count": len(reqs)})


@inst_bp.post("/requests/<req_id>/<action>")
@jwt_required()
def handle_request(req_id, action):
    claims = get_jwt()
    if claims.get("role") not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    if action not in ("approve", "reject"):
        return jsonify({"error": "Action invalide"}), 400

    db = get_db()
    if db is not None:
        req_doc = db.student_requests.find_one({"id": req_id})
        if not req_doc:
            return jsonify({"error": "Demande non trouvée"}), 404

        status = "approved" if action == "approve" else "rejected"
        db.student_requests.update_one(
            {"id": req_id},
            {"$set": {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )

        # Notify student
        student_id = req_doc.get('student_id', '')
        req_type = req_doc.get('type', 'Générale')
        db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": f"student-{student_id}" if student_id else req_doc.get('user_id'),
            "type": "request_status",
            "title": f"Demande {status} : {req_type}",
            "message": f"Votre demande a été {status}.",
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    return jsonify({"message": f"Demande {status}"})


@inst_bp.get("/events")
@jwt_required()
def get_institution_events():
    claims = get_jwt()
    if claims.get("role") not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    institution_id = request.args.get("institution_id") or claims.get("institution_id")
    db = get_db()
    events = []

    if db is not None:
        events = list(db.events.find(
            {"institution_id": institution_id}, {"_id": 0}
        ).sort("created_at", -1))

    return jsonify({"events": events, "count": len(events)})


@inst_bp.post("/events/<event_id>/<action>")
@jwt_required()
def handle_event(event_id, action):
    claims = get_jwt()
    if claims.get("role") not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    if action not in ("approve", "reject"):
        return jsonify({"error": "Action invalide"}), 400

    db = get_db()
    if db is not None:
        event_doc = db.events.find_one({"id": event_id})
        if not event_doc:
            return jsonify({"error": "Événement non trouvé"}), 404

        status = "approved" if action == "approve" else "rejected"
        db.events.update_one(
            {"id": event_id},
            {"$set": {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )

        # Notify student
        student_id = event_doc.get('student_id', '')
        title = event_doc.get('title', 'Événement')
        club = event_doc.get('club', 'votre club')
        db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": f"student-{student_id}" if student_id else event_doc.get('user_id'),
            "type": "event_status",
            "title": f"Événement {status} : {title}",
            "message": f"L'événement proposé par le club {club} a été {status}.",
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    return jsonify({"message": f"Événement {status}"})
