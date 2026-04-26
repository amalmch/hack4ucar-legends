"""
generate_ucar_data.py
─────────────────────
Generates 3 CSV files with realistic UCAR Tunisia example data:
  - data/students.csv      (~900 student records)
  - data/teachers.csv      (~380 teacher records)
  - data/administration.csv (~32 institution admin records)

Run: python generate_ucar_data.py
"""
import csv, random, uuid
from datetime import datetime, timedelta

random.seed(2025)

# ── UCAR Institutions (32 institutions provided by user) ─────────────
INSTITUTIONS = [
    ("UCAR-FSJPST", "Faculté des Sciences Juridiques, Politiques et Sociales de Tunis", "Tunis"),
    ("UCAR-FSB", "Faculté des Sciences de Bizerte", "Bizerte"),
    ("UCAR-FSEGN", "Faculté des Sciences Economiques et de Gestion de Nabeul", "Nabeul"),
    ("UCAR-ENAU", "Ecole Nationale d'Architecture et d'Urbanisme de Tunis", "Tunis"),
    ("UCAR-EPT", "Ecole Polytechnique de Tunisie", "Carthage"),
    ("UCAR-ESTI", "Ecole Supérieure de Technologie et d'Informatique à Carthage", "Carthage"),
    ("UCAR-ESSAI", "Ecole Supérieure des Statistiques et d'Analyse de l'Information", "Tunis"),
    ("UCAR-ESAC", "Ecole Supérieure de l'Audiovisuel et du Cinéma de Gammarth", "Gammarth"),
    ("UCAR-IPEIB", "Institut Préparatoire aux Etudes d'Ingénieur de Bizerte", "Bizerte"),
    ("UCAR-IHEC", "Institut des Hautes Etudes Commerciales de Carthage", "Carthage"),
    ("UCAR-INSAT", "Institut National des Sciences Appliquées et de Technologie", "Tunis"),
    ("UCAR-ISSATM", "Institut Supérieur des Sciences Appliquées et de la Technologie de Mateur", "Mateur"),
    ("UCAR-IPEIN", "Institut Préparatoire aux Etudes d'Ingénieur Nabeul", "Nabeul"),
    ("UCAR-IPEST", "Institut Préparatoire aux Etudes Scientifiques et Techniques de la Marsa", "La Marsa"),
    ("UCAR-ISBAN", "Institut Supérieur des Beaux Arts de Nabeul", "Nabeul"),
    ("UCAR-ISTEUB", "Institut Sup. des Technologies de l'Environnement, de L'Urbanisme et du Bâtiment", "Tunis"),
    ("UCAR-ISLT", "Institut Supérieur des Langues de Tunis", "Tunis"),
    ("UCAR-ISLAIN", "Institut Supérieur des Langues Appliquées et d'Informatique de Nabeul", "Nabeul"),
    ("UCAR-ISSTE", "Institut Sup. des Sciences et Technologies de l'Environnement de Borj Cédria", "Borj Cédria"),
    ("UCAR-ISCCB", "Institut Supérieur de Commerce et de Comptabilité de Bizerte", "Bizerte"),
    ("UCAR-ISEPBG", "Institut Sup. des Etudes Préparatoires en Biologie et Géologie à Soukra", "Soukra"),
    ("UCAR-SUPCOM", "Sup'Com", "Ariana"),
    ("UCAR-ESAM", "Ecole Supérieure d'Agriculture de Mograne", "Mograne"),
    ("UCAR-ESAMateur", "Ecole Supérieure d'Agriculture de Mateur", "Mateur"),
    ("UCAR-ESIAT", "Ecole Supérieure des Industries Alimentaires de Tunis", "Tunis"),
    ("UCAR-ISPA", "Institut Supérieur de Pêche et d'Aquaculture de Bizerte", "Bizerte"),
    ("UCAR-INTES", "Institut National du Travail et des Etudes Sociales de Tunis", "Tunis"),
    ("UCAR-ISCE", "Institut Supérieur des Cadres de l'Enfance", "Carthage"),
    ("UCAR-INAT", "Institut National Agronomique de Tunisie", "Tunis"),
    ("UCAR-IHET", "Institut des Hautes Etudes Touristiques de Sidi Dhrif", "Sidi Dhrif"),
    ("UCAR-INRGREF", "Institut National de Recherche en Génie Rural, Eau et Forêt", "Ariana"),
    ("UCAR-INRAT", "Institut National de Recherche Agronomique de Tunis", "Ariana"),
]

