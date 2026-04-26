"""
load_csv_to_api.py
───────────────────
Reads the 3 UCAR CSV files and pushes aggregated KPI records
to the API via POST /internal/kpi/ingest.

Aggregation logic:
  - students.csv    → taux_reussite, taux_abandon, nb_inscriptions,
                       taux_presence, gender_ratio per institution
  - teachers.csv    → nb_enseignants, taux_absenteisme_rh,
                       heures_moy, publications_total per institution
  - administration  → budget_execute_pct, nb_conventions,
                       nb_projets_recherche, taux_emploi per institution

Run: python load_csv_to_api.py
"""

import csv
import requests
from collections import defaultdict

BASE_URL     = "http://localhost:5001"
INTERNAL_KEY = "binome-a-internal-key"

def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def safe_float(v, default=0.0):
    try: return float(v)
    except: return default

def safe_int(v, default=0):
    try: return int(float(v))
    except: return default

# ── Load all 3 files ──────────────────────────────────────────────────────
print("📂 Loading CSV files...")
students = load_csv("data/students.csv")
teachers = load_csv("data/teachers.csv")
admin    = load_csv("data/administration.csv")
print(f"   {len(students)} students | {len(teachers)} teachers | {len(admin)} admin records")

# ── Aggregate students per institution ───────────────────────────────────
stu_by_inst = defaultdict(list)
for s in students:
    stu_by_inst[s["institution_id"]].append(s)

stu_kpis = {}
for inst_id, rows in stu_by_inst.items():
    total = len(rows)
    passed   = sum(1 for r in rows if safe_float(r["moyenne_s1"]) >= 10)
    dropped  = sum(1 for r in rows if r["statut"] == "abandonne")
    female   = sum(1 for r in rows if r["genre"] == "F")
    scholars = sum(1 for r in rows if r["boursier"] == "Oui")
    avg_grade = round(sum(safe_float(r["moyenne_s1"]) for r in rows) / total, 3)
    avg_abs   = round(sum(safe_float(r["nb_absences_s1"]) for r in rows) / total, 2)
    stu_kpis[inst_id] = {
        "nb_inscriptions":  total,
        "taux_reussite":    round(passed / total, 3),
        "taux_abandon":     round(dropped / total, 3),
        "gender_ratio":     round(female / total, 3),
        "taux_boursiers":   round(scholars / total, 3),
        "moyenne_generale": avg_grade,
        "absences_moy":     avg_abs,
    }

# ── Aggregate teachers per institution ───────────────────────────────────
tch_by_inst = defaultdict(list)
for t in teachers:
    tch_by_inst[t["institution_id"]].append(t)

tch_kpis = {}
for inst_id, rows in tch_by_inst.items():
    total = len(rows)
    perm  = sum(1 for r in rows if r["statut"] == "Permanent")
    heures_moy = round(sum(safe_float(r["nb_heures_cours_annee"]) for r in rows) / total, 1)
    pubs   = sum(safe_int(r["nb_publications_annee"]) for r in rows)
    absences = round(sum(safe_float(r["taux_absenteisme_pct"]) for r in rows) / total, 4)
    tch_kpis[inst_id] = {
        "nb_enseignants":           total,
        "taux_permanents":          round(perm / total, 3),
        "heures_cours_moy":         heures_moy,
        "nb_publications_total":    pubs,
        "taux_absenteisme_rh":      absences,
    }

# ── Build final KPI records from administration rows ────────────────────
records = []
for row in admin:
    inst_id = row["institution_id"]
    stu = stu_kpis.get(inst_id, {})
    tch = tch_kpis.get(inst_id, {})

    record = {
        "institution_id":            inst_id,
        "institution_name":          row["institution_name"],
        "ville":                     row["ville"],
        "date":                      f"{row['annee_budgetaire']}-01-01",
        "annee_reference":           row["annee_reference"],

        # Academic (from students)
        "nb_inscriptions":           stu.get("nb_inscriptions", safe_int(row["nb_etudiants_total"])),
        "taux_reussite":             stu.get("taux_reussite",   safe_float(row["taux_reussite_global"])),
        "taux_abandon":              stu.get("taux_abandon",    safe_float(row["taux_abandon_global"])),
        "gender_ratio":              stu.get("gender_ratio", 0.5),
        "moyenne_generale":          stu.get("moyenne_generale"),
        "taux_boursiers":            stu.get("taux_boursiers"),

        # Employment
        "taux_emploi":               safe_float(row["taux_emploi_diplomes"]),

        # Finance
        "budget_alloue_tnd":         safe_int(row["budget_alloue_tnd"]),
        "budget_execute_tnd":        safe_int(row["budget_execute_tnd"]),
        "budget_execute_pct":        safe_float(row["budget_execute_pct"]),

        # HR (from teachers)
        "nb_enseignants":            tch.get("nb_enseignants",    safe_int(row["nb_enseignants_total"])),
        "nb_administratifs":         safe_int(row["nb_personnels_admin"]),
        "taux_absenteisme_rh":       tch.get("taux_absenteisme_rh", 0.07),
        "heures_cours_moy":          tch.get("heures_cours_moy"),
        "taux_permanents":           tch.get("taux_permanents"),

        # Research
        "nb_publications":           tch.get("nb_publications_total", safe_int(row["nb_projets_recherche"])),
        "nb_projets_recherche":      safe_int(row["nb_projets_recherche"]),
        "financements_recherche_tnd":safe_int(row["financements_recherche_tnd"]),

        # Infrastructure
        "nb_salles":                 safe_int(row["nb_salles_cours"]),
        "nb_salles_informatique":    safe_int(row["nb_salles_informatique"]),
        "nb_equipements_info":       safe_int(row["nb_equipements_info"]),
        "surface_campus_m2":         safe_int(row["surface_campus_m2"]),

        # ESG
        "consommation_energie_kwh":  safe_int(row["consommation_energie_kwh"]),
        "taux_recyclage":            safe_float(row["taux_recyclage_pct"]),

        # Partnerships
        "nb_conventions_nationales": safe_int(row["nb_conventions_nationales"]),
        "nb_conventions_intl":       safe_int(row["nb_conventions_intl"]),
        "nb_etudiants_mobilite_out": safe_int(row["nb_etudiants_mobilite_out"]),
        "nb_etudiants_mobilite_in":  safe_int(row["nb_etudiants_mobilite_in"]),
    }
    records.append(record)

# ── POST to API ──────────────────────────────────────────────────────────
print(f"\n🚀 Sending {len(records)} KPI records to API...")
resp = requests.post(
    f"{BASE_URL}/internal/kpi/ingest",
    json={"records": records},
    headers={"X-Internal-Key": INTERNAL_KEY},
    timeout=15,
)

if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Ingested: {data['ingested']} records | Total stored: {data['total_stored']}")
else:
    print(f"❌ Error {resp.status_code}: {resp.text}")

# ── Verify with status check ─────────────────────────────────────────────
print("\n🔍 Checking internal status...")
status = requests.get(
    f"{BASE_URL}/internal/status",
    headers={"X-Internal-Key": INTERNAL_KEY},
    timeout=5,
)
print(f"   {status.json()}")
