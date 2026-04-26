"""
seed_mongo.py
──────────────
Seeds MongoDB with data from the CSV files + demo accounts + sample data
for grades, exams, courses, requests, and notifications.

Run: python seed_mongo.py
     python seed_mongo.py --force   (to reseed KPIs)
"""
import csv, sys, random, uuid
from datetime import datetime, timezone, timedelta
from db.mongo import get_db

def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

# ── Subject definitions per programme level ──────────────────────────────────
SUBJECTS_BY_LEVEL = {
    "L1": ["Mathématiques I", "Physique I", "Informatique I", "Anglais", "Français Technique"],
    "L2": ["Mathématiques II", "Algorithmique", "Bases de Données", "Réseaux", "Probabilités"],
    "L3": ["Génie Logiciel", "Systèmes d'Exploitation", "Intelligence Artificielle", "Projet de Fin d'Études", "Stage"],
    "M1": ["Machine Learning", "Big Data", "Sécurité Informatique", "Recherche Opérationnelle", "Méthodologie de Recherche"],
    "M2": ["Deep Learning", "Cloud Computing", "Mémoire de Recherche", "Stage PFE", "Entrepreneuriat"],
}

EXAM_TYPES = ["DS", "Examen", "TP"]

def seed():
    db = get_db()
    if db is None:
        print("❌ Cannot connect to MongoDB. Is it running on localhost:27017?")
        print("   Start with: docker run -d -p 27017:27017 --name mongo mongo:7")
        sys.exit(1)

    # 1. Students
    students = load_csv("data/students.csv")
    if db.students.count_documents({}) == 0:
        db.students.insert_many(students)
        print(f"✅ Inserted {len(students)} students")
    else:
        print(f"⏩ Students already seeded ({db.students.count_documents({})} records)")

    # 2. Teachers
    teachers = load_csv("data/teachers.csv")
    if db.teachers.count_documents({}) == 0:
        db.teachers.insert_many(teachers)
        print(f"✅ Inserted {len(teachers)} teachers")
    else:
        print(f"⏩ Teachers already seeded ({db.teachers.count_documents({})} records)")

    # 3. Administration → KPI records + institutions
    admin_rows = load_csv("data/administration.csv")

    force_reseed = "--force" in sys.argv
    if force_reseed:
        db.kpi_records.delete_many({})
        db.grades.delete_many({})
        db.exams.delete_many({})
        db.courses.delete_many({})
        db.student_requests.delete_many({})
        db.notifications.delete_many({})
        print("🗑️ Cleared existing data for re-seeding.")

    if db.kpi_records.count_documents({}) == 0:
        kpi_records = []
        for row in admin_rows:
            record = dict(row)
            record["date"] = f"{row['annee_budgetaire']}-01-01"
            budget_consomme = float(row.get('budget_execute_pct', 0.8)) * 1000000
            budget_alloue = budget_consomme / float(row.get('budget_execute_pct', 0.8)) if float(row.get('budget_execute_pct', 0.8)) > 0 else 1000000
            record["budget_alloue"] = round(budget_alloue, 2)
            record["budget_consomme"] = round(budget_consomme, 2)
            record["cout_par_etudiant"] = round(random.uniform(1500, 4500), 2)
            record["empreinte_carbone_tonnes"] = round(random.uniform(50, 500), 2)
            record["consommation_energie_kwh"] = round(random.uniform(10000, 150000), 2)
            record["taux_recyclage"] = round(random.uniform(0.1, 0.6), 2)
            kpi_records.append(record)
        db.kpi_records.insert_many(kpi_records)
        print(f"✅ Inserted {len(kpi_records)} KPI records")
    else:
        print(f"⏩ KPI records already seeded ({db.kpi_records.count_documents({})} records)")

    # 4. Institutions master
    if db.institutions.count_documents({}) == 0:
        institutions = [{"id": r["institution_id"], "name": r["institution_name"], "city": r["ville"]} for r in admin_rows]
        db.institutions.insert_many(institutions)
        print(f"✅ Inserted {len(institutions)} institutions")
    else:
        print(f"⏩ Institutions already seeded")

    # 5. User accounts
    from werkzeug.security import generate_password_hash

    def ensure_user(email, password, name, role, institution_id, user_id=None):
        if db.users.count_documents({"email": email}) == 0:
            db.users.insert_one({
                "id": user_id or str(uuid.uuid4()),
                "email": email,
                "password_hash": generate_password_hash(password),
                "name": name,
                "role": role,
                "institution_id": institution_id,
                "status": "approved",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            print(f"✅ Seeded {role}: {email} / {password}")
        else:
            print(f"⏩ {role} ({email}) already exists")

    ensure_user("admin@ucar.tn", "Admin@2025!", "UCAR Super Admin", "superucaradmin", None, "superadmin-001")
    ensure_user("admin@insat.tn", "Admin@2025!", "Admin INSAT", "institution_admin", "UCAR-INSAT", "instadmin-001")
    ensure_user("prof@ucar.tn", "Prof@2025!", "Dr. Ahmed Ben Salem", "teacher", "UCAR-INSAT", "teacher-001")

    # Find a real student from INSAT to create a login
    sample_student = db.students.find_one({"institution_id": "UCAR-INSAT"})
    if sample_student:
        student_name = f"{sample_student.get('prenom', 'Étudiant')} {sample_student.get('nom', 'Test')}"
        ensure_user("etudiant@ucar.tn", "Etud@2025!", student_name, "student", "UCAR-INSAT", f"student-{sample_student.get('student_id', '001')}")

    # 6. Seed grades for students
    if db.grades.count_documents({}) == 0:
        print("📝 Seeding grades...")
        grade_records = []
        insat_students = list(db.students.find({"institution_id": "UCAR-INSAT"}).limit(50))
        for stu in insat_students:
            niveau = stu.get("niveau", "L1")
            subjects = SUBJECTS_BY_LEVEL.get(niveau, SUBJECTS_BY_LEVEL["L1"])
            nb_absences = int(stu.get("nb_absences_s1", 0))

            for subject in subjects:
                abs_this_subject = random.randint(0, min(nb_absences, 6))
                eliminated = abs_this_subject > 3

                ds_note = round(random.uniform(0, 20), 2) if not eliminated else 0
                exam_note = round(random.uniform(0, 20), 2) if not eliminated else 0
                tp_note = round(random.uniform(5, 18), 2) if not eliminated else 0
                moyenne = round(ds_note * 0.3 + exam_note * 0.5 + tp_note * 0.2, 2) if not eliminated else 0

                grade_records.append({
                    "student_id": stu["student_id"],
                    "institution_id": "UCAR-INSAT",
                    "subject": subject,
                    "niveau": niveau,
                    "ds": ds_note,
                    "examen": exam_note,
                    "tp": tp_note,
                    "moyenne": moyenne,
                    "absences": abs_this_subject,
                    "eliminated": eliminated,
                    "semester": "S1",
                    "annee": "2023-2024",
                    "posted_by": "teacher-001",
                })

        if grade_records:
            db.grades.insert_many(grade_records)
            print(f"✅ Inserted {len(grade_records)} grade records")

    # 7. Seed exams
    if db.exams.count_documents({}) == 0:
        print("📅 Seeding exams...")
        exam_records = []
        now = datetime.now(timezone.utc)
        for niveau, subjects in SUBJECTS_BY_LEVEL.items():
            for subject in subjects:
                for exam_type in ["DS", "Examen"]:
                    exam_date = now + timedelta(days=random.randint(-30, 60))
                    exam_records.append({
                        "id": str(uuid.uuid4()),
                        "institution_id": "UCAR-INSAT",
                        "subject": subject,
                        "niveau": niveau,
                        "type": exam_type,
                        "date": exam_date.isoformat(),
                        "salle": f"Salle {random.choice(['A', 'B', 'C', 'D'])}{random.randint(1, 10)}",
                        "duree_minutes": 90 if exam_type == "Examen" else 60,
                        "created_by": "teacher-001",
                        "status": "past" if exam_date < now else "upcoming",
                    })
        db.exams.insert_many(exam_records)
        print(f"✅ Inserted {len(exam_records)} exam records")

    # 8. Seed courses
    if db.courses.count_documents({}) == 0:
        print("📚 Seeding courses...")
        course_records = []
        for niveau, subjects in SUBJECTS_BY_LEVEL.items():
            for subject in subjects:
                for i in range(random.randint(1, 4)):
                    course_records.append({
                        "id": str(uuid.uuid4()),
                        "institution_id": "UCAR-INSAT",
                        "subject": subject,
                        "niveau": niveau,
                        "title": f"Chapitre {i + 1} — {subject}",
                        "description": f"Support de cours pour {subject}, chapitre {i + 1}",
                        "file_type": random.choice(["pdf", "pptx", "docx"]),
                        "uploaded_by": "teacher-001",
                        "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    })
        db.courses.insert_many(course_records)
        print(f"✅ Inserted {len(course_records)} course records")

    # 9. Seed sample student requests
    if db.student_requests.count_documents({}) == 0 and sample_student:
        print("📄 Seeding student requests...")
        request_types = [
            ("Attestation de présence", "approved"),
            ("Attestation d'inscription", "pending"),
            ("Relevé de notes", "approved"),
        ]
        for req_type, status in request_types:
            db.student_requests.insert_one({
                "id": str(uuid.uuid4()),
                "student_id": sample_student["student_id"],
                "institution_id": "UCAR-INSAT",
                "type": req_type,
                "status": status,
                "message": f"Demande de {req_type.lower()} pour l'année 2023-2024",
                "admin_response": "Document disponible au secrétariat." if status == "approved" else None,
                "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat() if status != "pending" else None,
            })
        print(f"✅ Inserted {len(request_types)} student requests")

    # 10. Seed notifications
    if db.notifications.count_documents({}) == 0:
        print("🔔 Seeding notifications...")
        notifs = [
            {"user_id": "superadmin-001", "type": "system", "title": "Bienvenue sur UCAR Intel", "message": "La plateforme est opérationnelle. Consultez les KPIs globaux.", "read": False},
            {"user_id": "instadmin-001", "type": "system", "title": "Nouveau tableau de bord", "message": "Votre dashboard institutionnel est maintenant disponible.", "read": False},
            {"user_id": "teacher-001", "type": "system", "title": "Notes S1 à saisir", "message": "Veuillez saisir les notes du semestre 1 avant le 15 février.", "read": False},
            {"user_id": "instadmin-001", "type": "request", "title": "Nouvelle demande étudiante", "message": "Un étudiant a demandé une attestation de présence.", "read": False},
        ]
        if sample_student:
            stu_user_id = f"student-{sample_student.get('student_id', '001')}"
            notifs.extend([
                {"user_id": stu_user_id, "type": "grade", "title": "Notes publiées", "message": "Les notes de Mathématiques I ont été publiées.", "read": False},
                {"user_id": stu_user_id, "type": "request_status", "title": "Attestation approuvée", "message": "Votre attestation de présence est prête au secrétariat.", "read": False},
                {"user_id": stu_user_id, "type": "warning", "title": "Alerte absences", "message": "Attention : vous avez plus de 3 absences en Algorithmique.", "read": False},
            ])
        for n in notifs:
            n["id"] = str(uuid.uuid4())
            n["created_at"] = (datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 72))).isoformat()
        db.notifications.insert_many(notifs)
        print(f"✅ Inserted {len(notifs)} notifications")

    print(f"\n📊 MongoDB Summary:")
    print(f"   students:      {db.students.count_documents({})}")
    print(f"   teachers:      {db.teachers.count_documents({})}")
    print(f"   kpi_records:   {db.kpi_records.count_documents({})}")
    print(f"   institutions:  {db.institutions.count_documents({})}")
    print(f"   users:         {db.users.count_documents({})}")
    print(f"   grades:        {db.grades.count_documents({})}")
    print(f"   exams:         {db.exams.count_documents({})}")
    print(f"   courses:       {db.courses.count_documents({})}")
    print(f"   requests:      {db.student_requests.count_documents({})}")
    print(f"   notifications: {db.notifications.count_documents({})}")
    print(f"\n🔑 Login Accounts:")
    print(f"   Super Admin:    admin@ucar.tn / Admin@2025!")
    print(f"   Inst. Admin:    admin@insat.tn / Admin@2025!")
    print(f"   Teacher:        prof@ucar.tn / Prof@2025!")
    print(f"   Student:        etudiant@ucar.tn / Etud@2025!")

if __name__ == "__main__":
    seed()
