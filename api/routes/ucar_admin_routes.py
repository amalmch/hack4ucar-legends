"""
api/routes/ucar_admin_routes.py
────────────────────────────────
UCAR HQ Dashboard endpoints — accessible ONLY by superucaradmin.
Provides the global view across all 32 institutions.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from loguru import logger
from datetime import datetime, timezone

from db.mongo import get_db, audit

ucar_bp = Blueprint("ucar_admin", __name__)

UCAR_INSTITUTIONS = [
    ("UCAR-FSJPST", "Faculté des Sciences Juridiques, Politiques et Sociales de Tunis", "Tunis"),
    ("UCAR-FSB", "Faculté des Sciences de Bizerte", "Bizerte"),
    ("UCAR-FSEGN", "Faculté des Sciences Economiques et de Gestion de Nabeul", "Nabeul"),
    ("UCAR-ENAU", "Ecole Nationale d'Architecture et d'Urbanisme de Tunis", "Tunis"),
    ("UCAR-EPT", "Ecole Polytechnique de Tunisie", "Carthage"),
    ("UCAR-ESTI", "Ecole Supérieure de Technologie et d'Informatique à Carthage", "Carthage"),
    ("UCAR-ESSAI", "Ecole Supérieure des Statistiques et d'Analyse de l'Information", "Tunis"),
    ("UCAR-ESAC", "Ecole Supérieure de l'Audiovisuel et du Cinéma de Gammarth", "Gammarth"),
    ("UCAR-IPEIB", "Institut Préparatoire aux Etudes d'Ingénieur de Bizerte", "Bizerte"),
    ("UCAR-IHEC", "Institut des Hautes Etudes Commerciales de Carthage", "Carthage"),
    ("UCAR-INSAT", "Institut National des Sciences Appliquées et de Technologie", "Tunis"),
    ("UCAR-ISSATM", "Institut Supérieur des Sciences Appliquées et de la Technologie de Mateur", "Mateur"),
    ("UCAR-IPEIN", "Institut Préparatoire aux Etudes d'Ingénieur Nabeul", "Nabeul"),
    ("UCAR-IPEST", "Institut Préparatoire aux Etudes Scientifiques et Techniques de la Marsa", "La Marsa"),
    ("UCAR-ISBAN", "Institut Supérieur des Beaux Arts de Nabeul", "Nabeul"),
    ("UCAR-ISTEUB", "Institut Supérieur des Technologies de l'Environnement, de L'Urbanisme et du Bâtiment", "Tunis"),
    ("UCAR-ISLT", "Institut Supérieur des Langues de Tunis", "Tunis"),
    ("UCAR-ISLAIN", "Institut Supérieur des Langues Appliquées et d'Informatique de Nabeul", "Nabeul"),
    ("UCAR-ISSTE", "Institut Supérieur des Sciences et Technologies de l'Environnement de Borj Cédria", "Borj Cédria"),
    ("UCAR-ISCCB", "Institut Supérieur de Commerce et de Comptabilité de Bizerte", "Bizerte"),
    ("UCAR-ISEPBG", "Institut Supérieur des Etudes Préparatoires en Biologie et Géologie à Soukra", "Soukra"),
    ("UCAR-SUPCOM", "Sup'Com", "Ariana"),
    ("UCAR-ESAM", "Ecole Supérieure d'Agriculture de Mograne", "Mograne"),
    ("UCAR-ESAMateur", "Ecole Supérieure d'Agriculture de Mateur", "Mateur"),
    ("UCAR-ESIAT", "Ecole Supérieure des Industries Alimentaires de Tunis", "Tunis"),
    ("UCAR-ISPA", "Institut Supérieur de Pêche et d'Aquaculture de Bizerte", "Bizerte"),
    ("UCAR-INTES", "Institut National du Travail et des Etudes Sociales de Tunis", "Tunis"),
    ("UCAR-ISCE", "Institut Supérieur des Cadres de l'Enfance", "Carthage"),
    ("UCAR-INAT", "Institut National Agronomique de Tunisie", "Tunis"),
    ("UCAR-IHET", "Institut des Hautes Etudes Touristiques de Sidi Dhrif", "Sidi Dhrif"),
    ("UCAR-INRGREF", "Institut National de Recherche en Génie Rural, Eau et Forêt", "Ariana"),
    ("UCAR-INRAT", "Institut National de Recherche Agronomique de Tunis", "Ariana"),
]


def _require_superucaradmin():
    claims = get_jwt()
    if claims.get("role") != "superucaradmin":
        return jsonify({"error": "Accès réservé au Super Admin UCAR"}), 403
    return None


@ucar_bp.get("/overview")
@jwt_required()
def ucar_overview():
    err = _require_superucaradmin()
    if err: return err

    db = get_db()
    total_users = total_students = total_teachers = total_admins = 0
    total_pending = total_kpi = 0

    if db is not None:
        total_users    = db.users.count_documents({})
        total_students = db.students.count_documents({})
        total_teachers = db.teachers.count_documents({})
        total_admins   = db.users.count_documents({"role": "institution_admin"})
        total_pending  = db.users.count_documents({"status": "pending"})
        total_kpi      = db.kpi_records.count_documents({})

    # Build institution overview and global ESG metrics
    institutions = []
    global_esg = {
        "budget_alloue": 0,
        "budget_consomme": 0,
        "empreinte_carbone_tonnes": 0,
        "consommation_energie_kwh": 0,
        "taux_recyclage_avg": 0,
    }
    
    recyclage_total = 0
    recyclage_count = 0

    for inst_id, name, city in UCAR_INSTITUTIONS:
        inst_data = {"id": inst_id, "name": name, "city": city}
        if db is not None:
            inst_data["students"]   = db.students.count_documents({"institution_id": inst_id})
            inst_data["teachers"]   = db.teachers.count_documents({"institution_id": inst_id})
            latest_kpi = list(db.kpi_records.find(
                {"institution_id": inst_id}, {"_id": 0}
            ).sort("date", -1).limit(1))
            inst_data["latest_kpi"] = latest_kpi[0] if latest_kpi else {}
            
            if inst_data["latest_kpi"]:
                k = inst_data["latest_kpi"]
                global_esg["budget_alloue"] += k.get("budget_alloue", 0)
                global_esg["budget_consomme"] += k.get("budget_consomme", 0)
                global_esg["empreinte_carbone_tonnes"] += k.get("empreinte_carbone_tonnes", 0)
                global_esg["consommation_energie_kwh"] += k.get("consommation_energie_kwh", 0)
                if k.get("taux_recyclage") is not None:
                    recyclage_total += k["taux_recyclage"]
                    recyclage_count += 1
                    
        institutions.append(inst_data)

    if recyclage_count > 0:
        global_esg["taux_recyclage_avg"] = round(recyclage_total / recyclage_count, 2)

    audit("UCAR_OVERVIEW_ACCESS", user_id=get_jwt().get("sub"))

    return jsonify({
        "summary": {
            "total_institutions": len(UCAR_INSTITUTIONS),
            "total_users": total_users,
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_institution_admins": total_admins,
            "pending_approvals": total_pending,
            "kpi_records": total_kpi,
            "global_esg": global_esg,
        },
        "institutions": institutions,
    })


@ucar_bp.get("/users/pending")
@jwt_required()
def get_pending_users():
    err = _require_superucaradmin()
    if err: return err

    db = get_db()
    pending = []
    if db is not None:
        pending = list(db.users.find(
            {"status": "pending"},
            {"_id": 0, "password_hash": 0}
        ).sort("created_at", -1).limit(50))
    else:
        pending = [u for u in _get_fallback_users() if u.get("status") == "pending"]

    return jsonify({"pending_users": pending, "count": len(pending)})


@ucar_bp.post("/users/<user_id>/approve")
@jwt_required()
def approve_user(user_id):
    err = _require_superucaradmin()
    if err: return err

    admin_claims = get_jwt()
    db = get_db()
    if db is not None:
        result = db.users.update_one(
            {"id": user_id},
            {"$set": {"status": "approved", "approved_by": admin_claims.get("email"), "approved_at": datetime.now(timezone.utc).isoformat()}}
        )
        if result.matched_count == 0:
            return jsonify({"error": "Utilisateur introuvable"}), 404

    audit("USER_APPROVED", user_id=admin_claims.get("sub"), details={"target_user_id": user_id})
    return jsonify({"message": "Compte approuvé avec succès", "user_id": user_id})


@ucar_bp.post("/users/<user_id>/reject")
@jwt_required()
def reject_user(user_id):
    err = _require_superucaradmin()
    if err: return err

    admin_claims = get_jwt()
    reason = (request.get_json() or {}).get("reason", "Document non valide")
    db = get_db()
    if db is not None:
        db.users.update_one(
            {"id": user_id},
            {"$set": {"status": "rejected", "rejection_reason": reason, "rejected_by": admin_claims.get("email")}}
        )

    audit("USER_REJECTED", user_id=admin_claims.get("sub"), details={"target_user_id": user_id, "reason": reason})
    return jsonify({"message": "Compte refusé", "user_id": user_id, "reason": reason})


@ucar_bp.get("/institutions")
@jwt_required()
def list_institutions():
    err = _require_superucaradmin()
    if err: return err

    return jsonify({
        "institutions": [{"id": i, "name": n, "city": c} for i, n, c in UCAR_INSTITUTIONS],
        "count": len(UCAR_INSTITUTIONS),
    })


@ucar_bp.get("/reports")
@jwt_required()
def all_reports():
    err = _require_superucaradmin()
    if err: return err

    db = get_db()
    reports = []
    if db is not None:
        reports = list(db.reports.find({}, {"_id": 0}).sort("created_at", -1).limit(100))

    return jsonify({"reports": reports, "count": len(reports)})


@ucar_bp.get("/audit-log")
@jwt_required()
def get_audit_log():
    err = _require_superucaradmin()
    if err: return err

    db = get_db()
    logs = []
    if db is not None:
        logs = list(db.audit_log.find({}, {"_id": 0}).sort("timestamp", -1).limit(200))

    return jsonify({"audit_log": logs, "count": len(logs)})


def _get_fallback_users():
    from api.routes.auth_routes import _user_store_fallback
    return list(_user_store_fallback.values())
