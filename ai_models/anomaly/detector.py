"""
ai_models/anomaly/detector.py
────────────────────────────
Layer 3 — Anomaly Detection

Two complementary strategies:
  1. Isolation Forest  → multivariate anomalies across all KPI dimensions
  2. Z-score           → fast univariate spike detection per metric

Usage:
    detector = AnomalyDetector()
    detector.fit(df_kpi)
    results = detector.detect(df_new)
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from loguru import logger

# KPI columns consumed from Binôme A's data contract
KPI_FEATURES = [
    "taux_reussite",       # % students passing
    "taux_abandon",        # % dropout
    "budget_execute_pct",  # budget execution rate
    "gender_ratio",        # female / total
    "nb_inscriptions",     # enrollments
]


class AnomalyDetector:
    """
    Dual-strategy anomaly detector for UCAR KPI data.
    Train once with .fit(), then call .detect() on new batches.
    """

    def __init__(
        self,
        contamination: float = 0.05,
        zscore_threshold: float = 3.0,
        model_path: Optional[str] = None,
    ):
        self.contamination = contamination
        self.zscore_threshold = zscore_threshold
        self.model_path = model_path or "./saved_models/isolation_forest.pkl"

        self.scaler = StandardScaler()
        self.iso_forest = IsolationForest(
            n_estimators=200,
            contamination=contamination,
            random_state=42,
            n_jobs=-1,
        )
        self._fitted = False

    # ── Training ──────────────────────────────────────────────────────────

    def fit(self, df: pd.DataFrame) -> "AnomalyDetector":
        """Train on historical KPI data."""
        X = self._extract_features(df)
        X_scaled = self.scaler.fit_transform(X)
        self.iso_forest.fit(X_scaled)
        self._fitted = True
        logger.info(f"IsolationForest trained on {len(df)} samples")
        self._save()
        return self

    # ── Detection ─────────────────────────────────────────────────────────

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Returns input DataFrame with added columns:
          - iso_anomaly (bool)
          - iso_score   (float, lower = more anomalous)
          - zscore_flags (dict: feature → zscore value if > threshold)
          - is_anomaly  (bool, union of both methods)
          - severity    (str: 'critical' | 'warning' | 'normal')
        """
        if not self._fitted:
            self._load()

        df = df.copy()
        X = self._extract_features(df)

        # ── Isolation Forest ──────────────────────────────
        X_scaled = self.scaler.transform(X)
        iso_preds = self.iso_forest.predict(X_scaled)       # -1 = anomaly, 1 = normal
        iso_scores = self.iso_forest.score_samples(X_scaled)  # lower = more anomalous

        df["iso_anomaly"] = iso_preds == -1
        df["iso_score"] = iso_scores

        # ── Z-score per feature ───────────────────────────
        zscore_flags = []
        for _, row in X.iterrows():
            flags: dict[str, float] = {}
            for col in X.columns:
                z = abs(float(stats.zscore(X[col])[X.index.get_loc(row.name)]))
                if z > self.zscore_threshold:
                    flags[col] = round(z, 2)
            zscore_flags.append(flags)

        df["zscore_flags"] = zscore_flags
        df["zscore_anomaly"] = df["zscore_flags"].apply(lambda f: len(f) > 0)

        # ── Combined flag ─────────────────────────────────
        df["is_anomaly"] = df["iso_anomaly"] | df["zscore_anomaly"]

        # ── Severity classification ───────────────────────
        df["severity"] = df.apply(self._classify_severity, axis=1)

        anomaly_count = df["is_anomaly"].sum()
        logger.info(f"Detected {anomaly_count}/{len(df)} anomalies")
        return df

    # ── Utilities ─────────────────────────────────────────────────────────

    def _extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract and fill missing KPI columns."""
        available = [c for c in KPI_FEATURES if c in df.columns]
        if not available:
            raise ValueError(f"DataFrame must contain at least one of: {KPI_FEATURES}")
        X = df[available].copy()
        X = X.fillna(X.median())
        return X

    def _classify_severity(self, row: pd.Series) -> str:
        if not row.get("is_anomaly", False):
            return "normal"
        zscore_max = max(row.get("zscore_flags", {}).values(), default=0)
        iso_score = row.get("iso_score", 0)
        if zscore_max > 5 or iso_score < -0.3:
            return "critical"
        return "warning"

    def _save(self):
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.model_path, "wb") as f:
            pickle.dump({"scaler": self.scaler, "model": self.iso_forest}, f)
        logger.info(f"Model saved → {self.model_path}")

    def _load(self):
        if not Path(self.model_path).exists():
            raise FileNotFoundError(
                f"Model not found at {self.model_path}. Run .fit() first."
            )
        with open(self.model_path, "rb") as f:
            obj = pickle.load(f)
        self.scaler = obj["scaler"]
        self.iso_forest = obj["model"]
        self._fitted = True
        logger.info(f"Model loaded ← {self.model_path}")

    def summary(self, df_result: pd.DataFrame) -> dict:
        anomalies = df_result[df_result["is_anomaly"]]
        
        # Fix: convert tuple keys to string keys for JSON serialization
        by_institution = {}
        if "institution_id" in df_result.columns:
            grouped = anomalies.groupby("institution_id")["severity"].value_counts()
            for (inst, sev), count in grouped.items():
                key = f"{inst}__{sev}"
                by_institution[key] = int(count)

        return {
            "total_records": len(df_result),
            "anomaly_count": len(anomalies),
            "anomaly_rate_pct": round(len(anomalies) / max(len(df_result), 1) * 100, 2),
            "critical": int((df_result["severity"] == "critical").sum()),
            "warning": int((df_result["severity"] == "warning").sum()),
            "by_institution": by_institution,
        }