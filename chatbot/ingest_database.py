# -*- coding: utf-8 -*-
"""
chatbot/ingest_database.py
──────────────────────────
Ingère les fichiers PDF/TXT du dossier chatbot_data/ dans ChromaDB.
Améliorations :
  - Chunks intelligents avec chevauchement
  - Injection d'un glossaire des acronymes UCAR
  - Encodage acronymes enrichi dans chaque chunk
NOTE: Pour l'encodage des caractères, utilisez PYTHONIOENCODING=utf-8
"""
import os
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


ACRONYMES_UCAR = {
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
    "UCAR":   "Université de Carthage",
    "INAT":   "Institut National d'Agronomie de Tunis",
    "IPEIG":  "Institut Préparatoire aux Études d'Ingénieur Nabeul",
    "ISBAN":  "Institut Supérieur des Beaux Arts de Nabeul",
    "ISLT":   "Institut Supérieur des Langues de Tunis",
    "SUPCOM": "Ecole Supérieure des Communications de Tunis",
    "FSB":    "Faculté des Sciences de Bizerte",
    "FSJPST": "Faculté des Sciences Juridiques, Politiques et Sociales de Tunis",
}


def chunk_text(text, chunk_size=800, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            for sep in [". ", ".\n", "\n\n", "\n", " "]:
                pos = text.rfind(sep, start, end)
                if pos > start + overlap:
                    end = pos + 1
                    break
        chunk = text[start:end].strip()
        if len(chunk) > 50:
            chunks.append(chunk)
        start = end - overlap
    return chunks


def enrichir_avec_acronymes(text):
    lignes_extra = []
    text_upper = text.upper()
    for sigle, definition in ACRONYMES_UCAR.items():
        if sigle in text_upper:
            lignes_extra.append(f"{sigle} signifie {definition}.")
    if lignes_extra:
        text = "\n".join(lignes_extra) + "\n\n" + text
    return text


def ingest():
    client = chromadb.PersistentClient(path="chroma_db")
    emb_fn = DefaultEmbeddingFunction()

    try:
        client.delete_collection("ucar_docs")
        print("[OK] Ancienne collection supprimee")
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name="ucar_docs",
        embedding_function=emb_fn,
        metadata={"hnsw:space": "cosine"},
    )

    # Inject acronym glossary as a dedicated document
    glossaire = "Glossaire des établissements de l'Université de Carthage (UCAR) :\n"
    for sigle, definition in ACRONYMES_UCAR.items():
        glossaire += f"- {sigle} : {definition}\n"

    collection.add(
        documents=[glossaire],
        ids=["glossaire_acronymes_ucar"],
        metadatas=[{"source": "glossaire", "type": "reference"}],
    )
    print("[OK] Glossaire des acronymes injete")

    data_dir = "chatbot_data"
    os.makedirs(data_dir, exist_ok=True)
    total_chunks = 0

    for filename in os.listdir(data_dir):
        path = os.path.join(data_dir, filename)
        content = ""

        if filename.endswith(".pdf"):
            try:
                from pypdf import PdfReader
                reader = PdfReader(path)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        content += page_text + "\n"
            except Exception as e:
                print(f"[WARN] Erreur PDF {filename}: {e}")
                continue
        elif filename.endswith(".txt"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                print(f"[WARN] Erreur TXT {filename}: {e}")
                continue
        else:
            continue

        if not content.strip():
            print(f"[WARN] Fichier vide ignore : {filename}")
            continue

        content = enrichir_avec_acronymes(content)
        chunks = chunk_text(content, chunk_size=800, overlap=200)

        ids       = [f"{filename}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"source": filename, "chunk_index": i} for i in range(len(chunks))]

        batch_size = 50
        for b in range(0, len(chunks), batch_size):
            collection.add(
                documents=chunks[b : b + batch_size],
                ids=ids[b : b + batch_size],
                metadatas=metadatas[b : b + batch_size],
            )

        total_chunks += len(chunks)
        print(f"[OK] {filename} -> {len(chunks)} chunks")

    print(f"\n[DONE] Ingestion terminee : {total_chunks} chunks dans ChromaDB")


if __name__ == "__main__":
    ingest()
