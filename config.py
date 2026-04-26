"""
config.py — Centralized configuration for Binôme B
Reads from environment variables (set via .env or Docker)
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Flask ──────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-prod")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    PORT = int(os.getenv("PORT", 5001))

    # ── JWT ───────────────────────────────────────────────
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = 3600          # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 86400 * 7   # 7 days

    # ── Database (TimescaleDB / PostgreSQL) ────────────────
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 5432))
    DB_NAME = os.getenv("DB_NAME", "ucar_db")
    DB_USER = os.getenv("DB_USER", "ucar_admin")
    DB_PASS = os.getenv("DB_PASS", "secret")
    DATABASE_URL = (
        os.getenv("DATABASE_URL")
        or f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    # ── Redis (cache, sessions, Celery) ───────────────────
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ── LLM / Mistral ─────────────────────────────────────
    # If using local Ollama:  MISTRAL_BACKEND=ollama
    # If using HuggingFace:   MISTRAL_BACKEND=hf
    MISTRAL_BACKEND = os.getenv("MISTRAL_BACKEND", "ollama")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    HF_API_KEY = os.getenv("HF_API_KEY", "")
    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral:7b")

    # ── Security / Encryption ─────────────────────────────
    AES_KEY = os.getenv("AES_KEY", "")   # 32-byte hex string; auto-generated if empty

    # ── Rate Limiting ─────────────────────────────────────
    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_STORAGE_URL = REDIS_URL

    # ── Model Paths ───────────────────────────────────────
    MODELS_DIR = os.getenv("MODELS_DIR", "./saved_models")
    ISOLATION_FOREST_PATH = f"{MODELS_DIR}/isolation_forest.pkl"
    LSTM_PATH = f"{MODELS_DIR}/lstm_model.pt"

    # ── Internal API contract with Binôme A ───────────────
    INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "binome-a-internal-key")

    # ── Thresholds ────────────────────────────────────────
    ANOMALY_CONTAMINATION = float(os.getenv("ANOMALY_CONTAMINATION", 0.05))
    ZSCORE_THRESHOLD = float(os.getenv("ZSCORE_THRESHOLD", 3.0))
    PREDICTION_HORIZON_DAYS = int(os.getenv("PREDICTION_HORIZON_DAYS", 30))


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False


def get_config() -> Config:
    env = os.getenv("FLASK_ENV", "development")
    return ProdConfig() if env == "production" else DevConfig()
