import streamlit as st
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from groq import Groq
import os
import datetime
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# 1. CONFIGURATION
# ─────────────────────────────────────────────
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

st.set_page_config(page_title="UCAR AI Assistant", page_icon="🏛️", layout="wide")

# ─────────────────────────────────────────────
# 2. SYSTEM PROMPT
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es l'assistant officiel de l'Université de Carthage (UCAR),
université publique tunisienne fondée en 1988, regroupant 32 établissements
d'enseignement supérieur et de recherche.

=== ÉTABLISSEMENTS ET ACRONYMES ===
- UCAR   : Université de Carthage (siège : Elghazala Technopark, Ariana)
- ISSTE  : Institut Supérieur des Sciences et Technologies de l'Environnement (Borj Cedria)
- INSAT  : Institut National des Sciences Appliquées et de Technologie (Tunis)
- IHEC   : Institut des Hautes Études Commerciales (Carthage)
- EPT    : École Polytechnique de Tunisie (La Marsa)
- IPEST  : Institut Préparatoire aux Études Scientifiques et Techniques (La Marsa)
- ESTI   : École Supérieure de Technologie et d'Informatique (Carthage)
- IPEIB  : Institut Préparatoire aux Études d'Ingénieur de Bizerte
- ESAC   : École Supérieure de l'Audiovisuel et du Cinéma (Gammarth)
- ESSAI  : École Supérieure des Statistiques et d'Analyse de l'Information (Tunis)
- ENAU   : École Nationale d'Architecture et d'Urbanisme (Tunis)
- INAT   : Institut National d'Agronomie de Tunis
- ISBAN  : Institut Supérieur des Beaux Arts (Nabeul)
- ISLT   : Institut Supérieur des Langues (Tunis)
- FSJPST : Faculté des Sciences Juridiques, Politiques et Sociales (Tunis)
- FSEGN  : Faculté des Sciences Économiques et de Gestion (Nabeul)
- SUP'COM: Ecole Supérieure des Communications de Tunis (Ariana)
- FSB    : Faculté des Sciences de Bizerte

=== RÈGLES DE RÉPONSE ===
1. Quand l'utilisateur écrit un sigle, résous-le TOUJOURS en son nom complet.
2. Utilise UNIQUEMENT le contexte fourni pour répondre. Si l'info manque dans
   le contexte, dis-le clairement et propose de contacter l'établissement.
