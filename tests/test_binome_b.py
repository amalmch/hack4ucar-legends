"""
tests/test_binome_b.py
──────────────────────
pytest unit tests for all Binôme B modules.

Run:  pytest tests/ -v --cov=. --cov-report=term-missing
"""
import json
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


# ══════════════════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════════════════

@pytest.fixture
def sample_kpi_df():
    """Generate synthetic KPI data for 60 days across 3 institutions."""
    np.random.seed(42)
    records = []
    for inst in ["ESST", "ISET", "FST"]:
        for day in range(60):
            date = (datetime(2024, 1, 1) + timedelta(days=day)).strftime("%Y-%m-%d")
            records.append({
                "institution_id": inst,
                "date": date,
                "taux_reussite": np.clip(np.random.normal(0.72, 0.08), 0.3, 1.0),
                "taux_abandon": np.clip(np.random.normal(0.12, 0.04), 0.0, 0.5),
                "budget_execute_pct": np.clip(np.random.normal(0.85, 0.10), 0.5, 1.2),
                "gender_ratio": np.clip(np.random.normal(0.48, 0.05), 0.2, 0.8),
                "nb_inscriptions": int(np.random.normal(1500, 200)),
            })
    return pd.DataFrame(records)


@pytest.fixture
def anomaly_df_with_spike(sample_kpi_df):
    """Inject obvious anomalies for testing detection."""
    df = sample_kpi_df.copy()
    # Inject critical anomaly in row 10
    df.loc[10, "taux_abandon"] = 0.95   # extreme dropout
    df.loc[10, "taux_reussite"] = 0.05  # extreme failure
    # Inject warning in row 20
    df.loc[20, "budget_execute_pct"] = 1.8  # over budget
    return df


