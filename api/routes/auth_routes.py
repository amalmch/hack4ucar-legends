"""
api/routes/auth_routes.py
──────────────────────────
Authentication blueprint with MongoDB persistence + AI identity verification.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
import uuid, base64
from datetime import datetime, timezone
from loguru import logger

from db.mongo import get_db, audit

auth_bp = Blueprint("auth", __name__)

# In-memory fallback if MongoDB is down
_user_store_fallback = {}

# Pre-seed a superucaradmin so demo works even without MongoDB
_SEED_ADMIN = {
    "id": "superadmin-001",
    "email": "admin@ucar.tn",
    "password_hash": None,   # will be set on first import
    "name": "UCAR Super Admin",
    "role": "superucaradmin",
    "status": "approved",
    "institution_id": None,
}


def _get_collection():
    db = get_db()
    return db.users if db is not None else None


def _ensure_seed_admin():
    """Ensure at least one superucaradmin exists."""
    from werkzeug.security import generate_password_hash
    col = _get_collection()
    if col is not None:
        if col.count_documents({"role": "superucaradmin"}) == 0:
            seed = dict(_SEED_ADMIN)
            seed["password_hash"] = generate_password_hash("Admin@2025!")
            col.insert_one(seed)
            logger.info("Seeded superucaradmin: admin@ucar.tn / Admin@2025!")
    else:
        # fallback
        if "admin@ucar.tn" not in _user_store_fallback:
            seed = dict(_SEED_ADMIN)
            seed["password_hash"] = generate_password_hash("Admin@2025!")
            _user_store_fallback["admin@ucar.tn"] = seed


@auth_bp.record_once
def on_blueprint_init(state):
    _ensure_seed_admin()


@auth_bp.post("/register")
def register():
    # Support multipart (with document file) or JSON
    if request.content_type and "multipart" in request.content_type:
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")
        institution_id = request.form.get("institution_id", "")
        niveau = request.form.get("niveau", "")
        doc_file = request.files.get("document")
        image_data = doc_file.read() if doc_file else None
    else:
        data = request.get_json() or {}
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        role = data.get("role")
        institution_id = data.get("institution_id", "")
        niveau = data.get("niveau", "")
        image_data = None

    # Validation
    if not all([name, email, password, role]):
        return jsonify({"error": "Champs obligatoires manquants"}), 400

    valid_roles = ["student", "teacher", "institution_admin", "superucaradmin"]
    if role not in valid_roles:
        return jsonify({"error": f"Rôle invalide. Valeurs: {valid_roles}"}), 400

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    user_doc = {
        "id": user_id,
        "email": email,
        "password_hash": generate_password_hash(password),
        "name": name,
        "role": role,
        "institution_id": institution_id,
        "niveau": niveau,
        "status": "pending",      # starts as pending
        "created_at": now,
        "verification_result": None,
        "document_stored": False,
    }

    col = _get_collection()

    # Check duplicate
    if col is not None:
        if col.find_one({"email": email}):
            return jsonify({"error": "Un compte avec cet email existe déjà"}), 409
    else:
        if email in _user_store_fallback:
            return jsonify({"error": "Un compte avec cet email existe déjà"}), 409

    # Run AI identity verification if document provided
    verification_result = None
    if image_data:
        try:
            from ai_models.identity_verifier import verify_document
            db = get_db()
            verification_result = verify_document(
                image_data=image_data,
                declared_name=name,
                declared_institution=institution_id,
                db=db
            )
            user_doc["verification_result"] = verification_result
            user_doc["status"] = verification_result["status"]

            # Store document in MongoDB as base64
            if col is not None:
                db.documents.insert_one({
                    "user_id": user_id,
                    "type": "identity_document",
                    "data": base64.b64encode(image_data).decode(),
                    "uploaded_at": now,
                    "verification": verification_result,
                })
                user_doc["document_stored"] = True
        except Exception as e:
            logger.error(f"Identity verification error: {e}")
            user_doc["status"] = "pending"
    else:
        # No document = always pending
        user_doc["status"] = "pending"

    # Save user
    if col is not None:
        col.insert_one(user_doc)
    else:
        _user_store_fallback[email] = user_doc

    audit("USER_REGISTER", user_id=user_id, details={"email": email, "role": role, "status": user_doc["status"]})

    return jsonify({
        "message": "Compte créé avec succès",
        "user_id": user_id,
        "status": user_doc["status"],
        "verification": verification_result,
    }), 201


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400

    col = _get_collection()
    if col is not None:
        user = col.find_one({"email": email}, {"_id": 0})
    else:
        user = _user_store_fallback.get(email)

    if not user:
        return jsonify({"error": "Identifiants incorrects"}), 401

    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Identifiants incorrects"}), 401

    if user.get("status") not in ("approved",):
        status = user.get("status", "pending")
        msgs = {
            "pending": "Votre compte est en attente de vérification. Un administrateur UCAR examinera votre dossier.",
            "rejected": "Votre demande d'accès a été refusée. Contactez l'administration UCAR.",
        }
        return jsonify({"error": msgs.get(status, "Accès refusé"), "status": status}), 403

    token = create_access_token(
        identity=user["id"],
        additional_claims={
            "role": user["role"],
            "email": user["email"],
            "name": user["name"],
            "institution_id": user.get("institution_id", ""),
        }
    )

    audit("USER_LOGIN", user_id=user["id"], details={"email": email, "role": user["role"]})

    return jsonify({
        "message": "Connexion réussie",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "institution_id": user.get("institution_id", ""),
        }
    }), 200


@auth_bp.get("/me")
@jwt_required()
def get_me():
    claims = get_jwt()
    user_id = get_jwt_identity()
    col = _get_collection()
    user_data = None
    
    if col is not None:
        user_data = col.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    
    if not user_data:
        # Fallback to claims if user not in DB or DB is down
        user_data = {
            "id": user_id,
            "name": claims.get("name"),
            "email": claims.get("email"),
            "role": claims.get("role"),
            "institution_id": claims.get("institution_id", ""),
        }
        
    return jsonify(user_data), 200


@auth_bp.put("/profile")
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    # Only allow updating specific fields
    allowed_fields = ["name", "phone", "bio", "profile_image"]
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not update_data:
        return jsonify({"error": "Aucune donnée valide à mettre à jour"}), 400
        
    col = _get_collection()
    if col is not None:
        col.update_one({"id": user_id}, {"$set": update_data})
        
        # Also update fallback store if needed
        for email, u in _user_store_fallback.items():
            if u["id"] == user_id:
                u.update(update_data)
                
    audit("USER_PROFILE_UPDATE", user_id=user_id, details={"fields": list(update_data.keys())})
    return jsonify({"message": "Profil mis à jour avec succès", "updated": update_data}), 200
