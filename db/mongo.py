"""
db/mongo.py
────────────
MongoDB connection singleton for the UCAR platform.
Connects to localhost:27017 by default (or MONGO_URI env var).

Collections:
  users           — all accounts (students, teachers, admins)
  institutions    — 32 UCAR institutions master data
  students        — student records per institution
  teachers        — teacher records per institution
  kpi_records     — KPI time-series data
  documents       — uploaded identity / institutional documents
  reports         — generated reports metadata
  audit_log       — immutable audit trail
"""
import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure
from loguru import logger

_client = None
_db = None

def get_db():
    """Return the UCAR MongoDB database (lazy singleton)."""
    global _client, _db
    if _db is not None:
        return _db

    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    try:
        _client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        _client.admin.command("ping")   # test connection
        _db = _client["ucar_platform"]
        _create_indexes(_db)
        logger.info(f"✅ MongoDB connected: {uri}/ucar_platform")
    except ConnectionFailure as e:
        logger.warning(f"⚠️  MongoDB unavailable ({e}) — using in-memory fallback")
        _db = None

    return _db


def _create_indexes(db):
    """Ensure indexes exist for fast queries."""
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.users.create_index([("role", ASCENDING)])
    db.users.create_index([("status", ASCENDING)])
    db.students.create_index([("institution_id", ASCENDING)])
    db.students.create_index([("student_id", ASCENDING)])
    db.teachers.create_index([("institution_id", ASCENDING)])
    db.kpi_records.create_index([("institution_id", ASCENDING), ("date", DESCENDING)])
    db.documents.create_index([("user_id", ASCENDING)])
    db.audit_log.create_index([("timestamp", DESCENDING)])
    db.reports.create_index([("institution_id", ASCENDING), ("created_at", DESCENDING)])
    # Ingestion pipeline collections
    db.kpi_ingested.create_index([("institution_id", ASCENDING), ("nom_kpi", ASCENDING), ("periode", ASCENDING)])
    db.kpi_ingested.create_index([("inserted_at", DESCENDING)])
    db.ingestion_jobs.create_index([("institution_id", ASCENDING), ("started_at", DESCENDING)])
    db.kpi_rejected.create_index([("rejected_at", DESCENDING)])
    # Teacher / Student portal collections
    db.grades.create_index([("student_id", ASCENDING), ("subject", ASCENDING)])
    db.grades.create_index([("institution_id", ASCENDING), ("niveau", ASCENDING)])
    db.exams.create_index([("institution_id", ASCENDING), ("date", ASCENDING)])
    db.courses.create_index([("institution_id", ASCENDING), ("subject", ASCENDING)])
    db.student_requests.create_index([("student_id", ASCENDING), ("created_at", DESCENDING)])
    db.notifications.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    db.notifications.create_index([("user_id", ASCENDING), ("read", ASCENDING)])


def audit(action: str, user_id: str = None, details: dict = None):
    """Write an immutable audit log entry."""
    from datetime import datetime, timezone
    db = get_db()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user_id": user_id,
        "details": details or {},
    }
    if db is not None:
        db.audit_log.insert_one(entry)
    logger.info(f"AUDIT | {action} | user={user_id} | {details}")


def is_available() -> bool:
    return _db is not None
