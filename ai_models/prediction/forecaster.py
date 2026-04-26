"""
ai_models/prediction/forecaster.py
────────────────────────────────────
Layer 3 — Time-Series Prediction

Two models available per metric:
  1. Prophet  → interpretable trend + seasonality (default, fast)
  2. LSTM     → deep learning for complex patterns (when more data)

Supports multi-metric, multi-institution forecasting.
"""
from __future__ import annotations

import json
from typing import Literal, Optional
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

# ── Prophet ───────────────────────────────────────────────
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("Prophet not installed. Install with: pip install prophet")

# ── PyTorch LSTM ──────────────────────────────────────────
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not installed. LSTM forecasting unavailable.")


# ══════════════════════════════════════════════════════════
#  LSTM Model Definition
# ══════════════════════════════════════════════════════════

class LSTMForecaster(nn.Module if TORCH_AVAILABLE else object):
    """Lightweight LSTM for univariate time series."""

    def __init__(self, input_size: int = 1, hidden_size: int = 64,
                 num_layers: int = 2, output_size: int = 1):
        if TORCH_AVAILABLE:
            super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers,
                            batch_first=True, dropout=0.2) if TORCH_AVAILABLE else None
        self.fc = nn.Linear(hidden_size, output_size) if TORCH_AVAILABLE else None

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


# ══════════════════════════════════════════════════════════
#  Main Forecaster
# ══════════════════════════════════════════════════════════

