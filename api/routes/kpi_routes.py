# Expose all blueprints from the combined routes module
from api.routes import (
    kpi_bp, anomaly_bp, prediction_bp,
    xai_bp, report_bp, alert_bp, internal_bp
)

__all__ = [
    "kpi_bp", "anomaly_bp", "prediction_bp",
    "xai_bp", "report_bp", "alert_bp", "internal_bp",
]
