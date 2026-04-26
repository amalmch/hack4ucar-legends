"""
ai_models/kpi_engine.py
────────────────────────
Moteur KPI temps réel pour UCAR — adapté pour MongoDB.
Calcule, agrège et détecte les anomalies sur les valeurs KPI.

Remplace la version PostgreSQL originale par des requêtes MongoDB
utilisant le singleton db/mongo.py du projet.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

FEATURES = ["taux_reussite", "taux_abandon", "budget_execute_pct", "nb_inscrits", "ratio_mf"]
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "isolation_forest")


# ── Chargement des modèles Isolation Forest ──────────────────────────────────

_model_cache: dict = {}


def load_model(institution_code: Optional[str] = None):
    """Charge le modèle Isolation Forest (global ou par institution), mis en cache."""
    try:
        import joblib
    except ImportError:
        logger.warning("joblib non installé — détection d'anomalies par seuils uniquement")
        return None, None

    suffix = f"_{institution_code}" if institution_code else "_global"
    if suffix in _model_cache:
        return _model_cache[suffix]

    model_path  = os.path.join(MODEL_DIR, f"model{suffix}.pkl")
    scaler_path = os.path.join(MODEL_DIR, f"scaler{suffix}.pkl")

    if not os.path.exists(model_path):
        logger.warning(f"Modèle '{suffix}' introuvable, fallback sur global")
        suffix = "_global"
        model_path  = os.path.join(MODEL_DIR, "model_global.pkl")
        scaler_path = os.path.join(MODEL_DIR, "scaler_global.pkl")

    if not os.path.exists(model_path):
        logger.info("Aucun modèle Isolation Forest trouvé — utilisation des seuils statistiques")
        return None, None

    try:
        model  = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        _model_cache[suffix] = (model, scaler)
        logger.info(f"Modèle chargé : {model_path}")
        return model, scaler
    except Exception as e:
        logger.error(f"Impossible de charger le modèle : {e}")
        return None, None


# ── Requêtes MongoDB ─────────────────────────────────────────────────────────

def fetch_kpis_for_institution(institution_id: str, periode: Optional[str] = None) -> list:
    """Récupère les KPI d'une institution depuis MongoDB."""
    from db.mongo import get_db
    db = get_db()
    if db is None:
        return []

    # Merge data from kpi_records (seeded admin data) + kpi_ingested (pipeline data)
    all_kpis = []

    # 1. From kpi_records (seeded admin CSV data)
    query = {"institution_id": institution_id}
    if periode:
        query["date"] = {"$regex": f"^{periode}"}

    for rec in db.kpi_records.find(query, {"_id": 0}):
        # Convert flat kpi_record into individual KPI entries
        kpi_fields = {
            "taux_reussite":           ("academique", "Taux de réussite"),
            "taux_abandon":            ("academique", "Taux d'abandon"),
            "budget_execute_pct":      ("finance",    "Budget exécuté (%)"),
            "cout_par_etudiant":       ("finance",    "Coût par étudiant"),
            "empreinte_carbone_tonnes":("esg",        "Empreinte carbone"),
            "consommation_energie_kwh":("esg",        "Consommation énergie"),
            "taux_recyclage":          ("esg",        "Taux de recyclage"),
            "nb_enseignants_permanents":("rh",        "Enseignants permanents"),
            "taux_encadrement":        ("academique", "Taux d'encadrement"),
        }
        for field_name, (domaine, label) in kpi_fields.items():
            val = rec.get(field_name)
            if val is not None:
                try:
                    all_kpis.append({
                        "institution_id": institution_id,
                        "kpi_nom": label,
                        "domaine": domaine,
                        "valeur": float(val),
                        "periode": rec.get("date", ""),
                    })
                except (ValueError, TypeError):
                    pass

    # 2. From kpi_ingested (pipeline-ingested data)
    ing_query = {"institution_id": institution_id}
    if periode:
        ing_query["periode"] = periode
    for rec in db.kpi_ingested.find(ing_query, {"_id": 0}).sort("inserted_at", -1).limit(200):
        all_kpis.append({
            "institution_id": institution_id,
            "kpi_nom": rec.get("nom_kpi", ""),
            "domaine": rec.get("domaine", "autre"),
            "valeur": float(rec.get("valeur", 0)),
            "periode": rec.get("periode", ""),
        })

    return all_kpis