PROGRAMMES = {inst_id: ["Licence", "Master", "Cycle Ingénieur", "Doctorat"] for inst_id, _, _ in INSTITUTIONS}
# Specific overwrites for variety
PROGRAMMES["UCAR-INSAT"] = ["Génie Logiciel", "Réseaux et Télécoms", "Biologie Industrielle", "Chimie Industrielle"]
PROGRAMMES["UCAR-IHEC"] = ["Expertise Comptable", "Finance", "Marketing", "Management"]
PROGRAMMES["UCAR-ENAU"] = ["Architecture", "Urbanisme"]
PROGRAMMES["UCAR-ISLT"] = ["Anglais", "Français", "Italien", "Espagnol", "Chinois"]
PROGRAMMES["UCAR-INAT"] = ["Agronomie", "Génie Rural", "Production Animale", "Économie Rurale"]

NIVEAUX = ["L1", "L2", "L3", "M1", "M2"]
GENRES   = ["M", "F"]
VILLES   = ["Tunis", "Bizerte", "Nabeul", "Sousse", "Sfax", "Monastir", "Ariana", "Ben Arous", "Manouba", "Zaghouan"]

PRENOMS_M = ["Ahmed","Mohamed","Yassine","Anis","Rami","Hamza","Adam","Tarek","Bilel","Khaled","Sami","Nizar","Hedi","Mehdi"]
PRENOMS_F = ["Fatma","Mariem","Sarra","Ines","Amira","Nour","Salma","Rim","Asma","Lina","Hajer","Sirine","Maissa","Rania"]
NOMS      = ["Ben Ali","Trabelsi","Mzoughi","Khemiri","Belhaj","Chaari","Hamdi","Jebali","Mansouri","Oueslati","Dridi","Gafsi","Khlifi","Aloui","Sfaxi","Ayari","Baccouche","Zouaghi"]

def r(lo, hi, dec=2): return round(random.uniform(lo, hi), dec)
def ri(lo, hi): return random.randint(lo, hi)
def pick(lst): return random.choice(lst)

# ════════════════════════════════════════════════════════════════════════════
#  1. STUDENTS CSV
# ════════════════════════════════════════════════════════════════════════════
students = []
for inst_id, inst_name, city in INSTITUTIONS:
    n = ri(25, 35)
    for _ in range(n):
        genre = pick(GENRES)
        prenom = pick(PRENOMS_M if genre == "M" else PRENOMS_F)
        nom = pick(NOMS)
        niveau = pick(NIVEAUX)
        moy_s1 = r(7.0, 17.5)
        if random.random() < 0.08:
            moy_s1 = r(2.0, 6.5)
        moy_s2 = round(moy_s1 + r(-1.5, 2.0), 2)
        moy_s2 = max(0, min(20, moy_s2))
        nb_abs = ri(0, 12)
        if moy_s1 < 6: nb_abs = ri(15, 45)

        statut = "actif"
        if moy_s1 < 5 and nb_abs > 20: statut = "abandonne"
        elif niveau in ["L3","M2"] and moy_s1 >= 10: statut = pick(["actif","diplome"])

        students.append({
            "student_id":       f"ETU-{str(uuid.uuid4())[:8].upper()}",
            "nom":              nom,
            "prenom":           prenom,
            "genre":            genre,
            "institution_id":   inst_id,
            "institution_name": inst_name,
            "programme":        pick(PROGRAMMES[inst_id]),
            "niveau":           niveau,
            "annee_inscription":ri(2020, 2024),
            "ville_origine":    pick(VILLES),
            "boursier":         pick(["Oui","Non","Non","Non"]),
            "moyenne_s1":       moy_s1,
            "moyenne_s2":       moy_s2,
            "nb_absences_s1":   nb_abs,
            "nb_absences_s2":   ri(0, nb_abs + 3),
            "statut":           statut,
            "annee_academique": "2023-2024",
        })