@pytest.fixture
def flask_app():
    """Create test Flask app."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    app.config["JWT_SECRET_KEY"] = "test-secret"
    return app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture
def auth_headers(flask_app):
    """Generate JWT token for testing."""
    from flask_jwt_extended import create_access_token
    with flask_app.app_context():
        token = create_access_token(
            identity="test-user",
            additional_claims={"role": "superadmin"},
        )
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════════
#  Test: Anomaly Detector
# ══════════════════════════════════════════════════════════

class TestAnomalyDetector:

    def test_fit_and_detect(self, sample_kpi_df, tmp_path):
        from ai_models.anomaly.detector import AnomalyDetector
        detector = AnomalyDetector(model_path=str(tmp_path / "model.pkl"))
        detector.fit(sample_kpi_df)
        result = detector.detect(sample_kpi_df)

        assert "is_anomaly" in result.columns
        assert "severity" in result.columns
        assert "iso_score" in result.columns
        assert result["severity"].isin(["normal", "warning", "critical"]).all()

    def test_detects_injected_anomalies(self, anomaly_df_with_spike, tmp_path):
        from ai_models.anomaly.detector import AnomalyDetector
        detector = AnomalyDetector(contamination=0.1, model_path=str(tmp_path / "model.pkl"))
        detector.fit(anomaly_df_with_spike)
        result = detector.detect(anomaly_df_with_spike)

        # Row 10 should be flagged
        assert result.loc[10, "is_anomaly"] is True or result.loc[10, "iso_anomaly"]

    def test_summary_structure(self, sample_kpi_df, tmp_path):
        from ai_models.anomaly.detector import AnomalyDetector
        detector = AnomalyDetector(model_path=str(tmp_path / "model.pkl"))
        detector.fit(sample_kpi_df)
        result = detector.detect(sample_kpi_df)
        summary = detector.summary(result)

        assert "total_records" in summary
        assert "anomaly_count" in summary
        assert "anomaly_rate_pct" in summary
        assert summary["total_records"] == len(sample_kpi_df)

    def test_missing_columns_raises(self):
        from ai_models.anomaly.detector import AnomalyDetector
        detector = AnomalyDetector()
        df_bad = pd.DataFrame({"unrelated_col": [1, 2, 3]})
        with pytest.raises(ValueError, match="DataFrame must contain"):
            detector._extract_features(df_bad)

    def test_severity_classification(self, sample_kpi_df, tmp_path):
        from ai_models.anomaly.detector import AnomalyDetector
        detector = AnomalyDetector(model_path=str(tmp_path / "model.pkl"))
        detector.fit(sample_kpi_df)
        result = detector.detect(sample_kpi_df)
        # Severity should only contain valid values
        assert set(result["severity"].unique()).issubset({"normal", "warning", "critical"})


# ══════════════════════════════════════════════════════════
#  Test: KPI Forecaster
# ══════════════════════════════════════════════════════════

class TestKPIForecaster:

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("prophet"),
        reason="prophet not installed"
    )
    def test_prophet_forecast_returns_correct_shape(self, sample_kpi_df):
        from ai_models.prediction.forecaster import KPIForecaster
        fc = KPIForecaster(method="prophet")
        result = fc.forecast(sample_kpi_df, "taux_reussite", horizon=7)

        assert result["metric"] == "taux_reussite"
        assert result["method"] == "prophet"
        assert len(result["forecast"]) == 7
        assert "yhat" in result["forecast"][0]
        assert result["trend"] in ("up", "down", "stable")

    def test_unsupported_metric_raises(self, sample_kpi_df):
        from ai_models.prediction.forecaster import KPIForecaster
        fc = KPIForecaster()
        with pytest.raises(ValueError, match="Unsupported metric"):
            fc.forecast(sample_kpi_df, "made_up_metric", horizon=7)

    def test_insufficient_data_raises(self):
        from ai_models.prediction.forecaster import KPIForecaster
        fc = KPIForecaster()
        tiny_df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02"],
            "taux_reussite": [0.7, 0.8],
        })
        with pytest.raises(ValueError, match="Not enough data"):
            fc.forecast(tiny_df, "taux_reussite", horizon=7)

    def test_trend_detection(self):
        from ai_models.prediction.forecaster import KPIForecaster
        fc = KPIForecaster()
        assert fc._detect_trend(np.array([0.1, 0.2, 0.3, 0.4, 0.5])) == "up"
        assert fc._detect_trend(np.array([0.5, 0.4, 0.3, 0.2, 0.1])) == "down"
        assert fc._detect_trend(np.array([0.5, 0.5, 0.5, 0.5, 0.5])) == "stable"

    def test_alert_thresholds(self):
        from ai_models.prediction.forecaster import KPIForecaster
        fc = KPIForecaster()
        assert fc._should_alert("taux_abandon", 0.5) is True    # > 0.30
        assert fc._should_alert("taux_abandon", 0.1) is False
        assert fc._should_alert("taux_reussite", 0.3) is True   # < 0.50
        assert fc._should_alert("taux_reussite", 0.8) is False


# ══════════════════════════════════════════════════════════
#  Test: XAI Explainer
# ══════════════════════════════════════════════════════════

class TestXAIExplainer:

    @pytest.fixture
    def trained_detector_and_data(self, sample_kpi_df, tmp_path):
        from ai_models.anomaly.detector import AnomalyDetector, KPI_FEATURES
        detector = AnomalyDetector(model_path=str(tmp_path / "model.pkl"))
        detector.fit(sample_kpi_df)
        feature_cols = [c for c in KPI_FEATURES if c in sample_kpi_df.columns]
        X = detector.scaler.transform(
            sample_kpi_df[feature_cols].fillna(sample_kpi_df[feature_cols].median()).values
        )
        return detector, X, feature_cols

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("shap"),
        reason="shap not installed"
    )
    def test_shap_explanation_structure(self, trained_detector_and_data):
        from ai_models.xai.explainer import XAIExplainer
        detector, X, feature_cols = trained_detector_and_data

        explainer = XAIExplainer(
            model=detector.iso_forest,
            X_train=X,
            feature_names=feature_cols,
            model_type="isolation_forest",
        )

        result = explainer.explain_anomaly(X[0], method="shap", top_n=3)

        assert "top_features" in result
        assert "summary_fr" in result
        assert len(result["top_features"]) <= 3
        assert isinstance(result["summary_fr"], str)
        assert len(result["summary_fr"]) > 0

    def test_french_summary_generated(self, trained_detector_and_data):
        from ai_models.xai.explainer import XAIExplainer
        _, X, feature_cols = trained_detector_and_data

        explainer = XAIExplainer(feature_names=feature_cols, model_type="isolation_forest")
        features = [
            {"label_fr": "Taux d'abandon", "direction": "positive", "impact": 0.5},
            {"label_fr": "Taux de réussite", "direction": "negative", "impact": -0.3},
        ]
        summary = explainer._generate_summary_fr(features, "anomaly")
        assert "Taux d'abandon" in summary
        assert len(summary) > 10


# ══════════════════════════════════════════════════════════
#  Test: Security Module
# ══════════════════════════════════════════════════════════

class TestSecurity:

    def test_aes_encrypt_decrypt_roundtrip(self):
        from security.encryption import AESEncryptor
        enc = AESEncryptor()
        plaintext = "Données sensibles: taux_abandon = 0.85"
        ciphertext = enc.encrypt(plaintext)

        assert ciphertext != plaintext
        assert enc.decrypt(ciphertext) == plaintext

    def test_different_plaintexts_different_ciphertexts(self):
        from security.encryption import AESEncryptor
        enc = AESEncryptor()
        ct1 = enc.encrypt("valeur A")
        ct2 = enc.encrypt("valeur B")
        assert ct1 != ct2

    def test_encrypt_dict(self):
        from security.encryption import AESEncryptor
        enc = AESEncryptor()
        data = {"nom": "Ali Ben Salem", "taux": 0.78, "password": "secret123"}
        encrypted = enc.encrypt_dict(data, fields=["password"])

        assert encrypted["password"] != "secret123"
        assert encrypted["nom"] == "Ali Ben Salem"  # unchanged
        decrypted = enc.decrypt_dict(encrypted, fields=["password"])
        assert decrypted["password"] == "secret123"

    def test_rbac_permissions(self):
        from security.encryption import has_permission
        assert has_permission("superadmin", "delete") is True
        assert has_permission("student", "delete") is False
        assert has_permission("teacher", "read") is True
        assert has_permission("teacher", "admin") is False

    def test_audit_log_writes_file(self, tmp_path, monkeypatch):
        import security.encryption as sec_mod
        monkeypatch.setattr(sec_mod, "_AUDIT_LOG_DIR", tmp_path)

        entry = sec_mod.audit_log(
            action="TEST_ACTION",
            resource="kpi_data",
            user_id="test-user-123",
            role="institution_admin",
            success=True,
        )

        assert entry["action"] == "TEST_ACTION"
        assert entry["user_id"] == "test-user-123"
        assert "id" in entry
        assert "timestamp" in entry

    def test_mask_sensitive(self):
        from security.encryption import mask_sensitive
        data = {"email": "ali@ucar.tn", "taux_reussite": 0.78, "password": "mypassword"}
        masked = mask_sensitive(data)
        assert "****" in masked["password"]
        assert masked["taux_reussite"] == 0.78  # non-sensitive unchanged


# ══════════════════════════════════════════════════════════
#  Test: Alert Generator (no LLM)
# ══════════════════════════════════════════════════════════

class TestAlertGenerator:

    def test_alert_message_template_mode(self):
        from reports.alert_generator import alert_message
        result = alert_message(
            institution_name="ISET Tunis",
            metric="taux_abandon",
            current_value=0.45,
            severity="critical",
            use_llm=False,
        )
        assert result["institution"] == "ISET Tunis"
        assert result["severity"] == "critical"
        assert result["action_required"] is True
        assert len(result["message"]) > 10

    def test_alert_message_normal_no_action(self):
        from reports.alert_generator import alert_message
        result = alert_message(
            institution_name="FST",
            metric="taux_reussite",
            current_value=0.85,
            severity="normal",
            use_llm=False,
        )
        assert result["action_required"] is False

    def test_generate_report_structure(self):
        from reports.alert_generator import generate_report
        report = generate_report(
            kpi_data={"taux_reussite": 0.75, "taux_abandon": 0.12},
            anomalies=[{"severity": "warning", "metric": "taux_reussite"}],
            predictions=[{"metric": "taux_reussite", "alert": False, "trend": "stable"}],
            institution_name="ESST",
            format="json",
            use_llm=False,
        )
        assert report["institution"] == "ESST"
        assert "executive_summary" in report
        assert "anomaly_section" in report
        assert "prediction_section" in report
        assert isinstance(report["recommendations"], list)


# ══════════════════════════════════════════════════════════
#  Test: Flask API Endpoints
# ══════════════════════════════════════════════════════════

class TestFlaskAPI:

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["service"] == "binome-b"

    def test_kpi_requires_auth(self, client):
        resp = client.get("/api/kpi/latest")
        assert resp.status_code == 401

    def test_internal_ingest_requires_key(self, client):
        resp = client.post("/internal/kpi/ingest", json={"taux_reussite": 0.75})
        assert resp.status_code == 401

    def test_internal_ingest_with_valid_key(self, client, flask_app):
        resp = client.post(
            "/internal/kpi/ingest",
            json={"institution_id": "ISET", "taux_reussite": 0.75, "taux_abandon": 0.1},
            headers={"X-Internal-Key": flask_app.config.get("INTERNAL_API_KEY", "binome-a-internal-key")},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ingested"] == 1

    def test_get_alerts_empty(self, client, auth_headers):
        resp = client.get("/api/alerts", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 0
