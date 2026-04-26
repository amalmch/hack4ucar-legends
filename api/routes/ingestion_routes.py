"""
api/routes/ingestion_routes.py
───────────────────────────────
Flask Blueprint pour l'ingestion de fichiers (PDF, Excel, CSV, images).
Utilise le pipeline_ingestion pour extraire, transformer et charger les KPIs.
"""
import os
import tempfile
import threading
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from loguru import logger
from datetime import datetime, timezone

from db.mongo import get_db, audit

ingestion_bp = Blueprint("ingestion", __name__)

SUPPORTED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv", ".png", ".jpg", ".jpeg", ".tiff"}


@ingestion_bp.post("/upload")
@jwt_required()
def ingest_file():
    """
    Upload et ingère un fichier (PDF, Excel, CSV, image).
    Le pipeline extrait les données, les nettoie via ETL, et les insère dans MongoDB.
    """
    claims = get_jwt()
    role = claims.get("role")
    if role not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    institution_id = request.form.get("institution_id") or claims.get("institution_id")
    periode = request.form.get("periode", "")
    doc_file = request.files.get("file")

    if not doc_file:
        return jsonify({"error": "Aucun fichier fourni"}), 400

    filename = doc_file.filename
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        return jsonify({
            "error": f"Type de fichier non supporté : {ext}",
            "formats_acceptes": list(SUPPORTED_EXTENSIONS),
        }), 400

    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    doc_file.save(tmp.name)
    tmp_path = tmp.name
    tmp.close()

    # Log the ingestion attempt
    db = get_db()
    ingestion_id = f"ing-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    if db is not None:
        db.ingestion_jobs.insert_one({
            "id": ingestion_id,
            "institution_id": institution_id,
            "filename": filename,
            "periode": periode,
            "status": "processing",
            "uploaded_by": claims.get("email"),
            "started_at": datetime.now(timezone.utc).isoformat(),
        })

    def process():
        try:
            from pipeline_ingestion.pipeline import run_single
            result = run_single(tmp_path, institution_id, periode)
            logger.info(f"Ingestion terminée : {result}")

            # Update job status with detailed result
            if db is not None:
                db.ingestion_jobs.update_one(
                    {"id": ingestion_id},
                    {"$set": {
                        "status": "completed",
                        "data_type": result.get("data_type", "unknown"),
                        "collection": result.get("collection", "kpi_ingested"),
                        "rows_processed": result.get("rows_processed", 0),
                        "result": result,
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }}
                )
        except Exception as e:
            logger.error(f"Erreur ingestion : {e}")
            if db is not None:
                db.ingestion_jobs.update_one(
                    {"id": ingestion_id},
                    {"$set": {
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }}
                )
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    thread = threading.Thread(target=process, daemon=True)
    thread.start()

    audit("FILE_INGESTION_STARTED", user_id=claims.get("sub"), details={
        "institution_id": institution_id, "filename": filename, "ingestion_id": ingestion_id,
    })

    return jsonify({
        "message": "Fichier reçu — détection automatique du type de données en cours",
        "ingestion_id": ingestion_id,
        "fichier": filename,
        "institution_id": institution_id,
    }), 202





@ingestion_bp.get("/jobs")
@jwt_required()
def list_ingestion_jobs():
    """Liste les jobs d'ingestion pour l'institution de l'utilisateur."""
    claims = get_jwt()
    role = claims.get("role")
    if role not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    institution_id = request.args.get("institution_id") or claims.get("institution_id")
    db = get_db()
    jobs = []

    if db is not None:
        query = {}
        if role != "superucaradmin":
            query["institution_id"] = institution_id
        jobs = list(db.ingestion_jobs.find(query, {"_id": 0}).sort("started_at", -1).limit(50))

    return jsonify({"jobs": jobs, "count": len(jobs)})


@ingestion_bp.get("/data")
@jwt_required()
def get_ingested_data():
    """Retourne les KPIs ingérés pour une institution."""
    claims = get_jwt()
    role = claims.get("role")
    if role not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    institution_id = request.args.get("institution_id") or claims.get("institution_id")
    domaine = request.args.get("domaine")
    db = get_db()
    records = []

    if db is not None:
        query = {"institution_id": institution_id}
        if domaine:
            query["domaine"] = domaine
        records = list(db.kpi_ingested.find(query, {"_id": 0}).sort("inserted_at", -1).limit(200))

    return jsonify({"records": records, "count": len(records)})


@ingestion_bp.get("/analyse/<institution_id>")
@jwt_required()
def analyse_institution(institution_id):
    """
    Analyse KPI temps réel : agrégation + détection d'anomalies.
    Utilise le moteur KPI MongoDB.
    """
    claims = get_jwt()
    role = claims.get("role")
    if role not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    periode = request.args.get("periode")

    try:
        from ai_models.kpi_engine import run_realtime_analysis
        result = run_realtime_analysis(institution_id, periode)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Erreur analyse KPI : {e}")
        return jsonify({"error": str(e)}), 500