3. Réponds en français. Si l'utilisateur écrit en arabe, réponds en arabe.
4. Sois précis, concis et professionnel.
5. Ne jamais inventer des informations non présentes dans le contexte.
"""

# ─────────────────────────────────────────────
# 3. EXPANSION DES ACRONYMES
# ─────────────────────────────────────────────
ACRONYMES = {
    "ISSTE":  "Institut Supérieur des Sciences et Technologies de l'Environnement de Borj Cedria",
    "INSAT":  "Institut National des Sciences Appliquées et de Technologie de Tunis",
    "IHEC":   "Institut des Hautes Études Commerciales de Carthage",
    "EPT":    "École Polytechnique de Tunisie de La Marsa",
    "IPEST":  "Institut Préparatoire aux Études Scientifiques et Techniques de La Marsa",
    "ESTI":   "École Supérieure de Technologie et d'Informatique de Carthage",
    "IPEIB":  "Institut Préparatoire aux Études d'Ingénieur de Bizerte",
    "ESAC":   "École Supérieure de l'Audiovisuel et du Cinéma de Gammarth",
    "ESSAI":  "École Supérieure des Statistiques et d'Analyse de l'Information de Tunis",
    "ENAU":   "École Nationale d'Architecture et d'Urbanisme de Tunis",
    "INAT":   "Institut National d'Agronomie de Tunis",
    "ISBAN":  "Institut Supérieur des Beaux Arts de Nabeul",
    "ISLT":   "Institut Supérieur des Langues de Tunis",
    "UCAR":   "Université de Carthage",
    "FSJPST": "Faculté des Sciences Juridiques, Politiques et Sociales de Tunis",
    "FSB":    "Faculté des Sciences de Bizerte",
    "SUPCOM": "Ecole Supérieure des Communications de Tunis",
}


def enrichir_query(question: str) -> str:
    extras = []
    for sigle, nom in ACRONYMES.items():
        if sigle in question.upper():
            extras.append(f"{sigle} = {nom}")
    if extras:
        question = question + " [" + ", ".join(extras) + "]"
    return question


# ─────────────────────────────────────────────
# 4. CSS NEUMORPHIQUE
# ─────────────────────────────────────────────
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #e8edf4; }
    .header-card {
        background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
        padding: 28px 36px; border-radius: 20px;
        box-shadow: 0 10px 40px rgba(30,58,138,0.35);
        text-align: center; margin-bottom: 32px;
        color: white;
    }
    .stChatMessage {
        background: #e8edf4 !important; border-radius: 20px !important;
        box-shadow: 7px 7px 14px #c5cad0, -7px -7px 14px #ffffff !important;
        border: none !important; margin-bottom: 20px; padding: 16px;
    }
    [data-testid="stSidebar"] { background-color: #dde3ec !important; }
    .stButton>button {
        width: 100%; background: linear-gradient(135deg, #1e3a8a, #2563eb);
        color: white; font-weight: 700; border: none; border-radius: 12px;
        padding: 10px; transition: 0.2s; box-shadow: 0 4px 14px rgba(30,58,138,0.4);
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(30,58,138,0.5); }
    .score-badge {
        display: inline-block; padding: 2px 8px; border-radius: 12px;
        font-size: 11px; font-weight: 600; margin-left: 6px;
    }
    .score-high { background: #d1fae5; color: #065f46; }
    .score-low  { background: #fee2e2; color: #991b1b; }
    </style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 5. BACKEND
# ─────────────────────────────────────────────
@st.cache_resource
def load_system():
    os.makedirs("chatbot_data", exist_ok=True)
    db_client  = chromadb.PersistentClient(path="chroma_db")
    emb_fn     = DefaultEmbeddingFunction()
    collection = db_client.get_or_create_collection(
        name="ucar_docs", embedding_function=emb_fn
    )
    groq_client = Groq(api_key=GROQ_API_KEY)
    return collection, groq_client


collection, groq_client = load_system()


def learn_fact(fact: str) -> bool:
    try:
        fact_id = f"learned_{datetime.datetime.now().timestamp()}"
        collection.add(documents=[fact], ids=[fact_id],
                       metadatas=[{"source": "user_input"}])
        log_path = "chatbot_data/learning_logs.txt"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now()}] {fact}\n")
        return True
    except Exception as e:
        st.error(f"Erreur d'apprentissage : {e}")
        return False


def get_response(prompt: str, history: list) -> tuple:
    query_enrichie = enrichir_query(prompt)

    results = collection.query(
        query_texts=[query_enrichie],
        n_results=5,
        include=["documents", "distances", "metadatas"]
    )

    docs      = results["documents"][0] if results["documents"] else []
    distances = results["distances"][0]  if results.get("distances") else []
    metas     = results["metadatas"][0]  if results.get("metadatas") else []

    filtered = [
        (doc, dist, meta)
        for doc, dist, meta in zip(docs, distances, metas)
        if dist < 1.2
    ]

    contexte = "\n\n---\n\n".join([d for d, _, _ in filtered]) if filtered else ""

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if contexte:
        messages.append({
            "role": "system",
            "content": f"=== CONTEXTE BASE DE CONNAISSANCES ===\n{contexte}\n=== FIN DU CONTEXTE ==="
        })
    for msg in history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    chat = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.1,
        max_tokens=1024,
    )
    return chat.choices[0].message.content, contexte, filtered


# ─────────────────────────────────────────────
# 6. INTERFACE
# ─────────────────────────────────────────────
st.markdown("""
    <div class="header-card">
        <h1 style="margin:0; font-size:1.8rem;">🏛️ CARTHAGE AI-SPACE</h1>
        <p style="margin:6px 0 0; opacity:0.85; font-weight:600;">
            Assistant Virtuel de l'Université de Carthage — UCAR Intel Platform
        </p>
    </div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<h2 style='color:#1e3a8a;'>⚙️ Control Panel</h2>", unsafe_allow_html=True)
    st.write(f"📅 **Date :** {datetime.date.today().strftime('%d/%m/%Y')}")
    st.write(f"📂 **Mémoire :** {collection.count()} segments")

    st.markdown("---")
    st.subheader("🧠 Apprentissage continu")
    new_data = st.text_area(
        "Enseigner une nouvelle information :",
        placeholder="Ex: L'INSAT a ouvert un nouveau master en IA en 2024..."
    )
    if st.button("➕ Injecter dans la mémoire de l'IA"):
        if new_data and learn_fact(new_data):
            st.success("✅ Information mémorisée !")
            st.balloons()
        elif not new_data:
            st.warning("Veuillez saisir une information.")

    st.markdown("---")
    if st.button("🗑️ Nouvelle conversation"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.caption("Powered by Groq · LLaMA 3.3 70B · ChromaDB · UCAR Intel")

# ─────────────────────────────────────────────
# 7. ZONE DE CHAT
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Posez votre question sur l'UCAR, ses établissements, formations..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Recherche dans la base de connaissances UCAR..."):
            response, contexte, sources = get_response(
                prompt,
                st.session_state.messages[:-1]
            )
            st.markdown(response)

            if sources:
                with st.expander("🔍 Sources consultées"):
                    for i, (doc, dist, meta) in enumerate(sources, 1):
                        score_pct = max(0, round((1 - dist / 2) * 100))
                        badge_cls = "score-high" if score_pct >= 60 else "score-low"
                        src_name = meta.get("source", "base UCAR") if meta else "base UCAR"
                        st.markdown(
                            f"**Source {i}** — `{src_name}` "
                            f"<span class='score-badge {badge_cls}'>Pertinence : {score_pct}%</span>",
                            unsafe_allow_html=True
                        )
                        st.caption(doc[:300] + "..." if len(doc) > 300 else doc)
                        if i < len(sources):
                            st.divider()
            else:
                st.info("ℹ️ Réponse basée sur les connaissances générales.")

    st.session_state.messages.append({"role": "assistant", "content": response})