def fetch_latest_kpi_snapshot(institution_id: str) -> dict:
    """Retourne le dernier snapshot KPI (une valeur par nom de KPI)."""
    from db.mongo import get_db
    db = get_db()
    if db is None:
        return {}

    snapshot = {}

    # From kpi_records (seeded data)
    latest = db.kpi_records.find_one(
        {"institution_id": institution_id},
        {"_id": 0},
        sort=[("date", -1)]
    )
    if latest:
        field_map = {
            "taux_reussite": "taux_reussite",
            "taux_abandon": "taux_abandon",
            "budget_execute_pct": "budget_execute_pct",
            "nb_inscrits": "nb_inscrits",
            "ratio_mf": "ratio_mf",
            "empreinte_carbone_tonnes": "empreinte_carbone_tonnes",
            "consommation_energie_kwh": "consommation_energie_kwh",
        }
        for mongo_field, feature_name in field_map.items():
            val = latest.get(mongo_field)
            if val is not None:
                try:
                    snapshot[feature_name] = {
                        "valeur": float(val),
                        "periode": latest.get("date", ""),
                    }
                except (ValueError, TypeError):
                    pass

    # Merge with kpi_ingested (pipeline data takes priority if newer)
    for rec in db.kpi_ingested.find(
        {"institution_id": institution_id}, {"_id": 0}
    ).sort("inserted_at", -1).limit(50):
        nom = rec.get("nom_kpi", "")
        if nom and nom not in snapshot:
            snapshot[nom] = {
                "valeur": float(rec.get("valeur", 0)),
                "periode": rec.get("periode", ""),
            }

    return snapshot


# ── Calculs KPI ──────────────────────────────────────────────────────────────

def compute_tendance(valeurs: list) -> str:
    """Retourne 'hausse' | 'baisse' | 'stable' sur une série."""
    if len(valeurs) < 2:
        return "stable"
    delta = valeurs[-1] - valeurs[0]
    pct = abs(delta) / (abs(valeurs[0]) + 1e-9)
    if pct < 0.02:
        return "stable"
    return "hausse" if delta > 0 else "baisse"


def compute_variation(v_actuelle: float, v_precedente: float) -> float:
    """Variation en % entre deux valeurs."""
    if v_precedente == 0:
        return 0.0
    return round((v_actuelle - v_precedente) / abs(v_precedente) * 100, 2)


def aggregate_by_domaine(kpis: list) -> dict:
    """Agrège les KPIs par domaine."""
    agregats: dict = {}
    for kpi in kpis:
        domaine = kpi.get("domaine", "autre")
        if domaine not in agregats:
            agregats[domaine] = {"nb_kpis": 0, "total": 0.0, "kpis": []}
        agregats[domaine]["nb_kpis"] += 1
        agregats[domaine]["total"] += float(kpi.get("valeur", 0))
        agregats[domaine]["kpis"].append(kpi.get("kpi_nom", ""))
    for d, data in agregats.items():
        data["moyenne"] = round(data["total"] / data["nb_kpis"], 4) if data["nb_kpis"] else 0
        del data["total"]
    return agregats


# ── Détection d'anomalies ────────────────────────────────────────────────────

# Seuils statistiques par défaut (utilisés si aucun modèle ML n'est chargé)
KPI_THRESHOLDS = {
    "taux_reussite":      {"seuil_alerte": 0.50, "seuil_critique": 0.30, "direction": "below"},
    "taux_abandon":       {"seuil_alerte": 0.25, "seuil_critique": 0.40, "direction": "above"},
    "budget_execute_pct": {"seuil_alerte": 0.50, "seuil_critique": 0.30, "direction": "below"},
}


