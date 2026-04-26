"""
api/routes/teacher_routes.py
─────────────────────────────
Teacher portal backend: classes, courses, exams, grades.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime, timezone
import uuid

from db.mongo import get_db, audit

teacher_bp = Blueprint("teacher", __name__)


def _teacher_guard():
    """Returns (claims, error_response). If error_response is not None, return it."""
    from flask_jwt_extended import get_jwt
    claims = get_jwt()
    if claims.get("role") not in ("teacher", "superucaradmin"):
        return None, (jsonify({"error": "Accès non autorisé"}), 403)
    return claims, None


# ── Profile ───────────────────────────────────────────────────────────────────

@teacher_bp.get("/profile")
@jwt_required()
def get_profile():
    """Get the teacher's profile info from the teachers collection."""
    claims, err = _teacher_guard()
    if err:
        return err

    # teacher identity logic:
    user_id = get_jwt_identity()
    teacher_id = user_id.replace("teacher-", "", 1) if user_id.startswith("teacher-") else user_id

    db = get_db()
    profile = {}

    if db is not None:
        profile = db.teachers.find_one({"teacher_id": teacher_id}, {"_id": 0}) or {}
        if not profile:
            # fallback if teacher_id is slightly different
            user = db.users.find_one({"id": user_id})
            if user:
                profile = db.teachers.find_one({"teacher_id": user.get("id")}, {"_id": 0}) or {}

    return jsonify(profile)


# ── Classes (students by programme/niveau) ────────────────────────────────────

@teacher_bp.get("/classes")
@jwt_required()
def get_classes():
    """Get the teacher's classes (grouped by niveau)."""
    claims, err = _teacher_guard()
    if err:
        return err

    institution_id = claims.get("institution_id")
    db = get_db()
    classes = []

    if db is not None:
        pipeline = [
            {"$match": {"institution_id": institution_id}},
            {"$group": {
                "_id": {"programme": "$programme", "niveau": "$niveau"},
                "count": {"$sum": 1},
                "students": {"$push": {
                    "student_id": "$student_id",
                    "nom": "$nom",
                    "prenom": "$prenom",
                    "genre": "$genre",
                    "statut": "$statut",
                    "moyenne_s1": "$moyenne_s1",
                    "nb_absences_s1": "$nb_absences_s1",
                }},
            }},
            {"$sort": {"_id.niveau": 1}},
        ]
        for group in db.students.aggregate(pipeline):
            classes.append({
                "programme": group["_id"]["programme"],
                "niveau": group["_id"]["niveau"],
                "count": group["count"],
                "students": group["students"][:100],  # limit
            })

    return jsonify({"classes": classes, "count": len(classes)})


@teacher_bp.get("/classes/<niveau>/students")
@jwt_required()
def get_class_students(niveau):
    """Get students for a specific class."""
    claims, err = _teacher_guard()
    if err:
        return err

    institution_id = claims.get("institution_id")
    db = get_db()
    students = []

    if db is not None:
        students = list(db.students.find(
            {"institution_id": institution_id, "niveau": niveau},
            {"_id": 0}
        ).limit(200))

    return jsonify({"students": students, "count": len(students)})


# ── Courses ───────────────────────────────────────────────────────────────────

@teacher_bp.get("/courses")
@jwt_required()
def get_courses():
    """List all course materials."""
    claims, err = _teacher_guard()
    if err:
        return err

    institution_id = claims.get("institution_id")
    db = get_db()
    courses = []

    if db is not None:
        courses = list(db.courses.find(
            {"institution_id": institution_id},
            {"_id": 0}
        ).sort("uploaded_at", -1).limit(200))

    return jsonify({"courses": courses, "count": len(courses)})


