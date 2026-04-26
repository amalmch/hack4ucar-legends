# UCAR Platform — Binôme B (IA & Output)

## Responsibility: Layers 3 & 4

```
binome_b/
├── ai_models/
│   ├── anomaly/          # Layer 3 — Isolation Forest + Z-score
│   ├── prediction/       # Layer 3 — Prophet + LSTM
│   └── xai/              # Layer 4 — SHAP / LIME explanations
├── api/
│   ├── routes/           # Flask blueprints (KPI, anomaly, predict, xai, reports)
│   ├── middleware/        # Auth (JWT), RBAC, rate limiting
│   └── utils/            # Response helpers, validators
├── reports/              # Mistral 7B report + alert generator
├── security/             # AES encryption, audit log
├── tests/                # pytest unit tests
├── app.py                # Flask entry point
├── config.py             # Environment config
├── requirements.txt
└── docker-compose.yml
```

## Sync contract with Binôme A

Binôme A pushes KPI data to: `POST /internal/kpi/ingest`  
Payload: see `api/utils/schemas.py → KPIPayload`

Binôme B exposes to frontend/dashboard:
- `GET  /api/kpi/latest`
- `GET  /api/anomalies`
- `GET  /api/predictions`
- `GET  /api/xai/explain`
- `POST /api/reports/generate`
- `GET  /api/alerts`

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Or with Docker:
```bash
docker-compose up --build
```
