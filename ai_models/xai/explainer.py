"""
ai_models/xai/explainer.py
───────────────────────────
Layer 4 — Explainable AI (XAI)

Generates human-readable explanations IN FRENCH for:
  - Why a data point was flagged as anomalous (SHAP on IsolationForest)
  - What drives a KPI prediction (SHAP on any sklearn model)
  - LIME local explanations as fallback or complement

Output is JSON-serializable and ready for dashboard display.
"""
from __future__ import annotations

from typing import Optional
import numpy as np
import pandas as pd
from loguru import logger

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP not installed. Install with: pip install shap")

try:
    from lime.lime_tabular import LimeTabularExplainer
    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False
    logger.warning("LIME not installed. Install with: pip install lime")


# ── French labels for KPI features ────────────────────────
FEATURE_LABELS_FR = {
    "taux_reussite":        "Taux de réussite",
    "taux_abandon":         "Taux d'abandon",
    "budget_execute_pct":   "Taux d'exécution budgétaire",
    "gender_ratio":         "Ratio de genre (F/total)",
    "nb_inscriptions":      "Nombre d'inscriptions",
}

DIRECTION_LABELS_FR = {
    "positive": "↑ a augmenté l'anomalie",
    "negative": "↓ a réduit l'anomalie",
}


class XAIExplainer:
    """
    SHAP + LIME explainer for UCAR anomaly and prediction models.

    Usage:
        explainer = XAIExplainer(model, X_train)
        explanation = explainer.explain_anomaly(row, feature_names)
        explanation = explainer.explain_prediction(row, feature_names)
    """

    def __init__(
        self,
        model,
        X_train: Optional[np.ndarray] = None,
        feature_names: Optional[list[str]] = None,
        model_type: str = "isolation_forest",
    ):
        self.model = model
        self.X_train = X_train
        self.feature_names = feature_names or []
        self.model_type = model_type
        self._shap_explainer = None
        self._lime_explainer = None

    # ── Initialization ────────────────────────────────────

    def setup_shap(self):
        if not SHAP_AVAILABLE:
            raise RuntimeError("shap not installed")
        if self.X_train is None:
            raise ValueError("X_train required for SHAP setup")

        if self.model_type == "isolation_forest":
            # TreeExplainer works natively with sklearn IsolationForest
            self._shap_explainer = shap.TreeExplainer(self.model)
        else:
            # General explainer (for linear models, neural nets via KernelExplainer)
            background = shap.sample(self.X_train, min(100, len(self.X_train)))
            self._shap_explainer = shap.KernelExplainer(
                self.model.predict_proba if hasattr(self.model, "predict_proba")
                else self.model.predict,
                background,
            )
        logger.info(f"SHAP explainer initialized ({self.model_type})")

    def setup_lime(self):
        if not LIME_AVAILABLE:
            raise RuntimeError("lime not installed")
        if self.X_train is None:
            raise ValueError("X_train required for LIME setup")

        self._lime_explainer = LimeTabularExplainer(
            self.X_train,
            feature_names=self.feature_names,
            mode="regression",
            discretize_continuous=True,
        )
        logger.info("LIME explainer initialized")

    # ── Main explain methods ───────────────────────────────

    def explain_anomaly(
        self,
        row: np.ndarray,
        method: str = "shap",
        top_n: int = 5,
    ) -> dict:
        """
        Explain why a specific row was flagged as anomalous.

        Returns:
            {
              "method": "shap" | "lime",
              "top_features": [{"feature": str, "label_fr": str, "impact": float, "direction": str}],
              "summary_fr": str,   # Human-readable French summary
              "raw_values": {...}
            }
        """
        if method == "shap":
            return self._explain_shap(row, top_n, task="anomaly")
        elif method == "lime":
            return self._explain_lime(row, top_n)
        else:
            raise ValueError(f"Unknown method: {method}")

    def explain_prediction(
        self,
        row: np.ndarray,
        predicted_value: float,
        metric: str,
        method: str = "shap",
        top_n: int = 5,
    ) -> dict:
        """Explain what factors drive a specific KPI prediction."""
        result = self._explain_shap(row, top_n, task="prediction")
        result["predicted_value"] = predicted_value
        result["metric"] = metric
        result["metric_label_fr"] = FEATURE_LABELS_FR.get(metric, metric)
        return result

    # ── SHAP ──────────────────────────────────────────────

    def _explain_shap(self, row: np.ndarray, top_n: int, task: str) -> dict:
        if self._shap_explainer is None:
            self.setup_shap()

        row_2d = row.reshape(1, -1) if row.ndim == 1 else row
        shap_values = self._shap_explainer.shap_values(row_2d)

        # For IsolationForest, shap_values may be a list (multi-output)
        if isinstance(shap_values, list):
            sv = shap_values[0][0]
        else:
            sv = shap_values[0]

        # Build ranked feature list
        features = []
        for i, (name, val) in enumerate(zip(self.feature_names, sv)):
            features.append({
                "feature": name,
                "label_fr": FEATURE_LABELS_FR.get(name, name),
                "impact": round(float(val), 4),
                "direction": "positive" if val > 0 else "negative",
                "raw_value": round(float(row_2d[0][i]), 4) if i < len(row_2d[0]) else None,
            })

        features.sort(key=lambda x: abs(x["impact"]), reverse=True)
        top = features[:top_n]

        summary = self._generate_summary_fr(top, task)

        return {
            "method": "shap",
            "top_features": top,
            "all_features": features,
            "summary_fr": summary,
            "base_value": round(float(self._shap_explainer.expected_value
                                      if not isinstance(self._shap_explainer.expected_value, list)
                                      else self._shap_explainer.expected_value[0]), 4),
        }

    # ── LIME ──────────────────────────────────────────────

    def _explain_lime(self, row: np.ndarray, top_n: int) -> dict:
        if self._lime_explainer is None:
            self.setup_lime()

        predict_fn = (
            self.model.predict_proba
            if hasattr(self.model, "predict_proba")
            else self.model.predict
        )

        exp = self._lime_explainer.explain_instance(
            row, predict_fn, num_features=top_n, top_labels=1
        )

        lime_list = exp.as_list()
        features = []
        for condition, impact in lime_list:
            # Extract feature name from LIME condition string (e.g. "taux_abandon > 0.3")
            feat_name = condition.split(" ")[0]
            features.append({
                "feature": feat_name,
                "label_fr": FEATURE_LABELS_FR.get(feat_name, feat_name),
                "impact": round(float(impact), 4),
                "direction": "positive" if impact > 0 else "negative",
                "condition": condition,
            })

        summary = self._generate_summary_fr(features, task="anomaly")

        return {
            "method": "lime",
            "top_features": features,
            "summary_fr": summary,
        }

    # ── French summary generator ───────────────────────────

    def _generate_summary_fr(self, top_features: list[dict], task: str) -> str:
        if not top_features:
            return "Aucune explication disponible."

        top = top_features[0]
        label = top["label_fr"]
        direction = "élevé" if top["direction"] == "positive" else "faible"

        if task == "anomaly":
            parts = [f"Cette anomalie est principalement expliquée par un {label} {direction}"]
            if len(top_features) > 1:
                others = [f["label_fr"] for f in top_features[1:3]]
                parts.append(f"ainsi que par : {', '.join(others)}")
            return ". ".join(parts) + "."
        else:
            parts = [f"La prédiction est principalement influencée par le {label} ({direction})"]
            if len(top_features) > 1:
                others = [f["label_fr"] for f in top_features[1:3]]
                parts.append(f"et par : {', '.join(others)}")
            return ". ".join(parts) + "."

    # ── Batch explain ─────────────────────────────────────

    def explain_batch(
        self, X: np.ndarray, anomaly_mask: np.ndarray, top_n: int = 3
    ) -> list[dict]:
        """Explain all anomalous rows in a batch."""
        results = []
        for i, (row, is_anomaly) in enumerate(zip(X, anomaly_mask)):
            if is_anomaly:
                try:
                    exp = self.explain_anomaly(row, top_n=top_n)
                    exp["row_index"] = i
                    results.append(exp)
                except Exception as e:
                    logger.warning(f"XAI failed for row {i}: {e}")
        return results
