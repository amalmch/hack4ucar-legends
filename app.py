"""
app.py — Binôme B Flask entry point
Registers all blueprints, JWT, CORS, SocketIO, and rate limiting.
"""
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from loguru import logger
import sys

from config import get_config

# ── Blueprints ────────────────────────────────────────────
from api.routes.kpi_routes import kpi_bp
from api.routes.anomaly_routes import anomaly_bp
from api.routes.prediction_routes import prediction_bp
from api.routes.xai_routes import xai_bp
from api.routes.report_routes import report_bp
from api.routes.alert_routes import alert_bp
from api.routes.internal_routes import internal_bp
from api.routes.auth_routes import auth_bp
from api.routes.ucar_admin_routes import ucar_bp
from api.routes.institution_admin_routes import inst_bp
from api.routes.ai_routes import ai_bp
from api.routes.ingestion_routes import ingestion_bp
from api.routes.teacher_routes import teacher_bp
from api.routes.student_routes import student_bp
from api.routes.notification_routes import notif_bp

# ── Logger setup ─────────────────────────────────────────
logger.remove()
logger.add(sys.stderr, level="DEBUG", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
logger.add("logs/app.log", rotation="10 MB", retention="30 days", level="INFO")

cfg = get_config()

# ── App factory ───────────────────────────────────────────
def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(cfg)

    # Extensions
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
    JWTManager(app)
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[cfg.RATELIMIT_DEFAULT],
        storage_uri="memory://",
    )

    # Register blueprints
    app.register_blueprint(kpi_bp,        url_prefix="/api/kpi")
    app.register_blueprint(anomaly_bp,    url_prefix="/api/anomalies")
    app.register_blueprint(prediction_bp, url_prefix="/api/predictions")
    app.register_blueprint(xai_bp,        url_prefix="/api/xai")
    app.register_blueprint(report_bp,     url_prefix="/api/reports")
    app.register_blueprint(alert_bp,      url_prefix="/api/alerts")
    app.register_blueprint(auth_bp,       url_prefix="/api/auth")
    app.register_blueprint(ucar_bp,       url_prefix="/api/ucar")
    app.register_blueprint(inst_bp,       url_prefix="/api/institution")
    app.register_blueprint(ai_bp,         url_prefix="/api/ai")
    app.register_blueprint(ingestion_bp,  url_prefix="/api/ingestion")
    app.register_blueprint(teacher_bp,    url_prefix="/api/teacher")
    app.register_blueprint(student_bp,    url_prefix="/api/student")
    app.register_blueprint(notif_bp,      url_prefix="/api/notifications")
    app.register_blueprint(internal_bp,   url_prefix="/internal")  # Binôme A sync

    # Health check
    @app.get("/health")
    def health():
        return {"status": "ok", "service": "binome-b", "version": "1.0.0"}


    @app.post("/dev/token")
    def dev_token():
        from flask_jwt_extended import create_access_token
        token = create_access_token(
            identity="test-admin",
            additional_claims={"role": "superadmin"}
        )
        return {"token": token}
    logger.info("✅ Binôme B Flask app initialized")

    
    return app



socketio = SocketIO()


def create_socketio_app():
    app = create_app()
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")
    return app, socketio


if __name__ == "__main__":
    app, sio = create_socketio_app()
    logger.info(f"🚀 Starting on port {cfg.PORT}")
    sio.run(app, host="0.0.0.0", port=cfg.PORT, debug=cfg.DEBUG, use_reloader=False, allow_unsafe_werkzeug=True)
