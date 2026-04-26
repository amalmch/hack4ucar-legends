"""
api/routes/ai_routes.py
────────────────────────
Routes IA : Insights prédictifs, détection d'anomalies, et Chatbot NLP.
Combine les insights mockés pour le hackathon avec de vrais résultats
du moteur KPI MongoDB quand les données existent.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from loguru import logger
import random

ai_bp = Blueprint("ai", __name__)

# ── Insights statiques (démonstration hackathon) ─────────────────────────────

INSIGHTS_DB = [
    {
        "id": "ins-001",
        "type": "anomaly",
        "severity": "critical",
        "title": "Taux d'abandon anormalement élevé détecté",
        "description": "L'IA prédictive indique une probabilité de 82% d'abandon au semestre 2 pour la filière Informatique à l'INSAT en raison d'un pic d'absentéisme.",
        "action_recommended": "Organiser une session de tutorat d'urgence.",
        "institution_id": "UCAR-INSAT"
    },
    {
        "id": "ins-002",
        "type": "prediction",
        "severity": "warning",
        "title": "Dépassement de budget énergétique",
        "description": "Si la tendance actuelle se maintient, la Faculté des Sciences de Bizerte dépassera son budget énergétique de 15% d'ici fin novembre.",
        "action_recommended": "Lancer une campagne de sensibilisation et vérifier l'isolation des bâtiments C et D.",
        "institution_id": "UCAR-FSB"
    },
    {
        "id": "ins-003",
        "type": "opportunity",
        "severity": "info",
        "title": "Optimisation des ressources pédagogiques",
        "description": "Il y a un décalage entre le nombre d'heures d'enseignement disponibles et la charge des étudiants à Sup'Com. Possibilité de libérer 3 salles de TD.",
        "action_recommended": "Revoir la planification des salles pour le semestre de printemps.",
        "institution_id": "UCAR-SUPCOM"
    },
    {
        "id": "ins-004",
        "type": "prediction",
        "severity": "success",
        "title": "Amélioration globale de l'employabilité",
        "description": "Les données du dernier trimestre montrent une augmentation prévue de 4% du taux d'emploi post-diplôme pour les filières ingénierie.",
        "action_recommended": "Continuer les partenariats avec le pôle technologique.",
        "institution_id": "global"
    }
]


@ai_bp.get("/insights")
@jwt_required()
def get_insights():
    """
    Retourne les insights IA : combine les alertes mockées
    avec de vraies détections d'anomalies du KPI engine.
    """
    claims = get_jwt()
    role = claims.get("role")
    req_inst_id = request.args.get("institution_id")
    inst_id = req_inst_id or claims.get("institution_id")

    # Start with mocked insights
    if role == "superucaradmin" and not req_inst_id:
        results = [i for i in INSIGHTS_DB if i["institution_id"] == "global" or random.random() > 0.5]
    else:
        results = [i for i in INSIGHTS_DB if i["institution_id"] == inst_id or i["institution_id"] == "global"]

    # Enrich with real KPI engine analysis
    try:
        from ai_models.kpi_engine import run_realtime_analysis
        target_id = inst_id if inst_id else "UCAR-INSAT"
        if target_id and target_id != "global":
            analysis = run_realtime_analysis(target_id)
            # Convert real anomaly alerts into insight format
            for alerte in analysis.get("alertes", []):
                severity = "critical" if alerte["niveau"] == "critical" else "warning"
                results.append({
                    "id": f"real-{alerte['kpi_nom']}-{random.randint(100,999)}",
                    "type": "anomaly",
                    "severity": severity,
                    "title": f"Seuil franchi : {alerte['kpi_nom']}",
                    "description": f"La valeur actuelle de {alerte['kpi_nom']} ({alerte['valeur']}) a franchi le seuil {alerte['niveau']} de {alerte['seuil']}.",
                    "action_recommended": "Vérifier les données et prendre les mesures correctives.",
                    "institution_id": target_id,
                })
    except Exception as e:
        logger.debug(f"KPI engine enrichment skipped: {e}")

    return jsonify({"insights": results, "count": len(results)})


@ai_bp.get("/analyse/<institution_id>")
@jwt_required()
def analyse_kpi(institution_id):
    """
    Analyse KPI temps réel complète pour une institution.
    Retourne snapshot, agrégats par domaine, anomalies et alertes.
    """
    claims = get_jwt()
    role = claims.get("role")
    if role not in ("institution_admin", "superucaradmin"):
        return jsonify({"error": "Accès non autorisé"}), 403

    periode = request.args.get("periode")

    try:
        from ai_models.kpi_engine import run_realtime_analysis
        result = run_realtime_analysis(institution_id, periode)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Erreur analyse KPI : {e}")
        return jsonify({"error": str(e)}), 500


@ai_bp.post("/chat")
@jwt_required(optional=True)
def chat_with_bot():
    """
    Chatbot IA contextuel. Interroge ChromaDB pour le contexte
    et utilise Groq (LLaMA 3) pour générer la réponse.
    """
    data = request.get_json() or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"response": "Veuillez poser une question."})

    try:
        import os
        import chromadb
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        from groq import Groq
        from dotenv import load_dotenv

        # Absolute path to chroma_db
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        chroma_path = os.path.join(base_dir, "chatbot", "chroma_db")
        env_path = os.path.join(base_dir, "chatbot", ".env")

        GROQ_API_KEY = None
        try:
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("GROQ_API_KEY="):
                        GROQ_API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception as e:
            logger.error(f"Could not read .env file: {e}")

        logger.debug(f"Groq API Key loaded manually: {'Yes' if GROQ_API_KEY else 'No'}")
        if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
            return jsonify({"response": "Clé API Groq manquante dans la configuration."})
            
        groq_client = Groq(api_key=GROQ_API_KEY)
        
        db_client = chromadb.PersistentClient(path=chroma_path)
        emb_fn = DefaultEmbeddingFunction()
        collection = db_client.get_or_create_collection(name="ucar_docs", embedding_function=emb_fn)
        
        # 1. Retrieve context
        results = collection.query(
            query_texts=[message],
            n_results=3
        )
        
        context = ""
        if results and results['documents'] and results['documents'][0]:
            context = "\n\n".join(results['documents'][0])
            
        # 2. Build Prompt
        system_prompt = f"""Tu es l'Assistant IA officiel de l'Université de Carthage (UCAR).
Tu dois répondre en français de manière professionnelle, claire, et très concise (quelques phrases maximum).
Tu peux utiliser du formatage Markdown (gras, listes) pour rendre la réponse lisible.
Si on te dit bonjour, présente-toi poliment en une phrase.
Utilise le contexte suivant pour répondre avec précision à la question. Si la réponse ne s'y trouve pas, réponds avec tes connaissances générales de manière utile sans dire explicitement que ce n'est pas dans le contexte.

Contexte UCAR:
{context}"""

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.3,
            max_tokens=512
        )
        
        response_text = completion.choices[0].message.content
        return jsonify({"response": response_text})

    except Exception as e:
        logger.error(f"Erreur IA Chatbot: {e}")
        return jsonify({"response": "Désolé, une erreur technique est survenue lors du traitement de votre requête. Veuillez réessayer plus tard."})

