"""
api/routes/ — All Binôme B Flask Blueprints
============================================

Blueprints:
  kpi_bp        GET  /api/kpi/latest, /api/kpi/history, /api/kpi/aggregate
  anomaly_bp    GET  /api/anomalies, POST /api/anomalies/run
  prediction_bp GET  /api/predictions, POST /api/predictions/run
  xai_bp        GET  /api/xai/explain
  report_bp     POST /api/reports/generate, GET /api/reports/<id>
  alert_bp      GET  /api/alerts, POST /api/alerts/generate
  internal_bp   POST /internal/kpi/ingest   (Binôme A sync)
"""

# ══════════════════════════════════════════════════════════
#  kpi_routes.py
# ══════════════════════════════════════════════════════════
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from loguru import logger
import pandas as pd
from datetime import datetime, timedelta

kpi_bp = Blueprint("kpi", __name__)

# In-memory KPI store (replace with DB in prod)
_kpi_store: list[dict] = []


@kpi_bp.get("/latest")
@jwt_required()
def get_latest_kpi():
    """Return the most recent KPI snapshot (global or per institution)."""
    institution_id = request.args.get("institution_id")
    data = _kpi_store
    if institution_id:
        data = [d for d in data if d.get("institution_id") == institution_id]
    latest = data[-50:] if data else []
    return jsonify({"kpis": latest, "count": len(latest)})


@kpi_bp.get("/history")
@jwt_required()
def get_kpi_history():
    """Return KPI history with optional date filters."""
    institution_id = request.args.get("institution_id")
    days = int(request.args.get("days", 30))
    metric = request.args.get("metric")

    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    data = [
        d for d in _kpi_store
        if d.get("timestamp", "") >= cutoff
        and (not institution_id or d.get("institution_id") == institution_id)
        and (not metric or metric in d)
    ]
    return jsonify({"history": data, "count": len(data), "days": days})


@kpi_bp.get("/aggregate")
@jwt_required()
def get_kpi_aggregate():
    """Return aggregated KPI stats (mean, min, max) across institutions."""
    if not _kpi_store:
        return jsonify({"message": "No KPI data available"}), 404

    df = pd.DataFrame(_kpi_store)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    agg = df[numeric_cols].describe().round(4).to_dict()
    return jsonify({"aggregate": agg, "institutions": df["institution_id"].nunique() if "institution_id" in df else 0})


# ══════════════════════════════════════════════════════════
#  anomaly_routes.py
# ══════════════════════════════════════════════════════════

anomaly_bp = Blueprint("anomaly", __name__)
_anomaly_results: list[dict] = []


@anomaly_bp.get("")
@jwt_required()
def get_anomalies():
    """List all detected anomalies, filterable by severity/institution."""
    severity = request.args.get("severity")
    institution_id = request.args.get("institution_id")
    limit = int(request.args.get("limit", 50))

    results = _anomaly_results
    if severity:
        results = [r for r in results if r.get("severity") == severity]
    if institution_id:
        results = [r for r in results if r.get("institution_id") == institution_id]

    return jsonify({
        "anomalies": results[-limit:],
        "count": len(results),
        "critical": sum(1 for r in results if r.get("severity") == "critical"),
        "warning": sum(1 for r in results if r.get("severity") == "warning"),
    })


@anomaly_bp.post("/run")
@jwt_required()
def run_anomaly_detection():
    """
    Trigger anomaly detection on the latest KPI data.
    
    Body (optional): {"institution_id": "...", "method": "isolation_forest"|"zscore"}
    """
    from ai_models.anomaly.detector import AnomalyDetector
    from ai_models.xai.explainer import XAIExplainer

    if not _kpi_store:
        return jsonify({"error": "No KPI data ingested yet"}), 400

    body = request.get_json(silent=True) or {}
    institution_id = body.get("institution_id")
    data = _kpi_store
    if institution_id:
        data = [d for d in data if d.get("institution_id") == institution_id]

    try:
        df = pd.DataFrame(data)
        detector = AnomalyDetector()

        # Fit on first run, detect on subsequent
        try:
            detector._load()
        except FileNotFoundError:
            detector.fit(df)

        df_result = detector.detect(df)
        anomalies = df_result[df_result["is_anomaly"]].to_dict(orient="records")

        _anomaly_results.clear()
        _anomaly_results.extend(anomalies)

        summary = detector.summary(df_result)
        logger.info(f"Anomaly detection complete: {summary}")
        return jsonify({"status": "done", "summary": summary})

    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════
#  prediction_routes.py
# ══════════════════════════════════════════════════════════