@teacher_bp.post("/courses")
@jwt_required()
def add_course():
    """Add a new course material."""
    claims, err = _teacher_guard()
    if err:
        return err

    data = request.get_json() or {}
    db = get_db()

    course = {
        "id": str(uuid.uuid4()),
        "institution_id": claims.get("institution_id"),
        "subject": data.get("subject", ""),
        "niveau": data.get("niveau", ""),
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "file_type": data.get("file_type", "pdf"),
        "uploaded_by": get_jwt_identity(),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }

    if db is not None:
        db.courses.insert_one(course)

        # Notify students of the new course
        students = list(db.students.find(
            {"institution_id": claims.get("institution_id"), "niveau": course["niveau"]},
            {"student_id": 1}
        ))
        notifs = []
        now = datetime.now(timezone.utc).isoformat()
        for stu in students:
            user = db.users.find_one({"id": {"$regex": stu["student_id"]}})
            if user:
                notifs.append({
                    "id": str(uuid.uuid4()),
                    "user_id": user["id"],
                    "type": "course_material",
                    "title": f"Nouveau support de cours : {course['subject']}",
                    "message": f"Le document '{course['title']}' a été ajouté.",
                    "read": False,
                    "created_at": now,
                })
        if notifs:
            db.notifications.insert_many(notifs)

    audit("COURSE_ADDED", user_id=get_jwt_identity(), details={"title": course["title"]})
    return jsonify({"message": "Cours ajouté", "course": {k: v for k, v in course.items() if k != "_id"}}), 201


@teacher_bp.delete("/courses/<course_id>")
@jwt_required()
def delete_course(course_id):
    """Delete a course material."""
    claims, err = _teacher_guard()
    if err:
        return err

    db = get_db()
    if db is not None:
        result = db.courses.delete_one({"id": course_id})
        if result.deleted_count == 0:
            return jsonify({"error": "Cours non trouvé"}), 404

    return jsonify({"message": "Cours supprimé"})


# ── Exams ─────────────────────────────────────────────────────────────────────

@teacher_bp.get("/exams")
@jwt_required()
def get_exams():
    """List all exams."""
    claims, err = _teacher_guard()
    if err:
        return err

    institution_id = claims.get("institution_id")
    db = get_db()
    exams = []

    if db is not None:
        exams = list(db.exams.find(
            {"institution_id": institution_id},
            {"_id": 0}
        ).sort("date", 1).limit(200))

    return jsonify({"exams": exams, "count": len(exams)})


@teacher_bp.post("/exams")
@jwt_required()
def schedule_exam():
    """Schedule a new exam."""
    claims, err = _teacher_guard()
    if err:
        return err

    data = request.get_json() or {}
    db = get_db()
    now = datetime.now(timezone.utc)

    exam = {
        "id": str(uuid.uuid4()),
        "institution_id": claims.get("institution_id"),
        "subject": data.get("subject", ""),
        "niveau": data.get("niveau", ""),
        "type": data.get("type", "DS"),
        "date": data.get("date", ""),
        "salle": data.get("salle", ""),
        "duree_minutes": int(data.get("duree_minutes", 60)),
        "created_by": get_jwt_identity(),
        "status": "upcoming",
        "created_at": now.isoformat(),
    }

    if db is not None:
        db.exams.insert_one(exam)

        # Notify students
        students = list(db.students.find(
            {"institution_id": claims.get("institution_id"), "niveau": exam["niveau"]},
            {"student_id": 1}
        ))
        notifs = []
        for stu in students:
            user = db.users.find_one({"id": {"$regex": stu["student_id"]}})
            if user:
                notifs.append({
                    "id": str(uuid.uuid4()),
                    "user_id": user["id"],
                    "type": "exam_scheduled",
                    "title": f"Examen programmé : {exam['subject']}",
                    "message": f"{exam['type']} de {exam['subject']} le {exam['date'][:10]} en {exam['salle']}",
                    "read": False,
                    "created_at": now.isoformat(),
                })
        if notifs:
            db.notifications.insert_many(notifs)

    audit("EXAM_SCHEDULED", user_id=get_jwt_identity(), details={"subject": exam["subject"], "type": exam["type"]})
    return jsonify({"message": "Examen programmé", "exam": {k: v for k, v in exam.items() if k != "_id"}}), 201


