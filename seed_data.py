"""
seed_data.py — Simulate Binôme A's data pipeline for local testing.
Run: python seed_data.py
"""
import requests
import numpy as np
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5001"
INTERNAL_KEY = "binome-a-internal-key"

def generate_records(n=90):
    np.random.seed(42)
    institutions = ["ISET Tunis", "ESST", "FST", "ISSAT", "ENIM"]
    records = []
    for inst in institutions:
        for day in range(n):
            date = (datetime(2024, 1, 1) + timedelta(days=day)).strftime("%Y-%m-%d")
            records.append({
                "institution_id": inst,
                "date": date,
                "taux_reussite":      round(np.clip(np.random.normal(0.72, 0.08), 0.3, 1.0), 3),
                "taux_abandon":       round(np.clip(np.random.normal(0.12, 0.04), 0.0, 0.5), 3),
                "budget_execute_pct": round(np.clip(np.random.normal(0.85, 0.10), 0.5, 1.2), 3),
                "gender_ratio":       round(np.clip(np.random.normal(0.48, 0.05), 0.2, 0.8), 3),
                "nb_inscriptions":    int(np.random.normal(1500, 200)),
            })
    # Inject obvious anomalies so detection actually fires
    records[5]["taux_abandon"] = 0.92    # critical
    records[5]["taux_reussite"] = 0.08
    records[20]["budget_execute_pct"] = 1.75  # over budget warning
    return records

records = generate_records()
resp = requests.post(
    f"{BASE_URL}/internal/kpi/ingest",
    json={"records": records},
    headers={"X-Internal-Key": INTERNAL_KEY}
)
print(f"Ingested: {resp.json()}")