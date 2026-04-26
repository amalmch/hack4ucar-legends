# UCAR Platform —(IA & Output)

## Responsibility: Layers 3 & 4

```
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

this is a demo for the whole project:
ucar dashboard :
<img width="1897" height="902" alt="image" src="https://github.com/user-attachments/assets/9b584c98-a274-46b7-956c-7c29e92a18ec" />
student portal:
<img width="1892" height="895" alt="image" src="https://github.com/user-attachments/assets/78c19b21-5a72-4898-8fad-ec4bec858086" />
teacher's portal:
<img width="1902" height="896" alt="image" src="https://github.com/user-attachments/assets/5dd55268-95d4-4fa8-99a0-dcb0e4dae61f" />
admin's portal:
<img width="1900" height="908" alt="image" src="https://github.com/user-attachments/assets/8f6895bc-5c9b-41fe-962c-2156e4c19fff" />


pushing KPI data to: `POST /internal/kpi/ingest`  
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