# ── Grades ────────────────────────────────────────────────────────────────────

@teacher_bp.get("/grades")
@jwt_required()
def get_grades():
    """Get grades, optionally filtered by niveau/subject."""
    claims, err = _teacher_guard()
    if err:
        return err

    institution_id = claims.get("institution_id")
    niveau = request.args.get("niveau")
    subject = request.args.get("subject")
    db = get_db()
    grades = []

    if db is not None:
        query = {"institution_id": institution_id}
        if niveau:
            query["niveau"] = niveau
        if subject:
            query["subject"] = subject
        grades = list(db.grades.find(query, {"_id": 0}).limit(500))

    return jsonify({"grades": grades, "count": len(grades)})


@teacher_bp.post("/grades")
@jwt_required()
def submit_grades():
    """Submit or update grades for students."""
    claims, err = _teacher_guard()
    if err:
        return err

    data = request.get_json() or {}
    grades_list = data.get("grades", [])
    db = get_db()
    updated = 0
    inserted = 0
    now = datetime.now(timezone.utc)

    if db is not None:
        for g in grades_list:
            ds = float(g.get("ds", 0))
            examen = float(g.get("examen", 0))
            tp = float(g.get("tp", 0))
            absences = int(g.get("absences", 0))
            eliminated = absences > 3

            if eliminated:
                ds = examen = tp = 0

            moyenne = round(ds * 0.3 + examen * 0.5 + tp * 0.2, 2) if not eliminated else 0

            existing = db.grades.find_one({
                "student_id": g["student_id"],
                "subject": g["subject"],
                "semester": g.get("semester", "S1"),
            })

            grade_doc = {
                "student_id": g["student_id"],
                "institution_id": claims.get("institution_id"),
                "subject": g["subject"],
                "niveau": g.get("niveau", ""),
                "ds": ds,
                "examen": examen,
                "tp": tp,
                "moyenne": moyenne,
                "absences": absences,
                "eliminated": eliminated,
                "semester": g.get("semester", "S1"),
                "annee": g.get("annee", "2023-2024"),
                "posted_by": get_jwt_identity(),
                "updated_at": now.isoformat(),
            }

            if existing:
                db.grades.update_one({"_id": existing["_id"]}, {"$set": grade_doc})
                updated += 1
            else:
                db.grades.insert_one(grade_doc)
                inserted += 1

            # Notify student
            user = db.users.find_one({"id": {"$regex": g["student_id"]}})
            if user:
                db.notifications.insert_one({
                    "id": str(uuid.uuid4()),
                    "user_id": user["id"],
                    "type": "grade",
                    "title": f"Note publiée : {g['subject']}",
                    "message": f"Votre note de {g['subject']} a été mise à jour. Moyenne : {moyenne}/20",
                    "read": False,
                    "created_at": now.isoformat(),
                })

    return jsonify({"message": f"{inserted} notes ajoutées, {updated} mises à jour"})


# ── Stats ─────────────────────────────────────────────────────────────────────

@teacher_bp.get("/stats")
@jwt_required()
def get_stats():
    """Get summary stats for the teacher dashboard."""
    claims, err = _teacher_guard()
    if err:
        return err

    institution_id = claims.get("institution_id")
    db = get_db()

    stats = {"classes": 0, "students": 0, "courses": 0, "upcoming_exams": 0}

    if db is not None:
        # Count distinct niveaux
        niveaux = db.students.distinct("niveau", {"institution_id": institution_id})
        stats["classes"] = len(niveaux)
        stats["students"] = db.students.count_documents({"institution_id": institution_id})
        stats["courses"] = db.courses.count_documents({"institution_id": institution_id})
        stats["upcoming_exams"] = db.exams.count_documents({
            "institution_id": institution_id,
            "status": "upcoming",
        })

    return jsonify(stats)