prediction_bp = Blueprint("prediction", __name__)
_prediction_results: list[dict] = []


@prediction_bp.get("")
@jwt_required()
def get_predictions():
    """Return cached prediction results."""
    metric = request.args.get("metric")
    results = _prediction_results
    if metric:
        results = [r for r in results if r.get("metric") == metric]
    return jsonify({"predictions": results, "count": len(results)})


@prediction_bp.post("/run")
@jwt_required()
def run_predictions():
    """
    Run time-series forecasts for all KPIs.
    
    Body: {"metric": "taux_reussite", "horizon": 30, "method": "prophet", "institution_id": "..."}
    """
    from ai_models.prediction.forecaster import KPIForecaster

    if not _kpi_store:
        return jsonify({"error": "No KPI data ingested yet"}), 400

    body = request.get_json(silent=True) or {}
    method = body.get("method", "prophet")
    horizon = int(body.get("horizon", 30))
    metric = body.get("metric")          # None = all metrics
    institution_id = body.get("institution_id")

    try:
        df = pd.DataFrame(_kpi_store)
        forecaster = KPIForecaster(method=method)

        if metric:
            results = [forecaster.forecast(df, metric, horizon, institution_id)]
        else:
            results = forecaster.forecast_all(df, horizon, institution_id)

        _prediction_results.clear()
        _prediction_results.extend(results)

        alert_count = sum(1 for r in results if r.get("alert"))
        return jsonify({
            "status": "done",
            "metrics_forecasted": len(results),
            "alerts": alert_count,
            "predictions": results,
        })

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════
#  xai_routes.py
# ══════════════════════════════════════════════════════════

xai_bp = Blueprint("xai", __name__)


@xai_bp.get("/explain")
@jwt_required()
def explain_anomaly():
    """
    Return SHAP explanation for a specific anomaly row.
    
    Query: ?row_index=5&method=shap&top_n=5
    """
    row_index = int(request.args.get("row_index", 0))
    method = request.args.get("method", "shap")
    top_n = int(request.args.get("top_n", 5))

    if not _anomaly_results:
        return jsonify({"error": "Run anomaly detection first"}), 400

    if row_index >= len(_anomaly_results):
        return jsonify({"error": f"row_index {row_index} out of range"}), 400

    anomaly_row = _anomaly_results[row_index]
    # Return pre-computed explanation if available
    explanation = anomaly_row.get("explanation", {
        "summary_fr": "Explication non disponible — relancer la détection avec XAI activé.",
        "top_features": [],
    })

    return jsonify({
        "row_index": row_index,
        "institution_id": anomaly_row.get("institution_id"),
        "severity": anomaly_row.get("severity"),
        "explanation": explanation,
    })


@xai_bp.post("/explain/batch")
@jwt_required()
def explain_batch():
    """Trigger full XAI on all anomalies and store results."""
    from ai_models.anomaly.detector import AnomalyDetector, KPI_FEATURES
    from ai_models.xai.explainer import XAIExplainer
    import numpy as np

    if not _kpi_store or not _anomaly_results:
        return jsonify({"error": "Run anomaly detection first"}), 400

    try:
        df = pd.DataFrame(_kpi_store)
        feature_cols = [c for c in KPI_FEATURES if c in df.columns]
        X = df[feature_cols].fillna(df[feature_cols].median()).values

        detector = AnomalyDetector()
        detector._load()

        explainer = XAIExplainer(
            model=detector.iso_forest,
            X_train=detector.scaler.transform(X),
            feature_names=feature_cols,
            model_type="isolation_forest",
        )
        explainer.setup_shap()

        anomaly_mask = [r.get("is_anomaly", True) for r in _anomaly_results]
        X_anomaly = X[:len(anomaly_mask)]

        explanations = explainer.explain_batch(X_anomaly, anomaly_mask)

        # Attach to anomaly results
        for exp in explanations:
            idx = exp.get("row_index", -1)
            if 0 <= idx < len(_anomaly_results):
                _anomaly_results[idx]["explanation"] = exp

        return jsonify({"status": "done", "explained": len(explanations)})

    except Exception as e:
        logger.error(f"XAI batch failed: {e}")
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════
#  report_routes.py
# ══════════════════════════════════════════════════════════

import uuid as _uuid
report_bp = Blueprint("report", __name__)
_reports_store: dict[str, dict] = {}