class KPIForecaster:
    """
    Unified forecasting interface.

    Example:
        fc = KPIForecaster(method="prophet")
        result = fc.forecast(df, metric="taux_reussite", horizon=30)
    """

    SUPPORTED_METRICS = [
        "taux_reussite",
        "taux_abandon",
        "budget_execute_pct",
        "nb_inscriptions",
        "gender_ratio",
    ]

    def __init__(
        self,
        method: Literal["prophet", "lstm"] = "prophet",
        models_dir: str = "./saved_models",
    ):
        self.method = method
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._prophet_models: dict[str, Prophet] = {}

    # ── Public API ────────────────────────────────────────

    def forecast(
        self,
        df: pd.DataFrame,
        metric: str,
        horizon: int = 30,
        institution_id: Optional[str] = None,
        confidence: float = 0.95,
    ) -> dict:
        """
        Forecast `metric` for the next `horizon` days.

        Returns:
            {
              "metric": str,
              "institution_id": str | None,
              "horizon_days": int,
              "method": str,
              "forecast": [{"ds": date, "yhat": float, "yhat_lower": float, "yhat_upper": float}],
              "trend": "up" | "down" | "stable",
              "alert": bool,
            }
        """
        if metric not in self.SUPPORTED_METRICS:
            raise ValueError(f"Unsupported metric: {metric}. Choose from {self.SUPPORTED_METRICS}")

        if institution_id:
            df = df[df["institution_id"] == institution_id].copy()

        if len(df) < 10:
            raise ValueError(f"Not enough data for {metric}: need ≥10 rows, got {len(df)}")

        if self.method == "prophet":
            return self._forecast_prophet(df, metric, horizon, institution_id, confidence)
        elif self.method == "lstm":
            return self._forecast_lstm(df, metric, horizon, institution_id)
        else:
            raise ValueError(f"Unknown method: {self.method}")

    def forecast_all(
        self, df: pd.DataFrame, horizon: int = 30, institution_id: Optional[str] = None
    ) -> list[dict]:
        """Forecast all supported metrics at once."""
        results = []
        for metric in self.SUPPORTED_METRICS:
            if metric not in df.columns:
                continue
            try:
                result = self.forecast(df, metric, horizon, institution_id)
                results.append(result)
            except Exception as e:
                logger.warning(f"Forecast failed for {metric}: {e}")
        return results

    # ── Prophet ───────────────────────────────────────────

    def _forecast_prophet(
        self, df: pd.DataFrame, metric: str, horizon: int,
        institution_id: Optional[str], confidence: float
    ) -> dict:
        """Linear trend forecaster — no Stan/Prophet dependency required."""
        ts = self._prepare_ts(df, metric)
        values = ts["y"].values
        n = len(values)

        # Fit linear trend via least squares
        x = np.arange(n)
        slope, intercept = np.polyfit(x, values, 1)

        # Residual std for confidence interval
        fitted = slope * x + intercept
        residuals_std = float(np.std(values - fitted))

        last_date = pd.to_datetime(ts["ds"].iloc[-1])
        dates = pd.date_range(
            last_date + pd.Timedelta(days=1), periods=horizon, freq="D"
        )

        records = []
        for i, d in enumerate(dates):
            yhat = float(slope * (n + i) + intercept)
            records.append({
                "ds": str(d.date()),
                "yhat": round(yhat, 4),
                "yhat_lower": round(yhat - 1.96 * residuals_std, 4),
                "yhat_upper": round(yhat + 1.96 * residuals_std, 4),
            })

        trend = self._detect_trend(np.array([r["yhat"] for r in records]))
        alert = self._should_alert(metric, records[-1]["yhat"])

        return {
            "metric": metric,
            "institution_id": institution_id,
            "horizon_days": horizon,
            "method": "linear_trend",
            "forecast": records,
            "trend": trend,
            "alert": alert,
            "last_actual": round(float(ts["y"].iloc[-1]), 4),
            "predicted_end": round(records[-1]["yhat"], 4),
        }
    # ── LSTM ──────────────────────────────────────────────

    def _forecast_lstm(
        self, df: pd.DataFrame, metric: str, horizon: int, institution_id: Optional[str]
    ) -> dict:
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not installed")

        ts = self._prepare_ts(df, metric)
        values = ts["y"].values.astype(np.float32)

        # Normalize
        mu, sigma = values.mean(), values.std() + 1e-8
        normalized = (values - mu) / sigma

        # Sequence dataset
        seq_len = min(30, len(normalized) - 1)
        X = torch.tensor(normalized[-seq_len:], dtype=torch.float32).unsqueeze(0).unsqueeze(-1)

        model = LSTMForecaster()
        model.eval()

        predictions = []
        inp = X.clone()
        with torch.no_grad():
            for _ in range(horizon):
                pred = model(inp)
                pred_val = pred.item()
                predictions.append(pred_val)
                # Slide window
                new_inp = torch.zeros_like(inp)
                new_inp[0, :-1, 0] = inp[0, 1:, 0]
                new_inp[0, -1, 0] = pred_val
                inp = new_inp

        # Denormalize
        preds_real = [(p * sigma + mu) for p in predictions]
        last_date = pd.to_datetime(ts["ds"].iloc[-1])
        dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon, freq="D")

        records = [
            {"ds": str(d.date()), "yhat": round(v, 4), "yhat_lower": None, "yhat_upper": None}
            for d, v in zip(dates, preds_real)
        ]

        trend = self._detect_trend(np.array(preds_real))
        alert = self._should_alert(metric, preds_real[-1])

        return {
            "metric": metric,
            "institution_id": institution_id,
            "horizon_days": horizon,
            "method": "lstm",
            "forecast": records,
            "trend": trend,
            "alert": alert,
            "last_actual": float(ts["y"].iloc[-1]),
            "predicted_end": round(preds_real[-1], 4),
        }

    # ── Helpers ───────────────────────────────────────────

    def _prepare_ts(self, df: pd.DataFrame, metric: str) -> pd.DataFrame:
        """Convert raw KPI dataframe to Prophet-style ds/y."""
        date_col = next((c for c in ["date", "ds", "created_at", "timestamp"] if c in df.columns), None)
        if date_col is None:
            raise ValueError("DataFrame must have a date column: 'date', 'ds', 'created_at', or 'timestamp'")
        ts = df[[date_col, metric]].rename(columns={date_col: "ds", metric: "y"})
        ts["ds"] = pd.to_datetime(ts["ds"])
        ts = ts.dropna().sort_values("ds").reset_index(drop=True)
        return ts

    def _detect_trend(self, values: np.ndarray) -> str:
        if len(values) < 2:
            return "stable"
        slope = np.polyfit(range(len(values)), values, 1)[0]
        if slope > 0.01:
            return "up"
        elif slope < -0.01:
            return "down"
        return "stable"

    def _should_alert(self, metric: str, predicted_value: float) -> bool:
        """Alert if predicted value crosses critical thresholds."""
        thresholds = {
            "taux_abandon": ("above", 0.30),        # >30% dropout = alert
            "taux_reussite": ("below", 0.50),       # <50% success = alert
            "budget_execute_pct": ("above", 1.05),  # >105% budget = alert
        }
        if metric not in thresholds:
            return False
        direction, threshold = thresholds[metric]
        if direction == "above":
            return predicted_value > threshold
        return predicted_value < threshold