def detect_anomalies(snapshot: dict, institution_code: Optional[str] = None) -> dict:
    """
    Détecte les anomalies via Isolation Forest (si modèle disponible)
    ou par seuils statistiques (fallback).
    """
    model, scaler = load_model(institution_code)

    # If we have a trained model, use it
    if model is not None and scaler is not None:
        feature_vector = []
        missing = []
        for f in FEATURES:
            kpi_data = snapshot.get(f)
            if kpi_data is None:
                missing.append(f)
                feature_vector.append(0.0)
            else:
                feature_vector.append(float(kpi_data["valeur"]))

        X = np.array(feature_vector).reshape(1, -1)
        X_scaled = scaler.transform(X)
        prediction = model.predict(X_scaled)[0]
        score = float(model.score_samples(X_scaled)[0])

        return {
            "is_anomalie": bool(prediction == -1),
            "score_anomalie": round(score, 4),
            "methode": "isolation_forest",
            "features_manquantes": missing,
            "valeurs_utilisees": dict(zip(FEATURES, feature_vector)),
        }

    # Fallback: threshold-based anomaly detection
    alertes = []
    for kpi_name, thresholds in KPI_THRESHOLDS.items():
        kpi_data = snapshot.get(kpi_name)
        if kpi_data is None:
            continue
        valeur = float(kpi_data["valeur"])
        direction = thresholds["direction"]

        if direction == "below":
            if valeur < thresholds["seuil_critique"]:
                alertes.append({"kpi": kpi_name, "valeur": valeur, "niveau": "critical"})
            elif valeur < thresholds["seuil_alerte"]:
                alertes.append({"kpi": kpi_name, "valeur": valeur, "niveau": "warning"})
        elif direction == "above":
            if valeur > thresholds["seuil_critique"]:
                alertes.append({"kpi": kpi_name, "valeur": valeur, "niveau": "critical"})
            elif valeur > thresholds["seuil_alerte"]:
                alertes.append({"kpi": kpi_name, "valeur": valeur, "niveau": "warning"})

    return {
        "is_anomalie": len(alertes) > 0,
        "score_anomalie": -0.5 if alertes else 0.1,
        "methode": "seuils_statistiques",
        "alertes_seuils": alertes,
        "valeurs_utilisees": {
            f: float(snapshot[f]["valeur"]) for f in FEATURES if f in snapshot
        },
    }


def check_thresholds(institution_id: str, snapshot: dict) -> list:
    """Compare le snapshot KPI avec les seuils configurés."""
    alertes = []
    for kpi_name, thresholds in KPI_THRESHOLDS.items():
        kpi_data = snapshot.get(kpi_name)
        if kpi_data is None:
            continue
        valeur = float(kpi_data["valeur"])
        direction = thresholds["direction"]

        if direction == "below":
            if valeur < thresholds["seuil_critique"]:
                alertes.append({
                    "kpi_nom": kpi_name, "valeur": valeur,
                    "seuil": thresholds["seuil_critique"], "niveau": "critical",
                })
            elif valeur < thresholds["seuil_alerte"]:
                alertes.append({
                    "kpi_nom": kpi_name, "valeur": valeur,
                    "seuil": thresholds["seuil_alerte"], "niveau": "warning",
                })
        elif direction == "above":
            if valeur > thresholds["seuil_critique"]:
                alertes.append({
                    "kpi_nom": kpi_name, "valeur": valeur,
                    "seuil": thresholds["seuil_critique"], "niveau": "critical",
                })
            elif valeur > thresholds["seuil_alerte"]:
                alertes.append({
                    "kpi_nom": kpi_name, "valeur": valeur,
                    "seuil": thresholds["seuil_alerte"], "niveau": "warning",
                })
    return alertes


# ── Fonction principale ──────────────────────────────────────────────────────

def run_realtime_analysis(institution_id: str, periode: Optional[str] = None) -> dict:
    """
    Analyse complète temps réel pour une institution :
    1. Snapshot KPI depuis MongoDB
    2. Agrégation par domaine
    3. Détection d'anomalies (Isolation Forest ou seuils)
    4. Vérification des seuils

    Returns:
        dict avec snapshot, agrégats, anomalies, alertes
    """
    snapshot  = fetch_latest_kpi_snapshot(institution_id)
    kpis_list = fetch_kpis_for_institution(institution_id, periode)

    agregats = aggregate_by_domaine(kpis_list)
    anomalie = detect_anomalies(snapshot, institution_id)
    alertes  = check_thresholds(institution_id, snapshot)

    return {
        "institution_id":   institution_id,
        "analyse_a":        datetime.now(timezone.utc).isoformat(),
        "periode":          periode,
        "nb_kpis":          len(snapshot),
        "snapshot":         snapshot,
        "agregats_domaine": agregats,
        "anomalie":         anomalie,
        "alertes":          alertes,
        "nb_alertes":       len(alertes),
    }