with open("data/students.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(students[0].keys()))
    writer.writeheader()
    writer.writerows(students)
print(f"✅ students.csv — {len(students)} records")

# ════════════════════════════════════════════════════════════════════════════
#  2. TEACHERS CSV
# ════════════════════════════════════════════════════════════════════════════
GRADES      = ["Assistant", "Assistant B", "Maître Assistant A", "Maître Assistant B", "Maître de Conférences", "Professeur"]
SPECIALITES = ["Informatique","Mathématiques","Physique","Économie","Management","Droit","Langues","Génie Civil","Chimie","Biologie"]

teachers = []
for inst_id, inst_name, city in INSTITUTIONS:
    n = ri(10, 14)
    for _ in range(n):
        genre = pick(GENRES)
        prenom = pick(PRENOMS_M if genre=="M" else PRENOMS_F)
        anciennete = ri(1, 32)
        grade = GRADES[min(len(GRADES)-1, anciennete // 6)]
        heures = ri(192, 300)
        if random.random() < 0.07: heures = ri(320, 420)
        teachers.append({
            "teacher_id":           f"ENS-{str(uuid.uuid4())[:8].upper()}",
            "nom":                  pick(NOMS),
            "prenom":               prenom,
            "genre":                genre,
            "institution_id":       inst_id,
            "institution_name":     inst_name,
            "departement":          pick(PROGRAMMES[inst_id]),
            "grade":                grade,
            "specialite":           pick(SPECIALITES),
            "anciennete_ans":       anciennete,
            "nb_heures_cours_annee":heures,
            "nb_etudiants_encadres":ri(15, 85),
            "nb_publications_annee":ri(0, 8),
            "nb_projets_recherche": ri(0, 4),
            "nb_formations_suivies":ri(0, 5),
            "taux_absenteisme_pct": r(0.0, 0.12),
            "statut":               pick(["Permanent","Permanent","Permanent","Vacataire"]),
            "annee_academique":     "2023-2024",
        })

with open("data/teachers.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(teachers[0].keys()))
    writer.writeheader()
    writer.writerows(teachers)
print(f"✅ teachers.csv — {len(teachers)} records")

# ════════════════════════════════════════════════════════════════════════════
#  3. ADMINISTRATION CSV
# ════════════════════════════════════════════════════════════════════════════
admin_rows = []
for inst_id, inst_name, city in INSTITUTIONS:
    budget = ri(2_500_000, 15_000_000)
    execute_pct = r(0.55, 1.05)
    # Anomaly: INSAT over budget
    if inst_id == "UCAR-INSAT": execute_pct = 1.72
    admin_rows.append({
        "institution_id":            inst_id,
        "institution_name":          inst_name,
        "ville":                     city,
        "annee_budgetaire":          2024,
        "budget_alloue_tnd":         budget,
        "budget_execute_tnd":        round(budget * execute_pct),
        "budget_execute_pct":        execute_pct,
        "nb_personnels_admin":       ri(15, 80),
        "nb_enseignants_total":      ri(30, 180),
        "nb_etudiants_total":        ri(400, 4500),
        "nb_salles_cours":           ri(12, 60),
        "nb_amphitheatres":          ri(1, 8),
        "nb_salles_informatique":    ri(2, 12),
        "nb_equipements_info":       ri(40, 250),
        "surface_campus_m2":         ri(3000, 25000),
        "nb_conventions_nationales": ri(2, 18),
        "nb_conventions_intl":       ri(1, 12),
        "nb_projets_recherche":      ri(1, 20),
        "financements_recherche_tnd":ri(50_000, 800_000),
        "consommation_energie_kwh":  ri(80_000, 600_000),
        "taux_recyclage_pct":        r(0.05, 0.65),
        "nb_etudiants_mobilite_out": ri(0, 45),
        "nb_etudiants_mobilite_in":  ri(0, 30),
        "taux_reussite_global":      r(0.52, 0.92),
        "taux_abandon_global":       r(0.03, 0.28),
        "taux_emploi_diplomes":      r(0.45, 0.88),
        "annee_reference":           "2023-2024",
    })

with open("data/administration.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(admin_rows[0].keys()))
    writer.writeheader()
    writer.writerows(admin_rows)
print(f"✅ administration.csv — {len(admin_rows)} records")