@report_bp.post("/generate")
@jwt_required()
def generate_report():
    """
    Generate a full AI-written report (PDF, Excel, or JSON).
    
    Body: {"institution_name": "...", "format": "json|pdf|excel", "use_llm": true}
    """
    from reports.alert_generator import generate_report as gen

    body = request.get_json(silent=True) or {}
    institution_name = body.get("institution_name", "UCAR Global")
    fmt = body.get("format", "json")
    use_llm = bool(body.get("use_llm", True))

    kpi_snapshot = _kpi_store[-1] if _kpi_store else {}

    try:
        report = gen(
            kpi_data=kpi_snapshot,
            anomalies=_anomaly_results,
            predictions=_prediction_results,
            institution_name=institution_name,
            format=fmt,
            use_llm=use_llm,
        )
        report_id = str(_uuid.uuid4())
        _reports_store[report_id] = report
        return jsonify({"report_id": report_id, "report": report})

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return jsonify({"error": str(e)}), 500


@report_bp.get("/<report_id>")
@jwt_required()
def get_report(report_id: str):
    """Retrieve a previously generated report."""
    report = _reports_store.get(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report)


# ══════════════════════════════════════════════════════════
#  alert_routes.py
# ══════════════════════════════════════════════════════════

alert_bp = Blueprint("alert", __name__)
_alert_store: list[dict] = []


@alert_bp.get("")
@jwt_required()
def get_alerts():
    """List all active alerts."""
    severity = request.args.get("severity")
    institution_id = request.args.get("institution_id")
    alerts = _alert_store
    if severity:
        alerts = [a for a in alerts if a.get("severity") == severity]
    if institution_id:
        alerts = [a for a in alerts if a.get("institution") == institution_id]
    return jsonify({"alerts": alerts[-100:], "count": len(alerts)})


@alert_bp.post("/generate")
@jwt_required()
def generate_alerts():
    """Generate AI alerts for all current anomalies."""
    from reports.alert_generator import alert_message

    _alert_store.clear()
    generated = 0

    for anomaly in _anomaly_results:
        if anomaly.get("severity") not in ("critical", "warning"):
            continue
        for metric in ["taux_reussite", "taux_abandon", "budget_execute_pct"]:
            if anomaly.get(metric) is None:
                continue
            try:
                alert = alert_message(
                    institution_name=anomaly.get("institution_id", "Inconnu"),
                    metric=metric,
                    current_value=float(anomaly[metric]),
                    severity=anomaly.get("severity", "warning"),
                    xai_summary=anomaly.get("explanation", {}).get("summary_fr"),
                    use_llm=False,  # set True if Mistral is running
                )
                _alert_store.append(alert)
                generated += 1
                break  # One alert per anomaly row
            except Exception as e:
                logger.warning(f"Alert generation skipped: {e}")

    return jsonify({"status": "done", "alerts_generated": generated})


# ══════════════════════════════════════════════════════════
#  internal_routes.py — Binôme A sync endpoint
# ══════════════════════════════════════════════════════════

from flask import abort
from config import get_config as _get_config

internal_bp = Blueprint("internal", __name__)
_internal_cfg = _get_config()


def _verify_internal_key():
    """Verify X-Internal-Key header matches shared secret with Binôme A."""
    key = request.headers.get("X-Internal-Key", "")
    if key != _internal_cfg.INTERNAL_API_KEY:
        logger.warning("Unauthorized internal API access attempt")
        abort(401)


@internal_bp.post("/kpi/ingest")
def ingest_kpi():
    """
    Binôme A pushes KPI data here after ETL processing.
    
    Headers: X-Internal-Key: <shared-secret>
    Body: {"institution_id": "...", "date": "...", "taux_reussite": 0.78, ...}
    or:  {"records": [{...}, {...}]}  # batch
    """
    _verify_internal_key()

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Empty body"}), 400

    # Accept single record or batch
    if "records" in body:
        records = body["records"]
    elif isinstance(body, list):
        records = body
    else:
        records = [body]

    ingested = 0
    for record in records:
        record.setdefault("ingested_at", datetime.utcnow().isoformat() + "Z")
        _kpi_store.append(record)
        ingested += 1

    logger.info(f"Ingested {ingested} KPI records from Binôme A")
    return jsonify({"status": "ok", "ingested": ingested, "total_stored": len(_kpi_store)})


@internal_bp.get("/status")
def internal_status():
    """Health check for Binôme A to verify Binôme B is running."""
    _verify_internal_key()
    return jsonify({
        "status": "ok",
        "kpi_records": len(_kpi_store),
        "anomalies": len(_anomaly_results),
        "predictions": len(_prediction_results),
        "alerts": len(_alert_store),
    })
